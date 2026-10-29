"""Ein kleines Rätsel-Level für die Tests des Weltmodells und des Rollen-Weltmodells."""

from hekmatki.grid.world import DOWN, LEFT, RIGHT, UP, GridGame, Maze, Tile

# S = Start, B = Kiste, P = Druckplatte, G = Tor, E = Ausgang, T = Falle
PUZZLE = (
    "#######",
    "#S.B.P#",
    "#.###.#",
    "#.....#",
    "###G#T#",
    "#E....#",
    "#######",
)
COLORS = {
    Tile.FLOOR: "grau",
    Tile.WALL: "schwarz",
    Tile.OPEN_DOOR: "grün",
    Tile.TRAP: "rot",
    Tile.PLAYER: "blau",
    Tile.BOX: "braun",
    Tile.PLATE: "gelb",
    Tile.GATE: "pink",
    Tile.OPEN_GATE: "türkis",
}
BORDER = frozenset((r, c) for r in range(5) for c in range(5) if r in (0, 4) or c in (0, 4))
CONTROLS = {"hoch": UP, "runter": DOWN, "links": LEFT, "rechts": RIGHT}
SOLUTION = ["rechts", "rechts", "rechts", "links", "links", "links", "runter", "runter"]
SOLUTION += ["rechts", "rechts", "runter", "runter", "links", "links"]
PLATE_TOUR = ["runter", "runter", "rechts", "rechts", "rechts", "rechts", "hoch", "hoch", "runter"]
"""Ohne Kiste auf die Druckplatte und wieder herunter."""
FULL_TOUR = [*SOLUTION, *PLATE_TOUR, "rechts"]
BESIDE_PLATE = (
    "#######",
    "#PS.B.#",
    "#.###.#",
    "#.....#",
    "###G###",
    "#E....#",
    "#######",
)
"""Der Start liegt neben der Druckplatte: Der erste Schritt deckt zwei neue Farben auf und zu."""


def maze_of(rows: tuple[str, ...]) -> Maze:
    """Ein Labyrinth aus Textzeilen (Zeichen wie in `PUZZLE`)."""
    cells = {(r, c): char for r, row in enumerate(rows) for c, char in enumerate(row)}

    def where(char: str) -> list[tuple[int, int]]:
        return [cell for cell, found in cells.items() if found == char]

    return Maze(
        height=len(rows),
        width=len(rows[0]),
        walls=frozenset(where("#")),
        start=where("S")[0],
        door=where("E")[0],
        key=None,
        traps=frozenset(where("T")),
        boxes=frozenset(where("B")),
        plate=next(iter(where("P")), None),
        gate=next(iter(where("G")), None),
    )


def puzzle_game(maze: Maze | None = None) -> GridGame:
    return GridGame("Rätsel", maze or maze_of(PUZZLE), COLORS, CONTROLS)
