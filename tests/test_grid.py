import random
from pathlib import Path

import pytest

from hekmatki.experiments.grid_mechanics import LEARNERS as MECHANICS_LEARNERS
from hekmatki.experiments.grid_replay import (
    DATA_MARKER,
    TEMPLATE,
    puzzle_replay,
    replay,
    write_page,
)
from hekmatki.experiments.grid_transfer import LEARNERS, run_grid_transfer
from hekmatki.grid.agent import ObjectAgent, Reason
from hekmatki.grid.baseline import StateAgent
from hekmatki.grid.effects import Effect, Kind, observed_effect
from hekmatki.grid.knowledge import Knowledge
from hekmatki.grid.mazes import random_maze, shortest_win
from hekmatki.grid.perception import Shape, changed_cells, movement, shapes
from hekmatki.grid.planner import find_path, is_unknown, is_win
from hekmatki.grid.play import play_grid
from hekmatki.grid.roles import (
    GUESSED,
    LOCKED,
    RoleAdvisor,
    RoleSchema,
    possible_roles,
    revised,
    role_of,
    schema_from_knowledge,
)
from hekmatki.grid.world import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    GridGame,
    GridState,
    Maze,
    Tile,
    make_grid_game,
)

BORDER = frozenset((r, c) for r in range(5) for c in range(5) if r in (0, 4) or c in (0, 4))
# #####
# #S.K#   S = Start, K = Schlüssel
# #.#.#
# #T.D#   T = Falle, D = Tür
# #####
SMALL = Maze(
    5, 5, BORDER | {(2, 2)}, start=(1, 1), door=(3, 3), key=(1, 3), traps=frozenset({(3, 1)})
)
COLORS = {
    Tile.FLOOR: "grau",
    Tile.WALL: "schwarz",
    Tile.KEY: "gelb",
    Tile.DOOR: "braun",
    Tile.OPEN_DOOR: "grün",
    Tile.TRAP: "rot",
    Tile.PLAYER: "blau",
}
CONTROLS = {"hoch": UP, "runter": DOWN, "links": LEFT, "rechts": RIGHT}


def _game(maze: Maze = SMALL) -> GridGame:
    return GridGame("Test", maze, COLORS, CONTROLS)


def _press(game: GridGame, buttons: list[str]) -> GridState:
    state = game.start
    for button in buttons:
        state = game.step(state, button).state
    return state


def test_render_shows_player_key_and_closed_door() -> None:
    grid = _game().render(_game().start)
    assert grid[1][1:4] == ("blau", "grau", "gelb")
    assert grid[3][1:4] == ("rot", "grau", "braun")
    assert grid[0] == ("schwarz",) * 5


def test_key_opens_the_door_and_the_open_door_wins() -> None:
    game = _game()
    with_key = _press(game, ["rechts", "rechts"])
    assert with_key.has_key
    assert game.render(with_key)[3][3] == "grün"
    assert game.step(with_key, "runter").state.position == (2, 3)
    last = game.step(_press(game, ["rechts", "rechts", "runter"]), "runter")
    assert last.won
    assert last.state == game.start


def test_walls_and_the_closed_door_block_and_traps_send_back() -> None:
    game = _game()
    assert game.step(game.start, "hoch").state == game.start
    beside_door = _press(game, ["runter", "runter"])
    assert beside_door == game.start
    trapped = game.step(_press(game, ["runter"]), "runter")
    assert trapped.trapped
    below_key = GridState((2, 3), has_key=False)
    assert game.step(below_key, "runter").state == below_key


