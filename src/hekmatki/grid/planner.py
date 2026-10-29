"""Wege im Raster planen, mit dem, was der Agent über die Farben weiß oder vermutet.

Gesucht wird der kürzeste Weg (Breitensuche). Ein Suchzustand ist das Feld der Figur plus
die Farbwechsel, die unterwegs ausgelöst wurden. Farben mit unbekannter Wirkung, Wände und
Fallen betritt der Plan nicht, er kann aber gezielt *bis vor* eine unbekannte Farbe führen.
"""

from collections import deque
from collections.abc import Callable, Mapping

from hekmatki.grid.effects import Change, Effect, Kind
from hekmatki.grid.perception import color_at
from hekmatki.grid.world import Cell, Color, Direction, Grid, neighbor

EffectOf = Callable[[Color], Effect | None]
"""Was der Agent über die Wirkung einer Farbe weiß (`None`: nichts)."""
Wanted = Callable[[Effect | None], bool]
"""Welcher Schritt das Ziel der Suche ist."""

_PASS = Effect(Kind.PASS)
_State = tuple[Cell, frozenset[Change]]


def is_win(effect: Effect | None) -> bool:
    """Der Schritt gewinnt."""
    return effect is not None and effect.kind is Kind.WIN


def is_unknown(effect: Effect | None) -> bool:
    """Der Schritt betritt eine Farbe, deren Wirkung niemand kennt."""
    return effect is None


def find_path(
    grid: Grid,
    origin: Cell,
    controls: Mapping[str, Direction],
    effect_of: EffectOf,
    wanted: Wanted,
) -> list[str] | None:
    """Kürzeste Tastenfolge, deren letzter Schritt `wanted` erfüllt. `None`, wenn es keine gibt.

    Das Feld, auf dem die Figur steht, gilt als frei: Sie steht ja darauf.
    """
    start: _State = (origin, frozenset())
    seen = {start}
    queue: deque[tuple[_State, list[str]]] = deque([(start, [])])
    while queue:
        (cell, changes), path = queue.popleft()
        for button in sorted(controls):
            target = neighbor(cell, controls[button])
            if not (0 <= target[0] < len(grid) and 0 <= target[1] < len(grid[0])):
                continue
            effect = _PASS if target == origin else effect_of(_color(grid, target, changes))
            if wanted(effect):
                return [*path, button]
            following = _following(effect, target, changes)
            if following is not None and following not in seen:
                seen.add(following)
                queue.append((following, [*path, button]))
    return None


def _color(grid: Grid, cell: Cell, changes: frozenset[Change]) -> Color:
    """Die Farbe eines Feldes, nachdem die ausgelösten Farbwechsel gewirkt haben."""
    color = color_at(grid, cell)
    return next((new for old, new in changes if old == color), color)


def _following(effect: Effect | None, target: Cell, changes: frozenset[Change]) -> _State | None:
    """Wo die Suche nach diesem Schritt weitergeht. `None`, wenn dort nicht."""
    if effect is None or effect.kind not in (Kind.PASS, Kind.TRIGGER):
        return None
    return target, changes | effect.changes
