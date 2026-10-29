"""Level bauen und lösen: zufällige Labyrinthe und Kisten-Rätsel, kürzester Weg zum Sieg."""

import random
from collections import deque
from collections.abc import Iterator

from hekmatki.grid.world import DIRECTIONS, Cell, Maze, neighbor

ATTEMPTS = 200
"""So oft wird ein neues Level gewürfelt, bis eines lösbar ist."""


def random_maze(
    size: int, rng: random.Random, traps: int = 0, with_key: bool = True, loops: float = 0.15
) -> Maze:
    """Ein zufälliges, lösbares Labyrinth mit `size`×`size` Feldern (ungerade, ab 5).

    Fallen liegen mindestens drei Schritte vom Start entfernt und versperren nie den Weg.
    """
    _check_size(size)
    for _ in range(100):
        floor = _carve(size, rng, loops)
        maze = _furnish(size, floor, rng, traps, with_key)
        if maze is not None and shortest_win(maze) is not None:
            return maze
    raise ValueError(f"Kein lösbares Labyrinth {size}×{size} mit {traps} Fallen gefunden.")


def puzzle_maze(
    size: int, rng: random.Random, traps: int = 0, boxes: int = 1, loops: float = 0.15
) -> Maze:
    """Ein lösbares Kisten-Rätsel: Ein Tor versperrt den einzigen Weg zum Ausgang.

    Das Tor öffnet sich nur, solange etwas auf der Druckplatte steht. Platte und Kisten liegen
    auf der Seite des Starts, die Platte mindestens drei Felder vom Tor entfernt. Die erste
    Kiste steht zwei oder drei Felder vor der Platte, weitere Kisten irgendwo auf der Seite des
    Starts. Die Figur kann nicht zugleich auf der Platte und im Tor stehen, also muss eine
    Kiste auf die Platte.
    """
    _check_size(size)
    if boxes < 1:
        raise ValueError(f"Ein Kisten-Rätsel braucht mindestens eine Kiste, nicht {boxes}.")
    for _ in range(ATTEMPTS):
        floor = _carve(size, rng, loops)
        maze = _arrange(size, floor, rng, traps, boxes)
        if maze is not None and shortest_win(maze) is not None:
            return maze
    raise ValueError(f"Kein lösbares Kisten-Rätsel {size}×{size} mit {boxes} Kisten gefunden.")


def shortest_win(maze: Maze) -> int | None:
    """Kürzeste Zahl von Tastendrücken vom Start bis zum Sieg, ohne Fallen. `None`: unlösbar.

    Breitensuche über alle Zustände (Figur, Kisten, Schlüssel).
    """
    seen = {maze.initial}
    queue = deque([(maze.initial, 0)])
    while queue:
        state, steps = queue.popleft()
        for direction in DIRECTIONS:
            step = maze.advance(state, direction)
            if step.won:
                return steps + 1
            if not step.trapped and step.state not in seen:
                seen.add(step.state)
                queue.append((step.state, steps + 1))
    return None


def _check_size(size: int) -> None:
    if size < 5 or size % 2 == 0:
        raise ValueError(f"Die Größe muss ungerade und mindestens 5 sein, nicht {size}.")


