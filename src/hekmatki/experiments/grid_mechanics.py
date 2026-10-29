"""Experiment Weltmodell: Kisten, Druckplatten und Tore, und Vorwissen, das sich irrt.

Ein Spiel besteht aus sechs Leveln mit denselben Farben und Tasten (wie bei ARC-AGI-3).
Die Level führen nach und nach neue Regeln ein: erst Ausgang und Fallen, dann eine Kiste,
eine Druckplatte und ein Tor, das nur offen ist, solange etwas auf der Platte steht. Im
letzten Level („Tausch“) haben Ausgang und Fallen die Farben getauscht: Wer sich auf das
Gelernte verlässt, läuft in die Falle.

Vier Agenten spielen jedes Level:
- „Bilder“: der Entdecker aus Ergebnis 10, für den jedes Raster ein eigener Zustand ist
- „Objekte 0.12“: der Objekt-Agent aus Ergebnis 13; er scheidet aus, wenn eine Beobachtung
  seinem Wissen widerspricht
- „Weltmodell“: der Modell-Agent, in jedem Level ohne Vorwissen
- „Weltmodell + Vorwissen“: derselbe, aber mit seinem Modell aus den vorigen Leveln
"""

import random
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from hekmatki.experiments.grid_transfer import LEVELS as CLASSIC_LEVELS
from hekmatki.experiments.grid_transfer import build_level
from hekmatki.grid.agent import ObjectAgent
from hekmatki.grid.baseline import StateAgent
from hekmatki.grid.mazes import puzzle_maze, random_maze, shortest_win
from hekmatki.grid.model import WorldModel
from hekmatki.grid.model_agent import ModelAgent
from hekmatki.grid.play import GridAgent, GridPlay, play_grid
from hekmatki.grid.world import (
    PUZZLE_TILES,
    Color,
    Direction,
    GridGame,
    Maze,
    Tile,
    random_colors,
    random_controls,
)

Learner = Literal["Bilder", "Objekte 0.12", "Weltmodell", "Weltmodell + Vorwissen"]
LEARNERS: tuple[Learner, ...] = ("Bilder", "Objekte 0.12", "Weltmodell", "Weltmodell + Vorwissen")
STEPS_PER_LEVEL = 300


@dataclass(frozen=True)
class PuzzlePlan:
    """Wie ein Level gebaut wird."""

    size: int
    traps: int
    boxes: int = 0
    """Ohne Kisten gibt es auch keine Druckplatte und kein Tor."""
    swap: tuple[Tile, Tile] | None = None
    """Diese beiden Feldarten tauschen in diesem Level ihre Farben."""


LEVELS: dict[str, PuzzlePlan] = {
    "Ausgang": PuzzlePlan(9, traps=1),
    "Fallen": PuzzlePlan(11, traps=4),
    "Kiste": PuzzlePlan(9, traps=1, boxes=1),
    "zwei Kisten": PuzzlePlan(11, traps=2, boxes=2),
    "groß": PuzzlePlan(13, traps=3, boxes=1),
    "Tausch": PuzzlePlan(11, traps=2, boxes=1, swap=(Tile.OPEN_DOOR, Tile.TRAP)),
}


@dataclass(frozen=True)
class MechanicsRow:
    """Ein Level, gemittelt über alle Läufe, für alle vier Agenten."""

    level: str
    size: int
    first_win: dict[Learner, float]
    """Mittlere Zahl der Tastendrücke bis zum ersten Sieg (nie gewonnen: Tastendrücke + 1)."""
    wins: dict[Learner, float]
    traps: dict[Learner, float]
    stopped: dict[Learner, float]
    """Anteil der Läufe, in denen der Agent ausgeschieden ist."""
    optimal_first_win: float


@dataclass(frozen=True)
class LevelOutcome:
    """Wie ein Level für alle Agenten lief, und das Modell des Agenten mit Vorwissen danach."""

    plays: dict[Learner, GridPlay]
    optimal: int
    model: WorldModel


@dataclass(frozen=True)
class Look:
    """Farben und Tasten eines Spiels; sie gelten in allen seinen Leveln."""

    colors: Mapping[Tile, Color]
    controls: Mapping[str, Direction]
    restart: str | None = None
    """Name der Neustart-Taste (`None`: keine, wie in Ergebnis 14)."""


def run_mechanics(seeds: int = 20, steps: int = STEPS_PER_LEVEL) -> list[MechanicsRow]:
    """Spielt alle Level mit allen Agenten; alle bekommen dieselben Zufallszahlen."""
    outcomes: dict[str, list[LevelOutcome]] = {name: [] for name in LEVELS}
    for seed in range(seeds):
        for game, outcome in play_game(seed, steps):
            outcomes[game.name].append(outcome)
    return [_row(name, plan, outcomes[name], steps) for name, plan in LEVELS.items()]


