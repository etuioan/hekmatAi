"""Tests für den Raum aus eigener Bewegung (ab 0.19, H29)."""

import random
from dataclasses import replace

from hekmatki.general.causes import Kind, Literal, cover
from hekmatki.general.env import Transition
from hekmatki.general.space import REFRESH, Edge, Layout, Space, build

WIDTH, HEIGHT = 5, 5
"""Ein Blick von 5 × 5 Feldern um die Figur; die Mitte ist die Figur selbst."""
MOVES = {0: (1, 0), 1: (-1, 0), 2: (0, 1), 3: (0, -1)}
"""Taste → Schritt der Figur."""


def _cells() -> list[tuple[int, int]]:
    half_w, half_h = WIDTH // 2, HEIGHT // 2
    return [(x, y) for y in range(-half_h, half_h + 1) for x in range(-half_w, half_w + 1)]


class _Walker:
    """Eine Figur auf einer zufälligen Karte; sie sieht den Blick um sich, ihre Mitte (immer
    9) und ihren Ort (zwei Zahlen). Manche Schritte sind gesperrt."""

    def __init__(self, rng: random.Random, walls: bool = False) -> None:
        self.rng = rng
        self.walls = walls
        self.world = {
            (x, y): rng.choice((1, 1, 1, 2, 3)) for x in range(-40, 41) for y in range(-40, 41)
        }
        self.x = self.y = 0
        self.facing = (1, 0)

    def observe(self) -> tuple[int, ...]:
        view = [
            9 if (dx, dy) == (0, 0) else self.world[self.x + dx, self.y + dy] for dx, dy in _cells()
        ]
        front = self.world[self.x + self.facing[0], self.y + self.facing[1]]
        return (*view, self.x + 50, self.y + 50, front)

    def step(self, action: int) -> None:
        dx, dy = MOVES.get(action, (0, 0))
        if (dx, dy) != (0, 0):
            self.facing = (dx, dy)
        if self.rng.random() < 0.3:
            return  # Gesperrt: Er bleibt stehen.
        if self.walls and self.world[self.x + dx, self.y + dy] == 3:
            return  # Eine Mauer.
        if abs(self.x + dx) < 35 and abs(self.y + dy) < 35:
            self.x, self.y = self.x + dx, self.y + dy


def _learned(steps: int, seed: int = 0) -> tuple[Space, list[tuple[int, int]]]:
    rng = random.Random(seed)
    walker = _Walker(rng)
    space = Space()
    before = walker.observe()
    for _ in range(steps):
        action = rng.randrange(6)  # Zwei Tasten bewegen nichts.
        walker.step(action)
        after = walker.observe()
        space.observe(Transition(before, action, after, False))
        before = after
    return space, _cells()


def test_the_grid_is_learned_from_own_movement_and_he_is_the_gap() -> None:
    space, cells = _learned(20 * REFRESH)
    layout = space.layout
    assert layout.centred
    centre = cells.index((0, 0))
    assert centre not in layout.places
    for component, place in layout.places.items():
        x, y = cells[component]
        assert sorted(abs(v) for v in place) == sorted((abs(x), abs(y)))
    assert len(layout.places) == len(cells) - 1


def test_moves_get_opposite_directions_and_others_none() -> None:
    space, _ = _learned(20 * REFRESH)
    vectors = space.layout.vectors
    assert set(vectors) == {0, 1, 2, 3}
    assert vectors[0] == tuple(-v for v in vectors[1])
    assert vectors[2] == tuple(-v for v in vectors[3])


def test_near_groups_and_fetching_something_seen() -> None:
    space, cells = _learned(20 * REFRESH)
    layout = space.layout
    near = layout.groups()[0]
    assert sorted(cells[c] for c in near) == [(-1, 0), (0, -1), (0, 1), (1, 0)]
    observation = [1] * (len(cells) + 3)
    observation[cells.index((2, 0))] = 7  # Zwei Felder rechts steht etwas.
    step = layout.fetch(tuple(observation), 7, near)
    assert step is not None
    assert layout.relation(step, layout.places[cells.index((2, 0))]) == "hin"


