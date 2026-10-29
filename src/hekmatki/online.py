"""Lerner, die einen Beobachtungsstrom Schritt für Schritt vorhersagen und daraus lernen."""

from collections.abc import Iterable
from typing import Protocol

from hekmatki.markov import DEFAULT_PSEUDOCOUNT, MarkovModel


class LearningPredictor(Protocol):
    """Ein Modell, das vorhersagen und aus einzelnen Übergängen lernen kann."""

    def probability(self, previous: str, following: str) -> float:
        """Wahrscheinlichkeit, dass `following` direkt auf `previous` folgt."""
        ...

    def observe(self, previous: str, following: str) -> None:
        """Lernt einen beobachteten Übergang."""
        ...


class OnlineLearner(Protocol):
    """Sagt erst vorher, lernt dann. So wird nie mit bereits gesehenen Daten geprüft."""

    def step(self, previous: str, following: str) -> float:
        """Gibt die vorhergesagte Wahrscheinlichkeit für `following` zurück und lernt danach."""
        ...


class SingleModelLearner:
    """Vergleichsagent ohne Kontexte: Alles landet in einem einzigen gemeinsamen Modell."""

    def __init__(self, alphabet: Iterable[str], pseudocount: float = DEFAULT_PSEUDOCOUNT) -> None:
        self.model = MarkovModel(alphabet, pseudocount)

    def step(self, previous: str, following: str) -> float:
        """Vorhersage mit dem gemeinsamen Modell, danach Lernen im gemeinsamen Modell."""
        predicted = self.model.probability(previous, following)
        self.model.observe(previous, following)
        return predicted
