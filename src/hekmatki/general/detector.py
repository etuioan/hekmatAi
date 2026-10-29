"""Eine neue Umgebung erkennen (ab 0.16, H18).

Der Agent hat für jede Umgebung, die er kennt, eine eigene Karte (`Knowledge`). Nach jedem
Schritt fragt er: Passt das noch zu meiner jetzigen Karte? Drei Antworten werden verglichen:

- **jede Überraschung**: Liegt eine verlässliche Regel daneben, ist das eine andere Umgebung.
  Er wechselt zu einer Karte, die den Schritt erklärt, oder legt eine neue an.
- **nie neue Karte**: Es gibt nur eine Karte. Bei unerwarteter Überraschung lernt er sie neu
  (umlernen), die alte ist dann weg.
- **erwartet / unerwartet** (H18): Jede Regel weiß, wie oft sie danebenliegt (erwartete
  Unsicherheit). Unerwartet ist, wenn eine Regel in den letzten `WINDOW` Schritten so oft
  danebenlag, dass das bei ihrer gewohnten Fehlerquote fast unmöglich ist (Wahrscheinlichkeit
  unter `TAIL_LIMIT`). Dann prüft er seine anderen Karten und nimmt die, die die letzten
  Schritte am besten erklärt, oder legt eine neue an, falls keine passt.

Geprüft wird jede Regel einzeln, nicht die Summe: Viele unsichere Regeln würden sonst den
Fehler einer einzigen sicheren Regel verdecken (Lehre aus H16: Teile statt Ganzes).
Bevor der Agent auf eine andere Welt schließt, fragt er außerdem: War die Regel nur
unvollständig oder falsch? Gibt es eine verfeinerte Regel, die alte und neue Schritte erklärt
(etwa „-1, außer an einer Wand“ statt „-1“), verfeinert er sie und bleibt (Teile
korrigieren). Erklärt gar keine Regel die neuen Schritte, lässt er die Regel fallen. Nur wenn
eine *andere* Regel die neuen Schritte gut erklärt, spricht das für eine andere Welt.

Grundlage: Yu & Dayan 2005 (erwartete gegen unerwartete Unsicherheit), Sanders, Wilson und
Gershman 2020 (Remapping als Schluss auf einen verborgenen Zustand), Gershman 2017
(neue Karte statt Überschreiben), Ergebnis 3 und 12 dieses Prototyps.
"""

import math
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Literal

from hekmatki.general.env import Transition
from hekmatki.general.knowledge import Knowledge, Slot
from hekmatki.general.synthesis import Example, Found

WINDOW: Final = 20
"""So viele letzte Schritte zählen für den Test (von Hand gewählt, ohne Grundlage)."""
TAIL_LIMIT: Final = 1e-5
"""Unwahrscheinlicher als das ist unerwartet (von Hand gewählt, ohne Grundlage)."""
DOUBT: Final = 0.85
"""Lag eine Regel daneben, die mindestens so oft stimmt, lernt die Karte vorerst nicht daraus."""
RELIABLE: Final = 0.75
"""Ab dieser Trefferquote gilt eine Regel als verlässlich (für „jede Überraschung“)."""


class Strategy(StrEnum):
    """Wie der Agent auf Überraschung reagiert."""

    EVERY = "jede Überraschung"
    NEVER = "nie neue Karte"
    EXPECTED = "erwartet / unerwartet"


type Kind = Literal["neu", "zurück", "umlernen", "verfeinern"]


@dataclass(frozen=True)
class Decision:
    """Was der Agent mit seinen Karten tut."""

    kind: Kind
    target: int
    """Index der Karte, die danach gilt (bei „neu“: die nächste freie Stelle)."""
    refined: dict[Slot, Found] = field(default_factory=dict)
    """Bei „verfeinern“: die verbesserten Regeln."""


def binomial_tail(misses: int, uses: int, miss_rate: float) -> float:
    """Wahrscheinlichkeit, mindestens `misses` Fehler in `uses` Versuchen zu sehen."""
    return sum(
        math.comb(uses, k) * miss_rate**k * (1.0 - miss_rate) ** (uses - k)
        for k in range(misses, uses + 1)
    )


def tails(knowledge: Knowledge, transitions: Sequence[Transition]) -> dict[Slot, float]:
    """Je Regel mit Fehlern: wie unwahrscheinlich so viele Fehler bei ihrer Quote sind."""
    misses: defaultdict[Slot, int] = defaultdict(int)
    uses: defaultdict[Slot, int] = defaultdict(int)
    reliability: dict[Slot, float] = {}
    for transition in transitions:
        for check in knowledge.checks(transition):
            uses[check.slot] += 1
            misses[check.slot] += not check.hit
            reliability[check.slot] = check.reliability
    return {
        slot: binomial_tail(misses[slot], uses[slot], 1.0 - reliability[slot])
        for slot in uses
        if misses[slot]
    }


def smallest_tail(knowledge: Knowledge, transitions: Sequence[Transition]) -> float:
    """Wie unwahrscheinlich die Fehler der auffälligsten Regel sind (1: alles wie erwartet)."""
    return min(tails(knowledge, transitions).values(), default=1.0)