def test_the_field_in_front_of_him_is_no_place() -> None:
    """„Vorne“ zeigt beim Gehen den Wert von weiter vorn, wie ein Nachbar, aber in der
    Gegenrichtung nicht: Es bekommt keine Stelle im Gitter."""
    space, cells = _learned(20 * REFRESH)
    front = len(cells) + 2
    assert front not in space.layout.places


def test_two_holes_inside_mean_no_centre() -> None:
    """Fehlt innen mehr als eine Stelle, weiß er nicht, welche er ist."""
    grid = [(x, y) for y in range(-2, 3) for x in range(-2, 3) if (x, y) not in ((0, 0), (1, 1))]
    index = {cell: i for i, cell in enumerate(grid)}
    edges = [
        Edge(1.0, action, index[x + dx, y + dy], index[x, y])
        for action, (dx, dy) in MOVES.items()
        for x, y in grid
        if (x + dx, y + dy) in index
    ]
    layout = build(edges, {0: (30, 1), 1: (30, -1), 2: (31, 1), 3: (31, -1)})
    assert len(layout.places) == len(grid)
    assert not layout.centred


def test_a_view_that_is_not_around_him_has_no_centre() -> None:
    """Ein Gitter ohne Lücke in der Mitte: keine Abstände, keine Gruppen."""
    line = {0: {1: 0, 2: 1, 3: 2, 4: 3}, 1: {0: 1, 1: 2, 2: 3, 3: 4}}
    edges = [Edge(1.0, a, s, t) for a, flow in line.items() for s, t in flow.items()]
    layout = build(edges, {0: (10, 1), 1: (10, -1)})
    assert len(layout.places) == 5
    assert not layout.centred
    assert layout.groups() == ()


def test_a_weak_edge_that_contradicts_the_grid_is_left_out() -> None:
    """Das Feld links bekommt beim Gehen, worauf er stand; das sieht oft aus wie das Feld
    rechts. So eine Verschiebung über ihn hinweg ist schwächer und passt nicht ins Gitter."""
    ring = [(x, y) for y in (-1, 0, 1) for x in (-1, 0, 1) if (x, y) != (0, 0)]
    index = {cell: i for i, cell in enumerate(ring)}
    edges = [
        Edge(1.0, action, index[x + dx, y + dy], index[x, y])
        for action, (dx, dy) in MOVES.items()
        for x, y in ring
        if (x + dx, y + dy) in index
    ]
    across = Edge(0.92, 0, index[1, 0], index[-1, 0])
    walkers = {0: (10, 1), 1: (10, -1), 2: (11, 1), 3: (11, -1)}
    layout = build([*edges, across], walkers)
    assert layout.centred
    assert layout.flows[0].get(index[1, 0]) != index[-1, 0]


def test_a_group_literal_covers_a_danger_on_every_side() -> None:
    """Ein Gegner (15) mal links, mal rechts von ihm: Eine Gruppe deckt alle Fälle ab."""
    positives = [(15, 1, 1), (1, 15, 1)] * 5
    negatives = [(1, 1, 1), (1, 1, 15)] * 5
    rules = cover(positives, negatives, groups=((0, 1),))
    literals, hits, uses = rules[0]
    assert literals == (Literal.some((0, 1), 15),)
    assert (hits, uses) == (10, 10)
    assert literals[0].kind is Kind.SOME
    assert literals[0].where((1, 15, 1)) == [1]


def test_an_edge_across_him_does_not_put_a_field_on_his_place() -> None:
    """Beim Gehen bekommt das Feld hinter ihm, worauf er stand, und das ist oft dasselbe wie
    das Feld vor ihm. Ist so eine Verschiebung sicherer als die echten des Felds daneben,
    liegt zuerst ein Nachbar auf seiner Stelle; die Mehrheit rückt ihn zurück."""
    grid = [(x, y) for y in range(-2, 3) for x in range(-2, 3) if (x, y) != (0, 0)]
    index = {cell: i for i, cell in enumerate(grid)}
    right = index[1, 0]
    edges = [
        Edge(
            0.9 if right in (index[x + dx, y + dy], index[x, y]) else 0.95,
            action,
            index[x + dx, y + dy],
            index[x, y],
        )
        for action, (dx, dy) in MOVES.items()
        for x, y in grid
        if (x + dx, y + dy) in index
    ]
    across = [Edge(0.93, 0, right, index[-1, 0]), Edge(0.93, 1, index[-1, 0], right)]
    layout = build([*across, *edges], {0: (30, 1), 1: (30, -1), 2: (31, 1), 3: (31, -1)})
    assert layout.centred
    assert layout.places[right] == tuple(-v for v in layout.places[index[-1, 0]])
    assert len(layout.places) == len(grid)


