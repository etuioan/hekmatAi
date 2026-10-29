import random

import pytest

from hekmatki.situations import (
    Situation,
    commuting_situations,
    gate_stress_variants,
    lamp_situations,
    queue_situations,
    waiting_situations,
    with_disturbances,
)


def test_invalid_probabilities_raise() -> None:
    with pytest.raises(ValueError, match="ergeben nicht 1"):
        Situation(name="kaputt", transitions={"r": {"r": 0.5}}, symbols={"r": "s"})


def test_unknown_target_role_raises() -> None:
    with pytest.raises(ValueError, match="unbekannten Rollen"):
        Situation(name="kaputt", transitions={"r": {"x": 1.0}}, symbols={"r": "s"})


def test_sample_uses_only_own_symbols() -> None:
    gate = waiting_situations()["gate"]
    sequence = gate.sample(200, random.Random(0))
    assert set(sequence) <= set(gate.alphabet)
    assert len(sequence) == 200


def test_sample_respects_start_symbol() -> None:
    hinweg = commuting_situations()["hinweg"]
    assert hinweg.sample(5, random.Random(0), start="bahn")[0] == "bahn"


def test_true_probability_matches_definition() -> None:
    doctor = waiting_situations()["arzt"]
    assert doctor.probability("zeitschrift lesen", "zeitschrift lesen") == pytest.approx(0.85)
    assert doctor.probability("rezept abholen", "name aufgerufen") == 0.0


def test_disturbances_keep_valid_probabilities() -> None:
    disturbed = gate_stress_variants()["gestört"]
    for row in disturbed.transitions.values():
        assert sum(row.values()) == pytest.approx(1.0)
        assert min(row.values()) > 0.0


def test_disturbance_share_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="Störanteil"):
        with_disturbances({"r": {"r": 1.0}}, share=1.5)


def test_lamp_situations_share_symbols_but_not_meaning() -> None:
    situations = list(lamp_situations().values())
    assert len({s.alphabet for s in situations}) == 1
    meanings = {tuple(sorted(s.symbols.items())) for s in situations}
    assert len(meanings) == len(situations)


def test_unknown_action_role_raises() -> None:
    with pytest.raises(ValueError, match="Handlungsrolle"):
        Situation(name="kaputt", transitions={"r": {"r": 1.0}}, symbols={"r": "s"}, action_role="x")


def test_action_symbols_name_where_acting_works() -> None:
    assert waiting_situations()["arzt"].action_symbols == ("ins behandlungszimmer",)
    assert queue_situations()["post"].action_symbols == ("schalter frei",)
    assert commuting_situations()["hinweg"].action_symbols == ()
