import random

import pytest
from grid_puzzle import (
    BESIDE_PLATE,
    BORDER,
    COLORS,
    CONTROLS,
    FULL_TOUR,
    PLATE_TOUR,
    PUZZLE,
    SOLUTION,
    maze_of,
    puzzle_game,
)

from hekmatki.experiments.grid_mechanics import (
    LEARNERS,
    LEVELS,
    run_classic_check,
    run_mechanics,
)
from hekmatki.grid.agent import ObjectAgent
from hekmatki.grid.induction import Attempt, Induction, Observation, Outcome, rule_of
from hekmatki.grid.mazes import puzzle_maze, shortest_win
from hekmatki.grid.model import Event, Rule, WorldModel
from hekmatki.grid.model_agent import Intent, ModelAgent
from hekmatki.grid.play import play_grid
from hekmatki.grid.search import Goal, search
from hekmatki.grid.simulation import Simulator, read_layout, read_scene
from hekmatki.grid.world import (
    CLASSIC_TILES,
    GridGame,
    GridState,
    Maze,
    Tile,
    make_grid_game,
)


def _tour(buttons: list[str], game: GridGame | None = None) -> list[Observation]:
    """Spielt die Tasten und liefert jede Beobachtung."""
    game = game or puzzle_game()
    state, seen = game.start, []
    for button in buttons:
        step = game.step(state, button)
        seen.append(Observation(game.render(state), button, game.render(step.state), step.won))
        state = step.state
    return seen


def _learned(buttons: list[str]) -> Induction:
    induction = Induction()
    for observation in _tour(buttons):
        induction.add(observation)
    return induction


# Die Spielwelt


def test_boxes_are_pushed_only_where_there_is_room() -> None:
    game = puzzle_game()
    state = game.start
    for button in ["rechts", "rechts"]:
        state = game.step(state, button).state
    assert state.position == (1, 3)
    assert state.boxes == {(1, 4)}
    assert game.render(state)[1][4] == "braun"
    pressed = game.step(state, "rechts").state
    assert pressed.boxes == {(1, 5)}
    assert game.step(pressed, "rechts").state == pressed


def test_the_gate_is_open_while_something_is_on_the_plate() -> None:
    game = puzzle_game()
    assert game.render(game.start)[4][3] == "pink"
    on_plate = GridState((1, 5), has_key=False, boxes=frozenset({(1, 3)}))
    assert game.render(on_plate)[4][3] == "türkis"
    box_on_plate = GridState((3, 3), has_key=False, boxes=frozenset({(1, 5)}))
    assert game.step(box_on_plate, "runter").state.position == (4, 3)
    closed = GridState((3, 3), has_key=False, boxes=frozenset({(1, 3)}))
    assert game.step(closed, "runter").state == closed


def test_traps_put_player_and_boxes_back() -> None:
    game = puzzle_game()
    moved = GridState((3, 5), has_key=False, boxes=frozenset({(1, 4)}))
    step = game.step(moved, "runter")
    assert step.trapped
    assert step.state == game.start


def test_shortest_win_pushes_the_box_and_needs_it() -> None:
    maze = maze_of(PUZZLE)
    assert shortest_win(maze) == len(SOLUTION)
    state = puzzle_game().start
    for button in SOLUTION[:-1]:
        state = puzzle_game().step(state, button).state
    assert puzzle_game().step(state, SOLUTION[-1]).won
    without_box = maze_of(tuple(row.replace("B", ".") for row in PUZZLE))
    assert shortest_win(without_box) is None


def test_mazes_with_new_tiles_are_validated() -> None:
    with pytest.raises(ValueError, match="nur zusammen"):
        Maze(5, 5, BORDER, start=(1, 1), door=(3, 3), key=None, plate=(1, 2))
    with pytest.raises(ValueError, match="eigene Farbe"):
        GridGame("x", maze_of(PUZZLE), {**COLORS, Tile.BOX: "grau"}, CONTROLS)
    assert maze_of(PUZZLE).tiles == tuple(COLORS)


