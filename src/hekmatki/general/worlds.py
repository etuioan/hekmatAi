"""Drei ganz verschiedene Welten hinter derselben Schnittstelle (ab 0.16).

- `Lattice`: ein Raum aus Zellen mit beliebig vielen Dimensionen (2D: Raster, 3D: Würfel),
  mit Hindernissen. Innere Beobachtung: Position, je Richtung „versperrt?“, Zielposition.
  Tasten: je Dimension vor und zurück. Auf Wunsch rutschig: Ein Schritt geht manchmal nicht.
- `SortedSearch`: ein sortierter Datenbestand mit bis zu einer Million Schlüsseln und mehr,
  durchsucht über einen Suchbaum. Innere Beobachtung: Schlüssel hier, gesuchter Schlüssel,
  „ganz unten?“, „ganz oben?“. Tasten: links hinab, rechts hinab, hinauf.

Für den Agenten sind beide nur Zahlen und Tasten (siehe `env`). Die Namen hier sind für uns.
"""

import random
from collections import deque
from collections.abc import Iterator
from typing import Final

from hekmatki.general.env import Observation, Outcome, Wiring

type Cell = tuple[int, ...]

KEY_SPACING: Final = 1000
"""Abstand der Schlüssel: Schlüssel i liegt zwischen 1000·i und 1000·i + 999."""


class Lattice:
    """Ein Raum aus Zellen mit `dims` Dimensionen und Kantenlänge `size`."""

    def __init__(
        self,
        dims: int,
        size: int,
        blocked: frozenset[Cell],
        wiring: Wiring,
        slip: float = 0.0,
    ) -> None:
        if dims < 1 or size < 2:
            raise ValueError("Ein Raum braucht mindestens eine Dimension und Kantenlänge 2.")
        if not 0.0 <= slip < 1.0:
            raise ValueError(f"Rutschen muss zwischen 0 und 1 liegen, nicht {slip}.")
        if len(wiring.components) != 4 * dims or len(wiring.actions) != 2 * dims:
            raise ValueError("Die Mischung passt nicht zur Zahl der Dimensionen.")
        self.dims, self.size, self.blocked, self.wiring, self.slip = (
            dims,
            size,
            blocked,
            wiring,
            slip,
        )
        self.free = [cell for cell in _cells(dims, size) if cell not in blocked]
        if len(self.free) < 2 or len(_reachable(self, self.free[0])) != len(self.free):
            raise ValueError("Die freien Zellen müssen zusammenhängen (mindestens zwei).")
        self.position: Cell = self.free[0]
        self.goal: Cell = self.free[1]

    @property
    def actions(self) -> int:
        """Je Dimension eine Taste vor und eine zurück."""
        return 2 * self.dims

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde: Start und Ziel zufällig auf freien Zellen."""
        self.position, self.goal = rng.sample(self.free, 2)
        return self._observe()

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Ein Schritt, falls die Nachbarzelle frei ist (und man nicht rutscht)."""
        axis, backwards = divmod(self.wiring.inner_action(action), 2)
        target = _neighbour(self.position, axis, -1 if backwards else 1)
        slipped = self.slip > 0.0 and rng.random() < self.slip
        if not slipped and self.is_free(target):
            self.position = target
        return Outcome(self._observe(), self.position == self.goal)

    def least_steps(self) -> int:
        """Kürzester Weg von der jetzigen Zelle zum Ziel (direkt nach `reset`: vom Start)."""
        return _reachable(self, self.position)[self.goal]

    def names(self) -> tuple[list[str], list[str]]:
        """Namen der inneren Größen und Handlungen, nur für uns (der Agent sieht sie nie)."""
        axes = "xyzw"[: self.dims] if self.dims <= 4 else [f"a{i}" for i in range(self.dims)]
        sensors = [f"Wand {sign}{axis}" for axis in axes for sign in "+−"]
        components = [f"Position {a}" for a in axes] + sensors + [f"Ziel {a}" for a in axes]
        return components, [f"{sign}{axis}" for axis in axes for sign in "+−"]

    def is_free(self, cell: Cell) -> bool:
        """Liegt die Zelle im Raum und ist frei?"""
        return all(0 <= c < self.size for c in cell) and cell not in self.blocked

    def _observe(self) -> Observation:
        sensors = [
            int(not self.is_free(_neighbour(self.position, axis, sign)))
            for axis in range(self.dims)
            for sign in (1, -1)
        ]
        return self.wiring.observe([*self.position, *sensors, *self.goal])


