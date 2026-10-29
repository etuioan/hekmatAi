import random

from hekmatki.game import GREEN, TRAFFIC, YELLOW, Action, TrafficLightGame
from hekmatki.markov import MarkovModel
from hekmatki.overlap import find_overlap
from hekmatki.schema import Schema, merge
from hekmatki.situations import Situation, waiting_situations
from hekmatki.structure import mapping_distance


def _trained(situation: Situation, rng: random.Random) -> MarkovModel:
    model = MarkovModel(situation.alphabet)
    model.observe_sequence(situation.sample(400, rng))
    return model


def _waiting_schema() -> tuple[Schema, dict[str, str]]:
    rng = random.Random(0)
    situations = waiting_situations()
    doctor = _trained(situations["arzt"], rng)
    merged = merge(doctor, _trained(situations["ubahn"], rng), "Warten")
    assert merged.schema is not None
    roles = dict(zip(doctor.alphabet, merged.schema.roles, strict=True))
    meaning = {m: roles[s] for m, s in situations["arzt"].symbols.items()}
    return merged.schema, meaning


def _waiting_game_model(steps: int = 300) -> MarkovModel:
    game, rng = TrafficLightGame(), random.Random(1)
    model = MarkovModel(game.symbols)
    state = game.start
    for _ in range(steps):
        following = game.step(state, Action.WAIT, rng)
        model.observe(state, following)
        state = following
    return model


def test_waiting_is_found_inside_the_game() -> None:
    schema, meaning = _waiting_schema()
    overlap = find_overlap(_waiting_game_model(), [schema])
    assert overlap is not None
    assert overlap.binding[TRAFFIC] == meaning["beschäftigen"]
    assert overlap.binding[YELLOW] == meaning["hinweis"]
    assert overlap.binding[GREEN] == meaning["ereignis"]


def test_finding_an_overlap_leaves_the_schema_unchanged() -> None:
    schema, _ = _waiting_schema()
    before = schema.model.matrix()
    find_overlap(_waiting_game_model(), [schema])
    assert schema.model.matrix() == before


def test_unrelated_model_has_no_overlap() -> None:
    schema, _ = _waiting_schema()
    symbols = [f"s{i}" for i in range(6)]
    uniform = MarkovModel(symbols)
    for a in symbols:
        for b in symbols:
            uniform.observe(a, b, weight=10.0)
    assert find_overlap(uniform, [schema]) is None


def test_model_smaller_than_schema_has_no_overlap() -> None:
    schema, _ = _waiting_schema()
    assert find_overlap(MarkovModel(["a", "b"]), [schema]) is None


def test_identical_structure_has_distance_zero() -> None:
    schema, _ = _waiting_schema()
    identity = {role: role for role in schema.roles}
    assert mapping_distance(schema.model, schema.model, identity) == 0.0
