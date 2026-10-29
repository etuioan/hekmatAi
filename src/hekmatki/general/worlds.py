"""Ganz verschiedene Welten hinter derselben Schnittstelle (ab 0.16, mehr ab 0.17).

- `Lattice`: ein Raum aus Zellen mit beliebig vielen Dimensionen (2D: Raster, 3D: Würfel),
  mit Hindernissen. Innere Beobachtung: Position, je Richtung „versperrt?“, Zielposition.
  Tasten: je Dimension vor und zurück. Auf Wunsch rutschig: Ein Schritt geht manchmal nicht.
  Ab 0.17 auf Wunsch aus Eis: Die Figur rutscht, bis eine Wand sie stoppt (wie in 0.15).
  Runden beginnen und enden dann im Spielgebiet, aus dem keine Rutschpartie hinausführt.
- `SortedSearch`: ein sortierter Datenbestand mit bis zu einer Million Schlüsseln und mehr,
  durchsucht über einen Suchbaum. Innere Beobachtung: Schlüssel hier, gesuchter Schlüssel,
  „ganz unten?“, „ganz oben?“. Tasten: links hinab, rechts hinab, hinauf.
- `Dials` (ab 0.17): Drehscheiben wie bei einem Zahlenschloss. Nach dem letzten Wert kommt
  der erste. Innere Beobachtung: Stellung jeder Scheibe, Zielstellung. Tasten: je Scheibe
  vor und zurück. Die Form ist ein Produkt von Ringen.
- `Shuffle` (ab 0.17): Plätze mit Steinen, die man nur mit dem Nachbarn tauschen kann, bis
  die Reihenfolge stimmt. Innere Beobachtung: Stein auf jedem Platz, Zielreihenfolge. Diese
  Welt hat keine Achsen: Keine Größe wird von einer Taste stetig erhöht und einer anderen
  gesenkt. Sie prüft, ob der Agent ohne bekannte Form zurechtkommt.

Für den Agenten sind alle nur Zahlen und Tasten (siehe `env`). Die Namen hier sind für uns.
"""

import random
from collections import deque
from collections.abc import Iterator, Set
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
        ice: bool = False,
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
        self.ice = ice
        self.free = [cell for cell in _cells(dims, size) if cell not in blocked]
        if len(self.free) < 2 or len(_reachable(self, self.free[0])) != len(self.free):
            raise ValueError("Die freien Zellen müssen zusammenhängen (mindestens zwei).")
        area = _ice_area(dims, size, blocked) if ice else set(self.free)
        if area is None or len(area) < 2:
            raise ValueError("Auf diesem Eis gibt es Fallen oder kein Spielgebiet.")
        self.places = sorted(area)
        """Wo Runden beginnen und enden: alle freien Zellen, auf Eis das Spielgebiet."""
        self.position: Cell = self.places[0]
        self.goal: Cell = self.places[1]

    @property
    def actions(self) -> int:
        """Je Dimension eine Taste vor und eine zurück."""
        return 2 * self.dims

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde: Start und Ziel zufällig im Spielgebiet."""
        self.position, self.goal = rng.sample(self.places, 2)
        return self._observe()

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Ein Schritt, falls die Nachbarzelle frei ist (und man nicht rutscht). Auf Eis
        weiter, bis die nächste Zelle versperrt ist."""
        axis, backwards = divmod(self.wiring.inner_action(action), 2)
        sign = -1 if backwards else 1
        slipped = self.slip > 0.0 and rng.random() < self.slip
        if not slipped:
            self.position = self._move(self.position, axis, sign)
        return Outcome(self._observe(), self.position == self.goal)

    def least_steps(self) -> int:
        """Kürzester Weg von der jetzigen Zelle zum Ziel (direkt nach `reset`: vom Start)."""
        return self._distances()[self.goal]

    def _move(self, cell: Cell, axis: int, sign: int) -> Cell:
        while self.is_free(target := _neighbour(cell, axis, sign)):
            cell = target
            if not self.ice:
                break
        return cell

    def _distances(self) -> dict[Cell, int]:
        """Breitensuche über die Zellen, an denen man (nach einem Tastendruck) steht."""
        if not self.ice:
            return _reachable(self, self.position)
        distance = {self.position: 0}
        queue = deque([self.position])
        while queue:
            cell = queue.popleft()
            for axis in range(self.dims):
                for sign in (1, -1):
                    nxt = self._move(cell, axis, sign)
                    if nxt not in distance:
                        distance[nxt] = distance[cell] + 1
                        queue.append(nxt)
        return distance

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
    ice: bool = False,
) -> Lattice:
    """Ein Raum mit etwa `obstacles` Anteil Hindernissen, die die freien Zellen nicht trennen.

    Auf Eis kommen nur Hindernisse hinzu, die keine Falle bauen (eine Haltestelle, von der man
    nicht zurückkommt) und das Spielgebiet nicht verkleinern. Dort gibt es daher weniger
    Hindernisse als `obstacles`, typisch etwa zwei Drittel davon."""
    if not 0.0 <= obstacles < 0.5:
        raise ValueError(f"Hindernisanteil muss zwischen 0 und 0,5 liegen, nicht {obstacles}.")
    cells = list(_cells(dims, size))
    rng.shuffle(cells)
    blocked: set[Cell] = set()
    area = _ice_area(dims, size, blocked) if ice else set()
    for cell in cells[: round(obstacles * len(cells))]:
        blocked.add(cell)
        free = [c for c in cells if c not in blocked]
        if len(_reachable_cells(dims, size, blocked, free[0])) != len(free):
            blocked.remove(cell)  # Würde den Raum zerteilen.
        elif ice:
            bigger = _ice_area(dims, size, blocked)
            if bigger is None or area is None or len(bigger) < len(area):
                blocked.remove(cell)  # Würde eine Falle bauen oder das Spielgebiet verkleinern.
            else:
                area = bigger
    return Lattice(dims, size, frozenset(blocked), wiring, slip, ice)


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


