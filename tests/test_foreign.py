import random
from dataclasses import replace

import pytest
from grid_puzzle import CONTROLS, FULL_TOUR, PUZZLE, maze_of, puzzle_game

from hekmatki.experiments.cross_world import HANDLINGS, compare_worlds
from hekmatki.experiments.grid_foreign import BASELINE, LEARNERS, run_foreign
from hekmatki.experiments.grid_replay import FOREIGN_SHOWN, foreign_replay
from hekmatki.experiments.schema_learning import run_h11_stress
from hekmatki.grid.induction import Induction, Observation
from hekmatki.grid.model import Event, Rule, WorldModel
from hekmatki.grid.model_agent import ModelAgent
from hekmatki.grid.play import play_grid
from hekmatki.grid.trust import Trust, check, verdict
from hekmatki.grid.world import DOWN, LEFT, RIGHT, Maze, Mechanics

CLOSING = (
    "#######",
    "#S.P..#",
    "#.###.#",
    "#.....#",
    "###G###",
    "#E....#",
    "#######",
)
"""Wie das Rätsel, aber die Kiste lässt sich von der Platte nach rechts schieben."""
PLATE = Event("gelb", covered=True)


def _ice(row: str) -> Maze:
    """Ein Gang auf Eis (S = Start, T = Falle, B = Kiste), der Ausgang liegt darunter."""
    below = "#E" + "#" * (len(row) - 2)
    rows = ("#" * len(row), row, "#." + "#" * (len(row) - 2), below, "#" * len(row))
    return replace(maze_of(rows), mechanics=Mechanics(ice=True))


def _learned_model() -> WorldModel:
    """Das Modell nach der ganzen Runde durch das übliche Rätsel."""
    game = puzzle_game()
    induction, state = Induction(), game.start
    for button in FULL_TOUR:
        step = game.step(state, button)
        induction.add(Observation(game.render(state), button, game.render(step.state), step.won))
        state = step.state
    return induction.model


def _closing_game() -> Maze:
    """Die Kiste steht auf der Platte, und die Platte schließt das Tor."""
    maze = maze_of(CLOSING)
    assert maze.plate is not None
    return replace(maze, boxes=frozenset({maze.plate}), mechanics=Mechanics(plate_closes=True))


# Fremde Mechanik


def test_plate_can_close_the_gate_instead() -> None:
    usual = maze_of(PUZZLE)
    closing = replace(usual, mechanics=Mechanics(plate_closes=True))
    assert usual.plate is not None
    on_plate = replace(usual.initial, boxes=frozenset({usual.plate}))
    assert not usual.gate_open(usual.initial)
    assert usual.gate_open(on_plate)
    assert closing.gate_open(closing.initial)
    assert not closing.gate_open(on_plate)


def test_a_box_may_start_on_the_plate() -> None:
    maze = _closing_game()
    assert maze.initial.boxes == {maze.plate}
    assert not maze.gate_open(maze.initial)
    pushed = maze.advance(maze.advance(maze.initial, RIGHT).state, RIGHT).state
    assert pushed.boxes == {(1, 4)}
    assert not maze.gate_open(pushed)  # Jetzt steht die Figur auf der Platte.
    assert maze.gate_open(maze.advance(pushed, LEFT).state)


def test_on_ice_the_figure_slides_until_something_stops_it() -> None:
    corridor = _ice("#S...#")
    assert corridor.advance(corridor.initial, RIGHT).state.position == (1, 4)
    boxed = _ice("#S..B.#")
    assert boxed.advance(boxed.initial, RIGHT).state.position == (1, 3)
    trap_row = _ice("#S..T#")
    assert trap_row.advance(trap_row.initial, RIGHT).trapped
    assert corridor.advance(corridor.initial, DOWN).won  # Rutscht bis in den Ausgang.


# Vorwissen erst trauen, wenn es sich bewährt hat (H17)


