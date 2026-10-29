import random

import pytest

from hekmatki.game import (
    ACCIDENT,
    ARRIVED,
    GREEN,
    MISSED,
    TRAFFIC,
    YELLOW,
    Action,
    TrafficLightGame,
)
from hekmatki.player import GamePlayer


def test_running_only_wins_at_green() -> None:
    game, rng = TrafficLightGame(), random.Random(0)
    assert game.step(GREEN, Action.RUN, rng) == ARRIVED
    assert game.step(TRAFFIC, Action.RUN, rng) == ACCIDENT
    assert game.step(YELLOW, Action.RUN, rng) == ACCIDENT


def test_waiting_at_green_misses_the_chance() -> None:
    assert TrafficLightGame().step(GREEN, Action.WAIT, random.Random(0)) == MISSED


def test_every_round_end_starts_a_new_round() -> None:
    game, rng = TrafficLightGame(), random.Random(0)
    for ending in (ARRIVED, MISSED, ACCIDENT):
        assert game.step(ending, Action.RUN, rng) == TRAFFIC


def test_waiting_eventually_reaches_green() -> None:
    game, rng = TrafficLightGame(), random.Random(0)
    state = game.start
    for _ in range(200):
        state = game.step(state, Action.WAIT, rng)
        if state == GREEN:
            return
    pytest.fail("Grün kam in 200 Schritten nie.")


def test_invalid_game_input_raises() -> None:
    with pytest.raises(ValueError, match="Unbekannter Spielzustand"):
        TrafficLightGame().step("kaffee", Action.WAIT, random.Random(0))
    with pytest.raises(ValueError, match="traffic_stay"):
        TrafficLightGame(traffic_stay=1.0)


def test_player_without_experience_does_not_run_blindly() -> None:
    player = GamePlayer(TrafficLightGame().symbols, ARRIVED)
    choices = [player.choose(TRAFFIC, random.Random(seed)) for seed in range(100)]
    assert choices.count(Action.RUN) < 40


def test_player_learns_from_a_win() -> None:
    player = GamePlayer(TrafficLightGame().symbols, ARRIVED)
    player.learn(GREEN, Action.RUN, ARRIVED)
    assert player.choose(GREEN, random.Random(0)) is Action.RUN


def test_player_rejects_unknown_goal() -> None:
    with pytest.raises(ValueError, match="kein Symbol"):
        GamePlayer(["a", "b"], "c")
