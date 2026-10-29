"""Das Spiel der 2D-Welt: ein Labyrinth als Farbraster, wie bei ARC-AGI-3.

Der Agent steuert eine Figur mit vier Tasten durch ein Labyrinth. Wer den Ausgang (die
offene Tür) betritt, gewinnt und beginnt am Start von vorn. Fallen schicken ihn zurück zum
Start. Dazu kommen je nach Level:
- ein **Schlüssel**: Wer ihn betritt, nimmt ihn mit, und die Tür öffnet sich.
- **Kisten**: Läuft die Figur gegen eine Kiste, schiebt sie sie ein Feld weiter, wenn
  dahinter Boden, eine Druckplatte oder ein offenes Tor ist.
- eine **Druckplatte** und ein **Tor**: Das Tor ist offen, solange die Figur oder eine Kiste
  auf der Platte steht.

Fallen setzen Figur und Kisten an ihren Startplatz zurück; ein genommener Schlüssel bleibt
genommen. Ab 0.14 kann ein Spiel eine **Neustart-Taste** haben wie ARC-AGI-3: Sie stellt das
Level wieder auf den Anfang und kostet wie jede Taste einen Druck. Anders als die anderen
Tasten ist sie dem Agenten bekannt (in ARC-AGI-3 heißt sie RESET).

Ab 0.15 kann ein Level **fremde Mechanik** haben (`Mechanics`), für die Gegenprobe: Die
Druckplatte schließt das Tor, statt es zu öffnen, oder die Figur rutscht wie auf Eis über
den Boden, bis etwas sie aufhält. Das Rutschen passt in keine der Regelarten, die der
Modell-Agent kennt.

Jedes Spiel hat eigene Farben und eine eigene Tastenbelegung. Der Agent sieht nur das
Raster aus Farbnamen. Was welche Farbe bedeutet, muss er selbst herausfinden.
"""

import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

Color = str
Cell = tuple[int, int]
"""(Zeile, Spalte)."""
Grid = tuple[tuple[Color, ...], ...]
"""Was der Agent sieht: eine Farbe pro Feld."""
Direction = tuple[int, int]

UP: Direction = (-1, 0)
DOWN: Direction = (1, 0)
LEFT: Direction = (0, -1)
RIGHT: Direction = (0, 1)
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)

PALETTE = ("schwarz", "blau", "rot", "grün", "gelb", "grau", "pink", "orange", "türkis", "braun")
"""Die zehn Farben von ARC."""
BUTTON_NAMES = tuple(f"taste {n}" for n in range(1, 10))
"""Mögliche Namen für Tasten."""


class Tile(StrEnum):
    """Was ein Feld in Wahrheit ist. Das weiß nur das Spiel, nicht der Agent."""

    FLOOR = "boden"
    WALL = "wand"
    KEY = "schlüssel"
    DOOR = "tür"
    OPEN_DOOR = "offene tür"
    TRAP = "falle"
    PLAYER = "spieler"
    BOX = "kiste"
    PLATE = "druckplatte"
    GATE = "tor"
    OPEN_GATE = "offenes tor"


CLASSIC_TILES = (
    Tile.FLOOR,
    Tile.WALL,
    Tile.KEY,
    Tile.DOOR,
    Tile.OPEN_DOOR,
    Tile.TRAP,
    Tile.PLAYER,
)
"""Die Feldarten der Labyrinthe aus Ergebnis 13."""
PUZZLE_TILES = (
    Tile.FLOOR,
    Tile.WALL,
    Tile.OPEN_DOOR,
    Tile.TRAP,
    Tile.PLAYER,
    Tile.BOX,
    Tile.PLATE,
    Tile.GATE,
    Tile.OPEN_GATE,
)
"""Die Feldarten der Kisten-Rätsel (der Ausgang ist immer offen, es gibt keinen Schlüssel)."""
BOX_CAN_ENTER = frozenset({Tile.FLOOR, Tile.PLATE, Tile.OPEN_GATE})
"""Wohin eine Kiste geschoben werden kann."""


def neighbor(cell: Cell, direction: Direction) -> Cell:
    """Das Nachbarfeld in einer Richtung."""
    return cell[0] + direction[0], cell[1] + direction[1]


@dataclass(frozen=True)
class GridState:
    """Der verborgene Zustand: wo Figur und Kisten stehen und ob der Schlüssel genommen ist."""

    position: Cell
    has_key: bool
    boxes: frozenset[Cell] = frozenset()


@dataclass(frozen=True)
class Step:
    """Was ein Tastendruck bewirkt hat."""

    state: GridState
    won: bool = False
    trapped: bool = False
    restarted: bool = False


@dataclass(frozen=True)
class Mechanics:
    """Abweichungen von den üblichen Regeln der 2D-Welt (ab 0.15, für die Gegenprobe)."""

    plate_closes: bool = False
    """Das Tor ist offen, solange nichts auf der Druckplatte steht."""
    ice: bool = False
    """Betritt die Figur Boden, rutscht sie weiter, bis sie auf etwas anderes trifft."""


