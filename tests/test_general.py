import random

import pytest

from hekmatki.general.agent import GeneralAgent, Planning
from hekmatki.general.detector import Detector, Strategy, binomial_tail
from hekmatki.general.env import Transition, Wiring
from hekmatki.general.form import AxisKind, find_form
from hekmatki.general.knowledge import Knowledge, RuleBook, learn_goal
from hekmatki.general.library import (
    AnyShift,
    Hole,
    Library,
    Template,
    anti_unify,
    generalize,
    instances,
    subsumes,
)
from hekmatki.general.programs import (
    Falls,
    Keep,
    Program,
    Rises,
    Shift,
    When,
    core,
    cost,
    describe,
    direction,
    fits,
    predict,
)
from hekmatki.general.run import play_episode
from hekmatki.general.synthesis import Example, synthesize, vocabulary
from hekmatki.general.worlds import Lattice, SortedSearch, random_lattice

BLOCKED_STEP = When(2, 1, Keep(), Shift(1))
"""„+1, außer Größe 2 ist 1“: ein Schritt, den eine Wand sperren kann."""


def _corridor(slip: float = 0.0) -> Lattice:
    """Ein Gang 4×2 ohne Hindernisse, ungemischt."""
    return Lattice(2, 4, frozenset(), Wiring.plain(8, 4), slip)


def _trained(env: Lattice | SortedSearch, episodes: int, seed: int = 0) -> GeneralAgent:
    agent = GeneralAgent(env.actions)
    rng = random.Random(seed)
    for _ in range(episodes):
        play_episode(env, agent, rng, 300)
    return agent


# Welten


def test_wiring_mixes_components_and_actions() -> None:
    wiring = Wiring((2, 0, 1), (1, 0))
    assert wiring.observe([10, 20, 30]) == (30, 10, 20)
    assert wiring.inner_action(0) == 1
    with pytest.raises(ValueError, match="Umordnung"):
        Wiring((0, 0, 1), (0, 1))
    with pytest.raises(ValueError, match="Taste 5"):
        wiring.inner_action(5)


def test_lattice_moves_senses_walls_and_slips() -> None:
    room = _corridor()
    room.position, room.goal = (0, 0), (1, 0)
    # Innere Beobachtung: x, y, versperrt +x, -x, +y, -y, Ziel x, Ziel y.
    assert room.step(0, random.Random(0)).observation == (1, 0, 0, 0, 0, 1, 1, 0)
    assert room.step(3, random.Random(0)).observation[:2] == (1, 0)  # Rand bei y = -1.
    slippery = _corridor(slip=0.999)
    slippery.position = (0, 0)
    assert slippery.step(0, random.Random(0)).observation[:2] == (0, 0)


def test_random_lattice_keeps_free_cells_connected() -> None:
    rng = random.Random(3)
    room = random_lattice(3, 5, Wiring.plain(12, 6), rng, obstacles=0.3)
    assert len(room.blocked) > 10
    room.reset(rng)
    assert room.least_steps() >= 1
    with pytest.raises(ValueError, match="Hindernisanteil"):
        random_lattice(2, 4, Wiring.plain(8, 4), rng, obstacles=0.7)


def test_sorted_search_walks_a_tree_of_a_million_keys() -> None:
    search = SortedSearch(20, Wiring.plain(4, 3))
    assert search.count == 1_048_575
    keys = [search.key(i) for i in range(0, search.count, 4099)]
    assert keys == sorted(set(keys))
    rng = random.Random(1)
    start = search.reset(rng)
    assert start[3] == 1  # ganz oben
    went_left = search.step(SortedSearch.LEFT, rng).observation
    assert went_left[0] < start[0]
    assert search.step(SortedSearch.UP, rng).observation == start
    assert search.least_steps() <= 19


# Programme


def test_programs_predict_check_and_describe() -> None:
    before = (5, 0, 0)
    assert fits(BLOCKED_STEP, before, (6, 0, 0), 0)
    assert not fits(BLOCKED_STEP, (5, 0, 1), (6, 0, 1), 0)
    assert predict(BLOCKED_STEP, before, 0) == 6
    assert predict(Rises(), before, 0) is None
    assert direction(Falls(), before) == -1
    assert cost(BLOCKED_STEP) == 3
    assert core(BLOCKED_STEP) == Shift(1)
    assert core(When(2, 1, Rises(), Falls())) is None
    assert describe(BLOCKED_STEP) == "+1, außer G2 = 1 (dann bleibt sie)"


