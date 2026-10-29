import random

import pytest

from hekmatki.experiments.discovery import play
from hekmatki.experiments.rule_transfer import run_rule_transfer
from hekmatki.explorer import Explorer
from hekmatki.puzzle import STANDARD, KeyDoorGame, Layout, Move
from hekmatki.rules import (
    BACKWARD,
    FORWARD,
    Controls,
    Effect,
    Event,
    Place,
    RuleAdvisor,
    RuleSchema,
    all_controls,
    corridor_map,
    learn_rules,
    places_of,
    revised,
    rules_after_game,
)

TRUE_CONTROLS = Controls(forward="r", backward="l", use="u")
LONG = Layout(length=7, door=6)


def _game(layout: Layout = STANDARD) -> KeyDoorGame:
    looks = {state: f"s{state[0]}{'k' if state[1] else ''}" for state in layout.hidden_states}
    controls = {"l": Move.LEFT, "r": Move.RIGHT, "u": Move.USE}
    return KeyDoorGame("Test", layout, looks, controls)


def _full_model(game: KeyDoorGame) -> dict[tuple[str, str], str]:
    """Alle Übergänge des Spiels, als hätte der Agent alles ausprobiert."""
    return {
        (symbol, button): game.step(symbol, button)
        for symbol in game.looks.values()
        for button in game.buttons
    }


def _schema(key: frozenset[Place], door: frozenset[Place]) -> RuleSchema:
    return RuleSchema("Gang", (Event(Effect.SWITCH, key), Event(Effect.WIN, door)))


WALL_BACK, WALL_FORWARD = Place("wand", BACKWARD), Place("wand", FORWARD)
ONE_BACK, TWO_FORWARD = Place("start", BACKWARD, 1), Place("start", FORWARD, 2)


def test_three_buttons_give_six_interpretations() -> None:
    assert len(all_controls(["a", "b", "c"])) == 6
    with pytest.raises(ValueError, match="genau drei Tasten"):
        all_controls(["a", "b"])
    with pytest.raises(ValueError, match="Unbekannte Taste"):
        TRUE_CONTROLS.direction("x")


def test_map_counts_positions_from_the_start() -> None:
    corridor = corridor_map(_full_model(_game()), "s1", TRUE_CONTROLS)
    assert corridor is not None
    assert corridor.spots["s0"] == (-1, 0)
    assert corridor.spots["s0k"] == (-1, 1)
    assert corridor.walls == {(-1, BACKWARD), (2, FORWARD)}
    assert corridor.uses[(-1, 0)] is Effect.SWITCH
    assert corridor.uses[(2, 1)] is Effect.WIN


def test_wrong_interpretation_contradicts_itself() -> None:
    swapped = Controls(forward="u", backward="l", use="r")
    assert corridor_map(_full_model(_game()), "s1", swapped) is None


def test_unseen_wall_stays_possible() -> None:
    corridor = corridor_map({("s1", "l"): "s0"}, "s1", TRUE_CONTROLS)
    assert corridor is not None
    assert places_of(-1, corridor) == {ONE_BACK, WALL_BACK}
    assert WALL_BACK.matches(-1, corridor) is None
    assert WALL_FORWARD.matches(0, corridor) is None
    assert WALL_BACK.matches(0, corridor) is False


def test_places_read_well() -> None:
    assert str(ONE_BACK) == "1 Schritt vom Start (rückwärts)"
    assert str(WALL_FORWARD) == "Wand (vorwärts)"
    assert ONE_BACK.mirrored() == Place("start", FORWARD, 1)


def test_rules_must_end_with_a_win_and_name_a_place() -> None:
    with pytest.raises(ValueError, match="Sieg"):
        RuleSchema("x", (Event(Effect.SWITCH, frozenset({ONE_BACK})),))
    with pytest.raises(ValueError, match="Ort"):
        _schema(frozenset(), frozenset({WALL_FORWARD}))