@dataclass(frozen=True)
class Maze:
    """Der Bauplan eines Levels und seine Regeln. Der Rand besteht immer aus Wand."""

    height: int
    width: int
    walls: frozenset[Cell]
    start: Cell
    door: Cell
    key: Cell | None
    """`None`: Die Tür ist von Anfang an offen."""
    traps: frozenset[Cell] = frozenset()
    boxes: frozenset[Cell] = frozenset()
    """Wo die Kisten zu Beginn stehen."""
    plate: Cell | None = None
    gate: Cell | None = None
    """Offen, solange die Druckplatte belastet ist. Platte und Tor gibt es nur zusammen.

    Ab 0.15 darf eine Kiste schon zu Beginn auf der Platte stehen.
    """
    mechanics: Mechanics = Mechanics()

    def __post_init__(self) -> None:
        if self.height < 3 or self.width < 3:
            raise ValueError(f"Ein Labyrinth braucht mindestens 3×3 Felder, nicht {self.size}.")
        if not self.border <= self.walls:
            raise ValueError("Der Rand des Labyrinths muss ganz aus Wand bestehen.")
        if (self.plate is None) != (self.gate is None):
            raise ValueError("Druckplatte und Tor gibt es nur zusammen.")
        optional = [self.key, self.plate, self.gate]
        special = [self.start, self.door, *self.traps, *(self.boxes - {self.plate})]
        special += [cell for cell in optional if cell is not None]  # Kiste auf Platte geht.
        if len(set(special)) != len(special):
            raise ValueError(
                "Start, Tür, Schlüssel, Fallen und Kisten brauchen verschiedene Felder."
            )
        if any(not self.inside(cell) or cell in self.walls for cell in special):
            raise ValueError(
                "Start, Tür, Schlüssel, Fallen und Kisten müssen auf freien Feldern liegen."
            )

    @property
    def size(self) -> str:
        """Größe als Text, etwa „9×9“."""
        return f"{self.height}×{self.width}"

    @property
    def border(self) -> frozenset[Cell]:
        """Alle Randfelder."""
        last_row, last_column = self.height - 1, self.width - 1
        cells = [(r, c) for r in range(self.height) for c in range(self.width)]
        return frozenset((r, c) for r, c in cells if r in (0, last_row) or c in (0, last_column))

    @property
    def tiles(self) -> tuple[Tile, ...]:
        """Die Feldarten, die in diesem Level zu sehen sein können."""
        used = {Tile.FLOOR, Tile.WALL, Tile.PLAYER, Tile.OPEN_DOOR}
        if self.key is not None:
            used |= {Tile.KEY, Tile.DOOR}
        if self.traps:
            used.add(Tile.TRAP)
        if self.boxes:
            used.add(Tile.BOX)
        if self.plate is not None:
            used |= {Tile.PLATE, Tile.GATE, Tile.OPEN_GATE}
        return tuple(tile for tile in Tile if tile in used)

    @property
    def initial(self) -> GridState:
        """Der Zustand zu Beginn jeder Runde."""
        return GridState(self.start, has_key=False, boxes=self.boxes)

    def inside(self, cell: Cell) -> bool:
        """Liegt das Feld im Labyrinth?"""
        return 0 <= cell[0] < self.height and 0 <= cell[1] < self.width

    def tile(self, cell: Cell, state: GridState) -> Tile:
        """Was das Feld im Zustand `state` ist (ohne Figur und Kisten)."""
        if cell in self.walls:
            return Tile.WALL
        if cell == self.door:
            return Tile.OPEN_DOOR if self.door_open(state.has_key) else Tile.DOOR
        if cell == self.key and not state.has_key:
            return Tile.KEY
        if cell == self.plate:
            return Tile.PLATE
        if cell == self.gate:
            return Tile.OPEN_GATE if self.gate_open(state) else Tile.GATE
        return Tile.TRAP if cell in self.traps else Tile.FLOOR

    def door_open(self, has_key: bool) -> bool:
        """Offen, wenn der Schlüssel genommen wurde oder es keinen gibt."""
        return has_key or self.key is None

    def pressed(self, state: GridState) -> bool:
        """Steht die Figur oder eine Kiste auf der Druckplatte?"""
        return self.plate is not None and (
            self.plate == state.position or self.plate in state.boxes
        )

    def gate_open(self, state: GridState) -> bool:
        """Ist das Tor offen? Üblich: wenn die Platte belastet ist; sonst umgekehrt."""
        return self.pressed(state) != self.mechanics.plate_closes

    def advance(self, state: GridState, direction: Direction) -> Step:
        """Die Figur versucht, in `direction` zu gehen (auf Eis rutscht sie weiter)."""
        step = self._advance_once(state, direction)
        while self.mechanics.ice and self._slides(state, step, direction):
            state, step = step.state, self._advance_once(step.state, direction)
        return step

    def _slides(self, before: GridState, step: Step, direction: Direction) -> bool:
        """Rutscht die Figur nach diesem Schritt weiter? Nur auf Boden und nie in eine Kiste."""
        after = step.state
        moved = after.position == neighbor(before.position, direction)
        plain = moved and after.boxes == before.boxes and not (step.won or step.trapped)
        ahead = neighbor(after.position, direction)
        return plain and self.tile(after.position, after) is Tile.FLOOR and ahead not in after.boxes

    def _advance_once(self, state: GridState, direction: Direction) -> Step:
        """Ein einzelner Schritt in `direction`."""
        target = neighbor(state.position, direction)
        if target in state.boxes:
            return self._push(state, target, neighbor(target, direction))
        match self.tile(target, state):
            case Tile.WALL | Tile.DOOR | Tile.GATE:
                return Step(state)
            case Tile.OPEN_DOOR:
                return Step(self.initial, won=True)
            case Tile.TRAP:
                return Step(replace(self.initial, has_key=state.has_key), trapped=True)
            case Tile.KEY:
                return Step(replace(state, position=target, has_key=True))
            case _:
                return Step(replace(state, position=target))

    def _push(self, state: GridState, box: Cell, behind: Cell) -> Step:
        """Schiebt die Kiste auf `box` nach `behind`, wenn dort Platz ist."""
        if behind in state.boxes or self.tile(behind, state) not in BOX_CAN_ENTER:
            return Step(state)
        boxes = state.boxes - {box} | {behind}
        return Step(replace(state, position=box, boxes=boxes))


