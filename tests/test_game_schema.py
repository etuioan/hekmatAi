import pytest

from hekmatki.game_schema import (
    GameSchema,
    interpretations,
    merged_schema,
    path_to,
    schema_from_model,
    shortest_paths,
    updated,
)
from hekmatki.puzzle import WIN

LINE = {("a", "go"): "b", ("b", "go"): WIN, ("a", "stay"): "a", ("b", "stay"): "b"}


def test_path_to_finds_the_shortest_way() -> None:
    assert path_to(LINE, "a", lambda s: s == WIN) == ["go", "go"]
    assert path_to(LINE, "b", lambda s: s == "b") == []
    assert path_to(LINE, "a", lambda s: s == "nirgends") is None


def test_schema_uses_neutral_names() -> None:
    schema = schema_from_model("Linie", LINE, "a", ["go", "stay"])
    assert schema.start == "zustand_1"
    assert schema.buttons == ("aktion_1", "aktion_2")
    assert schema.plan("zustand_1") == ["aktion_1", "aktion_1"]


def test_schema_rejects_unknown_buttons() -> None:
    with pytest.raises(ValueError, match="unbekannten Tasten"):
        GameSchema("x", "a", ("go",), {("a", "fly"): "b"})


def test_one_interpretation_per_button_assignment() -> None:
    schema = schema_from_model("Linie", LINE, "a", ["go", "stay"])
    assert len(interpretations(schema, ["p", "q"], "x")) == 2
    with pytest.raises(ValueError, match="Tasten"):
        interpretations(schema, ["p"], "x")


def test_observations_bind_symbols_or_rule_out_interpretations() -> None:
    schema = schema_from_model("Linie", LINE, "a", ["go", "stay"])
    p_goes, p_stays = interpretations(schema, ["p", "q"], "x")
    moved = updated(p_goes, schema, "x", "p", "y")
    assert moved is not None
    assert moved.states["y"] == "zustand_2"
    assert updated(p_stays, schema, "x", "p", "y") is None


def test_merging_adds_what_the_new_game_taught() -> None:
    partial = GameSchema("Linie", "a", ("go", "stay"), {("a", "go"): "b"})
    first = interpretations(partial, ["p", "q"], "x")[0]
    bound = updated(first, partial, "x", "p", "y")
    assert bound is not None
    merged = merged_schema(partial, bound, {("x", "p"): "y", ("y", "p"): "x", ("x", "q"): "x"})
    assert merged.transitions[("b", "go")] == "a"
    assert merged.transitions[("a", "stay")] == "a"


def test_shortest_paths_list_nearer_states_first() -> None:
    paths = shortest_paths(LINE, "a")
    assert list(paths) == ["a", "b", WIN]
    assert paths[WIN] == ["go", "go"]
