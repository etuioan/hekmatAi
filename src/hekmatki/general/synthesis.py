"""Regeln suchen: kurze Programme zuerst, Ausnahmen kosten (ab 0.16, H20).

Für eine Taste und eine Größe probiert der Agent Programme der Länge nach: erst einzelne
Bausteine, dann Bibliotheksmuster, dann Schalter-Regeln aus der ganzen Grammatik. Er nimmt
das Programm mit der kürzesten Beschreibung: Länge der Regel plus ihre Ausnahmen
(Prinzip der minimalen Beschreibungslänge, Rissanen; Ockham). Gibt es eine Regel ohne
Ausnahme, kann keine längere sie schlagen, und die Suche hört dort auf.

`tested` zählt die geprüften Programme. Das ist das Maß für Rechenaufwand, an dem die
Bibliothek sich messen lassen muss (Berlot-Attwell 2026: Vergleich bei gleicher Rechenzeit).

Grundlage für die Suche nach Länge: Programm-Induktion bei Kindern und in DreamCoder
(Rule 2024, Ellis 2021), datengesteuerte Grammatiksuche (Duvenaud 2013).
"""

import math
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from hekmatki.general.env import Observation
from hekmatki.general.library import CALL_COST, Library, Vocabulary, instances
from hekmatki.general.programs import (
    Falls,
    Keep,
    Leaf,
    Program,
    Rises,
    Shift,
    When,
    cost,
    fits,
)

NODE_BITS: Final = 4.0
"""Bits je Baustein einer Regel (von Hand gewählt, ohne Grundlage)."""
MAX_COST: Final = 3
"""Längste Regel aus der Grundgrammatik: ein Schalter mit zwei Bausteinen."""
MAX_ERROR_RATE: Final = 0.3
"""Liegt die beste Regel öfter daneben, gilt die Größe als unvorhersagbar (ohne Grundlage)."""
MAX_SHIFTS: Final = 4
"""Höchstens so viele verschiedene Schritte kommen als `Shift` in Frage."""


@dataclass(frozen=True)
class Example:
    """Ein Schritt mit derselben Taste: vorher und nachher."""

    before: Observation
    after: Observation


@dataclass(frozen=True)
class Candidate:
    """Ein Programm, das die Suche prüfen kann, mit Länge und Herkunft."""

    program: Program
    cost: int
    entry: str | None = None
    """Name des Bibliothekseintrags, aus dem es stammt."""


@dataclass(frozen=True)
class Found:
    """Ergebnis einer Suche: die gewählte Regel, ihre Ausnahmen und der Aufwand."""

    program: Program | None
    errors: int
    examples: int
    tested: int
    entry: str | None = None

    @property
    def exact(self) -> bool:
        """Eine Regel ohne Ausnahme?"""
        return self.program is not None and self.errors == 0

    @property
    def reliability(self) -> float:
        """Wie oft die Regel stimmt, vorsichtig geschätzt (Laplace: +1 / +2)."""
        return (self.examples - self.errors + 1) / (self.examples + 2)


def vocabulary(
    examples: Sequence[Example], component: int, sensors: Mapping[int, tuple[int, int]]
) -> Vocabulary:
    """Bausteine für diese Größe, mit den Schritten, die in den Daten vorkommen."""
    changes = Counter(e.after[component] - e.before[component] for e in examples)
    changes.pop(0, None)
    shifts = tuple(sorted(by for by, _ in changes.most_common(MAX_SHIFTS)))
    leaves: tuple[Leaf, ...] = (Keep(), *(Shift(by) for by in shifts), Rises(), Falls())
    return Vocabulary(leaves, dict(sensors), shifts)