@dataclass(frozen=True)
class GridGame:
    """Ein Level: Bauplan plus Farben plus Tastenbelegung."""

    name: str
    maze: Maze
    colors: Mapping[Tile, Color]
    """Darf mehr Feldarten enthalten, als das Level zeigt (Farben eines ganzen Spiels)."""
    controls: Mapping[str, Direction]
    restart: str | None = None
    """Name der Neustart-Taste (`None`: Das Spiel hat keine)."""

    def __post_init__(self) -> None:
        if self.restart is not None and self.restart in self.controls:
            raise ValueError(f"{self.name}: Die Neustart-Taste darf keine Richtung haben.")
        if not set(self.maze.tiles) <= set(self.colors):
            raise ValueError(f"{self.name}: Jede Feldart braucht eine eigene Farbe.")
        if len(set(self.colors.values())) != len(self.colors):
            raise ValueError(f"{self.name}: Jede Feldart braucht eine eigene Farbe.")
        if sorted(self.controls.values()) != sorted(DIRECTIONS):
            raise ValueError(f"{self.name}: Jede Richtung braucht genau eine Taste.")

    @property
    def buttons(self) -> tuple[str, ...]:
        """Die Richtungstasten, sortiert (ohne Neustart-Taste)."""
        return tuple(sorted(self.controls))

    @property
    def start(self) -> GridState:
        """Der Zustand zu Beginn jeder Runde."""
        return self.maze.initial

    def render(self, state: GridState) -> Grid:
        """Was der Agent im Zustand `state` sieht. Die Figur verdeckt Kisten, Kisten Felder."""
        maze = self.maze

        def color(cell: Cell) -> Color:
            if cell == state.position:
                return self.colors[Tile.PLAYER]
            if cell in state.boxes:
                return self.colors[Tile.BOX]
            return self.colors[maze.tile(cell, state)]

        return tuple(tuple(color((r, c)) for c in range(maze.width)) for r in range(maze.height))

    def step(self, state: GridState, button: str) -> Step:
        """Führt einen Tastendruck aus. Nach einem Sieg steht die Figur wieder am Start."""
        if button == self.restart:
            return Step(self.start, restarted=True)
        if button not in self.controls:
            raise ValueError(f"{self.name}: Unbekannte Taste {button!r}.")
        return self.maze.advance(state, self.controls[button])


def random_colors(tiles: Iterable[Tile], rng: random.Random) -> dict[Tile, Color]:
    """Jede Feldart bekommt eine eigene zufällige Farbe."""
    tiles = tuple(tiles)
    if len(tiles) > len(PALETTE):
        raise ValueError(f"{len(tiles)} Feldarten, aber nur {len(PALETTE)} Farben.")
    return dict(zip(tiles, rng.sample(PALETTE, len(tiles)), strict=True))


def random_controls(rng: random.Random) -> dict[str, Direction]:
    """Vier zufällige Tastennamen für die vier Richtungen."""
    return dict(zip(rng.sample(BUTTON_NAMES, len(DIRECTIONS)), DIRECTIONS, strict=True))


def make_grid_game(name: str, maze: Maze, rng: random.Random) -> GridGame:
    """Ein Level mit eigenen zufälligen Farben und Tasten.

    Labyrinthe ohne neue Feldarten bekommen wie in Ergebnis 13 Farben für alle sieben alten
    Feldarten, damit dieselben Zufallszahlen dieselben Spiele ergeben.
    """
    classic = set(maze.tiles) <= set(CLASSIC_TILES)
    colors = random_colors(CLASSIC_TILES if classic else maze.tiles, rng)
    return GridGame(name, maze, colors, random_controls(rng))
