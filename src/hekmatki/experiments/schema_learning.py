"""Experiment H11 mit Härtetest: Lernt der Agent eine neue Situation schneller mit Schema?"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

from hekmatki.evaluation import typical_probability
from hekmatki.markov import MarkovModel
from hekmatki.schema import (
    Schema,
    adaptive_schema_predictor,
    fixed_schema_predictor,
    merge,
    schema_or_flat_predictor,
)
from hekmatki.situations import Situation, gate_stress_variants, small_talk, waiting_situations

TRAINING_LENGTH = 400
TEST_LENGTH = 500


@dataclass(frozen=True)
class H11Row:
    """Mittlere Trefferwahrscheinlichkeit nach `observations` Beobachtungen der neuen Situation."""

    observations: int
    flat: float
    schema: float
    optimum: float


@dataclass(frozen=True)
class H11Result:
    """Ergebnis von Experiment H11 inklusive der Verschmelzungsabstände zur Kontrolle."""

    rows: list[H11Row]
    waiting_distance: float
    small_talk_distance: float
    small_talk_merged: bool


def trained_model(situation: Situation, length: int, rng: random.Random) -> MarkovModel:
    model = MarkovModel(situation.alphabet)
    model.observe_sequence(situation.sample(length, rng))
    return model


def run_h11(
    seeds: int = 20,
    budgets: Sequence[int] = (5, 10, 20, 40, 80, 160),
) -> H11Result:
    """Lernt die Gate-Situation mit und ohne das Schema „Warten“ und vergleicht."""
    situations = waiting_situations()
    gate = situations["gate"]
    results: dict[int, list[H11Row]] = {n: [] for n in budgets}
    waiting_distances: list[float] = []
    small_talk_distances: list[float] = []
    small_talk_merged = False

    for seed in range(seeds):
        rng = random.Random(seed)
        doctor = trained_model(situations["arzt"], TRAINING_LENGTH, rng)
        schema, distance = waiting_schema(doctor, rng)
        waiting_distances.append(distance)

        control = merge(doctor, trained_model(small_talk(), TRAINING_LENGTH, rng), name="Kontrolle")
        small_talk_distances.append(control.distance)
        small_talk_merged = small_talk_merged or control.schema is not None

        observed = gate.sample(max(budgets), rng)
        test = gate.sample(TEST_LENGTH, rng)
        for n in budgets:
            results[n].append(_compare_on_gate(schema, gate, observed[:n], test))

    rows = [_average(results[n]) for n in budgets]
    return H11Result(rows, mean(waiting_distances), mean(small_talk_distances), small_talk_merged)


def waiting_schema(doctor: MarkovModel, rng: random.Random) -> tuple[Schema, float]:
    """Verschmilzt Arzt und U-Bahn zum Schema „Warten“. Scheitert das, ist der Prototyp kaputt."""
    subway = trained_model(waiting_situations()["ubahn"], TRAINING_LENGTH, rng)
    merged = merge(doctor, subway, name="Warten")
    if merged.schema is None:
        raise RuntimeError(
            f"Arzt und U-Bahn wurden nicht verschmolzen (Abstand {merged.distance:.3f})."
        )
    return merged.schema, merged.distance


def _compare_on_gate(
    schema: Schema, gate: Situation, observed: Sequence[str], test: Sequence[str]
) -> H11Row:
    flat = MarkovModel(gate.alphabet)
    flat.observe_sequence(observed)
    with_schema = fixed_schema_predictor(schema, gate.alphabet, observed)
    return H11Row(
        observations=len(observed),
        flat=typical_probability(flat, test),
        schema=typical_probability(with_schema, test),
        optimum=typical_probability(gate, test),
    )


def _average(rows: Sequence[H11Row]) -> H11Row:
    """Mittelt Zeilen mit gleicher Anzahl Beobachtungen über alle Zufallsstarts."""
    return H11Row(
        observations=rows[0].observations,
        flat=mean(r.flat for r in rows),
        schema=mean(r.schema for r in rows),
        optimum=mean(r.optimum for r in rows),
    )


@dataclass(frozen=True)
class StressRow:
    """Ein Härtetest-Ergebnis: eine Gate-Variante nach `observations` Beobachtungen."""

    variant: str
    observations: int
    flat: float
    fixed_schema: float
    adaptive_schema: float
    checked_schema: float
    optimum: float


def run_h11_stress(seeds: int = 20, budgets: Sequence[int] = (10, 40, 160)) -> list[StressRow]:
    """Härtetest für H11: Gate-Situationen, die vom Schema abweichen oder gestört sind."""
    variants = gate_stress_variants()
    collected: dict[tuple[str, int], list[StressRow]] = {
        (name, n): [] for name in variants for n in budgets
    }
    for seed in range(seeds):
        rng = random.Random(seed)
        doctor = trained_model(waiting_situations()["arzt"], TRAINING_LENGTH, rng)
        schema, _ = waiting_schema(doctor, rng)
        for name, gate in variants.items():
            observed = gate.sample(max(budgets), rng)
            test = gate.sample(TEST_LENGTH, rng)
            for n in budgets:
                collected[(name, n)].append(_stress_row(name, schema, gate, observed[:n], test))
    return [_average_stress(rows) for rows in collected.values()]


def _stress_row(
    variant: str, schema: Schema, gate: Situation, observed: Sequence[str], test: Sequence[str]
) -> StressRow:
    flat = MarkovModel(gate.alphabet)
    flat.observe_sequence(observed)
    fixed = fixed_schema_predictor(schema, gate.alphabet, observed)
    adaptive = adaptive_schema_predictor(schema, gate.alphabet, observed)
    checked = schema_or_flat_predictor(schema, gate.alphabet, observed)
    return StressRow(
        variant=variant,
        observations=len(observed),
        flat=typical_probability(flat, test),
        fixed_schema=typical_probability(fixed, test),
        adaptive_schema=typical_probability(adaptive, test),
        checked_schema=typical_probability(checked, test),
        optimum=typical_probability(gate, test),
    )


def _average_stress(rows: Sequence[StressRow]) -> StressRow:
    """Mittelt Härtetest-Zeilen derselben Variante und Beobachtungszahl."""
    return StressRow(
        variant=rows[0].variant,
        observations=rows[0].observations,
        flat=mean(r.flat for r in rows),
        fixed_schema=mean(r.fixed_schema for r in rows),
        adaptive_schema=mean(r.adaptive_schema for r in rows),
        checked_schema=mean(r.checked_schema for r in rows),
        optimum=mean(r.optimum for r in rows),
    )
