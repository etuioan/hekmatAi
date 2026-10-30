"""Minecraft an der allgemeinen Schnittstelle (nach 0.20).

Minecraft ist die offene 3D-Welt, die Crafter im Kleinen nachbaut. Der Agent spielt es über
eine Brücke (`minecraft_bridge/bridge.js`): einen Spieler-Client mit Mineflayer, der mit einem
Minecraft-Server spricht. Ein Server braucht weder Grafikkarte noch Bildschirm.

Wie bei Crafter bekommt der Agent nur Zahlen, in einer Reihenfolge, die jeder Startwert neu
mischt, und Tasten ohne Namen:
- **Sicht:** die Blöcke in einem Würfel von 5 × 5 Feldern in drei Höhen um die Figur (unter den
  Füßen, Füße, Kopf), je Block eine Nummer. Das ist geschenkte Wahrnehmung wie Crafters
  semantische Karte; im Bild müsste der Agent sie erst sehen lernen.
- **Wesen:** je Feld der 5 × 5 Felder die Nummer eines Tiers, Monsters oder liegenden Dings.
- **Im Blick:** der Block im Fadenkreuz und das Wesen im Fadenkreuz. Darauf wirken „angreifen“
  und „benutzen“.
- **Körper:** die neun Fächer der Schnellleiste (Ding und Anzahl), das gewählte Fach, Leben,
  Hunger, Blickrichtung, Position und die Tageszeit. All das zeigt Minecraft im Bild an.
- **Tasten:** laufen, springen, drehen, hoch und runter schauen, angreifen (abbauen oder
  schlagen), benutzen (setzen, essen, öffnen), Fach wechseln und neun Rezepte. Die Rezepte
  entsprechen Crafters Tasten „make_wood_pickaxe“ und so weiter: Was eine Taste herstellt und
  was dafür nötig ist, muss der Agent selbst herausfinden.
- **Ziel erreicht:** Minecraft meldet einen neuen Fortschritt (Advancement). Das ist das
  Signal des Spiels selbst. Keine eigene Belohnung, keine Liste der Fortschritte.

Die Brücke kennt Minecraft; dieser Adapter kennt nur die Brücke; der Agent kennt keins von
beiden. Die Verbindung ist austauschbar (`Connection`), damit Tests ohne Server laufen.
"""

import json
import random
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Protocol

from hekmatki.general.env import Observation, Outcome, Wiring

LENGTH: Final = 2000
"""Längste Runde in Schritten. Ein Schritt dauert etwa ein Viertel einer Sekunde Spielzeit,
eine Runde also etwa acht Minuten (ein Minecraft-Tag hat zwanzig)."""
BRIDGE: Final = Path(__file__).with_name("minecraft_bridge") / "bridge.js"

type Message = dict[str, Any]


class Connection(Protocol):
    """Die Leitung zur Brücke: ein Befehl hin, eine Antwort zurück."""

    @property
    def layout(self) -> tuple[str, ...]:
        """Was jede Zahl der inneren Beobachtung ist (nur für Seiten und Auswertung)."""
        ...

    @property
    def action_names(self) -> tuple[str, ...]:
        """Was jede innere Handlung ist (nur für Seiten und Auswertung)."""
        ...

    def request(self, message: Message) -> Message:
        """Schickt einen Befehl und wartet auf die Antwort."""
        ...

    def close(self) -> None:
        """Beendet die Verbindung."""
        ...


