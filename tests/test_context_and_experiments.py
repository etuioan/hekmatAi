import random
from itertools import pairwise

import pytest

from hekmatki.context import ContextInference
from hekmatki.experiments import run_h11, run_h12, run_recognition
from hekmatki.experiments.recognition import correct_share
from hekmatki.situations import commuting_situations


def test_context_inference_finds_both_commuting_directions() -> None:
    situations = commuting_situations()
    rng = random.Random(0)
    stream = situations["hinweg"].sample(200, rng)
    stream += situations["rueckweg"].sample(200, rng, start=stream[-1])[1:]
    agent = ContextInference(situations["hinweg"].alphabet)
    predictions = [agent.step(a, b) for a, b in pairwise(stream)]
    assert len(agent.contexts) == 2
    assert all(0.0 < p <= 1.0 for p in predictions)


def test_invalid_stay_probability_raises() -> None:
    with pytest.raises(ValueError, match="zwischen 0 und 1"):
        ContextInference(["a"], stay_probability=1.0)


def test_h11_schema_beats_flat_learner_with_few_observations() -> None:
    first = run_h11(seeds=3, budgets=(5,)).rows[0]
    assert first.schema > first.flat


def test_h12_contexts_beat_single_model() -> None:
    result = run_h12(seeds=3)
    assert result.with_contexts > result.single_model
    assert result.contexts_found == pytest.approx(2.0)


def test_h12_needs_at_least_three_blocks() -> None:
    with pytest.raises(ValueError, match="mindestens 3"):
        run_h12(seeds=1, blocks=2)


def test_invalid_new_context_share_raises() -> None:
    with pytest.raises(ValueError, match="new_context_share"):
        ContextInference(["a"], new_context_share=0.0)


def test_correct_share_counts_each_context_for_one_situation_only() -> None:
    merged = [("arzt", 0)] * 6 + [("ubahn", 0)] * 4
    assert correct_share(merged) == pytest.approx(0.6)
    clean = [("arzt", 0)] * 6 + [("ubahn", 1)] * 4
    assert correct_share(clean) == pytest.approx(1.0)


def test_recognition_keeps_many_similar_situations_apart() -> None:
    rows = {row.world: row for row in run_recognition(seeds=3)}
    assert rows["Lampen: Warten"].correct_share > 0.95
    assert rows["Lampen: Warten + Gespräche"].correct_share > 0.85