def test_learned_rules_describe_key_and_door() -> None:
    rules = learn_rules("Gang", _full_model(_game()), "s1", ["l", "r", "u"])
    assert rules is not None
    assert rules.effects == (Effect.SWITCH, Effect.WIN)
    places = {place.undirected for event in rules.events for place in event.places}
    assert places == {"1 Schritt vom Start", "2 Schritte vom Start", "Wand"}


def test_no_rules_without_a_win() -> None:
    assert learn_rules("Gang", {("s1", "l"): "s0"}, "s1", ["l", "r", "u"]) is None
    assert rules_after_game("Gang", None, {("s1", "l"): "s0"}, "s1", ["l", "r", "u"]) is None


def test_revision_keeps_shared_places_in_either_direction() -> None:
    short = _schema(frozenset({ONE_BACK, WALL_BACK}), frozenset({TWO_FORWARD, WALL_FORWARD}))
    longer_mirrored = _schema(
        frozenset({Place("start", FORWARD, 1), WALL_FORWARD}),
        frozenset({Place("start", BACKWARD, 3), WALL_BACK}),
    )
    rules = revised(short, longer_mirrored)
    assert rules.events[0].places == {ONE_BACK, WALL_BACK}
    assert [p.undirected for p in rules.events[1].places] == ["Wand"]


def test_revision_replaces_places_that_were_too_narrow() -> None:
    narrow = _schema(frozenset({ONE_BACK}), frozenset({TWO_FORWARD}))
    wider = _schema(frozenset({ONE_BACK}), frozenset({Place("start", FORWARD, 3), WALL_FORWARD}))
    assert revised(narrow, wider).events[1].places == wider.events[1].places


def test_rules_from_short_corridors_help_in_a_long_one() -> None:
    rules = None
    for layout in (STANDARD, Layout(length=5, door=4)):
        game = _game(layout)
        rules = rules_after_game("Gang", rules, _full_model(game), "s1", game.buttons)
    assert rules is not None
    assert [p.undirected for p in rules.events[1].places] == ["Wand"]
    longer = _game(LONG)
    with_rules, fresh = [], []
    for seed in range(5):
        advisor = RuleAdvisor(rules, longer.buttons, longer.start_symbol)
        informed = Explorer(longer.buttons, longer.start_symbol, advisor)
        with_rules.append(_first_win(longer, informed, seed))
        fresh.append(_first_win(longer, Explorer(longer.buttons, longer.start_symbol), seed))
        assert advisor.fits()
    assert sum(with_rules) < sum(fresh)


def _first_win(game: KeyDoorGame, explorer: Explorer, seed: int) -> int:
    first_win = play(game, explorer, 60, random.Random(seed)).first_win
    assert first_win is not None
    return first_win


def test_rule_advisor_gives_up_when_nothing_fits() -> None:
    rules = _schema(frozenset({ONE_BACK}), frozenset({TWO_FORWARD}))
    advisor = RuleAdvisor(rules, ["l", "r", "u"], "s1")
    for symbol in ("s1", "s2", "s3", "s4", "s5"):
        advisor.learn(symbol, "r", f"s{int(symbol[1]) + 1}")
    advisor.learn("s1", "u", "s1")
    advisor.learn("s1", "l", "s0")
    advisor.learn("s0", "u", "s0k")
    advisor.learn("s0k", "r", "s1k")
    advisor.learn("s1k", "r", "s2k")
    advisor.learn("s2k", "r", "s3k")
    advisor.learn("s3k", "u", "s3k")
    assert not advisor.fits()
    assert advisor.advice("s3k", random.Random(0)) is None
    assert not advisor.predicts("s1", "l")


def test_rule_transfer_experiment() -> None:
    result = run_rule_transfer(seeds=3)
    rows = {row.game: row for row in result.rows}
    first = rows["Spiel 1"].first_win
    assert first["ohne Vorwissen"] == first["Zustands-Schema"] == first["Regel-Schema"]
    longest = rows["viel länger"].first_win
    assert longest["Regel-Schema"] < longest["ohne Vorwissen"]
    assert rows["viel länger"].length == 8
    assert result.descriptions[1] == {"Wand": 3}
