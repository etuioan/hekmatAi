"""Die Bibliothek über Welten hinweg (ab 0.16, H20): Hilft sie, und wird sie wirklich genutzt?

Der allgemeine Agent lernt drei Welten nacheinander. Nach jeder Welt verdichtet er seine
bewährten Regeln zu Bibliotheksmustern (`general/library.py`). In der nächsten Welt probiert
er diese Muster vor den langen Regeln der Grundgrammatik.

Gemessen wird, was Berlot-Attwell 2026 fordert:
- **Aufwand**: geprüfte Programme, einmal nur für die Suchen mit Erfolg (Größen, die am
  Ende eine Regel ohne Ausnahme haben), einmal für alle Suchen, auch die vergeblichen
- **Wiederverwendung**: wie viele Regeln einer neuen Welt aus einem Eintrag stammen
- **gleiches Budget**: Darf jede Regelsuche nur `BUDGET` Programme prüfen, wie oft erreicht
  der Agent dann in der Prüfung sein Ziel?
- **Kontrolle**: eine Bibliothek aus Zufallsmustern gleicher Länge, die nie entfernt wird.
  Sie zeigt, was eine Bibliothek kostet, die nicht passt.
- **Vorprüfung** (ab 0.17, H24): Mit Vorprüfung probiert der Agent ein Muster nur, wenn
  seine Bausteine die beobachteten Änderungen überhaupt erzeugen können (DeepCoder 2017).
  „ohne Vorprüfung“ ist die Bibliothek wie in 0.16.

Zwei Reihenfolgen: Raum zuerst (2D → 3D → Suche) und Suche zuerst (Suche → 2D → 3D).
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Final, Literal

from hekmatki.experiments.general_worlds import WORLD_BY_NAME, WorldRun, run_world
from hekmatki.general.agent import GeneralAgent, Planning
from hekmatki.general.library import (
    AnyShift,
    Hole,
    Library,
    Pattern,
    Template,
    describe_pattern,
)
from hekmatki.general.programs import Falls, Rises

ORDERS: Final = (("2D-Raum", "3D-Raum", "Suche"), ("Suche", "2D-Raum", "3D-Raum"))
BUDGET: Final = 20
"""Programme je Regelsuche im Versuch mit gleichem Budget (von Hand gewählt)."""
RANDOM_PATTERNS: Final = 2

Condition = Literal["ohne Bibliothek", "mit Bibliothek", "ohne Vorprüfung", "Zufallsbibliothek"]
CONDITIONS: tuple[Condition, ...] = (
    "ohne Bibliothek",
    "mit Bibliothek",
    "ohne Vorprüfung",
    "Zufallsbibliothek",
)
LEARNING: tuple[Condition, ...] = ("mit Bibliothek", "ohne Vorprüfung")
"""Die Bedingungen, deren Bibliothek aus den gelernten Regeln wächst."""
Budgeted = Literal["ohne Bibliothek", "mit Bibliothek"]
BUDGETED: tuple[Budgeted, ...] = ("ohne Bibliothek", "mit Bibliothek")


@dataclass(frozen=True)
class LibraryRow:
    """Eine Welt in einer Reihenfolge, gemittelt über alle Läufe."""

    order: str
    world: str
    tested: dict[Condition, float]
    """Geprüfte Programme aller Regelsuchen in dieser Welt (der ganze Rechenaufwand)."""
    tested_found: dict[Condition, float]
    """Davon für Größen, die am Ende eine Regel ohne Ausnahme haben (Suche mit Erfolg)."""
    exact: dict[Condition, float]
    """Zahl der bewährten Regeln am Ende."""
    borrowed: dict[Condition, float]
    """Davon aus der Bibliothek."""
    budget_reached: dict[Budgeted, float]
    """Ziel erreicht in der Prüfung, wenn jede Regelsuche nur `BUDGET` Programme prüfen darf."""


@dataclass(frozen=True)
class EntryRow:
    """Ein Bibliothekseintrag am Ende einer Reihenfolge (erster Lauf)."""

    order: str
    name: str
    pattern: str
    origin: str
    reuses: dict[str, int]
    removed: bool


@dataclass(frozen=True)
class _Pass:
    """Ein Durchgang durch eine Reihenfolge: je Welt die Messwerte."""

    tested: list[int]
    tested_found: list[int]
    exact: list[int]
    borrowed: list[int]
    reached: list[float]
    library: Library | None


def random_library(rng: random.Random, count: int = RANDOM_PATTERNS) -> Library:
    """Zufallsmuster gleicher Länge wie die gelernten, ohne die Sperr-Form („bleibt, außer“)."""
    library = Library(patience=10**6)
    leaves: list[Pattern] = [Rises(), Falls(), AnyShift(), Hole()]
    while len(library.entries) < count:
        then, otherwise = rng.sample(leaves, 2)
        library.add(Template(rng.choice((0, 1)), then, otherwise), "Zufall")
    return library


def run_library_transfer(seeds: int = 10) -> tuple[list[LibraryRow], list[EntryRow]]:
    """Beide Reihenfolgen, alle Bedingungen."""
    rows: list[LibraryRow] = []
    entries: list[EntryRow] = []
    for order in ORDERS:
        label = " → ".join(order)
        passes = {c: [_pass(order, c, seed, None) for seed in range(seeds)] for c in CONDITIONS}
        budgeted = {c: [_pass(order, c, seed, BUDGET) for seed in range(seeds)] for c in BUDGETED}
        for index, world in enumerate(order):
            rows.append(
                LibraryRow(
                    label,
                    world,
                    {c: mean(p.tested[index] for p in passes[c]) for c in CONDITIONS},
                    {c: mean(p.tested_found[index] for p in passes[c]) for c in CONDITIONS},
                    {c: mean(p.exact[index] for p in passes[c]) for c in CONDITIONS},
                    {c: mean(p.borrowed[index] for p in passes[c]) for c in CONDITIONS},
                    {c: mean(p.reached[index] for p in budgeted[c]) for c in BUDGETED},
                )
            )
        first = passes["mit Bibliothek"][0].library
        if first is not None:
            entries += _entry_rows(label, first)
    return rows, entries


def _pass(order: Sequence[str], condition: Condition, seed: int, budget: int | None) -> _Pass:
    library = {
        "ohne Bibliothek": None,
        "mit Bibliothek": Library(),
        "ohne Vorprüfung": Library(recognition=False),
        "Zufallsbibliothek": random_library(random.Random(seed)),
    }[condition]
    result = _Pass([], [], [], [], [], library)
    for world in order:
        spec = WORLD_BY_NAME[world]
        agent = GeneralAgent(spec.actions, Planning.FORM, library, budget)
        run = run_world(spec, agent, seed)
        _measure(result, run, agent)
        if library is not None and condition in LEARNING:
            found = agent.knowledge.rules.found.values()
            exact = [f for f in found if f.exact and f.program is not None]
            library.close_world(world, [f.entry for f in exact if f.entry is not None])
            library.absorb([f.program for f in exact if f.program is not None], world)
    return result


def _measure(result: _Pass, run: WorldRun, agent: GeneralAgent) -> None:
    rules = agent.knowledge.rules
    exact = {slot for slot, f in rules.found.items() if f.exact}
    result.tested.append(sum(f.tested for _, f in rules.searches))
    result.tested_found.append(sum(f.tested for slot, f in rules.searches if slot in exact))
    result.exact.append(len(exact))
    result.borrowed.append(sum(rules.found[slot].entry is not None for slot in exact))
    result.reached.append(mean(run.test_reached))


def _entry_rows(order: str, library: Library) -> list[EntryRow]:
    return [
        EntryRow(
            order,
            entry.name,
            describe_pattern(entry.pattern),
            entry.origin,
            dict(entry.reuses),
            removed,
        )
        for entries, removed in ((library.entries, False), (library.removed, True))
        for entry in entries
    ]
