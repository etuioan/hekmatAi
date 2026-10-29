"""Tests für 0.18: Ursachen, Teilziele, eigene Ziele, der Baustein „wird v“ und die Trennung
zwischen Agent und Adaptern."""

import ast
import random
from pathlib import Path

from hekmatki.general.agent import GeneralAgent
from hekmatki.general.causes import Change, Event, Kind, Literal, cover
from hekmatki.general.env import Observation, Outcome, Transition
from hekmatki.general.knowledge import Knowledge
from hekmatki.general.programs import Becomes, Copy, fits, predict
from hekmatki.general.run import RandomAgent
from hekmatki.general.subgoals import Target, achieve, imagine, model, search
from hekmatki.general.synthesis import Example, synthesize

GENERAL = Path(__file__).parent.parent / "src" / "hekmatki" / "general"


class Spring:
    """Ein Gang mit einer Quelle am rechten Ende: Größe 0 Ort, 1 „an der Quelle“, 2 Vorrat.

    Tasten: 0 links, 1 rechts, 2 schöpfen (Vorrat +1, nur an der Quelle), 3 nichts. Alle
    `decay` Schritte sinkt der Vorrat um 1, egal was der Agent tut.
    """

    def __init__(self, length: int = 4, decay: int = 0) -> None:
        self.length, self.decay = length, decay
        self.position, self.stock, self.time = 0, 0, 0

    @property
    def actions(self) -> int:
        return 4

    def reset(self, rng: random.Random) -> Observation:
        self.position, self.stock, self.time = 0, 4 if self.decay else 0, 0
        return self._observe()

    def step(self, action: int, rng: random.Random) -> Outcome:
        self.time += 1
        if action == 0:
            self.position = max(0, self.position - 1)
        elif action == 1:
            self.position = min(self.length - 1, self.position + 1)
        elif action == 2 and self.position == self.length - 1:
            self.stock += 1
        if self.decay and self.time % self.decay == 0 and self.stock > 0:
            self.stock -= 1
        return Outcome(self._observe(), False)

    def least_steps(self) -> int:
        return 0

    def _observe(self) -> Observation:
        return (self.position, int(self.position == self.length - 1), self.stock)


def _experience(env: Spring, steps: int, seed: int = 0) -> Knowledge:
    knowledge, rng = Knowledge(), random.Random(seed)
    observation = env.reset(rng)
    for _ in range(steps):
        action = rng.randrange(env.actions)
        after = env.step(action, rng).observation
        knowledge.learn(Transition(observation, action, after, False))
        observation = after
    return knowledge


# Baustein „wird v“


def test_becomes_is_found_when_every_change_ends_at_the_same_value() -> None:
    examples = [Example((before, 0), (-1, 0)) for before in (1, 0, -1, 1, 0)]
    found = synthesize(examples, 0, {})
    assert found.program == Becomes(-1)
    assert predict(Becomes(-1), (1, 0), 0) == -1
    assert fits(Becomes(-1), (0, 0), (-1, 0), 0)


def test_becomes_is_not_proposed_for_a_single_step() -> None:
    examples = [Example((0, 0), (1, 0)), Example((0, 1), (1, 1))]
    assert synthesize(examples, 0, {}).program != Becomes(1)


def test_copy_is_found_despite_noise() -> None:
    """Ein Feld übernimmt meist den Wert seines Nachbarn, ab und zu stört ein Tier."""
    rng = random.Random(1)
    examples = []
    for index in range(40):
        neighbour = rng.choice((2, 6, 14) if index % 5 == 0 else (2, 6))
        after = 14 if index % 20 == 0 else neighbour  # Ein Tier läuft ins Bild.
        examples.append(Example((rng.choice((2, 6)), neighbour), (after, neighbour)))
    assert synthesize(examples, 0, {}).program == Copy(1)


# Ursachen


