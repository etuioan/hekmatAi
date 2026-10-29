"""Experiment Rollen-Weltmodell (H14): Wissen aus einem Spiel in einem Spiel mit neuen Farben.

Der Agent spielt zuerst ein ganzes Spiel aus Ergebnis 14 (sechs Level, Spiel A) und macht
aus seinen Modellen ein Rollen-Weltmodell. Dann bekommt er ein neues Level jeder Art. Jedes
neue Labyrinth gibt es zweimal: in den Farben von Spiel A und in den Farben eines neuen
Spiels B, mit neuen Tastennamen. Was in Spiel A braun war, ist in Spiel B vielleicht gelb,
und braun bedeutet etwas anderes.

Vier Agenten spielen jedes neue Level:
- „ohne Vorwissen“: der Modell-Agent ohne jedes Vorwissen (Farben von Spiel B)
- „Farben aus A“: mit seinem Modell aus Spiel A, wie in Ergebnis 14 (Farben von Spiel B).
  Sein Wissen über Farben passt nicht mehr.
- „Rollen aus A“: mit dem Rollen-Weltmodell aus Spiel A (Farben von Spiel B)
- „gleiches Spiel“: mit seinem Modell aus Spiel A in den Farben von Spiel A. Das ist der
  Bestwert aus Ergebnis 14, an dem sich die Übertragung messen lässt.

Die neuen Level haben eine Neustart-Taste wie ARC-AGI-3. Alle vier Agenten kennen sie.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from hekmatki.experiments import grid_mechanics as mechanics
from hekmatki.grid.model import WorldModel
from hekmatki.grid.model_agent import ModelAgent
from hekmatki.grid.play import GridPlay, play_grid
from hekmatki.grid.role_model import RoleWorld
from hekmatki.grid.world import PUZZLE_TILES, GridGame, random_colors, random_controls

Learner = Literal["ohne Vorwissen", "Farben aus A", "Rollen aus A", "gleiches Spiel"]
LEARNERS: tuple[Learner, ...] = ("ohne Vorwissen", "Farben aus A", "Rollen aus A", "gleiches Spiel")
NEW_COLORS: tuple[Learner, ...] = ("ohne Vorwissen", "Farben aus A", "Rollen aus A")
"""Diese Agenten spielen in den Farben von Spiel B."""
RESTART = "neustart"
"""Die neuen Level haben eine Neustart-Taste wie ARC-AGI-3."""


@dataclass(frozen=True)
class GameA:
    """Was der Agent aus Spiel A mitnimmt: sein Modell über Farben und über Rollen."""

    look: mechanics.Look
    model: WorldModel
    roles: RoleWorld


@dataclass(frozen=True)
class NewLevel:
    """Ein neues Level, einmal in den Farben von Spiel A, einmal in denen von Spiel B."""

    same: GridGame
    new: GridGame
    plays: dict[Learner, GridPlay]
    optimal: int


@dataclass(frozen=True)
class RoleRow:
    """Eine Art von Level, gemittelt über alle Läufe."""

    level: str
    size: int
    first_win: dict[Learner, float]
    traps: dict[Learner, float]
    restarts: dict[Learner, float]
    no_win: dict[Learner, float]
    """Anteil der Läufe ohne Sieg."""
    optimal_first_win: float


def play_game_a(seed: int, steps: int = mechanics.STEPS_PER_LEVEL) -> GameA:
    """Spielt Spiel A wie in Ergebnis 14 und macht aus jedem Level ein Rollen-Weltmodell."""
    roles: RoleWorld | None = None
    model: WorldModel | None = None
    look: mechanics.Look | None = None
    for game, outcome in mechanics.play_game(seed, steps):
        level = RoleWorld.from_level(outcome.model, game.render(game.start))
        roles = level if roles is None else roles.merged(level)
        model = outcome.model
        look = mechanics.Look(game.colors, game.controls)
    if roles is None or model is None or look is None:
        raise ValueError("Spiel A hat keine Level.")
    return GameA(look, model, roles)


def play_new_levels(
    seed: int,
    learned: GameA,
    steps: int = mechanics.STEPS_PER_LEVEL,
    record: str | None = None,
) -> list[NewLevel]:
    """Spielt ein neues Level jeder Art mit allen vier Agenten. `record` wird aufgezeichnet."""
    rng = random.Random(f"Spiel B {seed}")
    look_a = mechanics.Look(learned.look.colors, learned.look.controls, RESTART)
    look_b = mechanics.Look(random_colors(PUZZLE_TILES, rng), random_controls(rng), RESTART)
    if dict(look_b.colors) == dict(look_a.colors):
        raise ValueError("Spiel B braucht andere Farben als Spiel A.")
    levels = []
    for name, plan in mechanics.LEVELS.items():
        maze = mechanics.build_maze(plan, rng)
        same = mechanics.dress(name, maze, plan, look_a)
        new = mechanics.dress(name, maze, plan, look_b)
        agents: dict[Learner, ModelAgent] = {
            "ohne Vorwissen": ModelAgent(new.buttons, restart=RESTART),
            "Farben aus A": ModelAgent(
                new.buttons, _without_controls(learned.model), restart=RESTART
            ),
            "Rollen aus A": ModelAgent(new.buttons, roles=learned.roles, restart=RESTART),
            "gleiches Spiel": ModelAgent(same.buttons, learned.model, restart=RESTART),
        }
        play_seed = rng.random()
        plays: dict[Learner, GridPlay] = {
            learner: play_grid(
                new if learner in NEW_COLORS else same,
                agent,
                steps,
                random.Random(play_seed),
                record=name == record,
            )
            for learner, agent in agents.items()
        }
        levels.append(NewLevel(same, new, plays, mechanics.optimal_first_win(new)))
    return levels


def run_roles(seeds: int = 20, steps: int = mechanics.STEPS_PER_LEVEL) -> list[RoleRow]:
    """Für jeden Lauf: Spiel A spielen, dann ein neues Level jeder Art mit allen Agenten."""
    results = [play_new_levels(seed, play_game_a(seed, steps), steps) for seed in range(seeds)]
    return [
        _row(name, plan.size, [levels[index] for levels in results], steps)
        for index, (name, plan) in enumerate(mechanics.LEVELS.items())
    ]


def _without_controls(model: WorldModel) -> WorldModel:
    """Das Modell ohne Tastenwissen: Die Tasten von Spiel B heißen anders."""
    return WorldModel(
        player=model.player,
        rules=model.rules,
        box_enters=model.box_enters,
        leaves=model.leaves,
        consequences=model.consequences,
        unsure=model.unsure,
        blocked_with=model.blocked_with,
    )


def _row(name: str, size: int, levels: list[NewLevel], steps: int) -> RoleRow:
    def average(learner: Learner, measure: Callable[[GridPlay], float]) -> float:
        return mean(measure(level.plays[learner]) for level in levels)

    return RoleRow(
        level=name,
        size=size,
        first_win={
            learner: average(learner, lambda p: mechanics.first_win(p, steps))
            for learner in LEARNERS
        },
        traps={learner: average(learner, lambda p: p.traps) for learner in LEARNERS},
        restarts={learner: average(learner, lambda p: p.restarts) for learner in LEARNERS},
        no_win={learner: average(learner, lambda p: p.first_win is None) for learner in LEARNERS},
        optimal_first_win=mean(level.optimal for level in levels),
    )
