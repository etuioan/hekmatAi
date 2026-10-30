"""Tests für 0.22: Eine Taste ohne Wirkung probiert er nicht endlos (H36)."""

import random

from hekmatki.general.agent import GeneralAgent
from hekmatki.general.drives import FUTILE
from hekmatki.general.env import Observation, Outcome, Transition


class EndlessCorridor:
    """Ein Gang ohne Ende und eine Uhr: Der Ort ist fast immer neu, die Uhr immer.

    Größe 0 Ort, 1 Uhr. Tasten: 0 links, 1 rechts, 2 und 3 tun nie etwas. So ist in jedem
    Schritt etwas „selten“, wie in einer großen offenen Welt.
    """

    def __init__(self) -> None:
        self.position, self.time = 0, 0

    @property
    def actions(self) -> int:
        return 4

    def reset(self, rng: random.Random) -> Observation:
        self.position, self.time = 0, 0
        return (self.position, self.time)

    def step(self, action: int, rng: random.Random) -> Outcome:
        self.time += 1
        self.position += {0: -1, 1: 1}.get(action, 0)
        return Outcome((self.position, self.time), False)

    def least_steps(self) -> int:
        return 0


def _trials(steps: int) -> int:
    """Wie oft er eine wirkungslose Taste als „Versuch“ drückt."""
    agent = GeneralAgent(4, own_goals=True)
    env, rng = EndlessCorridor(), random.Random(0)
    observation = env.reset(rng)
    agent.begin(observation)
    trials = 0
    for _ in range(steps):
        action = agent.act(observation, rng)
        assert agent.drives is not None
        trials += action in (2, 3) and agent.drives.reason.startswith("Versuch")
        outcome = env.step(action, rng)
        agent.learn(Transition(observation, action, outcome.observation, outcome.reached))
        observation = outcome.observation
    return trials


def test_a_key_without_effect_is_tried_at_most_futile_times() -> None:
    """Etwas Seltenes gibt es hier immer. Bis 0.21 probierte er die wirkungslosen Tasten
    darum ohne Ende (1314 Versuche in 2000 Schritten); jetzt höchstens `FUTILE`-mal je Taste
    und Besitz. Den Ort hält er hier für einen Besitz, darum zählt es ein paarmal neu."""
    assert _trials(2000) <= 3 * FUTILE
