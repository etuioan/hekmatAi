"""Ratgeber: Vorwissen, das dem Entdecker in einem neuen Spiel Tasten empfiehlt.

Ein Ratgeber hält mehrere Deutungen des neuen Spiels bereit, streicht die widerlegten und
empfiehlt die Taste, für die die meisten noch möglichen Deutungen stimmen. Es gibt zwei
Arten: Spiel-Schemata über Zustände (`game_schema.SchemaAdvisor`) und Regel-Schemata
(`rules.RuleAdvisor`).
"""

import random
from collections import Counter
from collections.abc import Iterable
from typing import Protocol


class Advisor(Protocol):
    """Was der Entdecker von seinem Vorwissen braucht."""

    def advice(self, state: str, rng: random.Random) -> str | None:
        """Die empfohlene Taste, oder `None`, wenn das Vorwissen hier nichts sagt."""
        ...

    def learn(self, state: str, button: str, outcome: str) -> None:
        """Streicht Deutungen, die der Beobachtung widersprechen."""
        ...

    def predicts(self, state: str, button: str) -> bool:
        """True, wenn das Vorwissen sicher sagt, was diese Taste hier bewirkt."""
        ...

    def fits(self) -> bool:
        """True, solange noch mindestens eine Deutung möglich ist."""
        ...


def majority(votes: Iterable[str], rng: random.Random) -> str | None:
    """Die häufigste Stimme; bei Gleichstand entscheidet der Zufall. `None` ohne Stimmen."""
    counts = Counter(votes)
    if not counts:
        return None
    most = max(counts.values())
    return rng.choice(sorted(vote for vote, n in counts.items() if n == most))
