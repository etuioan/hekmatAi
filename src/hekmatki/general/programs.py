"""Regeln als kleine Programme aus allgemeinen Bausteinen (ab 0.16, H20; erweitert in 0.17).

Eine Regel sagt, wie sich eine Größe der Beobachtung ändert, wenn der Agent eine Taste
drückt. Statt aus festen Regelarten der Spielwelt zu wählen, baut der Agent sie aus
Bausteinen, die zu keiner bestimmten Welt gehören.

Grundbausteine (0.16):
- `Keep`: Die Größe bleibt gleich.
- `Shift(by)`: Sie ändert sich um einen festen Schritt.
- `Rises` / `Falls`: Sie wird größer / kleiner, um wie viel ist offen.
- `When(sensor, value, then, otherwise)`: Hat eine andere Größe (ein „Schalter“ mit zwei
  Werten) den Wert `value`, gilt `then`, sonst `otherwise`.

Neu in 0.17 (Runde 7, H21 und H22):
- `Copy(source)`: Sie übernimmt den Wert einer anderen Größe (Tauschen, Verschieben).
- `Cycle(by, modulus)`: ein Schritt im Ring: Nach dem letzten Wert kommt der erste.
- `Until(by, sensor, value)`: die einzige Schleife. Schritt um Schritt, solange der Schalter
  nicht `value` zeigt (Rutschen auf Eis: bis eine Wand kommt). Eine Option mit
  Abbruchbedingung (Sutton 1999, Bacon 2017); Schleifen nur in dieser engen Form, weil
  freie Schleifen die Suche sprengen (Gulwani 2017).

Neu in 0.18:
- `Becomes(value)`: Sie wird `value`, egal was vorher war (eine Blickrichtung nach einem Schritt,
  ein Schalter, den eine Taste immer auf denselben Wert stellt).

Grundlage: Begriffe als Programme aus einer kleinen Grammatik (Piantadosi 2012,
Ullman 2012, Rule 2020 und 2024), Weltmodelle als Programme (Tycho, Kepler, Schema 2026),
Schleifen als Kompression (Ellis 2018), Bausteine höherer Ordnung (Cropper 2020).
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
class Copy:
    """Die Größe übernimmt den Wert, den Größe `source` vorher hatte."""

    source: int


@dataclass(frozen=True)
class Becomes:
    """Die Größe wird `value`, egal was vorher war."""

    value: int


@dataclass(frozen=True)
class Cycle:
    """Ring: Die Größe ändert sich um `by`, gezählt im Kreis über `modulus` Werte."""

    by: int
    modulus: int


@dataclass(frozen=True)
class Until:
    """Schleife: Schritte um `by`, solange Schalter `sensor` nicht `value` zeigt."""

    by: int
    sensor: int
    value: int


@dataclass(frozen=True)
class When:
    """Je nach Schalter `sensor` gilt die eine oder die andere Regel."""

    sensor: int
    value: int
    then: "Program"
    otherwise: "Program"


type Leaf = Keep | Shift | Rises | Falls | Copy | Becomes | Cycle | Until
type Program = Leaf | When

LEAF_TYPES = (Keep, Shift, Rises, Falls, Copy, Becomes, Cycle, Until)
LOOP_COST = 2
"""Ring und Schleife kosten zwei Bausteine: Schritt plus Rand oder Abbruchbedingung."""


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
        case Copy(source):
            return new == before[source]
        case Becomes(value):
            return new == value
        case Cycle(by, modulus):
            return new == (old + by) % modulus
        case Until(by, sensor, value):
            if before[sensor] == value:
                return new == old  # Schon am Ende: Die Schleife läuft kein einziges Mal.
            steps, rest = divmod(new - old, by)
            return rest == 0 and steps >= 1 and after[sensor] == value


def predict(program: Program, before: Observation, component: int) -> int | None:
    """Der genaue neue Wert, wenn die Regel ihn festlegt (sonst None)."""
    old = before[component]
    match branch(program, before):
        case Keep():
            return old
        case Shift(by):
            return old + by
        case Copy(source):
            return before[source]
        case Becomes(value):
            return value
        case Cycle(by, modulus):
            return (old + by) % modulus
        case Until(_, sensor, value) if before[sensor] == value:
            return old  # Der Schalter zeigt schon das Ende: kein Schritt.
        case _:
            return None


def direction(program: Program, before: Observation, component: int) -> int:
    """In welche Richtung sich die Größe hier ändert: +1, -1 oder 0."""
    match branch(program, before):
        case Keep():
            return 0
        case Shift(by) | Cycle(by, _):
            return _sign(by)
        case Rises():
            return 1
        case Falls():
            return -1
        case Copy(source):
            return _sign(before[source] - before[component])
        case Becomes(value):
            return _sign(value - before[component])
        case Until(by, sensor, value):
            return 0 if before[sensor] == value else _sign(by)


def cost(program: Program) -> int:
    """Länge der Regel: Zahl der Bausteine (Schalter und Werte zählen nicht extra)."""
    match program:
        case When(_, _, then, otherwise):
            return 1 + cost(then) + cost(otherwise)
        case Cycle() | Until():
            return LOOP_COST
        case _:
            return 1


def leaves(program: Program) -> list[Leaf]:
    """Alle Bausteine, die in der Regel vorkommen."""
    if isinstance(program, When):
        return [*leaves(program.then), *leaves(program.otherwise)]
    return [program]


def can_change(leaf: Leaf, delta: int) -> bool:
    """Kann dieser Baustein die Größe um `delta` ändern? (Ohne die Lage zu kennen.)"""
    match leaf:
        case Keep():
            return delta == 0
        case Shift(by):
            return delta == by
        case Rises():
            return delta > 0
        case Falls():
            return delta < 0
        case Copy() | Becomes():
            return True
        case Cycle(by, modulus):
            return delta in (by, by - modulus, by + modulus)
        case Until(by, _, _):
            steps, rest = divmod(delta, by)
            return rest == 0 and steps >= 0


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
        case Copy(source):
            return f"übernimmt G{source}"
        case Becomes(value):
            return f"wird {value}"
        case Cycle(by, modulus):
            return f"{by:+d} im Ring aus {modulus} Werten"
        case Until(by, sensor, value):
            return f"{by:+d} immer wieder, bis G{sensor} = {value}"
        case When(sensor, value, Keep(), other):
            return f"{describe(other)}, außer G{sensor} = {value} (dann bleibt sie)"
        case When(sensor, value, then, other):
            return f"wenn G{sensor} = {value}: {describe(then)}, sonst {describe(other)}"


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)
