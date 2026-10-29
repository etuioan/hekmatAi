"""Kontexterkennung: Ordnet der Agent jeden Übergang der richtigen Situation zu?

Der Agent kennt die wahren Situationen nicht. Darum wird jeder Situation höchstens ein
Kontext zugeordnet und umgekehrt, gierig nach Häufigkeit. Richtig ist ein Übergang, wenn er
im Kontext landet, der seiner Situation zugeordnet ist. Ein Kontext für zwei Situationen
zählt so nur für eine davon, und zerlegte Situationen zählen nur mit ihrem größten Teil.
"""

import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean

from hekmatki.context import ContextInference
from hekmatki.experiments.blocks import block_stream, transitions
from hekmatki.experiments.sleep import MULTI_SCHEMA_ORDER, TEST_ORDER, TRAINING_ORDER
from hekmatki.situations import (
    Situation,
    commuting_situations,
    lamp_conversations,
    lamp_situations,
)


@dataclass(frozen=True)
class RecognitionRow:
    """Wie gut der Agent die Situationen einer Welt auseinanderhält."""

    world: str
    situations: int
    contexts_found: float
    correct_share: float


def run_recognition(seeds: int = 20, block_length: int = 150) -> list[RecognitionRow]:
    """Misst die Kontexterkennung in drei Welten, von leicht bis schwer."""
    lamps = lamp_situations()
    worlds: dict[str, tuple[Mapping[str, Situation], Sequence[str]]] = {
        "Pendeln (H12)": (commuting_situations(), ("hinweg", "rueckweg") * 4),
        "Lampen: Warten": (lamps, (*TRAINING_ORDER, *TEST_ORDER)),
        "Lampen: Warten + Gespräche": ({**lamps, **lamp_conversations()}, MULTI_SCHEMA_ORDER),
    }
    return [
        _measure(name, situations, order, seeds, block_length)
        for name, (situations, order) in worlds.items()
    ]


def _measure(
    world: str,
    situations: Mapping[str, Situation],
    order: Sequence[str],
    seeds: int,
    block_length: int,
) -> RecognitionRow:
    shares: list[float] = []
    found: list[int] = []
    for seed in range(seeds):
        stream = block_stream([situations[n] for n in order], block_length, random.Random(seed))
        agent = ContextInference(situations[order[0]].alphabet)
        assigned: list[tuple[str, int]] = []
        for block, _, previous, following in transitions(stream):
            agent.step(previous, following)
            if agent.active is None:
                raise RuntimeError("Nach einem Schritt muss ein Kontext aktiv sein.")
            assigned.append((order[block], agent.active))
        shares.append(correct_share(assigned))
        found.append(len(agent.contexts))
    return RecognitionRow(world, len(set(order)), mean(found), mean(shares))


def correct_share(assigned: Sequence[tuple[str, int]]) -> float:
    """Anteil der Übergänge (Situation, Kontext), die im zugeordneten Kontext landen."""
    if not assigned:
        raise ValueError("Es wurden keine Übergänge zugeordnet.")
    counts = Counter(assigned)
    taken_situations: set[str] = set()
    taken_contexts: set[int] = set()
    correct = 0
    for (situation, context), n in counts.most_common():
        if situation in taken_situations or context in taken_contexts:
            continue
        taken_situations.add(situation)
        taken_contexts.add(context)
        correct += n
    return correct / len(assigned)