def test_cover_finds_the_condition_of_an_effect() -> None:
    positives = [(6, 0, k) for k in range(3)]
    negatives = [(value, 0, k) for value in (2, 3, 5) for k in range(3)]
    ((literals, hits, uses),) = cover(positives, negatives)
    assert literals == (Literal(0, 6),)
    assert (hits, uses) == (3, 3)


def test_cover_finds_two_causes_and_at_least() -> None:
    positives = [(6, 1, 0), (6, 2, 0), (0, 0, 7), (1, 0, 7)]
    negatives = [(6, 0, 0), (2, 0, 0), (0, 0, 3), (1, 0, 3)]
    found = {literals for literals, _, _ in cover(positives, negatives)}
    assert (Literal(1, 1, Kind.AT_LEAST),) in found
    assert (Literal(2, 7),) in found


def test_cause_book_learns_where_scooping_works() -> None:
    knowledge = _experience(Spring(), 1000)
    (cause,) = knowledge.causes.causes(Event(2, Change.RISES))
    assert cause.action == 2
    assert cause.literals in ((Literal(1, 1),), (Literal(0, 3),), (Literal(0, 3, Kind.AT_LEAST),))
    assert cause.ready((3, 1, 0))
    assert not cause.ready((1, 0, 0))


def test_literal_with_unknown_value_never_holds() -> None:
    assert not Literal(0, 3).holds((None, 3))
    assert Literal(1, 2, Kind.AT_LEAST).holds((None, 3))


# Teilziele


def test_imagination_moves_and_keeps_the_unknown_unknown() -> None:
    knowledge = _experience(Spring(), 1000)
    world = model(knowledge, 4)
    assert imagine(world, (1, 0, 0), 1)[0] == 2
    assert search(world, (1, 0, 0), [Target((Literal(0, 3),))]) == 1


def test_achieve_walks_to_the_spring_then_scoops() -> None:
    env, rng = Spring(), random.Random(3)
    knowledge = _experience(env, 1000)
    world = model(knowledge, 4)
    goal = Literal(2, 1, Kind.AT_LEAST)
    observation = env.reset(rng)
    for _ in range(12):
        if goal.holds(observation):
            break
        step = achieve(knowledge, world, observation, goal)
        assert step is not None
        observation = env.step(step, rng).observation
    assert goal.holds(observation)


# Eigene Ziele


def _live(
    agent: GeneralAgent | RandomAgent, env: Spring, steps: int, seed: int = 0
) -> list[Observation]:
    rng = random.Random(seed)
    observation = env.reset(rng)
    agent.begin(observation)
    seen = [observation]
    for _ in range(steps):
        action = agent.act(observation, rng)
        after = env.step(action, rng).observation
        agent.learn(Transition(observation, action, after, False))
        observation = after
        seen.append(observation)
    return seen


def test_own_goals_raise_a_quantity_without_any_goal_from_the_world() -> None:
    """Niemand sagt dem Agenten, dass der Vorrat zählt; er will ihn trotzdem höher bringen."""
    seen = _live(GeneralAgent(4, own_goals=True), Spring(length=8), 600)
    blind = _live(RandomAgent(4), Spring(length=8), 600)
    assert seen[-1][2] > 2 * max(blind[-1][2], 1)


def test_a_quantity_that_sinks_by_itself_becomes_a_need() -> None:
    agent = GeneralAgent(4, own_goals=True)
    seen = _live(agent, Spring(decay=8), 800)
    drives = agent.drives
    assert drives is not None
    own = drives.owned(agent.knowledge, agent.form())
    assert drives.needs(agent.knowledge, own) == [2]
    assert min(observation[2] for observation in seen[600:]) >= 1


def test_without_own_goals_the_agent_is_unchanged() -> None:
    assert GeneralAgent(4).drives is None


# Trennung: Der Agent kennt keine Welt


def test_general_never_imports_adapters_or_games() -> None:
    for path in GENERAL.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert not name.startswith("hekmatki.adapters"), path.name
                assert name.split(".")[0] not in {"crafter", "minerl", "minedojo"}, path.name
