import random

import pytest
from grid_puzzle import CONTROLS, FULL_TOUR, PUZZLE, maze_of, puzzle_game

from hekmatki.experiments.grid_roles import LEARNERS, run_roles
from hekmatki.grid.induction import Induction, Observation
from hekmatki.grid.model import Event, Rule, WorldModel
from hekmatki.grid.model_agent import ModelAgent
from hekmatki.grid.play import play_grid
from hekmatki.grid.role_model import RoleBinder, RoleWorld, fits, role_names
from hekmatki.grid.search import Goal, search
from hekmatki.grid.simulation import Simulator, read_layout, read_scene
from hekmatki.grid.world import DOWN, LEFT, RIGHT, UP, GridGame, GridState, Tile

NEW_COLORS = {
    Tile.FLOOR: "pink",
    Tile.WALL: "orange",
    Tile.OPEN_DOOR: "rot",
    Tile.TRAP: "grün",
    Tile.PLAYER: "gelb",
    Tile.BOX: "türkis",
    Tile.PLATE: "braun",
    Tile.GATE: "grau",
    Tile.OPEN_GATE: "blau",
}
"""Dasselbe Rätsel in einem anderen Spiel: Jede Farbe bedeutet etwas anderes."""
NEW_CONTROLS = {"a": LEFT, "b": UP, "c": RIGHT, "d": DOWN}
PLATE = Event("gelb", covered=True)
INTO_CORNER = ["runter", "runter", "rechts", "rechts", "rechts", "rechts", "hoch", "hoch"]
INTO_CORNER += ["links", "links", "links"]
"""Um die Kiste herum und sie dann in die linke obere Ecke schieben: Sie sitzt fest."""


def _learned_model(game: GridGame | None = None) -> WorldModel:
    """Das Modell nach der ganzen Runde durch das Rätsel."""
    game = game or puzzle_game()
    induction, state = Induction(), game.start
    for button in FULL_TOUR:
        step = game.step(state, button)
        induction.add(Observation(game.render(state), button, game.render(step.state), step.won))
        state = step.state
    return induction.model


def _roles() -> RoleWorld:
    game = puzzle_game()
    return RoleWorld.from_level(_learned_model(game), game.render(game.start))


def _new_game(restart: str | None = None) -> GridGame:
    return GridGame("neues Spiel", maze_of(PUZZLE), NEW_COLORS, NEW_CONTROLS, restart)


# Rollen statt Farben


def test_renamed_keeps_only_knowledge_about_renamed_colors() -> None:
    model = WorldModel(
        player="blau",
        controls=CONTROLS,
        rules={"blau": Rule.PASS, "rot": Rule.WIN, "grau": Rule.PASS},
        consequences={PLATE: frozenset({("pink", "türkis")})},
        unsure={PLATE: frozenset({("pink", "türkis")})},
        leaves={"grau": "grau"},
    )
    renamed = model.renamed({"blau": "ich", "rot": "ziel", "gelb": "auslöser", "pink": "zu"})
    assert renamed.player == "ich"
    assert renamed.controls == {}
    assert renamed.rules == {"ich": Rule.PASS, "ziel": Rule.WIN}
    assert renamed.leaves == {}
    assert renamed.consequences == {Event("auslöser", covered=True): frozenset()}
    assert renamed.unsure == {}


def test_each_color_is_named_after_its_role() -> None:
    names = role_names(_learned_model())
    assert names["blau"] == "ich"
    assert names["braun"] == "schiebbar"
    assert names["gelb"] == "auslöser"
    assert names["pink"] == "verschlossen"
    assert names["türkis"] == "geöffnet"
    assert names["schwarz"] == "blockiert"
    assert names["grau"] == "frei"


def test_role_world_keeps_rules_and_looks_without_colors() -> None:
    roles = _roles()
    assert roles.model.player == "ich"
    assert roles.model.rules["schiebbar"] is Rule.PUSH
    assert roles.model.consequences[Event("auslöser", covered=True)] == frozenset(
        {("verschlossen", "geöffnet")}
    )
    assert "geöffnet" not in roles.looks  # Das offene Tor war im ersten Bild nicht zu sehen.
    assert {"ich", "frei", "blockiert", "auslöser"} <= roles.roles
    merged = roles.merged(RoleWorld(WorldModel(rules={"neu": Rule.PASS}), {}))
    assert merged.model.rules["neu"] is Rule.PASS
    assert merged.looks == roles.looks


