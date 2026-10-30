import random
from collections.abc import Callable, Iterable, Sequence

import pytest

from hekmatki.action import ActionRecord
from hekmatki.evaluation import typical_probability
from hekmatki.markov import MarkovModel
from hekmatki.schema import (
    OnlineMixture,
    Schema,
    adaptive_schema_predictor,
    all_bindings,
    fixed_schema_predictor,
    instantiate,
    merge,
    merge_schemas,
    schema_or_flat_model,
    schema_or_flat_predictor,
    schemas_or_flat_model,
)
from hekmatki.situations import (
    Situation,
    conversation_situations,
    gate_stress_variants,
    small_talk,
    waiting_situations,
)


def _trained(situation: Situation, rng: random.Random) -> MarkovModel:
    model = MarkovModel(situation.alphabet)
    model.observe_sequence(situation.sample(400, rng))
    return model


def _waiting_schema(seed: int) -> Schema:
    rng = random.Random(seed)
    situations = waiting_situations()
    merged = merge(_trained(situations["arzt"], rng), _trained(situations["ubahn"], rng), "Warten")
    assert merged.schema is not None
    return merged.schema


def test_similar_waiting_situations_merge() -> None:
    assert _waiting_schema(1).roles == ("rolle_1", "rolle_2", "rolle_3", "rolle_4")


def test_different_structure_does_not_merge() -> None:
    rng = random.Random(1)
    doctor = _trained(waiting_situations()["arzt"], rng)
    result = merge(doctor, _trained(small_talk(), rng), "Kontrolle")
    assert result.schema is None
    assert result.distance > 0.1


def test_binding_requires_equal_sizes() -> None:
    with pytest.raises(ValueError, match="gleich viele"):
        all_bindings(["a", "b"], ["r1"])


def test_fixed_schema_predicts_matching_situation_almost_optimally() -> None:
    rng = random.Random(2)
    gate = waiting_situations()["gate"]
    predictor = fixed_schema_predictor(_waiting_schema(2), gate.alphabet, gate.sample(40, rng))
    test = gate.sample(500, rng)
    optimum = typical_probability(gate, test)
    assert typical_probability(predictor, test) == pytest.approx(optimum, abs=0.02)


def test_predictor_rejects_foreign_symbols() -> None:
    gate = waiting_situations()["gate"]
    with pytest.raises(ValueError, match="außerhalb des Alphabets"):
        fixed_schema_predictor(_waiting_schema(3), gate.alphabet, ["wetter", "urlaub"])


def test_adaptive_schema_recovers_when_situation_deviates() -> None:
    rng = random.Random(4)
    delayed = gate_stress_variants()["sehr lang"]
    schema = _waiting_schema(4)
    observed, test = delayed.sample(160, rng), delayed.sample(500, rng)
    fixed = fixed_schema_predictor(schema, delayed.alphabet, observed)
    adaptive = adaptive_schema_predictor(schema, delayed.alphabet, observed)
    assert typical_probability(adaptive, test) > typical_probability(fixed, test) + 0.05


def test_checked_schema_is_a_proper_mixture() -> None:
    rng = random.Random(5)
    gate = waiting_situations()["gate"]
    predictor = schema_or_flat_predictor(_waiting_schema(5), gate.alphabet, gate.sample(10, rng))
    for previous in gate.alphabet:
        total = sum(predictor.probability(previous, following) for following in gate.alphabet)
        assert total == pytest.approx(1.0)


def test_instantiate_rejects_incomplete_binding() -> None:
    with pytest.raises(ValueError, match="jede Rolle"):
        instantiate(_waiting_schema(6), {"a": "rolle_1"}, prior_strength=10.0)


@pytest.mark.parametrize(
    "make",
    [fixed_schema_predictor, adaptive_schema_predictor, schema_or_flat_predictor],
)
def test_predictors_accept_an_alphabet_that_can_be_read_once(
    make: Callable[[Schema, Iterable[str], Sequence[str]], OnlineMixture],
) -> None:
    rng = random.Random(7)
    gate = waiting_situations()["gate"]
    schema, observed = _waiting_schema(7), gate.sample(40, rng)
    from_list = make(schema, list(gate.alphabet), observed)
    from_iterator = make(schema, iter(gate.alphabet), observed)
    for previous in gate.alphabet:
        for following in gate.alphabet:
            assert from_iterator.probability(previous, following) == pytest.approx(
                from_list.probability(previous, following)
            )


def test_instantiate_rejects_a_role_bound_twice() -> None:
    schema = _waiting_schema(6)
    first, second, *rest = schema.roles
    binding = {f"s{i}": role for i, role in enumerate([first, first, second, *rest])}
    with pytest.raises(ValueError, match="genau einmal"):
        instantiate(schema, binding, prior_strength=10.0)