def candidates(
    words: Vocabulary,
    component: int,
    library: Library | None = None,
    max_cost: int = MAX_COST,
) -> Iterator[Candidate]:
    """Alle Programme bis `max_cost`, kürzeste zuerst; bei gleicher Länge die Bibliothek nach
    den einfachen Bausteinen und vor den Schalter-Regeln der Grundgrammatik."""
    borrowed = [] if library is None else _borrowed(words, component, library)
    for length in range(1, max_cost + 1):
        if length == 1:
            yield from (Candidate(leaf, 1) for leaf in words.leaves)
        yield from (c for c in borrowed if c.cost == length)
        if length == 3:
            yield from (Candidate(rule, 3) for rule in _switch_rules(words, component))


def synthesize(
    examples: Sequence[Example],
    component: int,
    sensors: Mapping[int, tuple[int, int]],
    library: Library | None = None,
    budget: int | None = None,
) -> Found:
    """Sucht die Regel mit der kürzesten Beschreibung für Größe `component`."""
    if not examples:
        return Found(None, 0, 0, 0)
    words = vocabulary(examples, component, sensors)
    exception_bits = bits_per_exception(len(examples))
    best: tuple[Candidate, int] | None = None
    best_bits = math.inf
    tested = 0
    for candidate in candidates(words, component, library):
        rule_bits = candidate.cost * NODE_BITS
        if rule_bits >= best_bits or (budget is not None and tested >= budget):
            break  # Länger kann nicht mehr gewinnen, oder das Budget ist aufgebraucht.
        tested += 1
        allowed = len(examples) if best is None else _allowed(best_bits - rule_bits, exception_bits)
        errors = _errors(candidate.program, examples, component, allowed)
        if errors <= allowed:
            best, best_bits = (candidate, errors), rule_bits + errors * exception_bits
    if best is None or best[1] > MAX_ERROR_RATE * len(examples):
        return Found(None, 0 if best is None else best[1], len(examples), tested)
    chosen, errors = best
    return Found(chosen.program, errors, len(examples), tested, chosen.entry)


def bits_per_exception(examples: int) -> float:
    """Bits, um eine Ausnahme zu benennen: welcher der Schritte es war."""
    return math.log2(examples + 1)


def description_bits(program: Program | None, errors: int, examples: int) -> float:
    """Länge der Beschreibung: Regel plus Ausnahmen. Ohne Regel ist jeder Fehler eine Ausnahme."""
    rule = 0.0 if program is None else cost(program) * NODE_BITS
    return rule + errors * bits_per_exception(examples)


def _allowed(spare_bits: float, exception_bits: float) -> int:
    """Wie viele Ausnahmen eine Regel haben darf, um die bisher beste echt zu schlagen.

    Der kleine Abzug fängt Rundungsfehler ab: Bei Gleichstand gewinnt die zuerst gefundene.
    """
    return math.floor(spare_bits / exception_bits - 1e-9)


def _borrowed(words: Vocabulary, component: int, library: Library) -> list[Candidate]:
    found = []
    for entry in library.ordered():
        for program, fill in instances(entry.pattern, words, component):
            found.append(Candidate(program, CALL_COST + fill, entry.name))
    return found


def _switch_rules(words: Vocabulary, component: int) -> Iterator[When]:
    """Schalter-Regeln mit zwei einfachen Bausteinen, ohne doppelte Schreibweisen.

    Ist ein Zweig `Keep`, steht er vorn, mit dem Schalterwert, der sperrt. Sonst nur der
    kleinere Schalterwert, denn „wenn 0: A, sonst B“ ist dasselbe wie „wenn 1: B, sonst A“.
    """
    for sensor, values in words.sensors.items():
        if sensor == component:
            continue
        for then in words.leaves:
            for otherwise in words.leaves:
                if then == otherwise or isinstance(otherwise, Keep):
                    continue
                for value in values if isinstance(then, Keep) else values[:1]:
                    yield When(sensor, value, then, otherwise)


def _errors(program: Program, examples: Sequence[Example], component: int, limit: int) -> int:
    """Zahl der Ausnahmen; hört bei `limit + 1` auf, weil es dann nicht mehr zählt."""
    errors = 0
    for example in examples:
        if not fits(program, example.before, example.after, component):
            errors += 1
            if errors > limit:
                break
    return errors