def test_a_role_fits_only_what_is_known_about_a_color() -> None:
    world = _roles().model
    evidence = WorldModel(
        player="gelb",
        rules={"orange": Rule.BLOCK},
        consequences={Event("braun", covered=True): frozenset({("grau", "blau")})},
    )
    assert fits("gelb", "ich", world, evidence)
    assert not fits("braun", "ich", world, evidence)
    assert fits("braun", "auslöser", world, evidence)
    assert not fits("türkis", "auslöser", world, WorldModel(consequences={
        Event("türkis", covered=True): frozenset()}))  # fmt: skip
    assert not fits("orange", "frei", world, evidence)
    assert fits("orange", "schiebbar", world, evidence)  # Eine Kiste vor der Wand blockiert.


def test_binder_keeps_only_what_all_best_bindings_share() -> None:
    game = _new_game()
    binder = RoleBinder(_roles(), game.render(game.start))
    binder.prior(WorldModel())
    assert binder.role_of("orange") == "blockiert"
    assert binder.role_of("pink") == "frei"
    assert binder.role_of("braun") is None  # Ein einzelnes Feld kann vieles sein.
    evidence = WorldModel(
        player="gelb",
        consequences={Event("braun", covered=True): frozenset({("grau", "blau")})},
    )
    prior = binder.prior(evidence)
    assert binder.role_of("gelb") == "ich"
    assert binder.role_of("braun") == "auslöser"
    assert binder.role_of("grau") == "verschlossen"
    assert prior.rules["blau"] is Rule.PASS  # Das offene Tor hat die beobachtete Farbe.


def test_role_knowledge_carries_over_to_new_colors() -> None:
    plain = play_grid(_new_game(), ModelAgent(list(NEW_CONTROLS)), 200, random.Random(0))
    agent = ModelAgent(list(NEW_CONTROLS), roles=_roles())
    play = play_grid(_new_game(), agent, 200, random.Random(0), record=True)
    assert plain.first_win is not None
    assert play.first_win is not None
    assert play.first_win < plain.first_win
    assert play.frames[0].beliefs["orange"] == "vermutlich blockiert (Rolle „blockiert“)"
    assert agent.knowledge().rules.keys() <= set(NEW_COLORS.values())


# Die Neustart-Taste


def test_restart_button_puts_the_level_back_to_its_start() -> None:
    game = _new_game(restart="neustart")
    assert game.buttons == tuple(sorted(NEW_CONTROLS))
    moved = game.step(game.step(game.start, "c").state, "c").state
    step = game.step(moved, "neustart")
    assert step.restarted
    assert step.state == game.start
    with pytest.raises(ValueError, match="Neustart"):
        GridGame("falsch", maze_of(PUZZLE), NEW_COLORS, NEW_CONTROLS, restart="a")
    with pytest.raises(ValueError, match="Neustart"):
        ModelAgent(list(NEW_CONTROLS), restart="a")


def test_simulator_knows_the_restart_button() -> None:
    game, model = puzzle_game(), _learned_model()
    first = game.render(game.start)
    simulator = Simulator(model, read_layout(first, model), restart="neustart")
    stuck = game.render(GridState((1, 3), has_key=False, boxes=frozenset({(1, 4)})))
    after = simulator.predict(read_scene(stuck, model, lambda cell: None), "neustart")
    assert after.scene == read_scene(first, model, lambda cell: None)


def test_search_restarts_when_the_box_is_stuck() -> None:
    game = puzzle_game()
    model = WorldModel(rules={"rot": Rule.RESET, "pink": Rule.BLOCK}).over(_learned_model())
    first = game.render(game.start)
    simulator = Simulator(model, read_layout(first, model), restart="neustart")
    state = game.start
    for button in INTO_CORNER:
        state = game.step(state, button).state
    assert state.boxes == frozenset({(1, 1)})
    stuck = read_scene(game.render(state), model, lambda cell: None)
    buttons = [*CONTROLS, "neustart"]
    assert search(simulator, stuck, buttons).plan is None
    plan = search(simulator, stuck, buttons, allow_reset=True).plan
    assert plan is not None
    assert plan.goal is Goal.WIN
    assert plan.buttons[0] == "neustart"
    assert plan.restarts


# Das Experiment


def test_roles_experiment() -> None:
    rows = run_roles(seeds=1, steps=80)
    assert len(rows) == 6
    for row in rows:
        assert set(row.first_win) == set(LEARNERS)
        assert 0 < row.optimal_first_win <= row.first_win["gleiches Spiel"]
        assert row.restarts["ohne Vorwissen"] >= 0
