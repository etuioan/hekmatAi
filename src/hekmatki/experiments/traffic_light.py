"""Experiment Ampelspiel: Findet der Agent „Warten“ als Schnittmenge, ohne zu verschmelzen?

Der Agent erlebt zuerst den Alltag: Arzt, U-Bahn und zwei Gespräche. Dabei probiert er ab
und zu, selbst zu handeln, und merkt sich, wo das klappte. Im Schlaf verdichtet er je zwei
Situationen zu einem Schema, „Warten“ und „Gespräch“, samt Handlungswissen pro Rolle.
Dann spielt er das Ampelspiel. Verglichen wird ein Spieler ohne Vorwissen mit einem, der
nach jeder Runde eine Schnittmenge zwischen seinem Spielmodell und den Schemata sucht.
"""

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import mean

from hekmatki.action import ActionRecord
from hekmatki.experiments.schema_learning import TRAINING_LENGTH
from hekmatki.game import (
    ACCIDENT,
    ARRIVED,
    GOAL,
    GREEN,
    ROUND_ENDS,
    TRAFFIC,
    YELLOW,
    TrafficLightGame,
)
from hekmatki.overlap import Overlap, find_overlap
from hekmatki.player import GamePlayer
from hekmatki.schema import Schema, merge_schemas
from hekmatki.situations import Situation, conversation_situations, waiting_situations
from hekmatki.stack import experience

ROUNDS = 30
EARLY_ROUNDS = 10


@dataclass(frozen=True)
class GameRow:
    """Wie gut ein Spieler spielt, gemittelt über alle Zufallsstarts."""

    player: str
    early_win_rate: float
    """Anteil gewonnener Runden in den ersten `EARLY_ROUNDS` Runden."""
    late_win_rate: float
    """Anteil gewonnener Runden danach."""
    accidents: float
    """Unfälle pro Spiel."""
    first_win: float
    """Runde des ersten Siegs."""


@dataclass(frozen=True)
class GameResult:
    """Spielergebnisse plus was der Agent über die Schnittmenge herausgefunden hat."""

    rows: list[GameRow]
    found_during_game: float
    """Anteil der Läufe, in denen der Spieler mit Schemata eine Schnittmenge fand."""
    found_in_round: float
    """Mittlere Runde, nach der er sie fand."""
    found_after_game: float
    """Anteil der Läufe, in denen der Spieler ohne Vorwissen sie nach dem Spiel fand."""
    core_correct: float
    """Anteil aller Funde mit Schema „Warten“ und richtiger Zuordnung von Autos, Gelb, Grün."""
    goal_as_continuation: float
    """Anteil aller Funde, in denen „drüben“ die Rolle „weitergehen“ bekam."""
    learned_action: dict[str, float]
    """Im Schema „Warten“ gelernte Erfolgswahrscheinlichkeit des Handelns pro Rolle."""


def run_traffic_light_game(seeds: int = 20, rounds: int = ROUNDS) -> GameResult:
    """Spielt das Ampelspiel mit und ohne Vorwissen aus den Alltagsschemata."""
    if rounds <= EARLY_ROUNDS:
        raise ValueError(f"Es braucht mehr als {EARLY_ROUNDS} Runden, waren {rounds}.")
    game = TrafficLightGame()
    outcomes: dict[str, list[list[str]]] = {"ohne Vorwissen": [], "mit Schemata": []}
    found_rounds: list[int | None] = []
    found: list[Overlap] = []
    found_after: list[Overlap | None] = []
    roles_by_meaning: list[Mapping[str, str]] = []
    learned_action: dict[str, list[float]] = {}

    for seed in range(seeds):
        schemas, meaning = _everyday_schemas(random.Random(seed))
        for role_meaning, role in meaning.items():
            record = schemas[0].action_knowledge.get(role, ActionRecord())
            learned_action.setdefault(role_meaning, []).append(record.success_probability())
        without = GamePlayer(game.symbols, GOAL)
        with_schemas = GamePlayer(game.symbols, GOAL, schemas)
        outcomes["ohne Vorwissen"].append(_play(without, game, rounds, random.Random(seed))[0])
        played, found_round = _play(with_schemas, game, rounds, random.Random(seed))
        outcomes["mit Schemata"].append(played)
        found_rounds.append(found_round)
        after_game = find_overlap(without.observations, schemas)
        found_after.append(after_game)
        for overlap in (with_schemas.overlap, after_game):
            if overlap is not None:
                found.append(overlap)
                roles_by_meaning.append(meaning)

    rows = [_summarize(name, games) for name, games in outcomes.items()]
    rows.append(GameRow("Optimum", 1.0, 1.0, 0.0, 1.0))
    rounds_found = [r for r in found_rounds if r is not None]
    pairs = list(zip(found, roles_by_meaning, strict=True))
    return GameResult(
        rows=rows,
        found_during_game=len(rounds_found) / seeds,
        found_in_round=mean(rounds_found) if rounds_found else float("nan"),
        found_after_game=sum(o is not None for o in found_after) / seeds,
        core_correct=_share(_core_is_correct(o, m) for o, m in pairs),
        goal_as_continuation=_share(o.binding.get(ARRIVED) == m["weitergehen"] for o, m in pairs),
        learned_action={m: mean(values) for m, values in learned_action.items()},
    )


