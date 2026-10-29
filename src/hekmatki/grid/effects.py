"""Was das Betreten eines Feldes einer Farbe bewirkt, abgelesen aus zwei Rastern.

Der Agent versucht, auf ein Nachbarfeld zu gehen. Danach vergleicht er die Raster:
- nichts hat sich geändert: die Farbe **blockiert**
- er steht auf dem Feld: die Farbe ist **frei**
- er steht auf dem Feld, und anderswo haben Felder die Farbe gewechselt: **Auslöser**
- er steht ganz woanders: die Farbe schickt ihn **zurück** (zum Start)
- das Spiel meldet einen Sieg: die Farbe ist das **Ziel**
"""

from dataclasses import dataclass
from enum import StrEnum

from hekmatki.grid.perception import changed_cells, color_at, movement
from hekmatki.grid.world import Cell, Color, Grid

Change = tuple[Color, Color]
"""Eine Farbe, die überall zu einer anderen wird."""


class ContradictionError(ValueError):
    """Eine Beobachtung widerspricht dem, was ein Agent sicher zu wissen glaubte."""


class Kind(StrEnum):
    """Die Arten von Wirkungen."""

    BLOCK = "blockiert"
    PASS = "frei"
    TRIGGER = "auslöser"
    RESET = "zurück"
    WIN = "ziel"


@dataclass(frozen=True)
class Effect:
    """Die Wirkung einer Farbe; bei Auslösern dazu, welche Farben wechseln."""

    kind: Kind
    changes: frozenset[Change] = frozenset()

    def __post_init__(self) -> None:
        if bool(self.changes) != (self.kind is Kind.TRIGGER):
            raise ValueError("Nur Auslöser (und alle Auslöser) wechseln Farben.")


def observed_effect(before: Grid, after: Grid, won: bool, origin: Cell, target: Cell) -> Effect:
    """Die Wirkung des Feldes `target`, nachdem die Figur von `origin` dorthin wollte."""
    if won:
        return Effect(Kind.WIN)
    if after == before:
        return Effect(Kind.BLOCK)
    moved = movement(before, after)
    if moved is None or moved.origin != origin:
        raise ContradictionError(f"Die Figur auf {origin} hat sich nicht wie erwartet bewegt.")
    if moved.destination != target:
        return Effect(Kind.RESET)
    others = [cell for cell in changed_cells(before, after) if cell not in (origin, target)]
    changes = frozenset((color_at(before, cell), color_at(after, cell)) for cell in others)
    return Effect(Kind.TRIGGER, changes) if changes else Effect(Kind.PASS)
