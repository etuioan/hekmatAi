import random

import pytest

from hekmatki.evaluation import geometric_mean, typical_probability
from hekmatki.markov import MarkovModel
from hekmatki.situations import waiting_situations


def test_geometric_mean_of_equal_values() -> None:
    assert geometric_mean([0.5, 0.5]) == pytest.approx(0.5)


def test_geometric_mean_is_zero_if_any_value_is_zero() -> None:
    assert geometric_mean([0.9, 0.0]) == 0.0


def test_geometric_mean_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="mindestens eine"):
        geometric_mean([])
    with pytest.raises(ValueError, match="zwischen 0 und 1"):
        geometric_mean([1.5])


def test_overconfident_model_cannot_beat_true_model() -> None:
    """Die Messgröße ist ehrlich: Übertriebene Sicherheit wird nicht belohnt."""
    gate = waiting_situations()["gate"]
    overconfident = MarkovModel(gate.alphabet, pseudocount=0.001)
    for symbol in gate.alphabet:
        for following in gate.alphabet:
            if gate.probability(symbol, following) == max(
                gate.probability(symbol, f) for f in gate.alphabet
            ):
                overconfident.observe(symbol, following, weight=1000.0)
    test = gate.sample(2000, random.Random(0))
    assert typical_probability(overconfident, test) < typical_probability(gate, test)
