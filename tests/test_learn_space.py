"""Tests für 0.22: den Raum durch Herumlaufen lernen (H37) und die eigene Stelle in einer
Schicht finden, wenn der Blick mehrere Schichten hat."""

import random

from hekmatki.general.agent import GeneralAgent
from hekmatki.general.drives import SPACE_PATIENCE
from hekmatki.general.env import Environment, Observation, Outcome, Transition
from hekmatki.general.space import Edge, build

MOVES = {0: (1, 0), 1: (-1, 0), 2: (0, 1), 3: (0, -1)}
"""Taste → Schritt der Figur."""
CELLS = [(x, y) for y in range(-2, 3) for x in range(-2, 3)]
"""Ein Blick von 5 × 5 Feldern um die Figur."""


def _layer(cells: list[tuple[int, int]], first: int) -> list[Edge]:
    """Verschiebungen in einer Schicht, deren Felder ab `first` nummeriert sind."""
    index = {cell: first + i for i, cell in enumerate(cells)}
    return [
        Edge(1.0, action, index[x + dx, y + dy], index[x, y])
        for action, (dx, dy) in MOVES.items()
        for x, y in cells
        if (x + dx, y + dy) in index
    ]


def test_his_place_is_found_in_the_layer_where_he_stands() -> None:
    """Unter den Füßen ist der Blick voll (Boden), auf Höhe der Füße fehlt seine Stelle. Das
    größere Stück ohne Lücke verdeckt sie nicht mehr."""
    ground = _layer(CELLS, 0)
    feet = _layer([cell for cell in CELLS if cell != (0, 0)], 100)
    layout = build(ground + feet, {0: (50, 1), 1: (50, -1), 2: (51, 1), 3: (51, -1)})
    assert layout.centred
    assert all(component >= 100 for component in layout.places)


class Meadow:
    """Eine Figur auf einer zufälligen Wiese; sie sieht 5 × 5 Felder um sich (ihre eigene
    Stelle als 9) und ihren Ort. Taste 0 bis 3 gehen, 4 bis 7 tun nichts."""

    def __init__(self) -> None:
        rng = random.Random(5)
        self.world = {
            (x, y): rng.choice((1, 1, 1, 2, 3)) for x in range(-60, 61) for y in range(-60, 61)
        }
        self.x = self.y = 0

    @property
    def actions(self) -> int:
        return 8

    def observe(self) -> Observation:
        view = [9 if c == (0, 0) else self.world[self.x + c[0], self.y + c[1]] for c in CELLS]
        return (*view, self.x + 60, self.y + 60)

    def reset(self, rng: random.Random) -> Observation:
        self.x = self.y = 0
        return self.observe()

    def step(self, action: int, rng: random.Random) -> Outcome:
        dx, dy = MOVES.get(action, (0, 0))
        if abs(self.x + dx) < 55 and abs(self.y + dy) < 55:
            self.x, self.y = self.x + dx, self.y + dy
        return Outcome(self.observe(), False)

    def least_steps(self) -> int:
        return 0


def _play(env: Environment, steps: int) -> tuple[GeneralAgent, list[str]]:
    agent = GeneralAgent(env.actions, own_goals=True)
    rng = random.Random(0)
    observation = env.reset(rng)
    agent.begin(observation)
    reasons = []
    for _ in range(steps):
        action = agent.act(observation, rng)
        assert agent.drives is not None
        reasons.append(agent.drives.reason)
        outcome = env.step(action, rng)
        agent.learn(Transition(observation, action, outcome.observation, outcome.reached))
        observation = outcome.observation
    return agent, reasons


def test_without_a_grid_he_walks_until_he_has_one() -> None:
    agent, reasons = _play(Meadow(), 2000)
    assert agent.knowledge.space.layout.centred
    found = max(i for i, reason in enumerate(reasons) if reason.startswith("Raum"))
    assert "Raum" in {reason.split(",")[0] for reason in reasons[:found]}
    assert not any(reason.startswith("Raum") for reason in reasons[found + 1 :])


class Corridor:
    """Ein Gang ohne Blick um sich: Hier gibt es kein Gitter zu finden."""

    def __init__(self) -> None:
        self.position = 0

    @property
    def actions(self) -> int:
        return 4

    def reset(self, rng: random.Random) -> Observation:
        self.position = 0
        return (self.position,)

    def step(self, action: int, rng: random.Random) -> Outcome:
        self.position += {0: -1, 1: 1}.get(action, 0)
        return Outcome((self.position,), False)

    def least_steps(self) -> int:
        return 0


def test_where_no_grid_grows_he_stops_walking_for_it() -> None:
    _, reasons = _play(Corridor(), 3 * SPACE_PATIENCE)
    walked = sum(reason.startswith("Raum") for reason in reasons)
    assert 0 < walked <= SPACE_PATIENCE