class Dials:
    """`count` Drehscheiben mit je `size` Stellungen, ringförmig (ab 0.17)."""

    def __init__(self, count: int, size: int, wiring: Wiring) -> None:
        if count < 1 or size < 3:
            raise ValueError("Mindestens eine Scheibe mit mindestens drei Stellungen.")
        if len(wiring.components) != 2 * count or len(wiring.actions) != 2 * count:
            raise ValueError("Die Mischung passt nicht zur Zahl der Scheiben.")
        self.count, self.size, self.wiring = count, size, wiring
        self.values = [0] * count
        self.targets = [0] * count

    @property
    def actions(self) -> int:
        """Je Scheibe eine Taste vor und eine zurück."""
        return 2 * self.count

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde: zufällige Stellung und zufälliges Ziel, nicht schon gelöst."""
        self.targets = [rng.randrange(self.size) for _ in range(self.count)]
        self.values = list(self.targets)
        while self.values == self.targets:
            self.values = [rng.randrange(self.size) for _ in range(self.count)]
        return self._observe()

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Dreht eine Scheibe um eine Stellung; nach der letzten kommt die erste."""
        dial, backwards = divmod(self.wiring.inner_action(action), 2)
        self.values[dial] = (self.values[dial] + (-1 if backwards else 1)) % self.size
        return Outcome(self._observe(), self.values == self.targets)

    def least_steps(self) -> int:
        """Je Scheibe der kürzere Weg um den Ring."""
        gaps = [abs(v - t) for v, t in zip(self.values, self.targets, strict=True)]
        return sum(min(gap, self.size - gap) for gap in gaps)

    def names(self) -> tuple[list[str], list[str]]:
        """Namen der inneren Größen und Handlungen, nur für uns."""
        numbers = range(1, self.count + 1)
        components = [f"Scheibe {n}" for n in numbers] + [f"Ziel {n}" for n in numbers]
        return components, [f"{sign}1 Scheibe {n}" for n in numbers for sign in "+−"]

    def _observe(self) -> Observation:
        return self.wiring.observe([*self.values, *self.targets])