# Regeln suchen


def test_synthesis_finds_the_shortest_rule_without_exceptions() -> None:
    examples = [
        Example((x, 0, wall), (x if wall else x + 1, 0, wall)) for x in range(5) for wall in (0, 1)
    ]
    found = synthesize(examples, 0, {2: (0, 1)})
    assert found.program == BLOCKED_STEP
    assert found.exact
    assert found.tested > 5
    assert synthesize(examples, 1, {2: (0, 1)}).program == Keep()


def test_synthesis_tolerates_noise_and_gives_up_on_chaos() -> None:
    steps = [Example((x, 0), (x + 1, 0)) for x in range(18)]
    slips = [Example((x, 0), (x, 0)) for x in range(2)]
    found = synthesize(steps + slips, 0, {})
    assert found.program == Shift(1)
    assert found.errors == 2
    chaos = [Example((x, 0), (x + (x % 3) - 1, 0)) for x in range(30)]
    assert synthesize(chaos, 0, {}).program is None


def test_budget_limits_the_search() -> None:
    examples = [
        Example((x, wall), (x if wall else x + 1, wall)) for x in range(4) for wall in (0, 1)
    ]
    assert synthesize(examples, 0, {1: (0, 1)}, budget=3).program is None


# Bibliothek


def test_anti_unification_finds_the_common_pattern() -> None:
    left = generalize(When(3, 1, Keep(), Shift(-1)))
    right = generalize(When(5, 1, Keep(), Shift(1)))
    common = anti_unify(left, right)
    assert common == Template(1, Keep(), AnyShift())
    assert subsumes(common, left)
    assert anti_unify(generalize(When(0, 1, Keep(), Falls())), right) == Template(1, Keep(), Hole())
    assert not subsumes(right, common)


def test_library_makes_known_patterns_cheap_and_counts_reuse() -> None:
    library = Library()
    rules: list[Program] = [When(2, 1, Keep(), Shift(1)), When(3, 1, Keep(), Shift(-1)), Keep()]
    [entry] = library.absorb(rules, "2D")
    assert entry.pattern == Template(1, Keep(), AnyShift())
    words = vocabulary([Example((0, 0), (1, 0))], 0, {1: (0, 1)})
    assert (When(1, 1, Keep(), Shift(1)), 0) in list(instances(entry.pattern, words, 0))
    examples = [
        Example((x, wall), (x if wall else x + 1, wall)) for x in range(4) for wall in (0, 1)
    ]
    with_library = synthesize(examples, 0, {1: (0, 1)}, library)
    without = synthesize(examples, 0, {1: (0, 1)})
    assert with_library.program == without.program
    assert with_library.entry == entry.name
    assert with_library.tested < without.tested
    assert library.close_world("3D", [entry.name]) == []
    assert entry.reuses == {"3D": 1}


def test_library_drops_entries_nobody_uses() -> None:
    library = Library(patience=2)
    [entry] = library.absorb([When(2, 1, Keep(), Shift(1)), When(3, 1, Keep(), Shift(-1))], "2D")
    assert library.close_world("Suche", []) == []
    assert library.close_world("Text", []) == [entry]
    assert library.removed == [entry]


# Ziel, Form, Plan


def test_goal_is_the_smallest_set_of_equal_pairs() -> None:
    reached = [(3, 3, 1, 1, 0), (5, 5, 2, 2, 0)]
    missed = [(3, 4, 1, 1, 0), (5, 5, 1, 2, 0), (2, 2, 0, 1, 0)]
    assert learn_goal(reached, missed) == ((0, 1), (2, 3))
    assert learn_goal([], missed) is None


