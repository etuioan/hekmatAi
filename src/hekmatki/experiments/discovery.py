"""Experiment Spielefamilie: Entdeckt der Agent Regeln selbst und überträgt er sie?

Der Agent spielt nacheinander drei Spiele „Schlüssel und Tür“ mit gleicher Mechanik, aber
anderem Aussehen und anderer Tastenbelegung. Nach jedem Spiel verdichtet er, was er gelernt
hat, zu einem Schema (beim zweiten und dritten Spiel ergänzt er es). Verglichen wird mit
einem Agenten, der jedes Spiel ohne Vorwissen beginnt.

Härtetest danach, jeweils mit dem Schema aus allen drei Spielen: ein gespiegeltes Spiel,
ein längeres und eines, bei dem die Tür auch ohne Schlüssel aufgeht.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

from hekmatki.curiosity import Curiosity
from hekmatki.explorer import Explorer
from hekmatki.game_schema import (
    GameSchema,
    SchemaAdvisor,
    Transitions,
    merged_schema,
    schema_from_model,
)
from hekmatki.puzzle import LONGER, MIRRORED, NO_KEY, STANDARD, WIN, KeyDoorGame, Layout, make_game

STEPS_PER_GAME = 60
"""So viele Tastendrücke hat der Agent pro Spiel."""
FAMILY = ("Spiel 1", "Spiel 2", "Spiel 3")
STRESS_TESTS: dict[str, Layout] = {
    "gespiegelt": MIRRORED,
    "länger": LONGER,
    "ohne Schlüssel": NO_KEY,
}


@dataclass(frozen=True)
class Play:
    """Wie ein Spiel lief."""

    first_win: int | None
    """Nach wie vielen Tastendrücken der erste Sieg kam (`None`: nie)."""
    wins: int


@dataclass(frozen=True)
class DiscoveryRow:
    """Ein Spiel, gemittelt über alle Läufe, für beide Agenten."""

    game: str
    fresh_first_win: float
    """Ohne Vorwissen: mittlere Zahl der Tastendrücke bis zum ersten Sieg."""
    schema_first_win: float
    """Mit Schema: dasselbe."""
    optimal_first_win: int
    """Kürzester Weg zum ersten Sieg, wenn man alles wüsste."""
    fresh_wins: float
    """Ohne Vorwissen: mittlere Zahl der Siege."""
    schema_wins: float
    """Mit Schema: dasselbe."""
    optimal_wins: int
    """So viele Siege sind höchstens möglich."""
    schema_fits: float
    """Anteil der Läufe, in denen am Ende noch eine Deutung des Schemas übrig war."""


@dataclass(frozen=True)
class DiscoveryResult:
    """Alle Spiele plus wie groß das Schema nach jedem Spiel der Familie war."""

    rows: list[DiscoveryRow]
    schema_size: dict[str, float]
    """Mittlere Zahl bekannter Übergänge im Schema nach Spiel 1, 2 und 3."""


def run_discovery(
    seeds: int = 20, steps: int = STEPS_PER_GAME, curiosity: Curiosity | None = None
) -> DiscoveryResult:
    """Spielt die Familie und den Härtetest mit und ohne Schema.

    Beide Agenten bekommen pro Spiel dieselben Zufallszahlen. Im ersten Spiel, in dem
    noch keiner ein Schema hat, spielen sie deshalb genau gleich. Mit `curiosity` sind
    beide Agenten neugierig, auch nachdem sie einen Weg zum Sieg kennen.
    """
    layouts = {name: STANDARD for name in FAMILY} | STRESS_TESTS
    plays: dict[str, dict[str, list[Play]]] = {n: {"fresh": [], "schema": []} for n in layouts}
    fits: dict[str, list[bool]] = {name: [] for name in layouts}
    sizes: dict[str, list[int]] = {name: [] for name in FAMILY}
    for seed in range(seeds):
        rng = random.Random(seed)
        schema: GameSchema | None = None
        for name, layout in layouts.items():
            game = make_game(name, layout, rng)
            advisor = (
                None if schema is None else SchemaAdvisor(schema, game.buttons, game.start_symbol)
            )
            fresh = Explorer(game.buttons, game.start_symbol, curiosity=curiosity)
            informed = Explorer(game.buttons, game.start_symbol, advisor, curiosity)
            play_seed = rng.random()
            plays[name]["fresh"].append(play(game, fresh, steps, random.Random(play_seed)))
            plays[name]["schema"].append(play(game, informed, steps, random.Random(play_seed)))
            fits[name].append(advisor is not None and advisor.fits())
            if name in FAMILY:
                schema = schema_after_game(schema, advisor, informed.model, game)
                sizes[name].append(len(schema.transitions))
    rows = [_row(name, layouts[name], plays[name], fits[name], steps) for name in layouts]
    return DiscoveryResult(rows, {name: mean(values) for name, values in sizes.items()})


def play(game: KeyDoorGame, explorer: Explorer, steps: int, rng: random.Random) -> Play:
    """Lässt den Entdecker `steps` Tasten drücken. Nach einem Sieg geht es am Start weiter."""
    state = game.start_symbol
    first_win: int | None = None
    wins = 0
    for step in range(1, steps + 1):
        button = explorer.choose(state, rng, steps_left=steps - step + 1)
        outcome = game.step(state, button)
        explorer.learn(state, button, outcome)
        if outcome == WIN:
            wins += 1
            first_win = step if first_win is None else first_win
            state = game.start_symbol
        else:
            state = outcome
    return Play(first_win, wins)


def schema_after_game(
    schema: GameSchema | None,
    advisor: SchemaAdvisor | None,
    model: Transitions,
    game: KeyDoorGame,
) -> GameSchema:
    """Nach dem Spiel: Schema neu bilden oder um das Gelernte ergänzen."""
    if schema is None or advisor is None:
        return schema_from_model("Schlüssel und Tür", model, game.start_symbol, game.buttons)
    interpretation = advisor.best_interpretation()
    if interpretation is None:
        return schema
    return merged_schema(schema, interpretation, model)


def shortest_win(layout: Layout) -> int:
    """Kürzester Weg vom Start zum Sieg, wenn man alles wüsste."""
    if not layout.needs_key:
        return abs(layout.start - layout.door) + 1
    return abs(layout.start - layout.key) + 1 + abs(layout.key - layout.door) + 1


def _row(
    name: str, layout: Layout, plays: dict[str, list[Play]], fits: Sequence[bool], steps: int
) -> DiscoveryRow:
    def first_win(agent: str) -> float:
        return mean(p.first_win if p.first_win is not None else steps + 1 for p in plays[agent])

    return DiscoveryRow(
        game=name,
        fresh_first_win=first_win("fresh"),
        schema_first_win=first_win("schema"),
        optimal_first_win=shortest_win(layout),
        fresh_wins=mean(p.wins for p in plays["fresh"]),
        schema_wins=mean(p.wins for p in plays["schema"]),
        optimal_wins=steps // shortest_win(layout),
        schema_fits=mean(fits),
    )
