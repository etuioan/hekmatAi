import random

import pytest

from hekmatki.experiments.discovery import play, run_discovery, shortest_win
from hekmatki.explorer import Explorer
from hekmatki.game_schema import SchemaAdvisor, schema_from_model
from hekmatki.puzzle import MIRRORED, STANDARD, make_game


def test_explorer_discovers_how_to_win() -> None:
    game = make_game("a", STANDARD, random.Random(0))
    result = play(game, Explorer(game.buttons, game.start_symbol), 60, random.Random(1))
    assert result.first_win is not None
    assert result.wins >= 3


def test_schema_from_one_game_transfers_to_a_mirrored_one() -> None:
    rng = random.Random(0)
    first = make_game("a", STANDARD, rng)
    learner = Explorer(first.buttons, first.start_symbol)
    play(first, learner, 60, random.Random(1))
    schema = schema_from_model("S", learner.model, first.start_symbol, first.buttons)
    second = make_game("b", MIRRORED, rng)
    advisor = SchemaAdvisor(schema, second.buttons, second.start_symbol)
    informed = Explorer(second.buttons, second.start_symbol, advisor)
    result = play(second, informed, 60, random.Random(2))
    assert advisor.fits()
    assert result.first_win is not None
    assert result.first_win <= 2 * shortest_win(MIRRORED)


def test_unknown_button_raises() -> None:
    with pytest.raises(ValueError, match="Unbekannte Taste"):
        Explorer(["a"], "s").learn("s", "b", "t")
    with pytest.raises(ValueError, match="mindestens eine Taste"):
        Explorer([], "s")


def test_schema_helps_in_the_second_game_of_the_family() -> None:
    rows = {row.game: row for row in run_discovery(seeds=3).rows}
    assert rows["Spiel 1"].schema_first_win == rows["Spiel 1"].fresh_first_win
    assert rows["Spiel 2"].schema_first_win < rows["Spiel 2"].fresh_first_win
    assert rows["Spiel 2"].schema_fits == 1.0
