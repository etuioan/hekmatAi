import random

import pytest

from hekmatki.curiosity import Curiosity, Detour
from hekmatki.experiments.discovery import play
from hekmatki.experiments.exploration import run_exploration, total_wins
from hekmatki.explorer import Explorer
from hekmatki.puzzle import NO_KEY, make_game

SHORTCUT = Detour(
    steps_there=2, steps_from_start=2, steps_on_to_win=4, steps_by_plan=4, round_trip=6
)


def test_detours_pay_off_only_with_enough_time_left() -> None:
    assert SHORTCUT.value(surprise=0.1, steps_left=200) > 0
    assert SHORTCUT.value(surprise=0.1, steps_left=10) < 0


def test_no_gain_without_a_possible_shortcut() -> None:
    no_shortcut = Detour(2, 6, 4, 4, 6)
    assert no_shortcut.value(surprise=1.0, steps_left=200) < 0


def test_invalid_curiosity_raises() -> None:
    with pytest.raises(ValueError, match="zwischen 0 und 1"):
        Curiosity(surprise=1.5)
    with pytest.raises(ValueError, match="mindestens einen Schritt"):
        Detour(0, 0, 0, 0, 0)


def test_curious_explorer_finds_the_open_door() -> None:
    game = make_game("offen", NO_KEY, random.Random(3))
    door = game.looks[(NO_KEY.door, False)]
    curious = Explorer(game.buttons, game.start_symbol, curiosity=Curiosity())
    play(game, curious, 200, random.Random(4))
    assert any(
        state == door and outcome == "gewonnen" for (state, _), outcome in curious.model.items()
    )


def test_curiosity_pays_off_in_long_games_with_surprises() -> None:
    result = run_exploration(seeds=3, horizons=(200,), schema_surprises=(0.05,))
    long_run = result.horizons[0]
    plain = {row.game: row for row in long_run.plain.rows}
    curious = {row.game: row for row in long_run.curious.rows}
    assert curious["ohne Schlüssel"].schema_wins > plain["ohne Schlüssel"].schema_wins
    assert total_wins(long_run.curious, "mit Schema") > total_wins(long_run.plain, "mit Schema")
    assert long_run.curious.schema_size["Spiel 3"] > long_run.plain.schema_size["Spiel 3"]
