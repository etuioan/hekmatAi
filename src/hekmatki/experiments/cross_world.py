"""Spielwelt gegen Alltagswelt (ab 0.15): Gilt dieselbe Lehre über Vorwissen in beiden?

Ziel ist eine allgemeine Intelligenz, nicht eine KI für Spiele. Eine Lehre aus der Spielwelt
zählt deshalb erst, wenn sie auch in einer ganz anderen Welt gilt. Beide Welten haben hier
Vorwissen, das nicht passt:
- Alltagswelt (Scheiben): Das Schema „Warten“ aus Arzt und U-Bahn trifft auf ein Gate mit
  Verspätung, sofortigem Boarding oder Störungen (Härtetest aus Ergebnis 2, `schema_learning`).
- Spielwelt: Das Modell aus Spiel A trifft auf Level, die aussehen wie A, aber andere Regeln
  haben (`grid_foreign`).

In beiden Welten gibt es dieselben drei Arten, mit Vorwissen umzugehen:
- „übernehmen“: unverändert nutzen (Alltag: starr; Spiel: Modell aus A)
- „als Ganzes prüfen“: erst prüfen, ob es insgesamt passt (geprüft; Modell + Prüfung)
- „Teile korrigieren“: jeden Teil durch eigene Beobachtung korrigieren (lernend;
  Modell + Teilprüfung)

Schaden heißt: um wie viel Prozent schlechter als ohne Vorwissen. In der Alltagswelt an der
Vorhersage (typische Wahrscheinlichkeit, gemittelt über alle Beobachtungszahlen), in der
Spielwelt an den Tastendrücken bis zum ersten Sieg. Negativ heißt: Vorwissen hilft.

Grenze: Die beiden Welten nutzen verschiedenen Code. Gleich ist das Prinzip, nicht der
Mechanismus. Ob ein gemeinsamer Mechanismus beides kann, ist offen.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from hekmatki.experiments.grid_foreign import BASELINE, ForeignRow
from hekmatki.experiments.grid_foreign import Learner as GameLearner
from hekmatki.experiments.schema_learning import StressRow

Handling = Literal["übernehmen", "als Ganzes prüfen", "Teile korrigieren"]
HANDLINGS: tuple[Handling, ...] = ("übernehmen", "als Ganzes prüfen", "Teile korrigieren")
GAME_LEARNERS: dict[Handling, GameLearner] = {
    "übernehmen": "Modell aus A",
    "als Ganzes prüfen": "Modell + Prüfung",
    "Teile korrigieren": "Modell + Teilprüfung",
}
"""Welcher Agent der Spielwelt welche Art vertritt."""


@dataclass(frozen=True)
class CrossRow:
    """Eine Lage in einer der beiden Welten: Schaden durch Vorwissen je Umgangsart."""

    world: Literal["Alltag", "Spiel"]
    situation: str
    harm: dict[Handling, float]
    """Prozent schlechter als ohne Vorwissen (negativ: besser)."""


def compare_worlds(stress: Sequence[StressRow], foreign: Sequence[ForeignRow]) -> list[CrossRow]:
    """Stellt Härtetest (Alltag) und Gegenprobe (Spiel) im selben Maß nebeneinander."""
    if not stress or not foreign:
        raise ValueError("Für den Vergleich braucht es Zeilen aus beiden Welten.")
    variants = dict.fromkeys(row.variant for row in stress)
    everyday = [_everyday_row(v, [r for r in stress if r.variant == v]) for v in variants]
    return everyday + [_game_row(row) for row in foreign]


def _everyday_row(variant: str, rows: Sequence[StressRow]) -> CrossRow:
    def loss(value_of: Callable[[StressRow], float]) -> float:
        return mean(100 * (r.flat - value_of(r)) / r.flat for r in rows)

    harm: dict[Handling, float] = {
        "übernehmen": loss(lambda r: r.fixed_schema),
        "als Ganzes prüfen": loss(lambda r: r.checked_schema),
        "Teile korrigieren": loss(lambda r: r.adaptive_schema),
    }
    return CrossRow("Alltag", variant, harm)


def _game_row(row: ForeignRow) -> CrossRow:
    def extra(learner: GameLearner) -> float:
        without = row.first_win[BASELINE[learner]]
        return 100 * (row.first_win[learner] - without) / without

    return CrossRow("Spiel", row.level, {h: extra(GAME_LEARNERS[h]) for h in HANDLINGS})
