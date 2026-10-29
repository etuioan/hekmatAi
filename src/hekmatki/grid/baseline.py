"""Zum Vergleich: der Entdecker aus Ergebnis 10, für den jedes Raster ein eigener Zustand ist.

Er lernt, wohin jede Taste von jedem gesehenen Bild aus führt. Dass Wände überall gleich
aussehen, kann er nicht nutzen: Jedes neue Bild ist für ihn völlig neu.
"""

import random
from collections.abc import Sequence

from hekmatki.explorer import Explorer
from hekmatki.grid.world import Color, Grid
from hekmatki.puzzle import WIN


class StateAgent:
    """Der alte Entdecker, angeschlossen an die 2D-Welt."""

    def __init__(self, buttons: Sequence[str], start: Grid) -> None:
        self.explorer = Explorer(buttons, _symbol(start))

    @property
    def reason(self) -> str:
        """Er hat nur einen Grund: seine Tabelle der gesehenen Bilder."""
        return f"kennt {self.known_states} Bilder, keine Farben"

    @property
    def known_states(self) -> int:
        """Wie viele verschiedene Bilder er schon gesehen hat."""
        model = self.explorer.model
        return len({state for state, _ in model} | set(model.values()) - {WIN})

    def choose(self, grid: Grid, rng: random.Random, steps_left: int) -> str:
        """Wählt die nächste Taste wie der Entdecker."""
        return self.explorer.choose(_symbol(grid), rng, steps_left)

    def learn(self, before: Grid, button: str, after: Grid, won: bool) -> None:
        """Merkt sich den Übergang zwischen zwei Bildern."""
        self.explorer.learn(_symbol(before), button, WIN if won else _symbol(after))

    def beliefs(self) -> dict[Color, str]:
        """Über Farben weiß er nichts."""
        return {}


def _symbol(grid: Grid) -> str:
    """Ein ganzes Raster als ein einziges Symbol."""
    return "/".join(",".join(row) for row in grid)