def test_instantiate_rejects_non_positive_strength() -> None:
    schema = _waiting_schema(7)
    binding = dict(zip("abcd", schema.roles, strict=True))
    with pytest.raises(ValueError, match="positiv"):
        instantiate(schema, binding, prior_strength=0.0)


def test_mixture_shifts_weight_to_the_better_model() -> None:
    good = MarkovModel(["a", "b"])
    good.observe("a", "b", weight=100.0)
    bad = MarkovModel(["a", "b"])
    bad.observe("a", "a", weight=100.0)
    mixture = OnlineMixture([good, bad])
    before = mixture.probability("a", "b")
    mixture.observe_sequence(["a", "b", "a", "b", "a", "b"])
    assert mixture.probability("a", "b") > before
    assert mixture.probability("a", "b") > 0.9


def test_mixture_rejects_invalid_setup() -> None:
    with pytest.raises(ValueError, match="mindestens ein Modell"):
        OnlineMixture([])
    with pytest.raises(ValueError, match="genau eine Vorab-Gewichtung"):
        OnlineMixture([MarkovModel(["a"])], log_priors=[0.0, 0.0])


def test_untrained_schema_model_is_a_distribution() -> None:
    alphabet = waiting_situations()["gate"].alphabet
    model = schema_or_flat_model(_waiting_schema(seed=0), alphabet)
    for previous in alphabet:
        total = sum(model.probability(previous, following) for following in alphabet)
        assert total == pytest.approx(1.0)


def test_several_schemas_give_a_distribution() -> None:
    talks = conversation_situations()
    rng = random.Random(0)
    talk = merge(_trained(talks["nachbar"], rng), _trained(talks["kollege"], rng), "Gespräch")
    assert talk.schema is not None
    alphabet = waiting_situations()["gate"].alphabet
    model = schemas_or_flat_model([_waiting_schema(seed=0), talk.schema], alphabet)
    for previous in alphabet:
        total = sum(model.probability(previous, following) for following in alphabet)
        assert total == pytest.approx(1.0)


def test_schemas_or_flat_needs_a_schema() -> None:
    with pytest.raises(ValueError, match="mindestens ein Schema"):
        schemas_or_flat_model([], ["a"])


def test_action_knowledge_must_use_known_roles() -> None:
    with pytest.raises(ValueError, match="unbekannte Rollen"):
        Schema("x", MarkovModel(["a", "b"]), action_knowledge={"c": ActionRecord(1.0, 2.0)})


def test_merge_reports_both_bindings() -> None:
    schema_result = merge(
        _trained(waiting_situations()["arzt"], random.Random(1)),
        _trained(waiting_situations()["ubahn"], random.Random(2)),
        "Warten",
    )
    assert schema_result.schema is not None
    assert set(schema_result.first_binding.values()) == set(schema_result.schema.roles)
    assert set(schema_result.second_binding.values()) == set(schema_result.schema.roles)


def _knowing(name: str, model: MarkovModel, acting_symbol: str | None) -> Schema:
    """Ein Modell, das an `acting_symbol` (und nur dort) erfolgreich gehandelt hat."""
    knowledge = {s: ActionRecord(10.0 if s == acting_symbol else 0.0, 10.0) for s in model.alphabet}
    return Schema(name, model, knowledge)


def test_merge_schemas_carries_action_knowledge_into_the_roles() -> None:
    arzt, ubahn = waiting_situations()["arzt"], waiting_situations()["ubahn"]
    rng = random.Random(0)
    first = _knowing("arzt", _trained(arzt, rng), arzt.action_symbols[0])
    second = _knowing("ubahn", _trained(ubahn, rng), ubahn.action_symbols[0])
    result = merge_schemas(first, second, "Warten")
    assert result.schema is not None
    acting = [r for r, rec in result.schema.action_knowledge.items() if rec.looks_successful()]
    assert acting == [result.first_binding[arzt.action_symbols[0]]]
    assert result.schema.action_knowledge[acting[0]].tries == 20.0


def test_merge_schemas_refuses_bindings_with_conflicting_decisions() -> None:
    arzt, ubahn = waiting_situations()["arzt"], waiting_situations()["ubahn"]
    rng = random.Random(0)
    first = _knowing("arzt", _trained(arzt, rng), arzt.action_symbols[0])
    second = _knowing("ubahn", _trained(ubahn, rng), None)
    assert merge_schemas(first, second, "Warten").schema is None
    assert merge_schemas(first, second, "Warten", check_decisions=False).schema is not None
