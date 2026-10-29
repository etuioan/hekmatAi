"""Tests für die Neuerungen von 0.17: Bausteine, Formen, Welten, Planer, Detektor (H21–H24)."""

import math
import random

import pytest

from hekmatki.experiments.new_forms import GENERAL, NEW_WORLDS, run_new_forms
from hekmatki.experiments.world_stream import PHASES, live, run_world_stream, worlds
from hekmatki.general.agent import GeneralAgent
from hekmatki.general.detector import BF_BITS, Detector, Strategy
from hekmatki.general.env import Padded, Transition, Wiring
from hekmatki.general.form import AxisKind, find_form
from hekmatki.general.knowledge import Knowledge
from hekmatki.general.library import plausible
from hekmatki.general.planner import plan_model
from hekmatki.general.programs import (
    Copy,
    Cycle,
    Keep,
    Program,
    Shift,
    Until,
    When,
    can_change,
    cost,
    describe,
    fits,
    predict,
)
from hekmatki.general.run import play_episode
from hekmatki.general.synthesis import Example, synthesize
from hekmatki.general.worlds import Dials, Lattice, Shuffle, random_lattice

# Bausteine


def test_copy_takes_the_value_of_another_component() -> None:
    assert fits(Copy(1), (0, 7), (7, 7), 0)
    assert not fits(Copy(1), (0, 7), (6, 7), 0)
    assert predict(Copy(1), (0, 7), 0) == 7
    assert describe(Copy(1)) == "übernimmt G1"


def test_cycle_wraps_around() -> None:
    ring = Cycle(1, 4)
    assert fits(ring, (3,), (0,), 0)
    assert predict(ring, (2,), 0) == 3
    assert cost(ring) == 2
    assert can_change(ring, -3)
    assert describe(ring) == "+1 im Ring aus 4 Werten"


def test_until_repeats_a_step_until_the_switch_is_set() -> None:
    slide = Until(1, 1, 1)
    assert fits(slide, (2, 0), (5, 1), 0)
    assert fits(slide, (2, 1), (2, 1), 0)  # Schalter schon gesetzt: null Schritte.
    assert not fits(slide, (2, 0), (5, 0), 0)
    assert predict(slide, (2, 1), 0) == 2
    assert predict(slide, (2, 0), 0) is None  # Wie weit, weiß die Regel nicht.
    assert describe(slide) == "+1 immer wieder, bis G1 = 1"


def test_synthesis_finds_a_ring_written_the_short_way() -> None:
    examples = [Example((v, 0), ((v + 1) % 5, 0)) for v in range(5)] * 4
    found = synthesize(examples, 0, {})
    assert found.program == Cycle(1, 5)
    assert found.exact


def test_synthesis_finds_a_loop_from_long_jumps() -> None:
    examples = [Example((0, 0), (3, 1)), Example((1, 0), (2, 1)), Example((4, 1), (4, 1))] * 3
    found = synthesize(examples, 0, {1: (0, 1)})
    assert found.program == Until(1, 1, 1)


def test_synthesis_without_extension_has_no_loop() -> None:
    examples = [Example((0, 0), (3, 1)), Example((1, 0), (2, 1)), Example((4, 1), (4, 1))] * 3
    found = synthesize(examples, 0, {1: (0, 1)}, extended=False)
    assert not isinstance(found.program, Until)


def test_copy_needs_a_source_with_every_value() -> None:
    # G0 wird zufällig zu G1, aber G1 ist ein Schalter und kann G0s Werte nicht liefern.
    coincidence = [Example((1, 0), (0, 0)), Example((2, 1), (1, 1)), Example((3, 0), (3, 0))]
    assert not isinstance(synthesize(coincidence * 3, 0, {1: (0, 1)}).program, Copy)
    swap = [Example((v, w), (w, w)) for v in range(4) for w in range(4) if v != w]
    assert synthesize(swap, 0, {}).program == Copy(1)


def test_library_precheck_skips_rules_that_cannot_make_the_changes() -> None:
    assert plausible(When(1, 1, Keep(), Shift(1)), {1: 9, 0: 1})
    assert not plausible(When(1, 1, Keep(), Shift(1)), {-1: 9, 0: 1})
    assert plausible(Shift(1), {})


# Formen


def test_rings_make_a_product_form() -> None:
    rules: dict[tuple[int, int], Program] = {
        (0, 0): Cycle(1, 5),
        (1, 0): Cycle(-1, 5),
        (0, 1): Keep(),
        (1, 1): Keep(),
        (2, 0): Keep(),
        (3, 0): Keep(),
        (2, 1): Cycle(1, 5),
        (3, 1): Cycle(-1, 5),
    }
    form = find_form(rules, rules, 4, 2)
    assert [axis.kind for axis in form.axes] == [AxisKind.RING, AxisKind.RING]
    assert form.name == "Ring × Ring"


def test_slides_and_switches() -> None:
    rules: dict[tuple[int, int], Program] = {
        (0, 0): Until(1, 1, 1),
        (1, 0): Until(-1, 2, 1),
        (0, 1): Shift(1),
        (1, 1): Shift(-1),
    }
    assert find_form(rules, rules, 2, 3).name == "Raum mit 1 Dimension × Rutschbahn mit 1 Dimension"
    assert find_form(rules, rules, 2, 3, switches={1}).name == "Rutschbahn mit 1 Dimension"


