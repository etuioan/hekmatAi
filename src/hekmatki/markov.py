"""Ein Markov-Modell erster Ordnung: die kleinste Form eines Situationsmodells."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from itertools import pairwise

DEFAULT_PSEUDOCOUNT = 0.1


class MarkovModel:
    """Zählt Übergänge zwischen Symbolen eines festen Alphabets und sagt das nächste voraus.

    Der Pseudozähler glättet die Schätzung, sodass kein Übergang die Wahrscheinlichkeit 0 bekommt.
    """

    def __init__(self, alphabet: Iterable[str], pseudocount: float = DEFAULT_PSEUDOCOUNT) -> None:
        symbols = tuple(sorted(set(alphabet)))
        if not symbols:
            raise ValueError("Das Alphabet darf nicht leer sein.")
        if pseudocount <= 0.0:
            raise ValueError(f"Der Pseudozähler muss positiv sein, war {pseudocount}.")
        self.alphabet: tuple[str, ...] = symbols
        self.pseudocount = pseudocount
        self._counts: dict[str, dict[str, float]] = {
            s: dict.fromkeys(symbols, 0.0) for s in symbols
        }

    def observe(self, previous: str, following: str, weight: float = 1.0) -> None:
        """Zählt einen beobachteten Übergang."""
        self._require_known(previous)
        self._require_known(following)
        if weight < 0.0:
            raise ValueError(f"Gewichte dürfen nicht negativ sein, war {weight}.")
        self._counts[previous][following] += weight

    def observe_sequence(self, sequence: Sequence[str]) -> None:
        """Zählt alle Übergänge einer Folge."""
        for previous, following in pairwise(sequence):
            self.observe(previous, following)

    def count(self, previous: str, following: str) -> float:
        """Wie oft der Übergang bisher gezählt wurde."""
        self._require_known(previous)
        self._require_known(following)
        return self._counts[previous][following]

    def total_count(self) -> float:
        """Wie viele Übergänge insgesamt gezählt wurden."""
        return sum(sum(row.values()) for row in self._counts.values())

    def probability(self, previous: str, following: str) -> float:
        """Geglättete Wahrscheinlichkeit, dass `following` auf `previous` folgt."""
        self._require_known(previous)
        self._require_known(following)
        row = self._counts[previous]
        total = sum(row.values()) + self.pseudocount * len(self.alphabet)
        return (row[following] + self.pseudocount) / total

    def matrix(self) -> list[list[float]]:
        """Übergangswahrscheinlichkeiten als Matrix, Zeilen und Spalten in Alphabet-Reihenfolge."""
        return [[self.probability(a, b) for b in self.alphabet] for a in self.alphabet]

    def relabeled(self, mapping: Mapping[str, str]) -> MarkovModel:
        """Kopie, in der jedes Symbol nach `mapping` umbenannt ist (z. B. Symbol → Rolle)."""
        if set(mapping) != set(self.alphabet):
            raise ValueError(
                f"Die Umbenennung muss genau das Alphabet abdecken: {self.alphabet}, "
                f"erhalten: {tuple(sorted(mapping))}."
            )
        if len(set(mapping.values())) != len(mapping):
            raise ValueError("Die Umbenennung muss eindeutig sein (keine doppelten Zielnamen).")
        result = MarkovModel(mapping.values(), self.pseudocount)
        for a in self.alphabet:
            for b in self.alphabet:
                result.observe(mapping[a], mapping[b], self._counts[a][b])
        return result

    def merged_with(self, other: MarkovModel) -> MarkovModel:
        """Neues Modell, dessen Zählungen die Summe beider Modelle sind."""
        if other.alphabet != self.alphabet:
            raise ValueError(
                f"Nur Modelle mit gleichem Alphabet lassen sich zusammenführen: "
                f"{self.alphabet} gegen {other.alphabet}."
            )
        result = MarkovModel(self.alphabet, self.pseudocount)
        for a in self.alphabet:
            for b in self.alphabet:
                result.observe(a, b, self._counts[a][b] + other._counts[a][b])
        return result

    def _require_known(self, symbol: str) -> None:
        if symbol not in self._counts:
            raise ValueError(f"Unbekanntes Symbol {symbol!r}. Erlaubt sind: {self.alphabet}.")