def test_invalid_mazes_and_games_are_rejected() -> None:
    with pytest.raises(ValueError, match="Rand"):
        Maze(5, 5, frozenset({(2, 2)}), start=(1, 1), door=(3, 3), key=None)
    with pytest.raises(ValueError, match="verschiedene Felder"):
        Maze(5, 5, BORDER, start=(1, 1), door=(1, 1), key=None)
    with pytest.raises(ValueError, match="freien Feldern"):
        Maze(5, 5, BORDER | {(2, 2)}, start=(2, 2), door=(1, 1), key=None)
    with pytest.raises(ValueError, match="eigene Farbe"):
        GridGame("x", SMALL, {**COLORS, Tile.KEY: "grau"}, CONTROLS)
    with pytest.raises(ValueError, match="Richtung"):
        GridGame("x", SMALL, COLORS, {**CONTROLS, "hoch": DOWN})
    with pytest.raises(ValueError, match="Unbekannte Taste"):
        _game().step(_game().start, "springen")


def test_shortest_win_counts_key_and_door() -> None:
    assert shortest_win(SMALL) == 4
    no_key = Maze(5, 5, BORDER | {(2, 2)}, start=(1, 1), door=(3, 3), key=None)
    assert shortest_win(no_key) == 4


def test_random_mazes_are_solvable_and_keep_traps_away_from_the_start() -> None:
    rng = random.Random(0)
    for size in (5, 9, 15):
        maze = random_maze(size, rng, traps=2)
        assert shortest_win(maze) is not None
        assert all(abs(t[0] - maze.start[0]) + abs(t[1] - maze.start[1]) >= 3 for t in maze.traps)
    with pytest.raises(ValueError, match="ungerade"):
        random_maze(8, rng)
    game = make_grid_game("Zufall", random_maze(7, rng), rng)
    assert len(game.buttons) == 4


def test_perception_finds_the_moving_color_and_shapes() -> None:
    game = _game()
    before = game.render(game.start)
    after = game.render(_press(game, ["rechts"]))
    moved = movement(before, after)
    assert moved is not None
    assert (moved.color, moved.origin, moved.destination) == ("blau", (1, 1), (1, 2))
    assert changed_cells(before, after) == [(1, 1), (1, 2)]
    assert shapes(before)["schwarz"] == Shape(single=False, border=True)
    assert shapes(before)["gelb"] == Shape(single=True, border=False)
    with pytest.raises(ValueError, match="verschieden groß"):
        changed_cells(before, before[:3])


def test_effects_are_read_from_two_grids() -> None:
    game = _game()
    start = game.render(game.start)
    beside_key = game.render(_press(game, ["rechts"]))
    on_key = game.render(_press(game, ["rechts", "rechts"]))
    trapped_from = game.render(_press(game, ["runter"]))
    assert observed_effect(start, start, False, (1, 1), (0, 1)) == Effect(Kind.BLOCK)
    assert observed_effect(start, beside_key, False, (1, 1), (1, 2)) == Effect(Kind.PASS)
    trigger = observed_effect(beside_key, on_key, False, (1, 2), (1, 3))
    assert trigger == Effect(Kind.TRIGGER, frozenset({("braun", "grün")}))
    assert observed_effect(trapped_from, start, False, (2, 1), (3, 1)) == Effect(Kind.RESET)
    assert observed_effect(on_key, start, True, (2, 3), (3, 3)) == Effect(Kind.WIN)
    with pytest.raises(ValueError, match="Nur Auslöser"):
        Effect(Kind.PASS, frozenset({("a", "b")}))


def test_planner_uses_triggers_and_finds_unknown_colors() -> None:
    game = _game()
    grid = game.render(game.start)
    effects = {
        "grau": Effect(Kind.PASS),
        "schwarz": Effect(Kind.BLOCK),
        "braun": Effect(Kind.BLOCK),
        "rot": Effect(Kind.RESET),
        "gelb": Effect(Kind.TRIGGER, frozenset({("braun", "grün")})),
        "grün": Effect(Kind.WIN),
    }
    path = find_path(grid, (1, 1), CONTROLS, effects.get, is_win)
    assert path == ["rechts", "rechts", "runter", "runter"]
    partial = {color: effects[color] for color in ("grau", "schwarz")}
    assert find_path(grid, (1, 1), CONTROLS, partial.get, is_unknown) == ["rechts", "rechts"]


