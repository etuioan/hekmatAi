"""Die Hekmat-Bibliothek: wiederverwendbare Regel-Muster mit Zähler (ab 0.16, H20).

Nach jeder Welt schaut der Agent auf seine bewährten Regeln (ohne Ausnahme) und sucht, was
mehrere gemeinsam haben. Zwei Regeln werden dazu übereinandergelegt (Anti-Unifikation):
Was gleich ist, bleibt; was verschieden ist, wird zur Lücke. Aus
„+1, außer G3 = 1“ und „-1, außer G5 = 1“ wird so das Muster „fester Schritt, außer ein
Schalter ist 1“. Welcher Schalter gemeint ist, bleibt immer offen, denn in jeder Welt
heißen die Größen anders.

Ein Muster ist in der nächsten Welt kürzer als die Regel, die es abkürzt, und wird darum
früher ausprobiert. Das spart Suche, aber nur, wenn es passt. Darum zählt die Bibliothek,
wie oft ein Eintrag wirklich in einer neuen Welt genutzt wird, und wirft Einträge weg, die
`PATIENCE` Welten lang niemand nutzt.

Ab 0.17 hat die Bibliothek ein Erkennungsmodell (H24): Bevor ein Muster probiert wird,
prüft der Agent eine billige Vorbedingung an den Daten, ohne ein Programm zu testen. Kommen
Änderungen vor, die das Muster gar nicht erzeugen kann (etwa -1, wenn das Muster nur 0 und
+1 kennt), wird es übersprungen. So kostet die Bibliothek dort nichts, wo sie nicht passen
kann (DeepCoder, Balog 2017: erst vorhersagen, welche Bausteine vorkommen, dann suchen).

Grundlage: DreamCoder und Stitch (Bibliothek durch Verdichten), LILO; die Warnung von
Berlot-Attwell 2026, dass gelernte Bibliotheken oft gar nicht wiederverwendet werden, und
von AbstractBeam (Zenkner 2024), dass unpassende Muster die Suche verlangsamen.
"""

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations, product
from typing import Final

from hekmatki.general.programs import (
    Keep,
    Leaf,
    Program,
    Shift,
    When,
    can_change,
    describe,
    leaves,
)

PATIENCE: Final = 2
"""So viele Welten darf ein Eintrag ungenutzt bleiben (von Hand gewählt, ohne Grundlage)."""
CALL_COST: Final = 1
"""Ein Bibliotheksaufruf zählt als ein Baustein; dazu kommen die gefüllten Lücken."""
MAX_NEW: Final = 2
"""Höchstens so viele neue Einträge pro Welt (von Hand gewählt, ohne Grundlage)."""
COVERAGE: Final = 0.9
"""Vorbedingung: So viele der beobachteten Änderungen muss ein Muster erzeugen können
(von Hand gewählt, ohne Grundlage; Rauschen darf den Rest ausmachen)."""


@dataclass(frozen=True)
class Hole:
    """Platz für einen beliebigen Baustein."""


@dataclass(frozen=True)
class AnyShift:
    """Ein fester Schritt; wie groß, ist offen."""


@dataclass(frozen=True)
class Template:
    """Ein Schalter-Muster; welcher Schalter, ist immer offen, der Wert nur, wenn `None`."""

    value: int | None
    then: "Pattern"
    otherwise: "Pattern"


type Pattern = Leaf | Hole | AnyShift | Template


@dataclass(frozen=True)
class Vocabulary:
    """Woraus der Agent in einer Lage Regeln bauen kann, aus seinen Daten abgelesen."""

    leaves: tuple[Leaf, ...]
    """Grundbausteine der Länge 1; aus ihnen werden auch Schalter-Regeln gebaut."""
    sensors: dict[int, tuple[int, int]]
    """Schalter: Größen mit genau zwei Werten (Größe → ihre beiden Werte)."""
    shifts: tuple[int, ...]
    """Schritte, die in den Daten vorkommen."""
    extra: tuple[Leaf, ...] = ()
    """Weitere Bausteine der Länge 1, nur einzeln probiert (ab 0.17: Übernehmen)."""
    loops: tuple[Leaf, ...] = ()
    """Bausteine der Länge 2 (ab 0.17: Ring, Schleife)."""
    changes: Mapping[int, int] = field(default_factory=dict)
    """Wie oft jede Änderung der Größe vorkam (für die Vorbedingung der Bibliothek)."""


def plausible(program: Program, changes: Mapping[int, int], coverage: float = COVERAGE) -> bool:
    """Kann die Regel genug der beobachteten Änderungen überhaupt erzeugen?

    Liest nur die Häufigkeiten der Änderungen, prüft kein Programm an den Daten.
    """
    total = sum(changes.values())
    if total == 0:
        return True
    parts = leaves(program)
    covered = sum(n for delta, n in changes.items() if any(can_change(p, delta) for p in parts))
    return covered >= coverage * total


def generalize(program: Program) -> Pattern:
    """Die Regel als Muster, mit offenen Schaltern."""
    if isinstance(program, When):
        return Template(program.value, generalize(program.then), generalize(program.otherwise))
    return program


def anti_unify(first: Pattern, second: Pattern) -> Pattern:
    """Das speziellste Muster, das beide abdeckt."""
    match first, second:
        case _ if first == second:
            return first
        case (Shift() | AnyShift(), Shift() | AnyShift()):
            return AnyShift()
        case (Template(), Template()):
            value = first.value if first.value == second.value else None
            then = anti_unify(first.then, second.then)
            return Template(value, then, anti_unify(first.otherwise, second.otherwise))
        case _:
            return Hole()