def play_game(
    seed: int, steps: int = STEPS_PER_LEVEL, record: str | None = None
) -> Iterator[tuple[GridGame, LevelOutcome]]:
    """Spielt die Level eines Spiels nacheinander. Das Level `record` wird aufgezeichnet."""
    rng = random.Random(seed)
    look = Look(random_colors(PUZZLE_TILES, rng), random_controls(rng))
    prior: WorldModel | None = None
    for name, plan in LEVELS.items():
        game = build_puzzle(name, plan, look, rng)
        outcome = play_level(game, prior, steps, rng, record=name == record)
        yield game, outcome
        prior = outcome.model


def build_puzzle(name: str, plan: PuzzlePlan, look: Look, rng: random.Random) -> GridGame:
    """Ein Level nach Plan, in den Farben und mit den Tasten des Spiels."""
    return dress(name, build_maze(plan, rng), plan, look)


def build_maze(plan: PuzzlePlan, rng: random.Random) -> Maze:
    """Das Labyrinth eines Levels nach Plan, noch ohne Farben und Tasten."""
    if plan.boxes:
        return puzzle_maze(plan.size, rng, traps=plan.traps, boxes=plan.boxes)
    return random_maze(plan.size, rng, traps=plan.traps, with_key=False)


def dress(name: str, maze: Maze, plan: PuzzlePlan, look: Look) -> GridGame:
    """Gibt einem Labyrinth die Farben und Tasten eines Spiels (mit dem Tausch des Plans)."""
    colors = dict(look.colors)
    if plan.swap is not None:
        first, second = plan.swap
        colors[first], colors[second] = colors[second], colors[first]
    return GridGame(name, maze, colors, look.controls, look.restart)


def play_level(
    game: GridGame,
    prior: WorldModel | None,
    steps: int,
    rng: random.Random,
    record: bool = False,
) -> LevelOutcome:
    """Spielt ein Level mit allen Agenten. Der Agent mit Vorwissen gibt sein Modell weiter."""
    informed = ModelAgent(game.buttons, prior)
    team: dict[Learner, GridAgent] = {
        "Bilder": StateAgent(game.buttons, game.render(game.start)),
        "Objekte 0.12": ObjectAgent(game.buttons),
        "Weltmodell": ModelAgent(game.buttons),
        "Weltmodell + Vorwissen": informed,
    }
    play_seed = rng.random()
    plays = {
        learner: play_grid(game, agent, steps, random.Random(play_seed), record)
        for learner, agent in team.items()
    }
    return LevelOutcome(plays, optimal_first_win(game), informed.world_model())


@dataclass(frozen=True)
class ClassicRow:
    """Ein Level aus Ergebnis 13: erster Sieg des Objekt-Agenten und des Modell-Agenten."""

    level: str
    objects: float
    model: float


def run_classic_check(seeds: int = 20, steps: int = 200) -> list[ClassicRow]:
    """Spielt die Labyrinthe aus Ergebnis 13 mit dem Objekt-Agenten und dem Modell-Agenten."""
    first_wins: dict[str, list[tuple[int, int]]] = {name: [] for name in CLASSIC_LEVELS}
    for seed in range(seeds):
        rng = random.Random(seed)
        for name, plan in CLASSIC_LEVELS.items():
            game = build_level(name, plan, rng)
            play_seed = rng.random()
            pair = (ObjectAgent(game.buttons), ModelAgent(game.buttons))
            plays = [play_grid(game, agent, steps, random.Random(play_seed)) for agent in pair]
            first_wins[name].append((first_win(plays[0], steps), first_win(plays[1], steps)))
    return [
        ClassicRow(name, mean(o for o, _ in pairs), mean(m for _, m in pairs))
        for name, pairs in first_wins.items()
    ]


def first_win(play: GridPlay, steps: int) -> int:
    """Tastendrücke bis zum ersten Sieg; ohne Sieg einer mehr, als erlaubt waren."""
    return play.first_win if play.first_win is not None else steps + 1


def optimal_first_win(game: GridGame) -> int:
    """Die kürzeste Zahl an Tastendrücken bis zum Sieg."""
    best = shortest_win(game.maze)
    if best is None:
        raise ValueError(f"{game.name} ist nicht lösbar.")
    return best


def _row(name: str, plan: PuzzlePlan, outcomes: list[LevelOutcome], steps: int) -> MechanicsRow:
    def average(learner: Learner, measure: Callable[[GridPlay], float]) -> float:
        return mean(measure(outcome.plays[learner]) for outcome in outcomes)

    return MechanicsRow(
        level=name,
        size=plan.size,
        first_win={
            learner: average(learner, lambda p: first_win(p, steps)) for learner in LEARNERS
        },
        wins={learner: average(learner, lambda p: p.wins) for learner in LEARNERS},
        traps={learner: average(learner, lambda p: p.traps) for learner in LEARNERS},
        stopped={
            learner: average(learner, lambda p: p.stopped is not None) for learner in LEARNERS
        },
        optimal_first_win=mean(outcome.optimal for outcome in outcomes),
    )
