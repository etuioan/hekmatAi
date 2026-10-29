import pytest

from hekmatki.experiments import run_traffic_light_game


def test_schemas_help_to_win_early_and_overlap_is_correct() -> None:
    result = run_traffic_light_game(seeds=3)
    rows = {row.player: row for row in result.rows}
    assert rows["mit Schemata"].early_win_rate > rows["ohne Vorwissen"].early_win_rate
    assert rows["mit Schemata"].accidents < rows["ohne Vorwissen"].accidents
    assert result.found_during_game == 1.0
    assert result.core_correct == 1.0
    assert result.learned_action["ereignis"] > 0.7
    assert result.learned_action["beschäftigen"] < 0.1


def test_game_needs_more_rounds_than_the_early_phase() -> None:
    with pytest.raises(ValueError, match="mehr als"):
        run_traffic_light_game(seeds=1, rounds=10)
