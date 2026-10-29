import random

import pytest

from hekmatki.puzzle import NO_KEY, STANDARD, WIN, KeyDoorGame, Layout, Move, make_game


def _game(layout: Layout = STANDARD) -> KeyDoorGame:
    looks = {state: f"s{state[0]}{'k' if state[1] else ''}" for state in layout.hidden_states}
    controls = {"l": Move.LEFT, "r": Move.RIGHT, "u": Move.USE}
    return KeyDoorGame("Test", layout, looks, controls)


def _press(game: KeyDoorGame, buttons: str) -> str:
    state = game.start_symbol
    for button in buttons:
        state = game.step(state, button)
    return state


def test_walls_stop_the_agent() -> None:
    assert _press(_game(), "ll") == "s0"
    assert _press(_game(), "rrrr") == "s3"


def test_door_needs_the_key() -> None:
    assert _press(_game(), "rru") == "s3"
    assert _press(_game(), "lurrru") == WIN


def test_open_door_needs_no_key() -> None:
    assert _press(_game(NO_KEY), "rru") == WIN


def test_invalid_layouts_raise() -> None:
    with pytest.raises(ValueError, match="außerhalb"):
        Layout(door=7)
    with pytest.raises(ValueError, match="verschiedene Felder"):
        Layout(key=3, door=3)
    with pytest.raises(ValueError, match="mindestens 2"):
        Layout(length=1, start=0, key=0, door=0)


def test_invalid_games_raise() -> None:
    game = _game()
    with pytest.raises(ValueError, match="Jede Bewegung"):
        KeyDoorGame("x", STANDARD, game.looks, {"l": Move.LEFT, "r": Move.LEFT, "u": Move.USE})
    with pytest.raises(ValueError, match="Unbekannte Taste"):
        game.step(game.start_symbol, "q")
    with pytest.raises(ValueError, match="Unbekanntes Symbol"):
        game.step("nirgends", "l")


def test_made_games_differ_in_looks_and_buttons() -> None:
    rng = random.Random(0)
    first, second = make_game("a", STANDARD, rng), make_game("b", STANDARD, rng)
    assert len(first.looks) == 8
    assert first.looks != second.looks or first.controls != second.controls