def subsumes(general: Pattern, special: Pattern) -> bool:
    """Deckt `general` alles ab, was `special` abdeckt?"""
    match general, special:
        case (Hole(), _):
            return True
        case (AnyShift(), Shift() | AnyShift()):
            return True
        case (Template(), Template()):
            value_ok = general.value is None or general.value == special.value
            return (
                value_ok
                and subsumes(general.then, special.then)
                and subsumes(general.otherwise, special.otherwise)
            )
        case _:
            return general == special


def size(pattern: Pattern) -> int:
    """Wie viel das Muster festlegt: Bausteine ohne Lücken."""
    match pattern:
        case Hole():
            return 0
        case Template(_, then, otherwise):
            return 1 + size(then) + size(otherwise)
        case _:
            return 1


def instances(
    pattern: Pattern, vocabulary: Vocabulary, component: int
) -> Iterator[tuple[Program, int]]:
    """Alle Regeln, die das Muster hier ergibt, mit ihrer Länge (Lücken kosten je 1)."""
    match pattern:
        case Hole():
            yield from ((leaf, 1) for leaf in vocabulary.leaves)
        case AnyShift():
            yield from ((Shift(by), 0) for by in vocabulary.shifts)
        case Template(value, then, otherwise):
            for sensor, values in vocabulary.sensors.items():
                if sensor == component:
                    continue
                allowed = values if value is None else [v for v in values if v == value]
                for chosen in allowed:
                    yield from _branches(sensor, chosen, then, otherwise, vocabulary, component)
        case _:
            yield pattern, 0


def _branches(
    sensor: int,
    value: int,
    then: Pattern,
    otherwise: Pattern,
    vocabulary: Vocabulary,
    component: int,
) -> Iterator[tuple[Program, int]]:
    first = list(instances(then, vocabulary, component))
    second = list(instances(otherwise, vocabulary, component))
    for (a, cost_a), (b, cost_b) in product(first, second):
        if a != b:
            yield When(sensor, value, a, b), cost_a + cost_b


def describe_pattern(pattern: Pattern) -> str:
    """Das Muster als deutscher Satz."""
    match pattern:
        case Hole():
            return "irgendetwas"
        case AnyShift():
            return "fester Schritt"
        case Template(value, Keep(), other):
            shown = "ein Wert" if value is None else str(value)
            return f"{describe_pattern(other)}, außer ein Schalter ist {shown} (dann bleibt sie)"
        case Template(value, then, other):
            shown = "ein Wert" if value is None else str(value)
            return f"wenn ein Schalter {shown} ist: {describe_pattern(then)}, sonst " + (
                describe_pattern(other)
            )
        case _:
            return describe(pattern)


@dataclass
class Entry:
    """Ein Bibliothekseintrag mit Herkunft und Wiederverwendung je Welt."""

    name: str
    pattern: Pattern
    origin: str
    reuses: dict[str, int] = field(default_factory=dict)
    idle: int = 0
    """Wie viele Welten nacheinander ihn niemand genutzt hat."""

    @property
    def total_reuses(self) -> int:
        """Regeln in anderen Welten, die aus diesem Eintrag entstanden sind."""
        return sum(self.reuses.values())


class Library:
    """Die wachsende Bibliothek."""

    def __init__(
        self, patience: int = PATIENCE, max_new: int = MAX_NEW, recognition: bool = True
    ) -> None:
        self.entries: list[Entry] = []
        self.removed: list[Entry] = []
        self.patience, self.max_new = patience, max_new
        self.recognition = recognition
        """Muster nur probieren, wenn ihre Vorbedingung stimmt (ab 0.17, H24)."""
        self._names = 0

    def add(self, pattern: Pattern, origin: str) -> Entry:
        """Nimmt ein Muster auf (auch für Kontrollversuche mit Zufallsmustern)."""
        self._names += 1
        entry = Entry(f"B{self._names}", pattern, origin)
        self.entries.append(entry)
        return entry

    def ordered(self) -> list[Entry]:
        """Die Einträge in der Reihenfolge, in der die Suche sie probiert: Bewährtes zuerst."""
        return sorted(self.entries, key=lambda entry: -entry.total_reuses)

    def close_world(self, world: str, used: Iterable[str]) -> list[Entry]:
        """Zählt die Nutzung in einer Welt und entfernt, was zu lange ungenutzt blieb."""
        counts = Counter(used)
        dropped = []
        for entry in list(self.entries):
            if entry.origin == world:
                continue
            if counts[entry.name]:
                entry.reuses[world] = counts[entry.name]
                entry.idle = 0
                continue
            entry.idle += 1
            if entry.idle >= self.patience:
                self.entries.remove(entry)
                self.removed.append(entry)
                dropped.append(entry)
        return dropped

    def absorb(self, programs: Sequence[Program], world: str) -> list[Entry]:
        """Verdichtet die bewährten Regeln einer Welt zu neuen Einträgen."""
        patterns = [generalize(p) for p in programs if isinstance(p, When)]
        candidates = {anti_unify(a, b) for a, b in combinations(patterns, 2)}
        scored = []
        for candidate in candidates:
            uses = sum(subsumes(candidate, pattern) for pattern in patterns)
            if size(candidate) >= 2 and uses >= 2:
                scored.append((uses * (size(candidate) - 1), size(candidate), candidate))
        chosen: list[Pattern] = []
        for _, _, candidate in sorted(scored, key=lambda item: (-item[0], -item[1], str(item))):
            known = [e.pattern for e in self.entries] + chosen
            if any(subsumes(other, candidate) for other in known):
                continue
            chosen.append(candidate)
            if len(chosen) == self.max_new:
                break
        return [self.add(pattern, world) for pattern in chosen]