class BridgeProcess:
    """Startet `bridge.js` mit Node und spricht über JSON-Zeilen mit ihr."""

    def __init__(
        self, host: str = "localhost", port: int = 25565, username: str = "hekmat"
    ) -> None:
        command = ["node", str(BRIDGE), "--host", host, "--port", str(port)]
        self._process = subprocess.Popen(
            [*command, "--username", username],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        ready = self._read()
        self._layout = tuple(str(name) for name in ready["layout"])
        self._actions = tuple(str(name) for name in ready["actions"])

    @property
    def layout(self) -> tuple[str, ...]:
        """Was jede Zahl ist, wie die Brücke es meldet."""
        return self._layout

    @property
    def action_names(self) -> tuple[str, ...]:
        """Was jede Handlung ist, wie die Brücke es meldet."""
        return self._actions

    def request(self, message: Message) -> Message:
        """Eine Zeile hin, eine Zeile zurück."""
        assert self._process.stdin is not None
        self._process.stdin.write(json.dumps(message) + "\n")
        self._process.stdin.flush()
        return self._read()

    def close(self) -> None:
        """Bittet die Brücke, sich abzumelden, und wartet auf ihr Ende."""
        if self._process.poll() is None:
            assert self._process.stdin is not None
            self._process.stdin.write(json.dumps({"op": "close"}) + "\n")
            self._process.stdin.close()
            self._process.wait(timeout=30)

    def _read(self) -> Message:
        assert self._process.stdout is not None
        line = self._process.stdout.readline()
        if not line:
            raise ConnectionError(f"Die Brücke ist beendet (Code {self._process.poll()}).")
        try:
            answer: Message = json.loads(line)
        except json.JSONDecodeError as error:
            raise ConnectionError(f"Die Brücke hat keine JSON-Zeile geschickt: {line!r}") from error
        if "error" in answer:
            raise RuntimeError(f"Fehler in der Brücke: {answer['error']}")
        return answer


@dataclass
class MinecraftWorld:
    """Minecraft mit fester Mischung; jede Runde beginnt an einem neuen Ort der Welt."""

    seed: int
    connection: Connection
    length: int = LENGTH
    wiring: Wiring = field(init=False)
    finished: bool = field(default=True, init=False)
    """Ist die Runde vorbei (Figur gestorben oder Zeit um)? Nur für die Messung, nicht für den
    Agenten."""
    unlocked: list[tuple[int, str]] = field(default_factory=list, init=False)
    """Die Fortschritte dieser Runde mit ihrem Schritt (nur für die Messung)."""

    def __post_init__(self) -> None:
        width, actions = len(self.connection.layout), len(self.connection.action_names)
        self.wiring = Wiring.shuffled(width, actions, random.Random(self.seed))
        self._steps = 0
        self._rounds = 0

    @property
    def actions(self) -> int:
        """Anzahl der Tasten."""
        return len(self.connection.action_names)

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde: leeres Inventar, volles Leben, ein neuer Ort, keine Fortschritte."""
        self._rounds += 1
        answer = self.connection.request({"op": "reset", "seed": self.seed * 1000 + self._rounds})
        self.finished, self.unlocked, self._steps = False, [], 0
        return self._observe(answer)

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Drückt eine Taste."""
        if self.finished:
            raise RuntimeError("Die Runde ist vorbei; erst `reset` aufrufen.")
        answer = self.connection.request({"op": "step", "action": self.wiring.inner_action(action)})
        self._steps += 1
        before = {name for _, name in self.unlocked}
        new = sorted({str(name) for name in answer["advancements"]} - before)
        self.unlocked += [(self._steps, name) for name in new]
        self.finished = bool(answer["dead"]) or self._steps >= self.length
        return Outcome(self._observe(answer), bool(new))

    def names(self) -> tuple[list[str], list[str]]:
        """Was jede Zahl und jede Taste in Wahrheit ist, in der gemischten Reihenfolge, die der
        Agent sieht. Nur für Seiten und Auswertung; der Agent bekommt das nie."""
        components = [self.connection.layout[i] for i in self.wiring.components]
        actions = [self.connection.action_names[i] for i in self.wiring.actions]
        return components, actions

    def least_steps(self) -> int:
        """Gibt es in Minecraft nicht."""
        return 0

    def _observe(self, answer: Message) -> Observation:
        return self.wiring.observe([int(value) for value in answer["inner"]])