def random_lattice(
    dims: int,
    size: int,
    wiring: Wiring,
    rng: random.Random,
    obstacles: float = 0.2,
    slip: float = 0.0,
) -> Lattice:
    """Ein Raum mit etwa `obstacles` Anteil Hindernissen, die die freien Zellen nicht trennen."""
    if not 0.0 <= obstacles < 0.5:
        raise ValueError(f"Hindernisanteil muss zwischen 0 und 0,5 liegen, nicht {obstacles}.")
    cells = list(_cells(dims, size))
    rng.shuffle(cells)
    blocked: set[Cell] = set()
    for cell in cells[: round(obstacles * len(cells))]:
        blocked.add(cell)
        free = [c for c in cells if c not in blocked]
        if len(_reachable_cells(dims, size, blocked, free[0])) != len(free):
            blocked.remove(cell)  # Würde den Raum zerteilen.
    return Lattice(dims, size, frozenset(blocked), wiring, slip)


class SortedSearch:
    """Ein sortierter Datenbestand mit 2^height - 1 Schlüsseln, als Suchbaum begehbar."""

    LEFT, RIGHT, UP = 0, 1, 2

    def __init__(self, height: int, wiring: Wiring, seed: int = 0) -> None:
        if height < 2:
            raise ValueError("Der Suchbaum braucht mindestens zwei Ebenen.")
        if len(wiring.components) != 4 or len(wiring.actions) != 3:
            raise ValueError("Die Mischung passt nicht zur Suche (4 Größen, 3 Tasten).")
        self.height, self.wiring, self.seed = height, wiring, seed
        self.count = 2**height - 1
        self.path: list[tuple[int, int]] = [(0, self.count - 1)]
        self.target = 0

    @property
    def actions(self) -> int:
        """Links hinab, rechts hinab, hinauf."""
        return 3

    def key(self, index: int) -> int:
        """Der Schlüssel an Stelle `index` der sortierten Liste (wird nie gespeichert)."""
        return index * KEY_SPACING + (index * 2_654_435_761 + self.seed) % KEY_SPACING

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde: oben beginnen, ein zufälliger vorhandener Schlüssel wird gesucht."""
        self.path = [(0, self.count - 1)]
        self.target = rng.randrange(self.count)
        while self.target == self._here():
            self.target = rng.randrange(self.count)
        return self._observe()

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Einen Schritt im Suchbaum; am Rand bleibt alles, wie es ist."""
        low, high = self.path[-1]
        middle = (low + high) // 2
        match self.wiring.inner_action(action):
            case self.LEFT if low < middle:
                self.path.append((low, middle - 1))
            case self.RIGHT if middle < high:
                self.path.append((middle + 1, high))
            case self.UP if len(self.path) > 1:
                self.path.pop()
            case _:
                pass
        return Outcome(self._observe(), self._here() == self.target)

    def least_steps(self) -> int:
        """Wie viele Schritte die binäre Suche von oben (Start jeder Runde) bis zum Ziel braucht."""
        low, high = self.interval(self.target)
        return self.height - (high - low + 1).bit_length()  # Teilbaum mit 2^k - 1 Schlüsseln.

    def names(self) -> tuple[list[str], list[str]]:
        """Namen der inneren Größen und Handlungen, nur für uns (der Agent sieht sie nie)."""
        components = ["Schlüssel hier", "gesuchter Schlüssel", "ganz unten", "ganz oben"]
        return components, ["links hinab", "rechts hinab", "hinauf"]

    def interval(self, index: int) -> tuple[int, int]:
        """Der Bereich der sortierten Liste, den der Knoten an Stelle `index` überblickt."""
        low, high = 0, self.count - 1
        while (middle := (low + high) // 2) != index:
            low, high = (low, middle - 1) if index < middle else (middle + 1, high)
        return low, high

    def _here(self) -> int:
        low, high = self.path[-1]
        return (low + high) // 2

    def _observe(self) -> Observation:
        low, high = self.path[-1]
        inner = [self.key(self._here()), self.key(self.target), int(low == high)]
        return self.wiring.observe([*inner, int(len(self.path) == 1)])


def _cells(dims: int, size: int) -> Iterator[Cell]:
    if dims == 0:
        yield ()
        return
    for rest in _cells(dims - 1, size):
        for value in range(size):
            yield (*rest, value)


def _neighbour(cell: Cell, axis: int, sign: int) -> Cell:
    return tuple(c + sign if index == axis else c for index, c in enumerate(cell))


def _reachable(lattice: Lattice, start: Cell) -> dict[Cell, int]:
    return _reachable_cells(lattice.dims, lattice.size, lattice.blocked, start)


def _reachable_cells(
    dims: int, size: int, blocked: set[Cell] | frozenset[Cell], start: Cell
) -> dict[Cell, int]:
    """Breitensuche: Abstand jeder erreichbaren freien Zelle vom Start."""
    distance = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for axis in range(dims):
            for sign in (1, -1):
                nxt = _neighbour(cell, axis, sign)
                inside = all(0 <= c < size for c in nxt)
                if inside and nxt not in blocked and nxt not in distance:
                    distance[nxt] = distance[cell] + 1
                    queue.append(nxt)
    return distance