def test_puzzle_mazes_are_solvable_only_with_a_box() -> None:
    rng = random.Random(1)
    for size, boxes in [(9, 1), (11, 2)]:
        maze = puzzle_maze(size, rng, traps=2, boxes=boxes)
        assert maze.plate is not None
        assert maze.gate is not None
        assert len(maze.boxes) == boxes
        assert shortest_win(maze) is not None
        empty = Maze(maze.height, maze.width, maze.walls, maze.start, maze.door, None,
                     maze.traps, frozenset(), maze.plate, maze.gate)  # fmt: skip
        assert shortest_win(empty) is None
    game = make_grid_game("Rätsel", puzzle_maze(9, rng), rng)
    assert set(game.colors) == set(game.maze.tiles)
    with pytest.raises(ValueError, match="Kiste"):
        puzzle_maze(9, rng, boxes=0)


def test_classic_mazes_keep_their_seven_colors() -> None:
    maze = Maze(5, 5, BORDER, start=(1, 1), door=(3, 3), key=None)
    game = make_grid_game("klassisch", maze, random.Random(0))
    assert tuple(game.colors) == CLASSIC_TILES


# Das Weltmodell


def test_rules_follow_from_all_attempts() -> None:
    blocked = Attempt("braun", Outcome.BLOCKED, "schwarz")
    pushed = Attempt("braun", Outcome.PUSHED, "grau")
    assert rule_of([blocked]) is Rule.BLOCK
    assert rule_of([blocked, pushed]) is Rule.PUSH
    assert rule_of([Attempt("grau", Outcome.ENTERED), blocked]) is None
    with pytest.raises(ValueError, match="Ohne Versuche"):
        rule_of([])


def test_induction_learns_rules_pushing_and_remote_effects() -> None:
    model = _learned(FULL_TOUR).model
    assert model.player == "blau"
    assert model.controls == CONTROLS
    assert model.rules["grau"] is Rule.PASS
    assert model.rules["schwarz"] is Rule.BLOCK
    assert model.rules["braun"] is Rule.PUSH
    assert model.rules["türkis"] is Rule.PASS
    assert model.rules["grün"] is Rule.WIN
    assert model.box_enters == {"grau": True, "gelb": True}
    assert model.consequences[Event("gelb", covered=True)] == {("pink", "türkis")}
    assert model.consequences[Event("grau", covered=True)] == frozenset()


def test_induction_relearns_instead_of_crashing() -> None:
    induction = Induction()
    walk = _tour(["rechts", "links"])
    for observation in walk:
        induction.add(observation)
    first = induction.model
    # Dieselbe Farbe blockiert plötzlich: Das neueste Wissen gilt, der Wechsel wird notiert.
    stuck = walk[0].before
    induction.add(Observation(stuck, "rechts", stuck, won=False))
    assert (first.rules["grau"], induction.model.rules["grau"]) == (Rule.PASS, Rule.BLOCK)
    assert induction.revisions == ["grau: erst „frei“, jetzt „blockiert“"]


def test_leaving_the_plate_closes_the_gate_again() -> None:
    model = _learned(PLATE_TOUR).model
    assert model.consequences[Event("gelb", covered=False)] == {("türkis", "pink")}
    assert model.leaves["gelb"] == "gelb"
    assert model.describe("gelb") == "frei; verdeckt: pink→türkis; aufgedeckt: türkis→pink"


