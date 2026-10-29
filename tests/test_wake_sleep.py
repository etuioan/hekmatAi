import random

import pytest

from hekmatki.experiments import run_multi_schema, run_wake_sleep
from hekmatki.situations import lamp_situations
from hekmatki.wake_sleep import WakeSleepAgent


def _live_through(agent: WakeSleepAgent, names: list[str], seed: int = 0) -> None:
    situations = lamp_situations()
    rng = random.Random(seed)
    previous: str | None = None
    for name in names:
        block = situations[name].sample(150, rng, start=previous)
        if previous is not None:
            block = block[1:]
        for symbol in block:
            if previous is not None:
                agent.step(previous, symbol)
            previous = symbol


def test_agent_sleeps_by_itself_and_builds_a_schema() -> None:
    agent = WakeSleepAgent(lamp_situations()["arzt"].alphabet)
    _live_through(agent, ["arzt", "ubahn"])
    assert agent.sleeps == 2
    assert agent.schemas
    assert agent.contexts_in_schemas == 2


def test_new_situation_grows_into_the_schema() -> None:
    agent = WakeSleepAgent(lamp_situations()["arzt"].alphabet)
    _live_through(agent, ["arzt", "ubahn", "gate"])
    assert agent.contexts_in_schemas == 3


def test_without_maturity_the_agent_only_sleeps_when_told() -> None:
    agent = WakeSleepAgent(lamp_situations()["arzt"].alphabet, maturity=None)
    _live_through(agent, ["arzt", "ubahn"])
    assert agent.sleeps == 0
    assert not agent.schemas
    agent.sleep()
    assert agent.schemas


def test_single_context_gives_no_schema() -> None:
    agent = WakeSleepAgent(lamp_situations()["arzt"].alphabet)
    _live_through(agent, ["arzt"])
    assert agent.sleeps == 1
    assert not agent.schemas


def test_invalid_maturity_raises() -> None:
    with pytest.raises(ValueError, match="mindestens 1"):
        WakeSleepAgent(["a"], maturity=0)


def test_own_sleep_is_as_good_as_fixed_sleep() -> None:
    rows = {row.agent: row for row in run_wake_sleep(seeds=3)}
    own, fixed, contexts = rows["eigener Schlaf"], rows["fester Schlaf"], rows["Kontexte"]
    assert own.new_gate > contexts.new_gate
    assert own.new_checkout > contexts.new_checkout
    assert own.new_gate == pytest.approx(fixed.new_gate, abs=0.02)
    assert own.contexts_in_schema is not None
    assert own.contexts_in_schema > 2


def test_invalid_max_schemas_raises() -> None:
    with pytest.raises(ValueError, match="max_schemas"):
        WakeSleepAgent(["a"], max_schemas=0)


def test_waiting_and_conversations_get_separate_schemas() -> None:
    rows = {row.agent: row for row in run_multi_schema(seeds=3)}
    assert rows["ein Schema"].schemas == 1
    assert rows["mehrere Schemata"].schemas is not None
    assert rows["mehrere Schemata"].schemas > 1.5
