"""Was der Agent in einem Spiel über Figur, Tasten und Farben lernt.

Er beginnt ohne jedes Wissen. Bewegt sich nach einem Tastendruck genau ein einzelnes Feld,
ist dessen Farbe seine Figur und die Verschiebung die Richtung der Taste. Kennt er Figur
und Richtung, liest er bei jedem weiteren Schritt die Wirkung der betretenen Farbe ab.
"""

from dataclasses import dataclass, field

from hekmatki.grid.effects import ContradictionError, Effect, Kind, observed_effect
from hekmatki.grid.perception import Movement, Shape, cells_of, color_at, movement, shapes
from hekmatki.grid.world import Cell, Color, Direction, Grid, neighbor


@dataclass
class Knowledge:
    """Gelerntes Wissen über ein Spiel."""

    player: Color | None = None
    controls: dict[str, Direction] = field(default_factory=dict)
    effects: dict[Color, Effect] = field(default_factory=dict)
    shapes: dict[Color, Shape] = field(default_factory=dict)
    """Wie jede Farbe aussah, als der Agent sie zum ersten Mal sah."""

    def position(self, grid: Grid) -> Cell | None:
        """Wo die Figur steht. `None`, solange der Agent seine Figur nicht kennt."""
        if self.player is None:
            return None
        cells = cells_of(grid, self.player)
        if len(cells) != 1:
            raise ContradictionError(f"Die Figur ({self.player}) muss genau ein Feld haben.")
        return cells[0]

    @property
    def triggers(self) -> list[Effect]:
        """Alle bekannten Auslöser-Wirkungen."""
        return [e for e in self.effects.values() if e.kind is Kind.TRIGGER]

    def observe(self, before: Grid, button: str, after: Grid, won: bool) -> None:
        """Lernt aus einem Tastendruck: Figur, Richtung der Taste, Wirkung einer Farbe."""
        for grid in (before, after):
            for color, shape in shapes(grid).items():
                self.shapes.setdefault(color, shape)
        moved = None if won else movement(before, after)
        if moved is not None and self.player is None:
            self.player = moved.color
        if moved is not None and button not in self.controls:
            self._learn_direction(button, moved)
        origin = self.position(before)
        direction = self.controls.get(button)
        if origin is None or direction is None:
            return
        target = neighbor(origin, direction)
        self._remember(
            color_at(before, target), observed_effect(before, after, won, origin, target)
        )

    def _learn_direction(self, button: str, moved: Movement) -> None:
        """Nur ein Schritt auf ein Nachbarfeld verrät die Richtung (nicht ein Sprung zum Start)."""
        shift = (moved.destination[0] - moved.origin[0], moved.destination[1] - moved.origin[1])
        if moved.color == self.player and abs(shift[0]) + abs(shift[1]) == 1:
            self.controls[button] = shift

    def _remember(self, color: Color, effect: Effect) -> None:
        known = self.effects.setdefault(color, effect)
        if known != effect:
            raise ContradictionError(
                f"Farbe {color} wirkte erst „{known.kind}“, jetzt „{effect.kind}“."
            )