def test_knowledge_learns_player_buttons_and_effects() -> None:
    game = _game()
    knowledge = Knowledge()
    start = game.render(game.start)
    knowledge.observe(start, "hoch", start, won=False)
    assert knowledge.player is None
    beside_key = game.render(_press(game, ["rechts"]))
    knowledge.observe(start, "rechts", beside_key, won=False)
    assert knowledge.player == "blau"
    assert knowledge.controls == {"rechts": RIGHT}
    assert knowledge.effects == {"grau": Effect(Kind.PASS)}
    with pytest.raises(ValueError, match="wirkte erst"):
        knowledge.observe(start, "rechts", start, won=False)


def test_object_agent_learns_the_game_and_wins() -> None:
    game = _game()
    agent = ObjectAgent(game.buttons)
    result = play_grid(game, agent, 60, random.Random(0), record=True)
    assert result.first_win is not None
    assert result.wins >= 5
    assert agent.knowledge.controls == CONTROLS
    assert agent.beliefs()["blau"] == "ich"
    assert result.frames[0].reason == Reason.TRY
    assert len(result.frames) == 61
    with pytest.raises(ValueError, match="Unbekannte Taste"):
        agent.learn(game.render(game.start), "springen", game.render(game.start), won=False)


def test_image_agent_learns_slowly_and_knows_no_colors() -> None:
    rng = random.Random(1)
    game = make_grid_game("Groß", random_maze(11, rng, traps=2), rng)
    images = StateAgent(game.buttons, game.render(game.start))
    objects = ObjectAgent(game.buttons)
    image_play = play_grid(game, images, 100, random.Random(2))
    object_play = play_grid(game, objects, 100, random.Random(2))
    assert object_play.wins > image_play.wins
    assert images.beliefs() == {}
    assert images.known_states > 0


RECOLORED = {
    Tile.FLOOR: "türkis",
    Tile.WALL: "orange",
    Tile.KEY: "pink",
    Tile.DOOR: "grau",
    Tile.OPEN_DOOR: "gelb",
    Tile.TRAP: "braun",
    Tile.PLAYER: "rot",
}
SHUFFLED = {"taste 1": LEFT, "taste 2": UP, "taste 3": RIGHT, "taste 4": DOWN}
"""Dieselbe Mechanik mit anderen Tastennamen und anderer Belegung."""


TOUR = [
    "rechts",
    "links",
    "runter",
    "hoch",
    "hoch",
    "runter",
    "runter",  # Wand, Falle
    "rechts",
    "rechts",
    "runter",
    "runter",  # Schlüssel, Tür
]


def _learned_knowledge() -> Knowledge:
    """Was ein Agent auf einem festen Rundgang durch das kleine Labyrinth lernt."""
    game = GridGame("Training", SMALL, COLORS, CONTROLS)
    knowledge = Knowledge()
    state = game.start
    for button in TOUR:
        step = game.step(state, button)
        knowledge.observe(game.render(state), button, game.render(step.state), step.won)
        state = step.state
    return knowledge


def test_roles_are_named_after_effects() -> None:
    knowledge = _learned_knowledge()
    assert role_of("blau", knowledge) == "ich"
    assert role_of("schwarz", knowledge) == "blockiert"
    assert role_of("braun", knowledge) == LOCKED
    assert role_of("gelb", knowledge) == "auslöser"
    assert role_of("grün", knowledge) == "ziel"
    assert role_of("rot", knowledge) == "zurück"
    assert possible_roles("braun", knowledge) == {LOCKED}


def test_blocking_color_is_ambiguous_until_a_trigger_is_seen() -> None:
    knowledge = Knowledge(player="blau", effects={"schwarz": Effect(Kind.BLOCK)})
    assert possible_roles("schwarz", knowledge) == {"blockiert", LOCKED}
    assert "ich" not in possible_roles("gelb", knowledge)


def test_schema_remembers_roles_shapes_and_what_triggers_open() -> None:
    schema = schema_from_knowledge(_learned_knowledge())
    assert schema.opens == {LOCKED: "ziel"}
    assert schema.shapes["blockiert"] == {Shape(single=False, border=True)}
    assert schema.shapes["auslöser"] == {Shape(single=True, border=False)}
    with pytest.raises(ValueError, match="Unbekannte Rollen"):
        RoleSchema({"fliegt": frozenset()}, {})


