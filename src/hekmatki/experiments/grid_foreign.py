"""Gegenprobe (ab 0.15): Schadet Vorwissen, wenn ein neues Spiel eine fremde Mechanik hat?

Runde 5 des Dossiers sagt: Ein ähnliches Spiel mit anderer Mechanik ist die gefährlichste
Lage für Vorwissen (falsche Analogie). Dieses Experiment misst das. Der Agent spielt zuerst
ein ganzes Spiel A wie in Ergebnis 14. Dann kommen neue Level eines Spiels B:
- „gewohnt“: Kisten-Rätsel mit den bekannten Regeln (Vergleich)
- „Tor umgekehrt“: Die Druckplatte schließt das Tor, statt es zu öffnen. Die Kiste steht
  zu Beginn auf der Platte, das Tor ist zu; man muss die Kiste herunterschieben. Gleiches
  Aussehen, umgekehrte Bedeutung: Das lässt sich als Fernwirkung lernen, widerspricht aber
  dem Vorwissen aus Spiel A.
- „Eis“: Auf Boden rutscht die Figur weiter, bis etwas sie aufhält. Das passt in keine der
  fünf Regelarten, die der Agent kennt: ein Test außerhalb des eingebauten Wissens.

Sieben Agenten spielen jedes Level, alle mit Neustart-Taste:
- „ohne Vorwissen“ (Farben und Tasten von B)
- „Rollen aus A“ und „Rollen + Prüfung“ (Farben und Tasten von B), mit dem Rollen-Weltmodell
  aus A
- „ohne, Aussehen A“: dasselbe Level in Farben und Tasten von Spiel A
- „Modell aus A“, „Modell + Prüfung“ und „Modell + Teilprüfung“: ebenfalls im Aussehen von A,
  mit dem Farb-Modell aus A. Das Spiel sieht aus wie A, hat aber zum Teil andere Regeln.
„+ Prüfung“ nutzt Vorwissen erst, wenn es sich bewährt hat (H17, `grid/trust.py`).
„+ Teilprüfung“ nutzt es sofort, testet aber bei Stillstand jeden Teil, den es nicht selbst
gesehen hat (H16, Stufe 4d in `grid/model_agent.py`). Nur mit dem Modell aus A, denn nur
dort schadet Vorwissen.

Gemessen wird der Schaden durch Vorwissen: Tastendrücke bis zum ersten Sieg mit Vorwissen
minus ohne, im selben Aussehen (negative Übertragung nach Wang 2019, wenn größer als null).
Figur und Tasten kennen die Agenten mit Modell aus A schon; das bleibt ein kleiner Vorteil.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, replace
from statistics import mean
from typing import Literal

from hekmatki.experiments import grid_mechanics as mechanics
from hekmatki.experiments.grid_roles import RESTART, GameA, play_game_a
from hekmatki.grid.mazes import shortest_win
from hekmatki.grid.model_agent import ModelAgent
from hekmatki.grid.play import GridPlay, play_grid
from hekmatki.grid.trust import Trust
from hekmatki.grid.world import (
    PUZZLE_TILES,
    GridGame,
    Maze,
    Mechanics,
    random_colors,
    random_controls,
)

Learner = Literal[
    "ohne Vorwissen",
    "Rollen aus A",
    "Rollen + Prüfung",
    "ohne, Aussehen A",
    "Modell aus A",
    "Modell + Prüfung",
    "Modell + Teilprüfung",
]
LEARNERS: tuple[Learner, ...] = (
    "ohne Vorwissen",
    "Rollen aus A",
    "Rollen + Prüfung",
    "ohne, Aussehen A",
    "Modell aus A",
    "Modell + Prüfung",
    "Modell + Teilprüfung",
)
LOOKS_LIKE_A: tuple[Learner, ...] = (
    "ohne, Aussehen A",
    "Modell aus A",
    "Modell + Prüfung",
    "Modell + Teilprüfung",
)
"""Diese Agenten spielen in den Farben und mit den Tasten von Spiel A."""
BASELINE: dict[Learner, Learner] = {
    learner: "ohne, Aussehen A" if learner in LOOKS_LIKE_A else "ohne Vorwissen"
    for learner in LEARNERS
}
"""Womit der Schaden verglichen wird: der Agent ohne Vorwissen im selben Aussehen."""
MAZE_TRIES = 300
"""So oft wird ein Labyrinth neu gebaut, bis es mit der fremden Mechanik lösbar ist."""


@dataclass(frozen=True)
class ForeignLevel:
    """Ein Level von Spiel B: Bauplan und Mechanik."""

    plan: mechanics.PuzzlePlan
    mechanics: Mechanics
    box_on_plate: bool = False
    """Die Kiste steht zu Beginn auf der Druckplatte (braucht genau eine Kiste)."""
    least_steps: int = 1
    """So viele Tastendrücke braucht der kürzeste Sieg mindestens, damit das Level kein
    Zufallstreffer ist (von Hand gewählt, ohne Grundlage)."""


LEVELS: dict[str, ForeignLevel] = {
    "gewohnt": ForeignLevel(mechanics.PuzzlePlan(11, traps=2, boxes=1), Mechanics()),
    "Tor umgekehrt": ForeignLevel(
        mechanics.PuzzlePlan(11, traps=2, boxes=1), Mechanics(plate_closes=True), box_on_plate=True
    ),
    "Eis": ForeignLevel(mechanics.PuzzlePlan(13, traps=2), Mechanics(ice=True), least_steps=6),
}


@dataclass(frozen=True)
class ForeignRow:
    """Eine Art von Level, gemittelt über alle Läufe."""

    level: str
    size: int
    first_win: dict[Learner, float]
    harm: dict[Learner, float]
    """Mittlerer Schaden: Tastendrücke bis zum ersten Sieg mit minus ohne Vorwissen
    (im selben Aussehen, siehe `BASELINE`)."""
    no_win: dict[Learner, float]
    """Anteil der Läufe ohne Sieg."""
    refuted: dict[Learner, float]
    """Anteil der Läufe, in denen der Agent sein Vorwissen am Ende als widerlegt ansah."""
    optimal_first_win: float


@dataclass(frozen=True)
class PlayedLevel:
    """Ein gespieltes Level von Spiel B, in beiden Farbgebungen."""

    same_look: GridGame
    new_look: GridGame
    plays: dict[Learner, GridPlay]
    trust: dict[Learner, Trust]
    """Wie weit jeder Agent am Ende seinem Vorwissen traut."""
    optimal: int


def build_foreign_maze(level: ForeignLevel, rng: random.Random) -> Maze:
    """Ein Labyrinth nach Plan mit fremder Mechanik, das sich damit lösen lässt."""
    if level.box_on_plate and level.plan.boxes != 1:
        raise ValueError(f"Kiste auf Platte geht nur mit einer Kiste, nicht {level.plan.boxes}.")
    for _ in range(MAZE_TRIES):
        maze = replace(mechanics.build_maze(level.plan, rng), mechanics=level.mechanics)
        if level.box_on_plate and maze.plate is not None:
            maze = replace(maze, boxes=frozenset({maze.plate}))
        best = shortest_win(maze)
        if best is not None and best >= level.least_steps:
            return maze
    raise ValueError(f"Kein lösbares Labyrinth in {MAZE_TRIES} Versuchen: {level}.")


def play_foreign_levels(
    seed: int,
    learned: GameA,
    steps: int = mechanics.STEPS_PER_LEVEL,
    record: str | None = None,
) -> list[PlayedLevel]:
    """Spielt jedes Level von Spiel B mit allen Agenten. `record` wird aufgezeichnet."""
    rng = random.Random(f"Gegenprobe {seed}")
    look_a = mechanics.Look(learned.look.colors, learned.look.controls, RESTART)
    look_b = mechanics.Look(random_colors(PUZZLE_TILES, rng), random_controls(rng), RESTART)
    played = []
    for name, level in LEVELS.items():
        maze = build_foreign_maze(level, rng)
        same = mechanics.dress(name, maze, level.plan, look_a)
        new = mechanics.dress(name, maze, level.plan, look_b)
        agents: dict[Learner, ModelAgent] = {
            "ohne Vorwissen": ModelAgent(new.buttons, restart=RESTART),
            "Rollen aus A": ModelAgent(new.buttons, roles=learned.roles, restart=RESTART),
            "Rollen + Prüfung": ModelAgent(
                new.buttons, roles=learned.roles, restart=RESTART, checked=True
            ),
            "ohne, Aussehen A": ModelAgent(same.buttons, restart=RESTART),
            "Modell aus A": ModelAgent(same.buttons, learned.model, restart=RESTART),
            "Modell + Prüfung": ModelAgent(
                same.buttons, learned.model, restart=RESTART, checked=True
            ),
            "Modell + Teilprüfung": ModelAgent(
                same.buttons, learned.model, restart=RESTART, doubts_parts=True
            ),
        }
        play_seed = rng.random()
        plays: dict[Learner, GridPlay] = {
            learner: play_grid(
                same if learner in LOOKS_LIKE_A else new,
                agent,
                steps,
                random.Random(play_seed),
                record=name == record,
            )
            for learner, agent in agents.items()
        }
        trust = {learner: agent.trust for learner, agent in agents.items()}
        played.append(PlayedLevel(same, new, plays, trust, mechanics.optimal_first_win(new)))
    return played


def run_foreign(seeds: int = 20, steps: int = mechanics.STEPS_PER_LEVEL) -> list[ForeignRow]:
    """Für jeden Lauf: Spiel A spielen, dann jedes Level mit fremder Mechanik."""
    results = [play_foreign_levels(seed, play_game_a(seed, steps), steps) for seed in range(seeds)]
    return [
        _row(name, level.plan.size, [played[index] for played in results], steps)
        for index, (name, level) in enumerate(LEVELS.items())
    ]


def _row(name: str, size: int, levels: list[PlayedLevel], steps: int) -> ForeignRow:
    def first(level: PlayedLevel, learner: Learner) -> int:
        return mechanics.first_win(level.plays[learner], steps)

    def harm(level: PlayedLevel, learner: Learner) -> int:
        return first(level, learner) - first(level, BASELINE[learner])

    def average(measure: Callable[[PlayedLevel, Learner], float]) -> dict[Learner, float]:
        return {learner: mean(measure(level, learner) for level in levels) for learner in LEARNERS}

    return ForeignRow(
        level=name,
        size=size,
        first_win=average(first),
        harm=average(harm),
        no_win=average(lambda level, learner: level.plays[learner].first_win is None),
        refuted=average(lambda level, learner: level.trust[learner] is Trust.REFUTED),
        optimal_first_win=mean(level.optimal for level in levels),
    )