def _carve(size: int, rng: random.Random, loops: float) -> set[Cell]:
    """Gräbt Gänge (Tiefensuche über ungerade Felder) und öffnet ein paar Wände für Schleifen."""
    floor = {(1, 1)}
    stack = [(1, 1)]
    while stack:
        cell = stack[-1]
        jumps = [(cell[0] + 2 * dr, cell[1] + 2 * dc) for dr, dc in DIRECTIONS]
        fresh = [j for j in jumps if 0 < j[0] < size - 1 and 0 < j[1] < size - 1 and j not in floor]
        if not fresh:
            stack.pop()
            continue
        nxt = rng.choice(fresh)
        floor |= {nxt, ((cell[0] + nxt[0]) // 2, (cell[1] + nxt[1]) // 2)}
        stack.append(nxt)
    inner = [(r, c) for r in range(1, size - 1) for c in range(1, size - 1)]
    for cell in inner:
        if cell not in floor and rng.random() < loops and _connects_two(cell, floor):
            floor.add(cell)
    return floor


def _connects_two(cell: Cell, floor: set[Cell]) -> bool:
    """True, wenn die Wand zwei gegenüberliegende Gänge trennt."""
    up, down, left, right = (neighbor(cell, d) in floor for d in DIRECTIONS)
    return (up and down) or (left and right)


def _furnish(
    size: int, floor: set[Cell], rng: random.Random, traps: int, with_key: bool
) -> Maze | None:
    """Verteilt Start, Schlüssel, Tür und Fallen. `None`, wenn die Fallen nicht passen."""
    cells = sorted(floor)
    start, door, key = rng.sample(cells, 3)
    free = [c for c in _far_from(start, cells) if c not in (door, key)]
    if len(free) < traps:
        return None
    return Maze(
        height=size,
        width=size,
        walls=_walls(size, floor),
        start=start,
        door=door,
        key=key if with_key else None,
        traps=frozenset(rng.sample(free, traps)),
    )


def _arrange(
    size: int, floor: set[Cell], rng: random.Random, traps: int, boxes: int
) -> Maze | None:
    """Verteilt Start, Ausgang, Tor, Platte, Kisten und Fallen. `None`, wenn es nicht passt."""
    cells = sorted(floor)
    start, door = rng.sample(cells, 2)
    gates = _far_from(start, _bottlenecks(start, door, floor))
    if not gates:
        return None
    gate = rng.choice(gates)
    home = sorted(_reachable(start, floor - {gate}))
    plates = [c for c in home if c != start and _manhattan(c, gate) >= 3]
    if not plates:
        return None
    plate = rng.choice(plates)
    lanes = _lanes(plate, set(home) - {start})
    if not lanes:
        return None
    lane = rng.choice(lanes)
    places = [c for c in home if c not in {start, *lane} and _manhattan(c, plate) >= 2]
    if len(places) < boxes - 1:
        return None
    box_cells = [lane[-2], *rng.sample(places, boxes - 1)]
    taken = {start, door, gate, plate, *box_cells}
    free = [c for c in _far_from(start, cells) if c not in taken]
    if len(free) < traps:
        return None
    return Maze(
        height=size,
        width=size,
        walls=_walls(size, floor),
        start=start,
        door=door,
        key=None,
        traps=frozenset(rng.sample(free, traps)),
        boxes=frozenset(box_cells),
        plate=plate,
        gate=gate,
    )


def _lanes(plate: Cell, free: set[Cell]) -> list[tuple[Cell, ...]]:
    """Gerade Bahnen zur Platte: Felder vor der Platte, Kiste, dahinter Platz für die Figur.

    Die Kiste steht zwei oder drei Felder vor der Platte und lässt sich geradeaus auf sie
    schieben.
    """
    lanes = []
    for dr, dc in DIRECTIONS:
        for distance in (2, 3):
            lane = tuple((plate[0] - j * dr, plate[1] - j * dc) for j in range(1, distance + 2))
            if set(lane) <= free:
                lanes.append(lane)
    return lanes


def _bottlenecks(start: Cell, goal: Cell, floor: set[Cell]) -> list[Cell]:
    """Felder, ohne die man nicht mehr vom Start zum Ziel kommt (sortiert)."""
    return [
        cell
        for cell in sorted(floor - {start, goal})
        if goal not in _reachable(start, floor - {cell})
    ]


def _reachable(start: Cell, floor: set[Cell]) -> set[Cell]:
    """Alle Felder, die man von `start` aus über `floor` erreicht."""
    seen = {start}
    queue = deque([start])
    while queue:
        for nxt in _neighbors(queue.popleft()):
            if nxt in floor and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _neighbors(cell: Cell) -> Iterator[Cell]:
    return (neighbor(cell, direction) for direction in DIRECTIONS)


def _far_from(start: Cell, cells: list[Cell]) -> list[Cell]:
    """Die Felder, die mindestens drei Schritte (Luftlinie im Raster) vom Start entfernt sind."""
    return [c for c in cells if _manhattan(c, start) >= 3]


def _manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _walls(size: int, floor: set[Cell]) -> frozenset[Cell]:
    return frozenset((r, c) for r in range(size) for c in range(size)) - floor
