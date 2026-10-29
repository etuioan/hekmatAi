import random

import pytest

from hekmatki.action import ActionRecord, by_role, combined, decisions_conflict, try_actions


def test_record_without_experience_is_undecided() -> None:
    assert ActionRecord().success_probability() == pytest.approx(0.5)


def test_record_learns_from_tries() -> None:
    record = ActionRecord().after(True).after(True).after(False)
    assert record == ActionRecord(2.0, 3.0)


def test_invalid_record_raises() -> None:
    with pytest.raises(ValueError, match="Erfolge"):
        ActionRecord(wins=2.0, tries=1.0)


def test_trying_finds_where_acting_succeeds() -> None:
    sequence = ["warten", "warten", "jetzt"] * 300
    records = try_actions(sequence, succeeds_in=["jetzt"], rng=random.Random(0), try_rate=0.2)
    assert records["jetzt"].success_probability() > 0.9
    assert records["warten"].success_probability() < 0.1


def test_knowledge_moves_to_roles_and_adds_up() -> None:
    first = by_role({"bahn": ActionRecord(3.0, 4.0)}, {"bahn": "rolle_1"})
    second = by_role({"aufruf": ActionRecord(1.0, 1.0)}, {"aufruf": "rolle_1"})
    assert combined(first, second) == {"rolle_1": ActionRecord(4.0, 5.0)}


def test_knowledge_for_symbol_without_role_raises() -> None:
    with pytest.raises(ValueError, match="ohne Rolle"):
        by_role({"x": ActionRecord()}, {})


def test_looks_successful_needs_more_wins_than_losses() -> None:
    assert ActionRecord(9.0, 10.0).looks_successful()
    assert not ActionRecord(1.0, 10.0).looks_successful()
    assert not ActionRecord().looks_successful()


def test_decisions_conflict_when_one_side_succeeds_and_the_other_fails() -> None:
    works = {"rolle_1": ActionRecord(9.0, 10.0)}
    fails = {"rolle_1": ActionRecord(0.0, 10.0)}
    assert decisions_conflict(works, fails)
    assert not decisions_conflict(works, works)


def test_untried_states_are_no_conflict() -> None:
    works = {"rolle_1": ActionRecord(9.0, 10.0)}
    assert not decisions_conflict(works, {"rolle_1": ActionRecord()})
    assert not decisions_conflict(works, {"rolle_2": ActionRecord(0.0, 10.0)})
