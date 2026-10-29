"""Gemeinsame Schnittstelle für Vorhersagen und deren Bewertung."""

import math
from collections.abc import Sequence
from itertools import pairwise
from typing import Protocol

ROUNDING_TOLERANCE = 1e-9


class Predictor(Protocol):
    """Alles, was sagen kann, wie wahrscheinlich ein Symbol auf ein anderes folgt."""

    def probability(self, previous: str, following: str) -> float:
        """Wahrscheinlichkeit, dass `following` direkt auf `previous` folgt."""
        ...


def _transitions(sequence: Sequence[str]) -> list[tuple[str, str]]:
    pairs = list(pairwise(sequence))
    if not pairs:
        raise ValueError("Die Folge braucht mindestens zwei Symbole.")
    return pairs


def typical_probability(predictor: Predictor, sequence: Sequence[str]) -> float:
    """Typische Wahrscheinlichkeit, die der Predictor dem tatsächlich folgenden Symbol gibt.

    Berechnet als geometrisches Mittel. Anders als das einfache Mittel belohnt es keine
    übertriebene Sicherheit: Niemand kann im Schnitt besser sein als das wahre Modell.
    1.0 heißt: immer sicher richtig.
    """
    return geometric_mean([predictor.probability(a, b) for a, b in _transitions(sequence)])


def geometric_mean(probabilities: Sequence[float]) -> float:
    """Geometrisches Mittel von Wahrscheinlichkeiten; 0, sobald eine davon 0 ist."""
    if not probabilities:
        raise ValueError("Es braucht mindestens eine Wahrscheinlichkeit.")
    if any(p < 0.0 or p > 1.0 + ROUNDING_TOLERANCE for p in probabilities):
        raise ValueError("Wahrscheinlichkeiten müssen zwischen 0 und 1 liegen.")
    if min(probabilities) == 0.0:
        return 0.0
    return math.exp(sum(math.log(p) for p in probabilities) / len(probabilities))


def log_likelihood(predictor: Predictor, sequence: Sequence[str]) -> float:
    """Natürlicher Logarithmus der Wahrscheinlichkeit der ganzen Folge."""
    total = 0.0
    for previous, following in _transitions(sequence):
        p = predictor.probability(previous, following)
        if p <= 0.0:
            return -math.inf
        total += math.log(p)
    return total
