"""Crafter an der allgemeinen Schnittstelle (ab 0.18).

Crafter (Hafner 2021) ist ein kleines 2D-Minecraft: Holz sammeln, eine Werkbank bauen,
Werkzeuge herstellen, Stein, Kohle, Eisen und Diamanten abbauen, essen, trinken, schlafen und
Zombies abwehren. Es gibt 22 Erfolge. Gemessen wird, wie viele davon ein Agent in einer
Runde schafft.

Was der Agent bekommt, sind nur Zahlen, in einer Reihenfolge, die jeder Startwert neu mischt:
- **Sicht:** die 9 × 7 Felder um die Figur, je Feld eine Nummer für das, was dort ist. Das
  ist Crafters eigene „semantische“ Karte. Es ist geschenkte Wahrnehmung: Aus Pixeln
  müsste der Agent das erst lernen (siehe docs/CRAFTER.md).
- **Vorne:** die Nummer des Felds, auf das die Figur schaut. Darauf wirken Crafters
  Handlungen (abbauen, trinken, angreifen, bauen). In Minecraft ist das der Block im
  Fadenkreuz; im Bild von Crafter sieht man es an der Blickrichtung der Figur. Ohne diese
  Zahl müsste der Agent erst lernen, dass Blickrichtung und Nachbarfeld zusammengehören.
- **Körper:** die 16 Werte des Inventars (darunter Gesundheit, Hunger, Durst, Müdigkeit),
  die Blickrichtung als zwei Zahlen, ob die Figur schläft, und ihre Position. Auch das zeigt
  Crafter im Bild an.
- **Tasten:** Crafters 17 Tasten, gemischt, ohne Namen.
- **Ziel erreicht:** Crafter meldet einen Erfolg, den es in dieser Runde noch nicht gab.
  Mehr nicht: keine eigene Belohnung, keine Liste der Erfolge.

`least_steps` gibt es in Crafter nicht; der Adapter gibt 0 zurück (nur für Messungen der
anderen Welten gebraucht).
"""

import random
from dataclasses import dataclass, field
from typing import Any, Final

import crafter
import numpy as np

from hekmatki.general.env import Observation, Outcome, Wiring

VIEW_WIDTH: Final = 9
VIEW_HEIGHT: Final = 7
ACTIONS: Final = 17
INVENTORY: Final = 16
WIDTH: Final = VIEW_WIDTH * VIEW_HEIGHT + 1 + INVENTORY + 2 + 1 + 2
"""Sicht, vorne, Inventar, Blickrichtung, Schlaf, Position."""
LENGTH: Final = 10_000
"""Längste Runde in Crafter."""
ITEMS: Final = tuple(crafter.constants.items)
"""Die Namen der Inventarwerte, in Crafters Reihenfolge."""
MATERIALS: Final = (
    "",
    *crafter.constants.materials,
    "player",
    "cow",
    "zombie",
    "skeleton",
    "arrow",
    "plant",
)
"""Was die Nummern in Sicht und „vorne“ bedeuten (0: außerhalb der Karte)."""


@dataclass
class CrafterWorld:
    """Eine Crafter-Welt mit fester Mischung; jede Runde ist eine neue Karte."""

    seed: int
    length: int = LENGTH
    wiring: Wiring = field(init=False)
    finished: bool = field(default=True, init=False)
    """Ist die Runde vorbei (Figur gestorben oder Zeit um)? Nur für die Messung, nicht für den
    Agenten."""
    unlocked: list[tuple[int, str]] = field(default_factory=list, init=False)
    """Die Erfolge dieser Runde mit ihrem Schritt (nur für die Messung)."""

    def __post_init__(self) -> None:
        self.wiring = Wiring.shuffled(WIDTH, ACTIONS, random.Random(self.seed))
        self._env = crafter.Env(length=self.length, seed=self.seed)
        self._steps = 0

    @property
    def actions(self) -> int:
        """Anzahl der Tasten."""
        return ACTIONS

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde auf einer neuen Karte."""
        self._env.reset()
        self.finished, self.unlocked, self._steps = False, [], 0
        _, _, _, info = self._env.step(0)  # Crafter gibt die Karte erst nach einem Schritt.
        return self._observe(info)

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Drückt eine Taste."""
        if self.finished:
            raise RuntimeError("Die Runde ist vorbei; erst `reset` aufrufen.")
        before = {name for _, name in self.unlocked}
        _, _, done, info = self._env.step(self.wiring.inner_action(action))
        self._steps += 1
        new = sorted(
            name for name, count in info["achievements"].items() if count and name not in before
        )
        self.unlocked += [(self._steps, name) for name in new]
        self.finished = bool(done)
        return Outcome(self._observe(info), bool(new))

    def names(self) -> tuple[list[str], list[str]]:
        """Was jede Zahl und jede Taste in Wahrheit ist, in der gemischten Reihenfolge, die der
        Agent sieht. Nur für Seiten und Auswertung; der Agent bekommt das nie."""
        view = [
            f"Sicht {x - VIEW_WIDTH // 2:+d},{y - VIEW_HEIGHT // 2:+d}"
            for y in range(VIEW_HEIGHT)
            for x in range(VIEW_WIDTH)
        ]
        inner = [*view, "vorne", *ITEMS, "Blick x", "Blick y", "schläft", "Ort x", "Ort y"]
        components = [inner[i] for i in self.wiring.components]
        actions = [crafter.constants.actions[i] for i in self.wiring.actions]
        return components, actions

    def least_steps(self) -> int:
        """Gibt es in Crafter nicht."""
        return 0

    def _observe(self, info: dict[str, Any]) -> Observation:
        x, y = (int(v) for v in info["player_pos"])
        semantic = np.pad(info["semantic"], VIEW_WIDTH)
        left, top = x + VIEW_WIDTH - VIEW_WIDTH // 2, y + VIEW_WIDTH - VIEW_HEIGHT // 2
        view = semantic[left : left + VIEW_WIDTH, top : top + VIEW_HEIGHT]
        player = self._env._player  # Blickrichtung und Schlaf zeigt Crafter nur im Bild.
        dx, dy = (int(v) for v in player.facing)
        front = semantic[x + VIEW_WIDTH + dx, y + VIEW_WIDTH + dy]
        inner = [
            *(int(v) for v in view.T.flatten()),
            int(front),
            *(int(v) for v in info["inventory"].values()),
            dx,
            dy,
            int(player.sleeping),
            x,
            y,
        ]
        return self.wiring.observe(inner)