class Shuffle:
    """`tokens` Steine auf Plätzen; eine Taste tauscht zwei benachbarte Plätze (ab 0.17)."""

    def __init__(self, tokens: int, wiring: Wiring) -> None:
        if tokens < 2:
            raise ValueError("Zum Tauschen braucht es mindestens zwei Steine.")
        if len(wiring.components) != 2 * tokens or len(wiring.actions) != tokens - 1:
            raise ValueError("Die Mischung passt nicht zur Zahl der Steine.")
        self.tokens, self.wiring = tokens, wiring
        self.slots = list(range(tokens))
        self.target = list(range(tokens))

    @property
    def actions(self) -> int:
        """Je Paar benachbarter Plätze eine Taste."""
        return self.tokens - 1

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde: zufällige Reihenfolge und zufälliges Ziel, nicht schon gelöst."""
        self.target = rng.sample(range(self.tokens), self.tokens)
        self.slots = list(self.target)
        while self.slots == self.target:
            self.slots = rng.sample(range(self.tokens), self.tokens)
        return self._observe()

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Tauscht die Steine auf Platz i und i+1."""
        i = self.wiring.inner_action(action)
        self.slots[i], self.slots[i + 1] = self.slots[i + 1], self.slots[i]
        return Outcome(self._observe(), self.slots == self.target)

    def least_steps(self) -> int:
        """Zahl der Fehlstellungen: So viele Nachbartausche braucht man mindestens."""
        place = {token: index for index, token in enumerate(self.target)}
        order = [place[token] for token in self.slots]
        return sum(a > b for i, a in enumerate(order) for b in order[i + 1 :])

    def names(self) -> tuple[list[str], list[str]]:
        """Namen der inneren Größen und Handlungen, nur für uns."""
        numbers = range(1, self.tokens + 1)
        components = [f"Platz {n}" for n in numbers] + [f"Ziel Platz {n}" for n in numbers]
        return components, [f"tausche {n}↔{n + 1}" for n in range(1, self.tokens)]

    def _observe(self) -> Observation:
        return self.wiring.observe([*self.slots, *self.target])


def _cells(dims: int, size: int) -> Iterator[Cell]:
    if dims == 0:
        yield ()
        return
    for rest in _cells(dims - 1, size):
        for value in range(size):
            yield (*rest, value)


def _neighbour(cell: Cell, axis: int, sign: int) -> Cell:
    return tuple(c + sign if index == axis else c for index, c in enumerate(cell))


def _inside(cell: Cell, size: int) -> bool:
    return all(0 <= c < size for c in cell)


def _reachable(lattice: Lattice, start: Cell) -> dict[Cell, int]:
    return _reachable_cells(lattice.dims, lattice.size, lattice.blocked, start)


def _reachable_cells(dims: int, size: int, blocked: Set[Cell], start: Cell) -> dict[Cell, int]:
    """Breitensuche: Abstand jeder erreichbaren freien Zelle vom Start."""
    distance = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for axis in range(dims):
            for sign in (1, -1):
                nxt = _neighbour(cell, axis, sign)
                if _inside(nxt, size) and nxt not in blocked and nxt not in distance:
                    distance[nxt] = distance[cell] + 1
                    queue.append(nxt)
    return distance


def _ice_area(dims: int, size: int, blocked: Set[Cell]) -> set[Cell] | None:
    """Auf Eis das Spielgebiet: das größte Gebiet von Haltestellen, die alle voneinander aus
    erreichbar sind. None, wenn eine Rutschpartie aus dem Gebiet hinausführt (eine Falle)."""
    free = [cell for cell in _cells(dims, size) if cell not in blocked]
    ends = {cell: _slide_ends(dims, size, blocked, cell) for cell in free}
    stops = set().union(*ends.values())
    area = _main_area(stops, ends)
    return area if all(ends[cell] <= area for cell in area) else None


def _slide_ends(dims: int, size: int, blocked: Set[Cell], cell: Cell) -> set[Cell]:
    """Wo man von hier aus mit jeder Taste auf Eis zum Stehen kommt."""
    found = set()
    for axis in range(dims):
        for sign in (1, -1):
            here = cell
            while _inside(nxt := _neighbour(here, axis, sign), size) and nxt not in blocked:
                here = nxt
            found.add(here)
    return found


def _main_area(stops: set[Cell], ends: dict[Cell, set[Cell]]) -> set[Cell]:
    """Das größte Gebiet von Haltestellen, die alle voneinander aus erreichbar sind."""
    reach = {stop: _reach(stop, ends) for stop in stops}
    areas = [{other for other in reach[stop] if stop in reach[other]} for stop in stops]
    return max(areas, key=len, default=set())


def _reach(start: Cell, ends: dict[Cell, set[Cell]]) -> set[Cell]:
    seen = {start}
    stack = [start]
    while stack:
        for nxt in ends[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen
