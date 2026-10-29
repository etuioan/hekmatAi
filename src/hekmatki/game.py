"""Das Ampelspiel: warten oder laufen. Nur wer im richtigen Moment läuft, kommt sicher drüben an.

Solange der Agent wartet, läuft das Spiel ab wie eine Wartesituation: Autos fahren eine
Weile, dann wird die Ampel gelb, dann grün. Läuft der Agent bei Grün, gewinnt er. Läuft er
zu früh, gibt es einen Unfall. Wartet er bei Grün, ist die Chance verpasst. Danach beginnt
eine neue Runde.
"""

import random
from dataclasses import dataclass
from enum import StrEnum


class Action(StrEnum):
    """Was der Agent in jedem Schritt tun kann."""

    WAIT = "warten"
    RUN = "laufen"


TRAFFIC = "autos fahren"
YELLOW = "ampel gelb"
GREEN = "ampel grün"
ARRIVED = "drüben"
MISSED = "verpasst"
ACCIDENT = "unfall"

GOAL = ARRIVED
ROUND_ENDS = frozenset({ARRIVED, MISSED, ACCIDENT})


@dataclass(frozen=True)
class TrafficLightGame:
    """Die Spielregeln. `traffic_stay` sagt, wie lange die Autos typischerweise fahren."""

    traffic_stay: float = 0.8
    yellow_stay: float = 0.2

    def __post_init__(self) -> None:
        for name, value in (("traffic_stay", self.traffic_stay), ("yellow_stay", self.yellow_stay)):
            if not 0.0 <= value < 1.0:
                raise ValueError(f"{name} muss in [0, 1) liegen, war {value}.")

    @property
    def symbols(self) -> tuple[str, ...]:
        """Alles, was der Agent im Spiel sehen kann, sortiert."""
        return tuple(sorted((TRAFFIC, YELLOW, GREEN, *ROUND_ENDS)))

    @property
    def start(self) -> str:
        """Jede Runde beginnt mit fahrenden Autos."""
        return TRAFFIC

    def step(self, state: str, action: Action, rng: random.Random) -> str:
        """Der nächste Zustand, wenn der Agent in `state` die Aktion `action` wählt."""
        if state not in self.symbols:
            raise ValueError(f"Unbekannter Spielzustand {state!r}.")
        if state in ROUND_ENDS:
            return self.start
        if action is Action.RUN:
            return ARRIVED if state == GREEN else ACCIDENT
        if state == TRAFFIC:
            return TRAFFIC if rng.random() < self.traffic_stay else YELLOW
        if state == YELLOW:
            return YELLOW if rng.random() < self.yellow_stay else GREEN
        return MISSED
