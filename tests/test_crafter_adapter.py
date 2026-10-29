"""Tests für den Crafter-Adapter und die Messung (ab 0.18); ohne `crafter` übersprungen."""

import math
import random

import pytest

pytest.importorskip("crafter")

from hekmatki.adapters.crafter import ACTIONS, MATERIALS, WIDTH, CrafterWorld
from hekmatki.experiments.crafter_run import (
    ACHIEVEMENTS,
    Round,
    play,
    rows,
    score,
    success_rates,
)


def test_observation_is_only_numbers_of_fixed_width() -> None:
    world = CrafterWorld(0)
    observation = world.reset(random.Random(0))
    assert len(observation) == WIDTH
    assert all(isinstance(value, int) for value in observation)
    outcome = world.step(0, random.Random(0))
    assert len(outcome.observation) == WIDTH


def test_names_are_only_for_the_page_and_match_the_mixing() -> None:
    world = CrafterWorld(3)
    components, actions = world.names()
    assert len(components) == WIDTH
    assert len(actions) == ACTIONS
    named = dict(zip(components, world.reset(random.Random(0)), strict=True))
    assert MATERIALS[named["Sicht +0,+0"]] == "player"
    assert named["health"] == 9


def test_different_seeds_mix_differently() -> None:
    assert CrafterWorld(0).wiring != CrafterWorld(1).wiring


def test_score_is_the_geometric_mean_of_the_paper() -> None:
    assert score(dict.fromkeys(ACHIEVEMENTS, 0.0)) == pytest.approx(0.0)
    assert score(dict.fromkeys(ACHIEVEMENTS, 1.0)) == pytest.approx(100.0)
    one = {**dict.fromkeys(ACHIEVEMENTS, 0.0), "collect_wood": 1.0}
    assert score(one) == pytest.approx(math.exp(math.log(101) / 22) - 1)


def test_success_rates_count_rounds() -> None:
    rounds = [Round(10, ((3, "collect_wood"),)), Round(10, ())]
    assert success_rates(rounds)["collect_wood"] == 0.5


def test_a_short_career_runs_and_is_summarised() -> None:
    career = play("Zufall", seed=0, episodes=2, length=30)
    assert len(career.rounds) == 2
    assert all(r.steps <= 30 for r in career.rounds)
    (row,) = rows([career], warmup=1)
    assert row.agent == "Zufall"
    assert len(row.curve) == 2