def test_form_from_rules_space_and_order() -> None:
    space: dict[tuple[int, int], Program] = {
        (0, 0): BLOCKED_STEP,
        (1, 0): When(3, 1, Keep(), Shift(-1)),
        (0, 1): Keep(),
        (1, 1): Keep(),
    }
    form = find_form(space, space, actions=2, components=2)
    assert [a.kind for a in form.axes] == [AxisKind.SPACE]
    assert form.fixed == (1,)
    assert form.name == "Raum mit 1 Dimension"
    order: dict[tuple[int, int], Program] = {
        (0, 0): Rises(),
        (1, 0): Falls(),
        (0, 1): Keep(),
        (1, 1): Keep(),
    }
    assert find_form(order, order, 2, 2).name == "Ordnung"
    assert find_form({}, {}, 2, 2).name == "unbekannt"


def test_rulebook_relearns_when_an_exact_rule_breaks() -> None:
    book = RuleBook()
    for x in range(4):
        book.add(Transition((x, 0), 0, (x + 1, 0), False))
    book.update()
    assert book.rule(0, 0) == Shift(1)
    for x in range(6):
        book.add(Transition((x, 1), 0, (x, 1), False))  # An der Wand bleibt alles.
    book.update()
    assert book.rule(0, 0) == When(1, 1, Keep(), Shift(1))


# Der allgemeine Agent


def test_general_agent_finds_space_and_walks_straight_to_the_goal() -> None:
    room = random_lattice(2, 6, Wiring.shuffled(8, 4, random.Random(2)), random.Random(2))
    agent = _trained(room, episodes=8)
    assert agent.form().name == "Raum mit 2 Dimensionen"
    rng = random.Random(9)
    episode = play_episode(room, agent, rng, 300)
    assert episode.reached
    assert episode.steps <= 3 * episode.least + 6


def test_general_agent_learns_binary_search_on_small_trees() -> None:
    wiring = Wiring.shuffled(4, 3, random.Random(4))
    agent = GeneralAgent(3)
    rng = random.Random(4)
    for height in (3, 4, 5):
        agent.new_place()
        for _ in range(6):
            play_episode(SortedSearch(height, wiring, 7), agent, rng, 300)
    assert agent.form().name == "Ordnung"
    agent.new_place()
    big = SortedSearch(20, wiring, 7)
    episode = play_episode(big, agent, rng, 100)
    assert episode.reached
    assert episode.steps == episode.least


def test_greedy_agent_cannot_search_without_form() -> None:
    wiring = Wiring.plain(4, 3)
    agent = GeneralAgent(3, Planning.GREEDY)
    rng = random.Random(0)
    for _ in range(10):
        play_episode(SortedSearch(3, wiring), agent, rng, 300)
    assert not play_episode(SortedSearch(16, wiring), agent, rng, 60).reached


# Neue Umgebung erkennen


def test_binomial_tail() -> None:
    assert binomial_tail(0, 5, 0.1) == pytest.approx(1.0)
    assert binomial_tail(5, 5, 0.1) == pytest.approx(1e-5)


def test_detector_switches_maps_and_comes_back() -> None:
    room = random_lattice(2, 5, Wiring.plain(8, 4), random.Random(1))
    swapped = Lattice(2, 5, room.blocked, Wiring(tuple(range(8)), (1, 0, 3, 2)))
    agent = GeneralAgent(4, detector=Detector(Strategy.EXPECTED))
    rng = random.Random(5)
    for env in (room, swapped, room):
        for _ in range(8):
            play_episode(env, agent, rng, 300)
    kinds = [event.kind for event in agent.events if event.kind != "verfeinern"]
    assert "neu" in kinds
    assert "zurück" in kinds
    assert agent.current == 0


def test_every_surprise_makes_many_maps_in_a_noisy_room() -> None:
    room = random_lattice(2, 5, Wiring.plain(8, 4), random.Random(1), slip=0.2)
    agent = GeneralAgent(4, detector=Detector(Strategy.EVERY))
    rng = random.Random(5)
    for _ in range(10):
        play_episode(room, agent, rng, 300)
    assert len(agent.maps) > 3


def test_knowledge_checks_each_rule() -> None:
    knowledge = Knowledge()
    for x in range(3):
        knowledge.learn(Transition((x, 0), 0, (x + 1, 0), False))
    checks = knowledge.checks(Transition((5, 0), 0, (5, 0), False))
    assert {(c.slot, c.hit) for c in checks} == {((0, 0), False), ((0, 1), True)}
