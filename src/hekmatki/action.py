"""Handlungswissen: Wo im Ablauf führt eigenes Handeln zum Ziel?

Der Agent probiert in Alltagssituationen ab und zu, selbst zu handeln (etwa einzusteigen),
und merkt sich pro Zustand, wie oft das klappte. Beim Verschmelzen wandert dieses Wissen
über die Zuordnung Symbol → Rolle ins Schema. So weiß ein Schema am Ende, in welcher Rolle
Handeln gelingt, ohne dass es ihm jemand sagt.
"""

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

DEFAULT_TRY_RATE = 0.1
"""Wie oft der Agent im Alltag ausprobiert, selbst zu handeln."""


@dataclass(frozen=True)
class ActionRecord:
    """Wie oft Handeln in einem Zustand versucht wurde und wie oft es zum Ziel führte."""

    wins: float = 0.0
    tries: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.wins <= self.tries:
            raise ValueError(
                f"Es muss 0 <= Erfolge <= Versuche gelten, war {self.wins} von {self.tries}."
            )

    def success_probability(self) -> float:
        """Geschätzte Erfolgswahrscheinlichkeit; ohne Erfahrung genau 0,5."""
        return (self.wins + 0.5) / (self.tries + 1.0)

    def looks_successful(self) -> bool:
        """Lohnt sich Handeln hier? Ja, wenn Erfolg wahrscheinlicher ist als Misserfolg."""
        return self.success_probability() > 0.5

    def plus(self, other: "ActionRecord") -> "ActionRecord":
        """Beide Erfahrungen zusammen."""
        return ActionRecord(self.wins + other.wins, self.tries + other.tries)

    def after(self, succeeded: bool) -> "ActionRecord":
        """Diese Erfahrung plus ein weiterer Versuch."""
        return ActionRecord(self.wins + (1.0 if succeeded else 0.0), self.tries + 1.0)


ActionKnowledge = Mapping[str, ActionRecord]
"""Handlungswissen pro Symbol oder pro Rolle."""


def try_actions(
    sequence: Sequence[str],
    succeeds_in: Iterable[str],
    rng: random.Random,
    try_rate: float = DEFAULT_TRY_RATE,
) -> dict[str, ActionRecord]:
    """Erlebt eine Folge und probiert in zufälligen Momenten zu handeln.

    `succeeds_in` sind die Symbole, in denen Handeln in dieser Situation gelingt. Das weiß
    nur die Welt; der Agent sieht nur, ob sein Versuch geklappt hat.
    """
    if not 0.0 <= try_rate <= 1.0:
        raise ValueError(f"try_rate muss zwischen 0 und 1 liegen, war {try_rate}.")
    successful = set(succeeds_in)
    records: dict[str, ActionRecord] = {}
    for symbol in sequence:
        if rng.random() < try_rate:
            records[symbol] = records.get(symbol, ActionRecord()).after(symbol in successful)
    return records


def by_role(knowledge: ActionKnowledge, binding: Mapping[str, str]) -> dict[str, ActionRecord]:
    """Übersetzt Handlungswissen pro Symbol in Handlungswissen pro Rolle."""
    unknown = set(knowledge) - set(binding)
    if unknown:
        raise ValueError(f"Handlungswissen für Symbole ohne Rolle: {sorted(unknown)}.")
    return {binding[symbol]: record for symbol, record in knowledge.items()}


def decisions_conflict(first: ActionKnowledge, second: ActionKnowledge) -> bool:
    """Widerspricht sich das Handlungswissen in einem Zustand, den beide ausprobiert haben?

    Ein Widerspruch heißt: Bei dem einen lohnt sich Handeln dort, bei dem anderen nicht.
    Zustände, die eine Seite nie ausprobiert hat, zählen nicht als Widerspruch.
    """
    shared = set(first) & set(second)
    tried_by_both = [k for k in shared if first[k].tries > 0 and second[k].tries > 0]
    return any(first[k].looks_successful() != second[k].looks_successful() for k in tried_by_both)


def combined(*parts: ActionKnowledge) -> dict[str, ActionRecord]:
    """Fasst Handlungswissen aus mehreren Situationen zusammen."""
    result: dict[str, ActionRecord] = {}
    for part in parts:
        for key, record in part.items():
            result[key] = result.get(key, ActionRecord()).plus(record)
    return result