def test_no_axis_means_no_known_form() -> None:
    rules = {(0, 0): Copy(1), (0, 1): Copy(0)}
    assert find_form(rules, rules, 1, 2).name == "keine bekannte Form"


# Welten


def test_dials_wrap_and_count_the_shorter_way() -> None:
    dials = Dials(2, 5, Wiring.plain(4, 4))
    dials.reset(random.Random(0))
    dials.values, dials.targets = [0, 4], [4, 4]
    assert dials.least_steps() == 1
    outcome = dials.step(1, random.Random(0))  # Scheibe 1 zurück: 0 -> 4
    assert outcome.reached
    assert dials.names()[0] == ["Scheibe 1", "Scheibe 2", "Ziel 1", "Ziel 2"]


def test_shuffle_swaps_neighbours_and_counts_inversions() -> None:
    shuffle = Shuffle(3, Wiring.plain(6, 2))
    shuffle.reset(random.Random(0))
    shuffle.slots, shuffle.target = [2, 1, 0], [0, 1, 2]
    assert shuffle.least_steps() == 3
    assert shuffle.step(0, random.Random(0)).observation[:3] == (1, 2, 0)


def test_ice_slides_until_a_wall() -> None:
    ice = Lattice(2, 4, frozenset({(3, 0)}), Wiring.plain(8, 4), ice=True)
    ice.reset(random.Random(0))
    ice.position = (0, 0)
    ice.step(0, random.Random(0))  # +x
    assert ice.position == (2, 0)


def test_ice_rooms_have_no_traps() -> None:
    rng = random.Random(3)
    room = random_lattice(2, 9, Wiring.plain(8, 4), rng, ice=True)
    places = set(room.places)
    for cell in places:
        for axis in range(2):
            for sign in (1, -1):
                assert room._move(cell, axis, sign) in places


def test_padded_world_adds_zeros_and_idle_keys() -> None:
    padded = Padded(Dials(1, 4, Wiring.plain(2, 2)), 4, 3)
    first = padded.reset(random.Random(0))
    assert len(first) == 4
    assert first[2:] == (0, 0)
    assert padded.step(2, random.Random(0)).observation == first
    with pytest.raises(ValueError, match="Tasten"):
        Padded(Dials(1, 4, Wiring.plain(2, 2)), 4, 1)


# Karte und Planer


def test_knowledge_remembers_where_a_loop_passed() -> None:
    knowledge = Knowledge()
    examples = [
        Transition((0, 0), 0, (3, 1), False),
        Transition((1, 0), 0, (2, 1), False),
        Transition((4, 1), 0, (4, 1), False),
    ]
    for transition in examples * 3:
        knowledge.learn(transition)
    assert knowledge.rules.rule(0, 0) == Until(1, 1, 1)
    assert any(p.start == (0, 0) and p.end == 3 for p in knowledge.passed)
    knowledge.forget_place()
    assert not knowledge.passed


def test_model_search_solves_shuffle_without_a_form() -> None:
    env = Shuffle(4, Wiring.shuffled(8, 3, random.Random(1)))
    agent = GeneralAgent(3)
    rng = random.Random(2)
    for _ in range(20):
        play_episode(env, agent, rng, 300)
    assert agent.form().name == "keine bekannte Form"
    observation = env.reset(rng)
    assert plan_model(agent.knowledge, observation, 3) is not None
    episode = play_episode(env, agent, rng, 300)
    assert episode.reached
    assert episode.steps == episode.least


# Neue Welt per Bayes-Faktor


def test_bayes_threshold_is_very_strong_evidence() -> None:
    assert 2 * math.log(2.0**BF_BITS) == pytest.approx(10.0)


def test_bayes_detector_switches_and_returns() -> None:
    room = random_lattice(2, 5, Wiring.plain(8, 4), random.Random(1))
    swapped = Lattice(2, 5, room.blocked, Wiring(tuple(range(8)), (1, 0, 3, 2)))
    agent = GeneralAgent(4, detector=Detector(Strategy.BAYES))
    rng = random.Random(5)
    for env in (room, swapped, room):
        for _ in range(8):
            play_episode(env, agent, rng, 300)
    kinds = [event.kind for event in agent.events if event.kind != "verfeinern"]
    assert kinds[:2] == ["neu", "zurück"]
    assert agent.current == 0


# Versuche


def test_new_forms_experiment() -> None:
    rows = run_new_forms(seeds=1)
    assert [row.world for row in rows] == [spec.name for spec in NEW_WORLDS]
    for row in rows:
        assert row.form_found("Stand 0.17") == 1.0
        assert row.reached["Stand 0.17"] == 1.0
        assert set(row.forms) == set(GENERAL)
    dials = rows[1]
    assert dials.steps["Stand 0.17"] == dials.best


def test_world_stream_uses_one_interface() -> None:
    envs = worlds(0)
    assert {env.actions for env in envs} == {6}
    assert {len(env.reset(random.Random(0))) for env in envs} == {8}
    life = live("Bayes-Faktor", 0)
    assert list(life.steps) == list(PHASES)


def test_world_stream_reports_every_handling() -> None:
    rows = run_world_stream(seeds=1)
    by_name = {row.handling: row for row in rows}
    assert by_name["ohne Erkennung"].maps == 1
    assert set(by_name["Bayes-Faktor"].detected) == set(PHASES[1:])
