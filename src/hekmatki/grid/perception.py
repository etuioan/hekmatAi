"""Was der Agent in einem Raster erkennen kann, ohne zu wissen, was die Farben bedeuten."""

from collections import Counter
from dataclasses import dataclass

from hekmatki.grid.world import Cell, Color, Grid


@dataclass(frozen=True)
class Shape:
    """Wie eine Farbe im Raster vorkommt: auf genau einem Feld? am Rand?"""

    single: bool
    border: bool

    def __str__(self) -> str:
        amount = "ein Feld" if self.single else "mehrere Felder"
        return f"{amount}, {'am Rand' if self.border else 'innen'}"


@dataclass(frozen=True)
class Movement:
    """Eine Farbe, deren einziges Feld sich bewegt hat."""

    color: Color
    origin: Cell
    destination: Cell


def cells_of(grid: Grid, color: Color) -> list[Cell]:
    """Alle Felder mit dieser Farbe."""
    return [(r, c) for r, row in enumerate(grid) for c, value in enumerate(row) if value == color]


def color_at(grid: Grid, cell: Cell) -> Color:
    """Die Farbe eines Feldes."""
    return grid[cell[0]][cell[1]]


def changed_cells(before: Grid, after: Grid) -> list[Cell]:
    """Alle Felder, deren Farbe sich geändert hat."""
    if [len(row) for row in before] != [len(row) for row in after]:
        raise ValueError("Die Raster sind verschieden groß.")
    return [
        (r, c)
        for r, (old, new) in enumerate(zip(before, after, strict=True))
        for c, (a, b) in enumerate(zip(old, new, strict=True))
        if a != b
    ]


def movement(before: Grid, after: Grid) -> Movement | None:
    """Die erste Farbe, die vorher und nachher genau ein Feld hat, aber ein anderes."""
    moved = movements(before, after)
    return moved[0] if moved else None


def movements(before: Grid, after: Grid) -> list[Movement]:
    """Alle Farben, die vorher und nachher genau ein Feld haben, aber ein anderes (sortiert)."""
    found = []
    for color in sorted(_counts(before).keys() & _counts(after).keys()):
        old, new = cells_of(before, color), cells_of(after, color)
        if len(old) == 1 and len(new) == 1 and old != new:
            found.append(Movement(color, old[0], new[0]))
    return found


def shapes(grid: Grid) -> dict[Color, Shape]:
    """Für jede Farbe im Raster: wie sie vorkommt."""
    counts = _counts(grid)
    border = {*grid[0], *grid[-1], *(row[0] for row in grid), *(row[-1] for row in grid)}
    return {color: Shape(counts[color] == 1, color in border) for color in counts}


def _counts(grid: Grid) -> Counter[Color]:
    return Counter(value for row in grid for value in row)