def _grid_layout(
    size: int = 2, front: int | None = None
) -> tuple[Layout, dict[tuple[int, int], int]]:
    """Ein fertiges Gitter (2·size+1)² um ihn herum; mit `front` dazu ein Fühler „vorne“,
    der beim Gehen den Wert des Nachbarfelds in Gehrichtung bekommt."""
    grid = [
        (x, y) for y in range(-size, size + 1) for x in range(-size, size + 1) if (x, y) != (0, 0)
    ]
    index = {cell: i for i, cell in enumerate(grid)}
    edges = [
        Edge(0.95, action, index[x + dx, y + dy], index[x, y])
        for action, (dx, dy) in MOVES.items()
        for x, y in grid
        if (x + dx, y + dy) in index
    ]
    oneway = (
        []
        if front is None
        else [Edge(0.95, a, index[2 * dx, 2 * dy], front) for a, (dx, dy) in MOVES.items()]
    )
    walkers = {0: (60, 1), 1: (60, -1), 2: (61, 1), 3: (61, -1)}
    return build(edges, walkers, oneway), index


def test_he_walks_around_an_obstacle_to_what_he_wants() -> None:
    """Rechts von ihm eine Mauer (7), dahinter etwas (5): Er geht oben oder unten herum."""
    layout, index = _grid_layout()
    layout = replace(layout, obstacles=frozenset({7}))
    observation = [1] * 62
    for y in (-1, 0, 1):
        observation[index[1, y]] = 7
    observation[index[2, 0]] = 5
    neighbours = [index[-1, 0], index[1, 0], index[0, 1], index[0, -1]]
    step = layout.fetch(tuple(observation), 5, neighbours)
    assert step is not None
    assert layout.vectors[step] in ((0, 1), (0, -1))


def test_a_feeler_points_him_at_the_thing_next_to_him() -> None:
    """„vorne“ zeigt das Nachbarfeld in Gehrichtung. Liegt 5 schon links neben ihm, dreht er
    sich hin (geht nach links); liegt es weiter weg, geht er daneben."""
    front = 40
    layout, index = _grid_layout(front=front)
    assert layout.mirrors[front] == {(1, 0), (-1, 0), (0, 1), (0, -1)}
    observation = [1] * 62
    observation[index[-1, 0]] = 5
    step = layout.fetch(tuple(observation), 5, [front])
    assert step is not None
    assert layout.vectors[step] == (-1, 0)


def test_heading_to_a_place_out_of_sight_goes_around_a_wall() -> None:
    layout, index = _grid_layout()
    layout = replace(layout, obstacles=frozenset({7}))
    observation = [1] * 62
    observation[index[1, 0]] = 7
    where = [0] * 62
    observation[60], observation[61] = 10, 10
    where[60], where[61] = 30, 10  # Weit rechts, hinter der Mauer.
    step = layout.head(tuple(observation), tuple(where))
    assert step is not None
    assert layout.vectors[step] != (1, 0)


def test_obstacles_are_learned_from_his_own_movement() -> None:
    """Felder mit dem Wert 3 kann die Figur nicht betreten; er merkt das selbst."""
    rng = random.Random(1)
    walker = _Walker(rng, walls=True)
    space = Space()
    before = walker.observe()
    for _ in range(40 * REFRESH):
        action = rng.randrange(6)
        walker.step(action)
        after = walker.observe()
        space.observe(Transition(before, action, after, False))
        before = after
    assert 3 in space.layout.obstacles
    assert 1 not in space.layout.obstacles
