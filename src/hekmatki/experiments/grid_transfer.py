"""Experiment 2D-Welt: Lernt der Agent über Objekte statt Bilder, und überträgt er Rollen?

Labyrinthe als Farbraster wie bei ARC-AGI-3. Jedes Level hat neue Farben, neue
Tastennamen und ein neues Labyrinth. Drei Agenten spielen dieselben Level:
- „Bilder“: der Entdecker aus Ergebnis 10, für den jedes Raster ein eigener Zustand ist
- „Objekte“: der Objekt-Agent, der in jedem Level von vorn lernt
- „Objekte + Schema“: derselbe, aber mit dem Rollen-Schema aus den bisherigen Leveln

Nach Level 1 bis 3 ergänzt der dritte Agent sein Rollen-Schema. Danach kommen drei
Härtetests: ein großes Labyrinth, eines ohne Schlüssel und eines mit vielen Fallen.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from hekmatki.grid.agent import ObjectAgent
from hekmatki.grid.baseline import StateAgent
from hekmatki.grid.mazes import random_maze, shortest_win
from hekmatki.grid.play import GridAgent, GridPlay, play_grid
from hekmatki.grid.roles import RoleAdvisor, RoleSchema, revised, schema_from_knowledge
from hekmatki.grid.world import GridGame, make_grid_game

Learner = Literal["Bilder", "Objekte", "Objekte + Schema"]
LEARNERS: tuple[Learner, ...] = ("Bilder", "Objekte", "Objekte + Schema")
STEPS_PER_LEVEL = 200


@dataclass(frozen=True)
class LevelPlan:
    """Wie ein Level gebaut wird."""

    size: int
    traps: int
    with_key: bool = True
    training: bool = False
    """Nach Trainingsleveln ergänzt der Agent sein Rollen-Schema."""


LEVELS: dict[str, LevelPlan] = {
    "Level 1": LevelPlan(7, traps=1, training=True),
    "Level 2": LevelPlan(9, traps=2, training=True),
    "Level 3": LevelPlan(11, traps=3, training=True),
    "groß": LevelPlan(15, traps=4),
    "ohne Schlüssel": LevelPlan(9, traps=2, with_key=False),
    "viele Fallen": LevelPlan(11, traps=10),
}


@dataclass(frozen=True)
class GridRow:
    """Ein Level, gemittelt über alle Läufe, für alle drei Agenten."""

    level: str
    size: int
    first_win: dict[Learner, float]
    """Mittlere Zahl der Tastendrücke bis zum ersten Sieg (nie gewonnen: Tastendrücke + 1)."""
    wins: dict[Learner, float]
    traps: dict[Learner, float]
    """Wie oft der Agent im Mittel in eine Falle trat."""
    optimal_first_win: float
    optimal_wins: float
    schema_fits: float
    """Anteil der Läufe, in denen am Ende noch eine Deutung des Rollen-Schemas übrig war."""


@dataclass(frozen=True)
class LevelResult:
    """Wie ein Level für alle drei Agenten lief, und das Rollen-Schema danach."""

    plays: dict[Learner, GridPlay]
    optimal: int
    schema_fits: bool
    schema: RoleSchema | None


def run_grid_transfer(seeds: int = 20, steps: int = STEPS_PER_LEVEL) -> list[GridRow]:
    """Spielt alle Level mit allen drei Agenten; alle bekommen dieselben Zufallszahlen."""
    results: dict[str, list[LevelResult]] = {name: [] for name in LEVELS}
    for seed in range(seeds):
        rng = random.Random(seed)
        schema: RoleSchema | None = None
        for name, plan in LEVELS.items():
            result = play_level(build_level(name, plan, rng), plan, schema, steps, rng)
            results[name].append(result)
            schema = result.schema
    return [_row(name, plan, results[name], steps) for name, plan in LEVELS.items()]


def build_level(name: str, plan: LevelPlan, rng: random.Random) -> GridGame:
    """Ein Level nach Plan, mit zufälligem Labyrinth, Farben und Tasten."""
    maze = random_maze(plan.size, rng, traps=plan.traps, with_key=plan.with_key)
    return make_grid_game(name, maze, rng)


def play_level(
    game: GridGame,
    plan: LevelPlan,
    schema: RoleSchema | None,
    steps: int,
    rng: random.Random,
    record: bool = False,
) -> LevelResult:
    """Spielt ein Level mit allen Agenten. Nach einem Trainingslevel wächst das Schema."""
    team = make_team(game, schema)
    play_seed = rng.random()
    plays = {
        learner: play_grid(game, agent, steps, random.Random(play_seed), record)
        for learner, agent in team.by_learner().items()
    }
    if plan.training:
        learned = schema_from_knowledge(team.informed.knowledge)
        schema = learned if schema is None else revised(schema, learned)
    fits = team.advisor is not None and team.advisor.fits()
    return LevelResult(plays, _optimal(game), fits, schema)


@dataclass(frozen=True)
class Team:
    """Die drei Agenten für ein Level. Ohne Schema spielt der dritte wie der zweite."""

    images: StateAgent
    objects: ObjectAgent
    informed: ObjectAgent
    advisor: RoleAdvisor | None

    def by_learner(self) -> dict[Learner, GridAgent]:
        """Die Agenten unter ihren Namen."""
        return {"Bilder": self.images, "Objekte": self.objects, "Objekte + Schema": self.informed}


def make_team(game: GridGame, schema: RoleSchema | None) -> Team:
    """Stellt die drei Agenten für ein Level auf."""
    start = game.render(game.start)
    advisor = None if schema is None else RoleAdvisor(schema, start)
    return Team(
        images=StateAgent(game.buttons, start),
        objects=ObjectAgent(game.buttons),
        informed=ObjectAgent(game.buttons, advisor),
        advisor=advisor,
    )


def _optimal(game: GridGame) -> int:
    best = shortest_win(game.maze)
    if best is None:
        raise ValueError(f"{game.name} ist nicht lösbar.")
    return best


def _row(name: str, plan: LevelPlan, results: list[LevelResult], steps: int) -> GridRow:
    def first_win(learner: Learner) -> float:
        wins = [r.plays[learner].first_win for r in results]
        return mean(w if w is not None else steps + 1 for w in wins)

    def average(learner: Learner, measure: Callable[[GridPlay], int]) -> float:
        return mean(measure(r.plays[learner]) for r in results)

    return GridRow(
        level=name,
        size=plan.size,
        first_win={learner: first_win(learner) for learner in LEARNERS},
        wins={learner: average(learner, lambda p: p.wins) for learner in LEARNERS},
        traps={learner: average(learner, lambda p: p.traps) for learner in LEARNERS},
        optimal_first_win=mean(r.optimal for r in results),
        optimal_wins=mean(steps // r.optimal for r in results),
        schema_fits=mean(r.schema_fits for r in results),
    )
