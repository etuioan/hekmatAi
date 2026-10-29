import random

import pytest

from hekmatki.experiments.meta_schema import (
    EXPECTED_META_SCHEMAS,
    EXPECTED_SCHEMAS,
    acts_at,
    build_stack,
    new_situations,
    run_meta_schema,
)
from hekmatki.markov import MarkovModel
from hekmatki.schema import Schema
from hekmatki.situations import queue_situations, waiting_situations
from hekmatki.stack import Group, consolidate, experience


def _members(groups: list[Group]) -> list[set[str]]:
    return sorted((set(g.members) for g in groups), key=sorted)


def test_experience_learns_where_acting_works() -> None:
    arzt = waiting_situations()["arzt"]
    lived = experience("arzt", arzt, 400, random.Random(0))
    assert lived.members == ("arzt",)
    acting = {s for s, rec in lived.schema.action_knowledge.items() if rec.looks_successful()}
    assert acting == set(arzt.action_symbols)


def test_consolidate_keeps_what_does_not_fit() -> None:
    rng = random.Random(0)
    lived = [
        experience("arzt", waiting_situations()["arzt"], 400, rng),
        experience("post", queue_situations()["post"], 400, rng),
    ]
    groups = consolidate(lived, threshold=0.1, prefix="Schema")
    assert _members(groups) == [{"arzt"}, {"post"}]
    assert not any(g.is_merged for g in groups)


def test_stack_forms_families_and_one_meta_schema() -> None:
    stack = build_stack(400, random.Random(0))
    assert _members(stack["Ebene 2"]) == sorted(EXPECTED_SCHEMAS, key=sorted)
    assert _members(stack["Ebene 3"]) == sorted(EXPECTED_META_SCHEMAS, key=sorted)
    assert len(stack["Ebene 3 ohne Prüfung"]) == 1
    names = {g.schema.name for g in stack["Ebene 3"]}
    assert "Meta-Schema 1" in names


def test_meta_schema_knows_where_to_act_in_a_new_situation() -> None:
    rng = random.Random(0)
    stack = build_stack(400, rng)
    gate = new_situations()["Gate"]
    model = MarkovModel(gate.alphabet)
    model.observe_sequence(gate.sample(200, rng))
    schemas = [g.schema for g in stack["Ebene 3"]]
    assert acts_at(schemas, model) == set(gate.action_symbols)


def test_acts_at_needs_a_fitting_slice() -> None:
    too_big = Schema("groß", MarkovModel(["a", "b", "c"]))
    with pytest.raises(ValueError, match="Keine Scheibe"):
        acts_at([too_big], MarkovModel(["x"]))


def test_acts_nowhere_without_action_knowledge() -> None:
    assert acts_at([Schema("leer", MarkovModel(["a", "b"]))], MarkovModel(["p", "q"])) == set()


def test_late_merging_beats_early_merging() -> None:
    early, late = run_meta_schema(seeds=5, lengths=(15, 400))
    assert late.schemas_as_expected == 1.0
    assert late.meta_as_expected == 1.0
    assert early.families_mixed > late.families_mixed
    assert late.right_decisions["Ebene 3"]["Gate"] > early.right_decisions["Ebene 3"]["Gate"]
    assert late.right_decisions["Ebene 3 ohne Prüfung"]["Gate"] < 0.5