def test_simultaneous_events_stay_unsure_until_one_step_settles_it() -> None:
    game = puzzle_game(maze_of(BESIDE_PLATE))
    walk = _tour(["links", "rechts", "rechts", "links", "links"], game)
    induction = Induction()
    for observation in walk[:2]:
        induction.add(observation)
    opens, closes = {("pink", "türkis")}, {("türkis", "pink")}
    # Platte betreten heißt auch: das Startfeld (grau) wird aufgedeckt. Wer öffnete das Tor?
    assert induction.model.unsure == {
        Event("gelb", covered=True): opens,
        Event("grau", covered=False): opens,
        Event("gelb", covered=False): closes,
        Event("grau", covered=True): closes,
    }
    assert induction.model.describe("gelb") == (
        "frei; verdeckt: pink→türkis?; aufgedeckt: türkis→pink?"
    )
    # Auf grau gehen, während das Tor zu ist (pink zu sehen): grau aufdecken öffnet nichts.
    induction.add(walk[2])
    assert induction.model.consequences[Event("grau", covered=False)] == frozenset()
    # Wieder auf die Platte: Jetzt erklärt nur noch gelb das Öffnen.
    for observation in walk[3:]:
        induction.add(observation)
    assert induction.model.consequences[Event("gelb", covered=True)] == opens
    assert Event("gelb", covered=True) not in induction.model.unsure


def test_simulator_asks_about_an_unsure_effect_when_a_step_would_settle_it() -> None:
    game = puzzle_game(maze_of(BESIDE_PLATE))
    induction = Induction()
    for observation in _tour(["links", "rechts"], game):
        induction.add(observation)
    model = induction.model
    simulator = Simulator(model, read_layout(game.render(game.start), model))
    # Etwas liegt auf der Platte, das Tor ist offen (türkis). Schließt Boden betreten es?
    opened = game.render(GridState((1, 2), has_key=False, boxes=frozenset({(1, 1)})))
    scene = read_scene(opened, model, lambda cell: None)
    question = simulator.predict(scene, "rechts").question
    assert question == "Wechselt türkis zu pink, wenn grau verdeckt wird?"


def test_models_combine_with_prior_knowledge() -> None:
    plate = Event("gelb", covered=True)
    prior = WorldModel(
        player="blau",
        rules={"grau": Rule.PASS, "rot": Rule.WIN},
        consequences={plate: frozenset({("pink", "türkis")})},
        unsure={plate: frozenset({("pink", "türkis")})},
    )
    own = WorldModel(rules={"rot": Rule.RESET}, consequences={plate: frozenset()})
    combined = own.over(prior)
    assert combined.player == "blau"
    assert combined.rules == {"grau": Rule.PASS, "rot": Rule.RESET}
    assert combined.without(["grau"]).rules == {"rot": Rule.RESET}
    assert combined.consequences == {plate: frozenset()}
    assert combined.unsure == {}


# Vorausdenken


def _full_model() -> WorldModel:
    return _learned(FULL_TOUR).model


def test_simulator_predicts_pushing_and_the_opening_gate() -> None:
    game, model = puzzle_game(), _full_model()
    grid = game.render(GridState((1, 4), has_key=False, boxes=frozenset({(1, 3)})))
    simulator = Simulator(model, read_layout(game.render(game.start), model))
    scene = read_scene(grid, model, lambda cell: None)
    assert scene.objects == ((1 * 7 + 3, "9"),)
    onto_plate = simulator.predict(scene, "rechts")
    assert onto_plate.scene is not None
    assert onto_plate.scene.background[4 * 7 + 3] == "8"
    assert simulator.predict(scene, "hoch").scene is scene
    assert simulator.predict(scene, "links").disturbs
    assert not simulator.predict(scene, "links").cornered


def test_simulator_notices_a_box_pushed_into_a_corner() -> None:
    game, model = puzzle_game(), _full_model()
    simulator = Simulator(model, read_layout(game.render(game.start), model))
    grid = game.render(GridState((1, 3), has_key=False, boxes=frozenset({(1, 4)})))
    into_corner = simulator.predict(read_scene(grid, model, lambda cell: None), "rechts")
    assert into_corner.cornered
    assert into_corner.disturbs


