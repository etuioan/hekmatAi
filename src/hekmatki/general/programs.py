"""Regeln als kleine Programme aus allgemeinen Bausteinen (ab 0.16, H20).

Eine Regel sagt, wie sich eine Größe der Beobachtung ändert, wenn der Agent eine Taste
drückt. Statt aus festen Regelarten der Spielwelt zu wählen, baut der Agent sie aus fünf
Bausteinen, die zu keiner bestimmten Welt gehören:
- `Keep`: Die Größe bleibt gleich.
- `Shift(by)`: Sie ändert sich um einen festen Schritt.
- `Rises` / `Falls`: Sie wird größer / kleiner, um wie viel ist offen.
- `When(sensor, value, then, otherwise)`: Hat eine andere Größe (ein „Schalter“ mit zwei
  Werten) den Wert `value`, gilt `then`, sonst `otherwise`.

Grundlage: Begriffe als Programme aus einer kleinen Grammatik (Piantadosi 2012,
Ullman 2012, Rule 2020 und 2024), Weltmodelle als Programme (Tycho, Kepler, Schema 2026).
"""

from dataclasses import dataclass

from hekmatki.general.env import Observation


@dataclass(frozen=True)
class Keep:
    """Die Größe bleibt gleich."""


@dataclass(frozen=True)
class Shift:
    """Die Größe ändert sich um `by`."""

    by: int


@dataclass(frozen=True)
class Rises:
    """Die Größe wird größer."""


@dataclass(frozen=True)
class Falls:
    """Die Größe wird kleiner."""


@dataclass(frozen=True)
class When:
    """Je nach Schalter `sensor` gilt die eine oder die andere Regel."""

    sensor: int
    value: int
    then: "Program"
    otherwise: "Program"


type Leaf = Keep | Shift | Rises | Falls
type Program = Leaf | When

LEAF_TYPES = (Keep, Shift, Rises, Falls)


def branch(program: Program, before: Observation) -> Leaf:
    """Der Baustein, der in dieser Lage gilt."""
    while isinstance(program, When):
        program = program.then if before[program.sensor] == program.value else program.otherwise
    return program


def fits(program: Program, before: Observation, after: Observation, component: int) -> bool:
    """Sagt die Regel für Größe `component` diesen Schritt richtig voraus?"""
    old, new = before[component], after[component]
    match branch(program, before):
        case Keep():
            return new == old
        case Shift(by):
            return new == old + by
        case Rises():
            return new > old
        case Falls():
            return new < old


def predict(program: Program, before: Observation, component: int) -> int | None:
    """Der genaue neue Wert, wenn die Regel ihn festlegt (sonst None)."""
    match branch(program, before):
        case Keep():
            return before[component]
        case Shift(by):
            return before[component] + by
        case _:
            return None


def direction(program: Program, before: Observation) -> int:
    """In welche Richtung sich die Größe hier ändert: +1, -1 oder 0."""
    match branch(program, before):
        case Keep():
            return 0
        case Shift(by):
            return (by > 0) - (by < 0)
        case Rises():
            return 1
        case Falls():
            return -1


def cost(program: Program) -> int:
    """Länge der Regel: Zahl der Bausteine (Schalter und Werte zählen nicht extra)."""
    if isinstance(program, When):
        return 1 + cost(program.then) + cost(program.otherwise)
    return 1


def core(program: Program) -> Leaf | None:
    """Was die Regel tut, wenn nichts sie sperrt: `When` mit einem `Keep`-Zweig abgezogen."""
    match program:
        case When(then=Keep(), otherwise=other) | When(then=other, otherwise=Keep()):
            return core(other)
        case When():
            return None
        case _:
            return program


def describe(program: Program | None) -> str:
    """Die Regel als deutscher Satz, mit Größen als „G3“."""
    match program:
        case None:
            return "unvorhersagbar"
        case Keep():
            return "bleibt"
        case Shift(by):
            return f"{by:+d}"
        case Rises():
            return "steigt"
        case Falls():
            return "fällt"
        case When(sensor, value, Keep(), other):
            return f"{describe(other)}, außer G{sensor} = {value} (dann bleibt sie)"
        case When(sensor, value, then, other):
            return f"wenn G{sensor} = {value}: {describe(then)}, sonst {describe(other)}"
