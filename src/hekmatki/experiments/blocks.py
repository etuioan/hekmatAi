"""Gemeinsame Werkzeuge für Experimente mit Blöcken: Ströme erzeugen, Lerner laufen lassen,
erste Schritte jedes Blocks messen und nach Etiketten sammeln."""

import random
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field

from hekmatki.evaluation import geometric_mean
from hekmatki.online import OnlineLearner
from hekmatki.situations import Situation

KNOWN = "bekannt"
"""Etikett für Blöcke, in denen der Agent in eine schon erlebte Situation zurückkehrt."""


@dataclass
class Scores:
    """Sammelt die Werte eines Agenten über alle Zufallsstarts, getrennt nach Blocketikett."""

    by_label: dict[str, list[float]] = field(default_factory=dict)

    def add(self, per_block: Sequence[Sequence[float]], labels: Sequence[str | None]) -> None:
        """Ordnet die Werte jedes Blocks seinem Etikett zu. Blöcke ohne Etikett zählen nicht."""
        for block_scores, label in zip(per_block, labels, strict=True):
            if label is not None:
                self.by_label.setdefault(label, []).extend(block_scores)

    def typical(self, label: str) -> float:
        """Typische Trefferwahrscheinlichkeit aller Blöcke mit diesem Etikett."""
        return geometric_mean(self.by_label[label])


def block_labels(
    order: Sequence[str], measured: Iterable[str], already_seen: Iterable[str] = ()
) -> list[str | None]:
    """Ein Etikett pro Block.

    Beim ersten Auftauchen einer gemessenen Situation: ihr Name. Bei jeder Rückkehr in eine
    schon erlebte Situation: `KNOWN`. Sonst `None`, dieser Block wird nicht gemessen.
    """
    measured_names = set(measured)
    seen = set(already_seen)
    labels: list[str | None] = []
    for name in order:
        if name in seen:
            labels.append(KNOWN)
        elif name in measured_names:
            labels.append(name)
        else:
            labels.append(None)
        seen.add(name)
    return labels


def block_stream(
    situations: Sequence[Situation],
    block_length: int,
    rng: random.Random,
    start: str | None = None,
) -> list[list[str]]:
    """Ein Block pro Situation. Jeder Block setzt am letzten Symbol des vorherigen an,
    damit beim Wechsel kein Übergang entsteht, den es in keiner Situation gibt."""
    stream: list[list[str]] = []
    previous = start
    for situation in situations:
        if previous is None:
            block = situation.sample(block_length, rng)
        else:
            block = situation.sample(block_length + 1, rng, start=previous)[1:]
        stream.append(block)
        previous = block[-1]
    return stream


def transitions(
    stream: Sequence[Sequence[str]], previous: str | None = None
) -> Iterator[tuple[int, int, str, str]]:
    """Alle Übergänge des Stroms als (Block, Position im Block, vorher, nachher).

    Position 0 ist der Übergang vom letzten Symbol des vorherigen Blocks in den neuen Block.
    """
    for block_index, block in enumerate(stream):
        for position, symbol in enumerate(block):
            if previous is not None:
                yield block_index, position, previous, symbol
            previous = symbol


def _in_window(position: int, window: int) -> bool:
    return 0 < position <= window


def first_steps(
    learner: OnlineLearner,
    stream: Sequence[Sequence[str]],
    window: int,
    previous: str | None = None,
) -> list[list[float]]:
    """Lässt den Lerner den ganzen Strom sehen. Gibt pro Block die Vorhersagen für die
    ersten `window` Übergänge innerhalb des Blocks zurück."""
    per_block: list[list[float]] = [[] for _ in stream]
    for block, position, before, after in transitions(stream, previous):
        predicted = learner.step(before, after)
        if _in_window(position, window):
            per_block[block].append(predicted)
    return per_block


def true_first_steps(
    situations: Sequence[Situation],
    stream: Sequence[Sequence[str]],
    window: int,
    previous: str | None = None,
) -> list[list[float]]:
    """Wie `first_steps`, aber mit den wahren Wahrscheinlichkeiten der Simulation."""
    if len(situations) != len(stream):
        raise ValueError("Für jeden Block wird genau eine Situation gebraucht.")
    per_block: list[list[float]] = [[] for _ in stream]
    for block, position, before, after in transitions(stream, previous):
        if _in_window(position, window):
            per_block[block].append(situations[block].probability(before, after))
    return per_block


def flatten(blocks: Sequence[Sequence[float]]) -> list[float]:
    return [value for block in blocks for value in block]