def test_check_counts_confirmations_and_contradictions() -> None:
    prior = WorldModel(
        rules={"grau": Rule.PASS, "schwarz": Rule.BLOCK, "braun": Rule.PUSH},
        consequences={PLATE: frozenset({("pink", "türkis")})},
    )
    assert check(prior, WorldModel(rules={"grau": Rule.PASS})) == (1, 0)
    assert verdict(prior, WorldModel(rules={"grau": Rule.PASS})) is Trust.WAITING
    both = WorldModel(rules={"grau": Rule.PASS, "schwarz": Rule.BLOCK})
    assert verdict(prior, both) is Trust.TRUSTED
    # Eine Kiste vor der Wand blockiert auch: kein Widerspruch.
    assert check(prior, WorldModel(rules={"braun": Rule.BLOCK})) == (0, 0)
    assert verdict(prior, WorldModel(rules={"grau": Rule.BLOCK})) is Trust.REFUTED
    assert check(prior, WorldModel(consequences={PLATE: frozenset({("pink", "türkis")})})) == (1, 0)
    assert check(prior, WorldModel(consequences={PLATE: frozenset()})) == (0, 1)


def test_checked_agent_waits_for_confirmation() -> None:
    prior = WorldModel(
        player="blau", controls=CONTROLS, rules={"grau": Rule.PASS, "schwarz": Rule.BLOCK}
    )
    game = puzzle_game()
    agent = ModelAgent(list(CONTROLS), prior, checked=True)
    assert agent.prior is None
    state = game.start
    for button in ("rechts", "hoch"):
        step = game.step(state, button)
        agent.learn(game.render(state), button, game.render(step.state), step.won)
        state = step.state
    assert agent.trust is Trust.TRUSTED
    assert agent.prior == prior


def test_checked_agent_drops_refuted_knowledge_for_good() -> None:
    wrong = WorldModel(player="blau", controls=CONTROLS, rules={"grau": Rule.BLOCK})
    game = puzzle_game()
    agent = ModelAgent(list(CONTROLS), wrong, checked=True)
    step = game.step(game.start, "rechts")
    agent.learn(game.render(game.start), "rechts", game.render(step.state), step.won)
    assert agent.trust is Trust.REFUTED
    assert agent.prior is None
    assert agent.world_model().rules == {"grau": Rule.PASS}


# Teile einzeln prüfen (H16)


def test_doubting_parts_frees_an_agent_stuck_on_old_knowledge() -> None:
    game = puzzle_game(_closing_game())
    prior = _learned_model()

    def first_win(doubts_parts: bool = False) -> int | None:
        agent = ModelAgent(list(CONTROLS), prior, doubts_parts=doubts_parts)
        return play_grid(game, agent, 200, random.Random(1)).first_win

    stuck, doubting = first_win(), first_win(doubts_parts=True)
    assert stuck is not None
    assert doubting is not None
    assert doubting < stuck / 2


# Die Experimente


def test_foreign_experiment_and_comparison_of_worlds() -> None:
    rows = run_foreign(seeds=1, steps=60)
    assert [row.level for row in rows] == ["gewohnt", "Tor umgekehrt", "Eis"]
    for row in rows:
        assert set(row.first_win) == set(LEARNERS)
        assert row.harm[BASELINE["Modell aus A"]] == 0
        assert row.optimal_first_win > 0
    stress = run_h11_stress(seeds=1, budgets=(10,))
    compared = compare_worlds(stress, rows)
    assert [row.world for row in compared] == ["Alltag"] * len(stress) + ["Spiel"] * len(rows)
    assert all(set(row.harm) == set(HANDLINGS) for row in compared)
    with pytest.raises(ValueError, match="beiden Welten"):
        compare_worlds([], rows)


def test_foreign_replay_shows_the_look_of_game_a() -> None:
    data = foreign_replay(seed=0, steps=30)
    assert data["level"] == "Tor umgekehrt"
    assert [agent["name"] for agent in data["agents"]] == list(FOREIGN_SHOWN)
    assert len(data["agents"][0]["frames"]) == 31
    with pytest.raises(ValueError, match="Unbekanntes Level"):
        foreign_replay(level="Mond")
