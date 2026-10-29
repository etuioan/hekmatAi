"""Strukturabbildung nach Gentner: Wie gut passt die Struktur eines Modells auf eine andere?

Das ist das gemeinsame Werkzeug hinter Verschmelzen und Schnittmenge. Verschmelzen ist der
Sonderfall, dass alle Symbole beider Modelle aufeinander passen. Bei einer Schnittmenge
passt die andere Struktur nur in einen Teil des Modells.
"""

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations, permutations

from hekmatki.markov import MarkovModel

MAX_SYMBOLS_FOR_SEARCH = 8


@dataclass(frozen=True)
class StructureMatch:
    """Die beste Zuordnung Symbol → Zustand der anderen Struktur und wie gut sie passt."""

    binding: Mapping[str, str]
    distance: float


def embeddings(symbols: Sequence[str], targets: Sequence[str]) -> Iterator[dict[str, str]]:
    """Alle Zuordnungen, die jedem Ziel genau ein eigenes Symbol geben.

    Bei gleich vielen Symbolen und Zielen sind das alle Umbenennungen. Gibt es weniger
    Symbole als Ziele, gibt es keine Zuordnung.
    """
    if len(symbols) > MAX_SYMBOLS_FOR_SEARCH:
        raise ValueError(
            f"Mehr als {MAX_SYMBOLS_FOR_SEARCH} Symbole sind für die vollständige Suche zu viele."
        )
    for chosen_symbols in combinations(symbols, len(targets)):
        for chosen_targets in permutations(targets):
            yield dict(zip(chosen_symbols, chosen_targets, strict=True))


def mapping_distance(
    model: MarkovModel, reference: MarkovModel, binding: Mapping[str, str]
) -> float:
    """Mittlerer absoluter Unterschied der Übergänge zwischen den zugeordneten Symbolen."""
    if not binding:
        raise ValueError("Die Zuordnung ist leer.")
    differences = [
        abs(model.probability(a, b) - reference.probability(binding[a], binding[b]))
        for a in binding
        for b in binding
    ]
    return sum(differences) / len(differences)


def best_match(
    model: MarkovModel,
    reference: MarkovModel,
    allowed: Callable[[Mapping[str, str]], bool] | None = None,
) -> StructureMatch | None:
    """Die Zuordnung, unter der die Struktur von `reference` am besten in `model` steckt.

    Mit `allowed` zählen nur Zuordnungen, die diese Prüfung bestehen. `None`, wenn es keine
    Zuordnung gibt, etwa weil `model` weniger Symbole hat als `reference`.
    """
    matches = [
        StructureMatch(binding, mapping_distance(model, reference, binding))
        for binding in embeddings(model.alphabet, reference.alphabet)
        if allowed is None or allowed(binding)
    ]
    return min(matches, key=lambda match: match.distance, default=None)