def test_revision_keeps_every_role_and_shape() -> None:
    first = RoleSchema({"frei": frozenset({Shape(False, False)})}, {})
    second = RoleSchema({"frei": frozenset({Shape(True, False)}), "ziel": frozenset()}, {})
    merged = revised(first, second)
    assert merged.shapes["frei"] == {Shape(False, False), Shape(True, False)}
    assert set(merged.shapes) == {"frei", "ziel"}


def test_advisor_guesses_roles_of_new_colors() -> None:
    schema = schema_from_knowledge(_learned_knowledge())
    game = GridGame("Neu", SMALL, RECOLORED, SHUFFLED)
    advisor = RoleAdvisor(schema, game.render(game.start))
    assert advisor.fits()
    advisor.pick(random.Random(0))
    knowledge = Knowledge()
    assert advisor.effect("orange", knowledge) == Effect(Kind.BLOCK)
    assert advisor.effect(GUESSED + "ziel", knowledge) == Effect(Kind.WIN)
    guesses = advisor.guesses(knowledge)
    assert guesses["orange"] == "blockiert"


def test_schema_with_traps_saves_steps_into_traps() -> None:
    single, many, border = Shape(True, False), Shape(False, False), Shape(False, True)
    schema = RoleSchema(
        {
            "ich": frozenset({single}),
            "frei": frozenset({many}),
            "blockiert": frozenset({border}),
            "auslöser": frozenset({single}),
            LOCKED: frozenset({single}),
            "ziel": frozenset({single}),
            "zurück": frozenset({many}),
        },
        {LOCKED: "ziel"},
    )
    plain_traps = informed_traps = 0
    for seed in range(10):
        rng = random.Random(seed)
        game = make_grid_game("Neu", random_maze(9, rng, traps=3), rng)
        advisor = RoleAdvisor(schema, game.render(game.start))
        informed = play_grid(game, ObjectAgent(game.buttons, advisor), 80, random.Random(seed))
        plain = play_grid(game, ObjectAgent(game.buttons), 80, random.Random(seed))
        assert informed.first_win is not None
        assert advisor.fits()
        plain_traps += plain.traps
        informed_traps += informed.traps
    assert informed_traps < plain_traps


def test_grid_transfer_experiment() -> None:
    rows = {row.level: row for row in run_grid_transfer(seeds=2, steps=120)}
    assert set(rows) >= {"Level 1", "groß", "ohne Schlüssel", "viele Fallen"}
    first = rows["Level 1"].first_win
    assert first["Objekte"] == first["Objekte + Schema"]
    big = rows["groß"].first_win
    assert big["Objekte"] < big["Bilder"]
    assert set(big) == set(LEARNERS)


def test_replay_and_page(tmp_path: Path) -> None:
    data = replay(seed=0, level="Level 1", steps=30)
    assert [agent["name"] for agent in data["agents"]] == list(LEARNERS)
    assert len(data["agents"][0]["frames"]) == 31
    with pytest.raises(ValueError, match="Unbekanntes Level"):
        replay(level="Mond")
    puzzle = puzzle_replay(seed=0, level="Kiste", steps=40)
    assert [agent["name"] for agent in puzzle["agents"]] == list(MECHANICS_LEARNERS)
    assert {"Kiste", "Druckplatte", "Tor"} <= {tile.capitalize() for tile in puzzle["truth"]}
    with pytest.raises(ValueError, match="Unbekanntes Level"):
        puzzle_replay(level="Mond")
    page = tmp_path / "seite.html"
    write_page(page, seeds=1)
    text = page.read_text(encoding="utf-8")
    assert DATA_MARKER not in text
    for scenario in ("fremd", "farben", "kisten", "tausch", "labyrinth"):
        assert f'"id":"{scenario}"' in text
    assert DATA_MARKER in TEMPLATE.read_text(encoding="utf-8")