def test_simulator_names_what_it_does_not_know() -> None:
    game = puzzle_game()
    model = WorldModel(player="blau", controls=CONTROLS, rules={"schwarz": Rule.BLOCK})
    layout = read_layout(game.render(game.start), model)
    plain, doubtful = Simulator(model, layout), Simulator(model, layout, doubt=True)
    below = game.render(GridState((3, 2), has_key=False, boxes=frozenset({(1, 3)})))
    scene = read_scene(below, model, lambda cell: None)
    assert plain.predict(scene, "rechts").question == "Was passiert auf grau?"
    assert plain.predict(scene, "hoch").scene is scene
    doubt = doubtful.predict(scene, "hoch").question
    assert doubt == "Blockiert schwarz auch mit grau dahinter?"


def test_search_finds_the_shortest_win_through_the_gate() -> None:
    game, model = puzzle_game(), _full_model()
    first = game.render(game.start)
    simulator = Simulator(model, read_layout(first, model))
    result = search(simulator, read_scene(first, model, lambda cell: None), list(CONTROLS))
    assert result.complete
    assert result.plan is not None
    assert result.plan.goal is Goal.WIN
    assert list(result.plan.buttons) == SOLUTION


def test_search_without_knowledge_asks_the_nearest_question() -> None:
    game = puzzle_game()
    model = WorldModel(player="blau", controls=CONTROLS, rules={"grau": Rule.PASS})
    first = game.render(game.start)
    simulator = Simulator(model, read_layout(first, model))
    result = search(simulator, read_scene(first, model, lambda cell: None), list(CONTROLS))
    assert result.plan is not None
    assert result.plan.goal is Goal.LEARN
    assert result.plan.buttons == ("hoch",)
    assert result.plan.question == "Was passiert auf schwarz?"


# Der Modell-Agent


def _play_model(game: GridGame, prior: WorldModel | None = None) -> tuple[ModelAgent, int]:
    agent = ModelAgent(game.buttons, prior)
    play = play_grid(game, agent, 150, random.Random(0))
    assert play.first_win is not None
    assert play.stopped is None
    return agent, play.first_win


def test_model_agent_solves_the_box_puzzle_and_explains_itself() -> None:
    agent, first_win = _play_model(puzzle_game())
    assert first_win <= 6 * len(SOLUTION)
    beliefs = agent.beliefs()
    assert beliefs["braun"] == "schiebbar"
    assert beliefs["gelb"].startswith("frei; verdeckt: pink→türkis")
    assert agent.reason in {str(intent) for intent in Intent} or ":" in agent.reason


def test_prior_knowledge_makes_the_next_level_fast_even_when_it_is_wrong() -> None:
    teacher, _ = _play_model(puzzle_game())
    _, informed = _play_model(puzzle_game(), teacher.world_model())
    assert informed == len(SOLUTION)
    swapped = {**COLORS, Tile.OPEN_DOOR: "rot", Tile.TRAP: "grün"}
    agent = ModelAgent(list(CONTROLS), teacher.world_model())
    play = play_grid(GridGame("Tausch", maze_of(PUZZLE), swapped, CONTROLS), agent, 150,
                     random.Random(0))  # fmt: skip
    assert play.first_win is not None
    assert agent.beliefs()["grün"] == "zurück (Vorwissen: ziel)"


def test_object_agent_of_version_12_stops_at_a_contradiction() -> None:
    play = play_grid(puzzle_game(), ObjectAgent(list(CONTROLS)), 150, random.Random(0), record=True)
    assert play.stopped is not None
    assert play.stopped_at is not None
    assert play.frames[-2].reason.startswith("bricht ab:")
    assert len(play.frames) == play.stopped_at + 1


def test_mechanics_experiment() -> None:
    rows = run_mechanics(seeds=2, steps=120)
    assert [row.level for row in rows] == list(LEVELS)
    for row in rows:
        assert set(row.first_win) == set(LEARNERS)
        assert row.stopped["Weltmodell"] == 0
        assert 0 < row.optimal_first_win <= row.first_win["Weltmodell + Vorwissen"]
    boxes = [row for row in rows if LEVELS[row.level].boxes]
    assert any(row.stopped["Objekte 0.12"] > 0 for row in boxes)
    classic = run_classic_check(seeds=1, steps=100)
    assert len(classic) == 6
    assert all(row.model <= 101 for row in classic)
