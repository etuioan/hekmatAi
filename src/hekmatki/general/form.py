"""Erst die Form der Umgebung, dann die Regeln darin (ab 0.16, H19; Grammatik ab 0.17, H21).

Aus seinen Regeln liest der Agent ab, welche Form die Umgebung hat. Eine Form ist keine
Auswahl aus einer Liste, sondern wird aus Achsen zusammengesetzt (eine kleine Grammatik wie
bei Grosse 2012 und Kemp und Tenenbaum 2008). Jede Größe, die zwei Tasten in
entgegengesetzte Richtungen ändern, während alle anderen Tasten sie sicher gleich lassen,
ist eine Achse. Welche Art, folgt aus dem Baustein, der sie bewegt:

- **Kette** (`Shift`): fester Schritt vor und zurück, wie eine Raum-Dimension. So viele
  unabhängige Tastenpaare, so viele Dimensionen (Philipona, O'Regan und Nadal 2003).
- **Ring** (`Cycle`): fester Schritt, aber nach dem letzten Wert kommt der erste.
- **Rutschbahn** (`Until`): Schritte in eine Richtung, bis ein Schalter (eine Wand) stoppt.
- **Ordnung** (`Rises` / `Falls`): Man weiß die Richtung, nicht die Weite (Suchbaum).

Eine Welt ist das Produkt ihrer Achsen, zum Beispiel „Ring × Ring × Ring“. Größen, die keine
Taste ändert, sind fest (zum Beispiel ein Ziel). Schalter (Größen mit nur zwei Werten, etwa
„Wand voraus?“) sind keine Achsen, auch wenn eine Taste sie setzt und eine andere löscht.
Passt keine Achse, heißt die Form „keine bekannte Form“, und der Agent plant direkt in seinem
Modell (siehe `planner`).
"""

from collections import Counter
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum

from hekmatki.general.programs import Cycle, Falls, Keep, Leaf, Program, Rises, Shift, Until, core

type Slot = tuple[int, int]


class AxisKind(StrEnum):
    """Die Arten von Achsen, aus denen Formen zusammengesetzt werden."""

    SPACE = "Kette"
    RING = "Ring"
    SLIDE = "Rutschbahn"
    ORDER = "Ordnung"


STEPPED = (AxisKind.SPACE, AxisKind.RING, AxisKind.SLIDE)
"""Achsen mit festem Schritt: Auf ihnen plant der Agent Wege."""


@dataclass(frozen=True)
class Axis:
    """Eine Größe, die zwei Tasten in entgegengesetzte Richtungen ändern."""

    component: int
    kind: AxisKind
    up: int
    down: int


@dataclass(frozen=True)
class Form:
    """Die Form einer Umgebung: ihre Achsen und festen Größen."""

    axes: tuple[Axis, ...]
    fixed: tuple[int, ...]

    def of_kind(self, *kinds: AxisKind) -> tuple[Axis, ...]:
        """Nur die Achsen dieser Arten."""
        return tuple(axis for axis in self.axes if axis.kind in kinds)

    @property
    def name(self) -> str:
        """Die Form in Worten, aus ihren Achsen zusammengesetzt."""
        counts = Counter(axis.kind for axis in self.axes)
        parts = [_part(kind, counts[kind]) for kind in AxisKind if counts[kind]]
        return " × ".join(parts) if parts else "keine bekannte Form"


def _part(kind: AxisKind, count: int) -> str:
    dimensions = f"{count} Dimension{'en' if count > 1 else ''}"
    match kind:
        case AxisKind.SPACE:
            return f"Raum mit {dimensions}"
        case AxisKind.SLIDE:
            return f"Rutschbahn mit {dimensions}"
        case AxisKind.RING:
            return " × ".join(["Ring"] * count)
        case AxisKind.ORDER:
            return "Ordnung" if count == 1 else f"Ordnung mit {count} Achsen"


def find_form(
    reliable: Mapping[Slot, Program],
    exact: Mapping[Slot, Program],
    actions: int,
    components: int,
    switches: Set[int] = frozenset(),
) -> Form:
    """Liest die Form aus den Regeln ab.

    `reliable`: Regeln, deren Ausnahmen zum Rauschen der Welt passen; daraus kommen die
    Bewegungen entlang einer Achse. `exact`: Regeln ohne Ausnahme; nur sie zählen für „bleibt“.
    Eine Größe ist nur dann Achse, wenn alle anderen Tasten sie sicher nicht ändern.
    """
    axes, fixed = [], []
    for component in range(components):
        kept = [a for a in range(actions) if isinstance(exact.get((a, component)), Keep)]
        if len(kept) == actions:
            fixed.append(component)
            continue
        if component in switches:
            continue
        moves = {
            a: core(reliable[a, component]) for a in range(actions) if (a, component) in reliable
        }
        axis = _axis(component, moves, set(kept))
        if axis is not None:
            axes.append(axis)
    return Form(tuple(axes), tuple(fixed))


def _axis(component: int, moves: Mapping[int, Leaf | None], kept: set[int]) -> Axis | None:
    ups = [a for a, e in moves.items() if isinstance(e, Rises) or _step(e) > 0]
    downs = [a for a, e in moves.items() if isinstance(e, Falls) or _step(e) < 0]
    others = [a for a in moves if a not in ups and a not in downs]
    if not ups or not downs or not all(a in kept for a in others):
        return None
    up, down = ups[0], downs[0]
    kind = _kind(moves[up], moves[down])
    return None if kind is None else Axis(component, kind, up, down)


def _kind(up: Leaf | None, down: Leaf | None) -> AxisKind | None:
    """Welche Art von Achse zwei entgegengesetzte Bausteine bilden."""
    inverse = _step(up) == -_step(down) != 0
    match up, down:
        case (Shift(), Shift()) if inverse:
            return AxisKind.SPACE
        case (Cycle(_, m), Cycle(_, n)) if inverse and m == n:
            return AxisKind.RING
        case (Until(), Until()) | (Until(), Shift()) | (Shift(), Until()) if inverse:
            return AxisKind.SLIDE
        case _:
            return AxisKind.ORDER


def _step(effect: Leaf | None) -> int:
    match effect:
        case Shift(by) | Cycle(by, _) | Until(by, _, _):
            return by
        case _:
            return 0