def _everyday_schemas(rng: random.Random) -> tuple[list[Schema], dict[str, str]]:
    """Alltag erleben und im Schlaf verdichten: „Warten“ und „Gespräch“ mit Handlungswissen.

    Gibt außerdem zurück, welche Rolle von „Warten“ welche Bedeutung hat. Das braucht nur die
    Auswertung; der Agent selbst kennt die Bedeutungen nicht.
    """
    waiting = waiting_situations()
    talks = conversation_situations()
    waiting_part, roles = _schema_with_action_knowledge(
        "Warten", waiting["arzt"], waiting["ubahn"], rng
    )
    talk, _ = _schema_with_action_knowledge("Gespräch", talks["nachbar"], talks["kollege"], rng)
    meaning = {m: roles[symbol] for m, symbol in waiting["arzt"].symbols.items()}
    return [waiting_part, talk], meaning


def _schema_with_action_knowledge(
    name: str, first: Situation, second: Situation, rng: random.Random
) -> tuple[Schema, Mapping[str, str]]:
    """Erlebt zwei Situationen, probiert dabei zu handeln und verschmilzt sie zum Schema.

    Der Agent erfährt nur, ob seine Versuche klappten. Gibt das Schema und die Zuordnung der
    Symbole von `first` zu den Rollen zurück.
    """
    lived = [experience(s.name, s, TRAINING_LENGTH, rng).schema for s in (first, second)]
    merged = merge_schemas(lived[0], lived[1], name)
    if merged.schema is None:
        raise RuntimeError(f"{name}: nicht verschmolzen (Abstand {merged.distance:.3f}).")
    return merged.schema, merged.first_binding


def _play(
    player: GamePlayer, game: TrafficLightGame, rounds: int, rng: random.Random
) -> tuple[list[str], int | None]:
    """Spielt `rounds` Runden. Gibt das Ende jeder Runde zurück und nach welcher Runde der
    Spieler seine Schnittmenge fand (`None`, wenn nie)."""
    state = game.start
    endings: list[str] = []
    found_in_round: int | None = None
    while len(endings) < rounds:
        action = player.choose(state, rng)
        outcome = game.step(state, action, rng)
        player.learn(state, action, outcome)
        if outcome in ROUND_ENDS:
            endings.append(outcome)
            player.reflect()
            if found_in_round is None and player.overlap is not None:
                found_in_round = len(endings)
        state = outcome
    return endings, found_in_round


def _summarize(player: str, games: Sequence[Sequence[str]]) -> GameRow:
    def win_rate(endings: Sequence[str]) -> float:
        return sum(e == GOAL for e in endings) / len(endings)

    return GameRow(
        player=player,
        early_win_rate=mean(win_rate(g[:EARLY_ROUNDS]) for g in games),
        late_win_rate=mean(win_rate(g[EARLY_ROUNDS:]) for g in games),
        accidents=mean(sum(e == ACCIDENT for e in g) for g in games),
        first_win=mean(_first_win(g) for g in games),
    )


def _first_win(endings: Sequence[str]) -> int:
    """Runde des ersten Siegs; ohne Sieg zählt die Runde nach dem Spielende."""
    return next((i + 1 for i, e in enumerate(endings) if e == GOAL), len(endings) + 1)


def _core_is_correct(overlap: Overlap, meaning: Mapping[str, str]) -> bool:
    """Autos = beschäftigen, Gelb = Hinweis, Grün = Ereignis, im Schema „Warten“."""
    expected = {TRAFFIC: "beschäftigen", YELLOW: "hinweis", GREEN: "ereignis"}
    return overlap.schema.name == "Warten" and all(
        overlap.binding.get(symbol) == meaning[role] for symbol, role in expected.items()
    )


def _share(values: Iterable[bool]) -> float:
    """Anteil der wahren Werte; ohne Werte `nan`, damit nichts still als 0 erscheint."""
    items = list(values)
    return sum(items) / len(items) if items else float("nan")
