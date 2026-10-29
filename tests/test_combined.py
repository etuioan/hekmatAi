from hekmatki.context import ContextInference
from hekmatki.experiments import run_combined
from hekmatki.markov import MarkovModel
from hekmatki.schema import OnlineMixture


def test_new_contexts_start_from_the_given_factory() -> None:
    agent = ContextInference(["a", "b"])
    agent.replace_new_context_model(
        lambda: OnlineMixture([MarkovModel(["a", "b"]), MarkovModel(["a", "b"])])
    )
    agent.step("a", "b")
    assert isinstance(agent.contexts[0], OnlineMixture)


def test_empty_model_is_the_default_for_new_contexts() -> None:
    agent = ContextInference(["a", "b"])
    agent.step("a", "b")
    assert isinstance(agent.contexts[0], MarkovModel)


def test_schema_helps_in_a_new_situation_without_hurting_known_ones() -> None:
    rows = {row.agent: row for row in run_combined(seeds=3)}
    single, contexts, schema = rows["ein Modell"], rows["Kontexte"], rows["Kontexte + Schema"]
    assert schema.new_situation > contexts.new_situation > single.new_situation
    assert schema.known_situations >= contexts.known_situations - 0.01
    assert rows["Optimum"].new_situation > schema.new_situation
    assert schema.contexts_found is not None
    assert single.contexts_found is None