def log_likelihood(knowledge: Knowledge, transitions: Sequence[Transition]) -> float:
    """Wie gut die Karte die Schritte erklärt (natürlicher Logarithmus)."""
    return sum(
        math.log(check.reliability if check.hit else 1.0 - check.reliability)
        for transition in transitions
        for check in knowledge.checks(transition)
    )


def _since_change(
    knowledge: Knowledge, slots: Sequence[Slot], window: Sequence[Transition]
) -> list[Transition]:
    """Die Schritte ab dem ersten Fehler einer auffälligen Regel: vermutlich schon die neue
    Welt. Nur an ihnen werden die anderen Karten geprüft."""
    for index, transition in enumerate(window):
        if any(not c.hit and c.slot in slots for c in knowledge.checks(transition)):
            return list(window[index:])
    return list(window)


class Detector:
    """Entscheidet nach jedem Schritt, ob die jetzige Karte noch gilt."""

    def __init__(self, strategy: Strategy, window: int = WINDOW, limit: float = TAIL_LIMIT) -> None:
        self.strategy, self.limit, self.window = strategy, limit, window
        self.recent: deque[Transition] = deque(maxlen=window)
        self.history: list[float] = []
        """Kleinste Wahrscheinlichkeit der jeweils geltenden Karte nach jedem Schritt."""

    def judge(
        self, maps: Sequence[Knowledge], current: int, transition: Transition
    ) -> Decision | None:
        """None heißt: Die Karte gilt weiter."""
        self.recent.append(transition)
        decision = self._decide(maps, current, transition)
        if decision is not None:
            self.recent.clear()
        return decision

    def doubts(self, knowledge: Knowledge, transition: Transition) -> bool:
        """Lag eine sonst sichere Regel daneben? Dann lernt die Karte vorerst nicht daraus.

        Sonst würde die alte Karte von der neuen Umgebung verdorben, bevor der Wechsel erkannt
        ist. Gelernt wird später: von der neuen Karte, oder von der alten, wenn es doch nur
        Rauschen war (Zuordnung zu einer verborgenen Ursache, Gershman 2017).
        """
        if self.strategy is Strategy.EVERY:
            return False
        return any(not c.hit and c.reliability >= DOUBT for c in knowledge.checks(transition))

    def _decide(
        self, maps: Sequence[Knowledge], current: int, transition: Transition
    ) -> Decision | None:
        if self.strategy is Strategy.EVERY:
            return self._every(maps, current, transition)
        window = list(self.recent)
        by_slot = tails(maps[current], window)
        self.history.append(min(by_slot.values(), default=1.0))
        unexpected = [slot for slot, tail in by_slot.items() if tail < self.limit]
        if not unexpected:
            return None
        refined = self._refine(maps[current], unexpected, window)
        if refined is not None:
            return Decision("verfeinern", current, refined)
        if self.strategy is Strategy.NEVER:
            return Decision("umlernen", current)
        since = _since_change(maps[current], unexpected, window)
        fitting = [
            (log_likelihood(knowledge, since), index)
            for index, knowledge in enumerate(maps)
            if index != current
            and knowledge.rules.found
            and smallest_tail(knowledge, since) >= self.limit
        ]
        if fitting:
            return Decision("zurück", max(fitting)[1])
        return Decision("neu", len(maps))

    def _refine(
        self, knowledge: Knowledge, slots: Sequence[Slot], window: Sequence[Transition]
    ) -> dict[Slot, Found] | None:
        """Erklären sich die auffälligen Regeln ohne neue Welt? Für jede Regel drei Fälle:

        1. Eine verfeinerte Regel erklärt alte und neue Schritte: verfeinern.
        2. Eine andere Regel erklärt allein die neuen Schritte gut: Hinweis auf eine andere
           Welt (None).
        3. Keine Regel erklärt die neuen Schritte: Die Größe ist hier nicht vorhersagbar, die
           Regel wird fallen gelassen. Das ist keine neue Welt, nur ein Irrtum über sie.
        """
        refined = {}
        for slot in slots:
            extra = [Example(t.before, t.after) for t in window if t.action == slot[0]]
            better = knowledge.rules.refine(slot, extra)
            if better is not None:
                refined[slot] = better
            elif knowledge.rules.fit_alone(slot, extra) is not None:
                return None
            else:
                refined[slot] = Found(None, 0, len(extra), 0)
        return refined

    def _every(
        self, maps: Sequence[Knowledge], current: int, transition: Transition
    ) -> Decision | None:
        def missed(knowledge: Knowledge) -> bool:
            checks = knowledge.checks(transition)
            return any(not c.hit and c.reliability >= RELIABLE for c in checks)

        if not missed(maps[current]):
            return None
        fitting = [
            i for i, k in enumerate(maps) if i != current and k.rules.found and not missed(k)
        ]
        return Decision("zurück", fitting[0]) if fitting else Decision("neu", len(maps))
