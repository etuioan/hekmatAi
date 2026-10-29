import math

import pytest

from hekmatki.markov import MarkovModel


def test_rows_are_probability_distributions() -> None:
    model = MarkovModel(["a", "b", "c"])
    model.observe_sequence(["a", "b", "a", "c", "a", "b"])
    for row in model.matrix():
        assert math.isclose(sum(row), 1.0)


def test_observed_transition_becomes_more_likely() -> None:
    model = MarkovModel(["a", "b"])
    before = model.probability("a", "b")
    model.observe("a", "b")
    assert model.probability("a", "b") > before


def test_unknown_symbol_raises() -> None:
    model = MarkovModel(["a", "b"])
    with pytest.raises(ValueError, match="Unbekanntes Symbol"):
        model.probability("a", "x")


def test_empty_alphabet_raises() -> None:
    with pytest.raises(ValueError, match="leer"):
        MarkovModel([])


def test_relabeled_keeps_counts() -> None:
    model = MarkovModel(["a", "b"])
    model.observe("a", "b", weight=3.0)
    renamed = model.relabeled({"a": "x", "b": "y"})
    assert renamed.count("x", "y") == 3.0


def test_relabeled_rejects_non_unique_mapping() -> None:
    model = MarkovModel(["a", "b"])
    with pytest.raises(ValueError, match="eindeutig"):
        model.relabeled({"a": "x", "b": "x"})


def test_merged_with_sums_counts() -> None:
    first, second = MarkovModel(["a", "b"]), MarkovModel(["a", "b"])
    first.observe("a", "b")
    second.observe("a", "b", weight=2.0)
    assert first.merged_with(second).count("a", "b") == 3.0


def test_total_count_sums_all_transitions() -> None:
    model = MarkovModel(["a", "b"])
    model.observe_sequence(["a", "b", "b", "a"])
    assert model.total_count() == pytest.approx(3.0)
