"""Tests für die Hinweisreize auf Schaden (`general/cues.py`, ab 0.21)."""

import random

import pytest

from hekmatki.general.causes import Literal
from hekmatki.general.cues import CONFIDENCE, Cues, above


def test_above_matches_the_beta_distribution() -> None:
    # Ohne Daten ist die Quote gleichverteilt: P(Quote > 0,3) = 0,7.
    assert above(0, 0, 0.3) == pytest.approx(0.7)
    # Beta(3, 1): P(Quote > 0,5) = 1 − 0,5³.
    assert above(2, 2, 0.5) == pytest.approx(1 - 0.5**3)


def test_two_of_two_is_a_danger_but_four_of_thirty_is_not() -> None:
    assert above(2, 2, 0.15) >= CONFIDENCE
    assert above(4, 30, 0.15) < CONFIDENCE


def test_above_rejects_impossible_counts() -> None:
    with pytest.raises(ValueError, match="Treffer"):
        above(3, 2, 0.15)
    with pytest.raises(ValueError, match="Schwelle"):
        above(1, 2, 1.0)


def _stream(
    cues: Cues, rng: random.Random, steps: int, groups: tuple[tuple[int, ...], ...]
) -> None:
    """Zwei Felder (0 und 1) und Gesundheit (2): Steht in einem Feld eine 5, sinkt die
    Gesundheit meist; sonst selten."""
    health = 100
    for _ in range(steps):
        cells = (rng.choice((1, 2, 5)), rng.choice((1, 2, 3)))
        harmful = 5 in cells
        after = health - (rng.random() < (0.5 if harmful else 0.02))
        cues.observe((*cells, health), (*cells, after), groups)
        health = after if after > 0 else 100


def test_the_harmful_value_becomes_an_alarm() -> None:
    cues = Cues()
    _stream(cues, random.Random(0), 600, ())
    assert cues.alarms(2, 0.15, frozenset({0, 1}), ()) == [Literal(0, 5)]


def test_a_group_literal_can_be_an_alarm() -> None:
    cues = Cues()
    groups = ((0, 1),)
    _stream(cues, random.Random(1), 600, groups)
    assert Literal.some((0, 1), 5) in cues.alarms(2, 0.15, frozenset({0, 1}), groups)


def test_one_case_is_not_enough() -> None:
    cues = Cues()
    cues.observe((5, 10), (5, 9), ())
    assert cues.alarms(1, 0.15, frozenset({0}), ()) == []
