"""Experiment Regeln statt Zustände: Überträgt der Agent ein Spiel auf andere Größen?

Ein Zustands-Schema (Ergebnis 10) merkt sich einzelne Zustände und passt deshalb nur auf
gleich große Spiele. Ein Regel-Schema merkt sich, *wo* etwas passiert, zum Beispiel
„Benutzen an der Wand“. Hier wird jedes Spiel der Familie länger (4, 5, 6 Felder).
Drei Agenten spielen dieselben Spiele: ohne Vorwissen, mit Zustands-Schema und mit
Regel-Schema. Härtetest danach: gespiegelt, viel länger (8 Felder) und ohne Schlüssel.
"""

import random
from collections import Counter
from dataclasses import dataclass, field
from statistics import mean
from typing import Literal

from hekmatki.experiments.discovery import (
    STEPS_PER_GAME,
    Play,
    play,
    schema_after_game,
    shortest_win,
)
from hekmatki.explorer import Explorer
from hekmatki.game_schema import GameSchema, SchemaAdvisor
from hekmatki.puzzle import MIRRORED, NO_KEY, STANDARD, KeyDoorGame, Layout, make_game
from hekmatki.rules import RuleAdvisor, RuleSchema, rules_after_game

Knowledge = Literal["ohne Vorwissen", "Zustands-Schema", "Regel-Schema"]
KNOWLEDGE: tuple[Knowledge, ...] = ("ohne Vorwissen", "Zustands-Schema", "Regel-Schema")
FAMILY: dict[str, Layout] = {
    "Spiel 1": STANDARD,
    "Spiel 2": Layout(length=5, door=4),
    "Spiel 3": Layout(length=6, door=5),
}
STRESS_TESTS: dict[str, Layout] = {
    "gespiegelt": MIRRORED,
    "viel länger": Layout(length=8, door=7),
    "ohne Schlüssel": NO_KEY,
}
GAME_NAME = "Schlüssel und Tür"


@dataclass(frozen=True)
class TransferRow:
    """Ein Spiel, gemittelt über alle Läufe, für alle drei Agenten."""

    game: str
    length: int
    first_win: dict[Knowledge, float]
    """Mittlere Zahl der Tastendrücke bis zum ersten Sieg (nie gewonnen zählt als 61)."""
    wins: dict[Knowledge, float]
    optimal_first_win: int
    optimal_wins: int
    rules_fit: float
    """Anteil der Läufe, in denen am Ende noch eine Deutung des Regel-Schemas übrig war."""


@dataclass(frozen=True)
class TransferResult:
    """Alle Spiele plus welche Ortsbeschreibungen nach Spiel 3 übrig blieben."""

    rows: list[TransferRow]
    descriptions: list[Counter[str]]
    """Pro Ereignis: wie oft welche Beschreibungen nach Spiel 3 übrig blieben."""


@dataclass
class _Memory:
    """Was die beiden lernenden Agenten von Spiel zu Spiel mitnehmen."""

    schema: GameSchema | None = None
    rules: RuleSchema | None = None


@dataclass
class _Tally:
    """Sammelt die Ergebnisse eines Spiels über alle Läufe."""

    plays: dict[Knowledge, list[Play]] = field(
        default_factory=lambda: {knowledge: [] for knowledge in KNOWLEDGE}
    )
    rules_fit: list[bool] = field(default_factory=list)


def run_rule_transfer(seeds: int = 20, steps: int = STEPS_PER_GAME) -> TransferResult:
    """Spielt Familie und Härtetest mit allen drei Agenten.

    Alle Agenten bekommen pro Spiel dieselben Zufallszahlen. In Spiel 1, in dem noch
    keiner Vorwissen hat, spielen sie deshalb genau gleich.
    """
    layouts = FAMILY | STRESS_TESTS
    tallies = {name: _Tally() for name in layouts}
    final_rules: list[RuleSchema] = []
    for seed in range(seeds):
        rng = random.Random(seed)
        memory = _Memory()
        for name, layout in layouts.items():
            _play_game(make_game(name, layout, rng), memory, tallies[name], steps, rng)
        if memory.rules is not None:
            final_rules.append(memory.rules)
    rows = [_row(name, layout, tallies[name], steps) for name, layout in layouts.items()]
    return TransferResult(rows, _descriptions(final_rules))


def _play_game(
    game: KeyDoorGame, memory: _Memory, tally: _Tally, steps: int, rng: random.Random
) -> None:
    """Ein Spiel für alle drei Agenten; in der Familie lernen die beiden mit Vorwissen."""
    buttons, start = game.buttons, game.start_symbol
    schema_advisor = None if memory.schema is None else SchemaAdvisor(memory.schema, buttons, start)
    rule_advisor = None if memory.rules is None else RuleAdvisor(memory.rules, buttons, start)
    explorers: dict[Knowledge, Explorer] = {
        "ohne Vorwissen": Explorer(buttons, start),
        "Zustands-Schema": Explorer(buttons, start, schema_advisor),
        "Regel-Schema": Explorer(buttons, start, rule_advisor),
    }
    play_seed = rng.random()
    for knowledge, explorer in explorers.items():
        tally.plays[knowledge].append(play(game, explorer, steps, random.Random(play_seed)))
    tally.rules_fit.append(rule_advisor is not None and rule_advisor.fits())
    if game.name in FAMILY:
        state_model = explorers["Zustands-Schema"].model
        rule_model = explorers["Regel-Schema"].model
        memory.schema = schema_after_game(memory.schema, schema_advisor, state_model, game)
        memory.rules = rules_after_game(GAME_NAME, memory.rules, rule_model, start, buttons)


def _row(name: str, layout: Layout, tally: _Tally, steps: int) -> TransferRow:
    def first_win(plays: list[Play]) -> float:
        return mean(p.first_win if p.first_win is not None else steps + 1 for p in plays)

    return TransferRow(
        game=name,
        length=layout.length,
        first_win={k: first_win(plays) for k, plays in tally.plays.items()},
        wins={k: mean(p.wins for p in plays) for k, plays in tally.plays.items()},
        optimal_first_win=shortest_win(layout),
        optimal_wins=steps // shortest_win(layout),
        rules_fit=mean(tally.rules_fit),
    )


def _descriptions(all_rules: list[RuleSchema]) -> list[Counter[str]]:
    """Pro Ereignis: Häufigkeit der übrig gebliebenen Beschreibungen, ohne Richtung.

    Die Richtung lassen wir weg, weil „vorwärts“ nur heißt: in der Richtung, die der
    Agent in seinem ersten Spiel so genannt hat.
    """
    if not all_rules:
        return []
    counters: list[Counter[str]] = [Counter() for _ in all_rules[0].events]
    for rules in all_rules:
        for counter, event in zip(counters, rules.events, strict=True):
            counter[" + ".join(sorted(p.undirected for p in event.places))] += 1
    return counters
