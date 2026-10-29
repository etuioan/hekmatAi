"""Wiedergabe: Level der 2D-Welt Schritt für Schritt aufzeichnen, zum Anschauen.

Die Seite zeigt fünf Fälle, jeweils mit den Mittelwerten aller Läufe:
- **Tor umgekehrt** (Ergebnis 16): Ein Level sieht aus wie Spiel A, aber die Druckplatte
  schließt das Tor. Vorwissen ohne, mit Prüfung und mit Teilprüfung
- **Neue Farben** (Ergebnis 15): ein Level in einem Spiel mit neuen Farben, mit und ohne
  Rollen-Weltmodell aus dem Spiel davor
- **Kisten-Rätsel** (Ergebnis 14): ein großes Level mit Kiste, Druckplatte und Tor
- **Tausch** (Ergebnis 14): Ausgang und Fallen haben die Farben getauscht
- **Labyrinth** (Ergebnis 13): das große Labyrinth mit Schlüssel und Tür

`write_page` setzt Aufzeichnungen und Mittelwerte in eine HTML-Vorlage ein.
Aufruf: `PYTHONPATH=src python -m hekmatki.experiments.grid_replay docs/wiedergabe.html`
"""

import json
import random
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from hekmatki.experiments import grid_foreign as foreign
from hekmatki.experiments import grid_mechanics as mechanics
from hekmatki.experiments import grid_roles as roles
from hekmatki.experiments import grid_transfer as transfer
from hekmatki.grid.play import Frame, GridPlay
from hekmatki.grid.roles import RoleSchema
from hekmatki.grid.world import PALETTE, Grid, GridGame

REPLAY_SEED = 3
REPLAY_LEVEL = "groß"
PUZZLE_SEED = 0
SWAP_SEED = 0
ROLES_SEED = 1
ROLES_LEVEL = "groß"
FOREIGN_SEED = 5
FOREIGN_LEVEL = "Tor umgekehrt"
FOREIGN_SHOWN: tuple[foreign.Learner, ...] = (
    "ohne, Aussehen A",
    "Modell aus A",
    "Modell + Prüfung",
    "Modell + Teilprüfung",
)
"""Die Agenten im Aussehen von Spiel A: Nur dort schadet Vorwissen."""
TEMPLATE = Path(__file__).with_name("grid_replay_template.html")
DATA_MARKER = "/*REPLAY_DATA*/null"


def replay(
    seed: int = REPLAY_SEED, level: str = REPLAY_LEVEL, steps: int = transfer.STEPS_PER_LEVEL
) -> dict[str, Any]:
    """Die Aufzeichnung eines Labyrinths aus Ergebnis 13 als JSON-taugliches Wörterbuch."""
    if level not in transfer.LEVELS:
        raise ValueError(f"Unbekanntes Level {level!r}; möglich: {sorted(transfer.LEVELS)}.")
    rng = random.Random(seed)
    schema: RoleSchema | None = None
    for name, plan in transfer.LEVELS.items():
        game = transfer.build_level(name, plan, rng)
        result = transfer.play_level(game, plan, schema, steps, rng, record=name == level)
        if name == level:
            return _as_data(game, result.plays, transfer.LEARNERS, result.optimal, seed)
        schema = result.schema
    raise AssertionError("unerreichbar: das Level steht in LEVELS")


def puzzle_replay(
    seed: int = PUZZLE_SEED, level: str = "groß", steps: int = mechanics.STEPS_PER_LEVEL
) -> dict[str, Any]:
    """Die Aufzeichnung eines Levels aus Ergebnis 14 als JSON-taugliches Wörterbuch."""
    if level not in mechanics.LEVELS:
        raise ValueError(f"Unbekanntes Level {level!r}; möglich: {sorted(mechanics.LEVELS)}.")
    for game, outcome in mechanics.play_game(seed, steps, record=level):
        if game.name == level:
            return _as_data(game, outcome.plays, mechanics.LEARNERS, outcome.optimal, seed)
    raise AssertionError("unerreichbar: das Level steht in LEVELS")


def roles_replay(
    seed: int = ROLES_SEED, level: str = ROLES_LEVEL, steps: int = mechanics.STEPS_PER_LEVEL
) -> dict[str, Any]:
    """Die Aufzeichnung eines neuen Levels aus Ergebnis 15 als JSON-taugliches Wörterbuch."""
    if level not in mechanics.LEVELS:
        raise ValueError(f"Unbekanntes Level {level!r}; möglich: {sorted(mechanics.LEVELS)}.")
    learned = roles.play_game_a(seed, steps)
    for found in roles.play_new_levels(seed, learned, steps, record=level):
        if found.new.name == level:
            return _as_data(found.new, found.plays, roles.LEARNERS, found.optimal, seed)
    raise AssertionError("unerreichbar: das Level steht in LEVELS")


