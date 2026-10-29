"""Erst die Form der Umgebung, dann die Regeln darin (ab 0.16, H19).

Aus seinen Regeln liest der Agent ab, welche Form die Umgebung hat:
- Eine Größe, die eine Taste um einen festen Schritt erhöht und eine andere um denselben
  Schritt senkt, ist eine **Raum-Achse**. Die beiden Tasten sind Gegenteile. So viele
  unabhängige Tastenpaare es gibt, so viele Dimensionen hat der Raum (Philipona, O'Regan und
  Nadal 2003: Dimension aus den Folgen eigener Bewegungen).
- Eine Größe, die eine Taste erhöht und eine andere senkt, ohne festen Schritt, ist eine
  **Ordnung**: Man weiß, in welche Richtung es geht, aber nicht, wie weit (Suchbaum, Liste).
- Eine Größe, die keine Taste ändert, ist **fest** (zum Beispiel ein Ziel).

Die Form entscheidet, wie der Agent plant (siehe `planner`): im Raum mit einer Karte, in einer
Ordnung durch Eingrenzen. Die Formen kommen aus einer kleinen festen Liste, wie bei Kemp und
Tenenbaum 2008; der Agent wählt sie, er erfindet keine neuen.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from hekmatki.general.programs import Falls, Keep, Leaf, Program, Rises, Shift, core

type Slot = tuple[int, int]


class AxisKind(StrEnum):
    """Raum-Achse oder Ordnung."""

    SPACE = "Raum"
    ORDER = "Ordnung"


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

    def of_kind(self, kind: AxisKind) -> tuple[Axis, ...]:
        """Nur die Achsen einer Art."""
        return tuple(axis for axis in self.axes if axis.kind is kind)

    @property
    def name(self) -> str:
        """Die Form in Worten."""
        space, order = len(self.of_kind(AxisKind.SPACE)), len(self.of_kind(AxisKind.ORDER))
        if space and order:
            return f"gemischt (Raum mit {space}, Ordnung mit {order} Achsen)"
        if space:
            return f"Raum mit {space} Dimension{'en' if space > 1 else ''}"
        if order:
            return "Ordnung" if order == 1 else f"Ordnung mit {order} Achsen"
        return "unbekannt"


def find_form(
    reliable: Mapping[Slot, Program],
    exact: Mapping[Slot, Program],
    actions: int,
    components: int,
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
    inverse = _step(moves[up]) == -_step(moves[down]) != 0
    return Axis(component, AxisKind.SPACE if inverse else AxisKind.ORDER, up, down)


def _step(effect: Leaf | None) -> int:
    return effect.by if isinstance(effect, Shift) else 0
