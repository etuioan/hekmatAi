"""Experiment Neugier: Hilft es, auch nach dem ersten Sieg neugierig zu bleiben?

Dieselbe Spielefamilie wie in `discovery`, einmal mit dem bisherigen Entdecker und einmal
mit einem, der Abstecher ins Unbekannte abwägt (`curiosity.py`). Gespielt wird kurz
(60 Tastendrücke) und lang (200). Dazu ein Regler: Wie sehr vertraut der Agent seinem
Schema? Je weniger, desto eher prüft er auch Tasten, für die das Schema „nichts passiert“
vorhersagt, etwa die Tür ohne Schlüssel.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from hekmatki.curiosity import Curiosity
from hekmatki.experiments.discovery import DiscoveryResult, run_discovery

Agent = Literal["ohne Schema", "mit Schema"]

HORIZONS = (60, 200)
"""Kurzes und langes Spiel, in Tastendrücken."""
LONG_HORIZON = HORIZONS[-1]
SCHEMA_SURPRISES = (0.0125, 0.025, 0.05, 0.1)
"""Wie viel Überraschung der Agent dem Schema zutraut (klein = viel Vertrauen)."""
ORDINARY_GAMES = ("Spiel 2", "Spiel 3", "gespiegelt")
"""Spiele, in denen das Schema stimmt."""
SURPRISING_GAME = "ohne Schlüssel"
"""Das Spiel, in dem das Schema einen Umweg vorschlägt."""


@dataclass(frozen=True)
class HorizonResult:
    """Beide Entdecker, ohne und mit Neugier, bei einer Spieldauer."""

    steps: int
    plain: DiscoveryResult
    curious: DiscoveryResult


@dataclass(frozen=True)
class TrustRow:
    """Was das Vertrauen ins Schema bewirkt (Agent mit Schema, langes Spiel)."""

    schema_surprise: float
    ordinary_wins: float
    """Mittlere Siege in Spielen, in denen das Schema stimmt."""
    surprising_wins: float
    """Siege im Spiel ohne Schlüssel."""


@dataclass(frozen=True)
class ExplorationResult:
    """Vergleich nach Spieldauer plus Regler für das Vertrauen ins Schema."""

    horizons: list[HorizonResult]
    trust: list[TrustRow]


def run_exploration(
    seeds: int = 20,
    horizons: Sequence[int] = HORIZONS,
    schema_surprises: Sequence[float] = SCHEMA_SURPRISES,
) -> ExplorationResult:
    """Spielt die Familie ohne und mit Neugier und variiert das Vertrauen ins Schema."""
    results = [
        HorizonResult(
            steps,
            run_discovery(seeds, steps),
            run_discovery(seeds, steps, Curiosity()),
        )
        for steps in horizons
    ]
    trust = [_trust_row(s, seeds) for s in schema_surprises]
    return ExplorationResult(results, trust)


def total_wins(result: DiscoveryResult, agent: Agent) -> float:
    """Summe der Siege in allen Spielen nach dem ersten."""
    later = result.rows[1:]
    return sum(row.fresh_wins if agent == "ohne Schema" else row.schema_wins for row in later)


def _trust_row(schema_surprise: float, seeds: int) -> TrustRow:
    curiosity = Curiosity(schema_surprise=schema_surprise)
    rows = {row.game: row for row in run_discovery(seeds, LONG_HORIZON, curiosity).rows}
    return TrustRow(
        schema_surprise=schema_surprise,
        ordinary_wins=mean(rows[name].schema_wins for name in ORDINARY_GAMES),
        surprising_wins=rows[SURPRISING_GAME].schema_wins,
    )