def foreign_replay(
    seed: int = FOREIGN_SEED, level: str = FOREIGN_LEVEL, steps: int = mechanics.STEPS_PER_LEVEL
) -> dict[str, Any]:
    """Die Aufzeichnung eines Levels aus Ergebnis 16 (Aussehen A) als JSON-taugliches Wörterbuch."""
    if level not in foreign.LEVELS:
        raise ValueError(f"Unbekanntes Level {level!r}; möglich: {sorted(foreign.LEVELS)}.")
    learned = roles.play_game_a(seed, steps)
    for found in foreign.play_foreign_levels(seed, learned, steps, record=level):
        if found.same_look.name == level:
            return _as_data(found.same_look, found.plays, FOREIGN_SHOWN, found.optimal, seed)
    raise AssertionError("unerreichbar: das Level steht in LEVELS")


def write_page(output: Path, template: Path = TEMPLATE, seeds: int = 20) -> None:
    """Schreibt die Wiedergabe-Seite: Vorlage plus Aufzeichnungen plus Mittelwerte."""
    page = template.read_text(encoding="utf-8")
    if page.count(DATA_MARKER) != 1:
        raise ValueError(f"Die Vorlage braucht genau einmal {DATA_MARKER!r}.")
    puzzles = [_row_data(row) for row in mechanics.run_mechanics(seeds)]
    mazes = [_row_data(row) for row in transfer.run_grid_transfer(seeds)]
    new_colors = [_row_data(row) for row in roles.run_roles(seeds)]
    foreign_rows = [_foreign_row_data(row) for row in foreign.run_foreign(seeds)]
    scenarios = [
        {"id": "fremd", "replay": foreign_replay(), "summary": foreign_rows},
        {"id": "farben", "replay": roles_replay(), "summary": new_colors},
        {"id": "kisten", "replay": puzzle_replay(), "summary": puzzles},
        {"id": "tausch", "replay": puzzle_replay(SWAP_SEED, "Tausch"), "summary": puzzles},
        {"id": "labyrinth", "replay": replay(), "summary": mazes},
    ]
    text = json.dumps({"scenarios": scenarios}, ensure_ascii=False, separators=(",", ":"))
    output.write_text(page.replace(DATA_MARKER, text.replace("</", "<\\/")), encoding="utf-8")


def _row_data(row: transfer.GridRow | mechanics.MechanicsRow | roles.RoleRow) -> dict[str, Any]:
    return {
        "level": row.level,
        "size": f"{row.size}×{row.size}",
        "firstWin": row.first_win,
        "traps": row.traps,
        "optimal": row.optimal_first_win,
    }


def _foreign_row_data(row: foreign.ForeignRow) -> dict[str, Any]:
    return {
        "level": row.level,
        "size": f"{row.size}×{row.size}",
        "firstWin": row.first_win,
        "optimal": row.optimal_first_win,
    }


def _as_data[Name: str](
    game: GridGame,
    plays: Mapping[Name, GridPlay],
    learners: Sequence[Name],
    optimal: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "level": game.name,
        "seed": seed,
        "size": game.maze.size,
        "optimal": optimal,
        "palette": list(PALETTE),
        "truth": {str(tile): color for tile, color in game.colors.items()},
        "agents": [_agent_data(name, plays[name]) for name in learners],
    }


def _agent_data(name: str, play: GridPlay) -> dict[str, Any]:
    return {
        "name": name,
        "firstWin": play.first_win,
        "wins": play.wins,
        "traps": play.traps,
        "stopped": play.stopped,
        "frames": [_frame_data(frame) for frame in play.frames],
    }


def _frame_data(frame: Frame) -> dict[str, Any]:
    return {
        "grid": _compact(frame.grid),
        "button": frame.button,
        "reason": frame.reason,
        "beliefs": frame.beliefs,
        "won": frame.won,
        "trapped": frame.trapped,
    }


def _compact(grid: Grid) -> list[str]:
    """Jede Zeile als Ziffernfolge: Ziffer = Platz der Farbe in `PALETTE`."""
    return ["".join(str(PALETTE.index(color)) for color in row) for row in grid]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Aufruf: python -m hekmatki.experiments.grid_replay ZIELDATEI.html")
    write_page(Path(sys.argv[1]))
