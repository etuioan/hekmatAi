"""Experiment Meta-Schema und H13: Was bringt eine dritte Ebene, und wann verschmelzen?

Der Agent erlebt sechs Alltagssituationen aus drei Familien: Warten (Arzt, U-Bahn),
Anstehen (Bäcker, Post) und Gespräch (Nachbar, Kollegin). Dabei probiert er ab und zu zu
handeln. Im Schlaf verdichtet er sie mit derselben Routine zweimal: zu Schemata (Ebene 2,
Schwellenwert 0,1) und zu Meta-Schemata (Ebene 3, Schwellenwert 0,2).

Gemessen wird:
- ob die Ebenen die erwarteten Gruppen bilden, mit und ohne Prüfung des Handlungswissens,
- ob der Agent in neuen Situationen (Gate, Kantine) mit dem geliehenen Handlungswissen
  genau im richtigen Moment handeln würde,
- H13: wie das alles davon abhängt, wie viel er vor dem Verschmelzen erlebt hat.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean

from hekmatki.experiments.schema_learning import TRAINING_LENGTH
from hekmatki.markov import MarkovModel
from hekmatki.schema import DEFAULT_MERGE_THRESHOLD, Schema
from hekmatki.situations import (
    Situation,
    conversation_situations,
    queue_situations,
    waiting_situations,
)
from hekmatki.stack import Group, consolidate, experience
from hekmatki.structure import best_match

META_THRESHOLD = 0.2
"""Schwellenwert für Ebene 3: doppelt so großzügig wie für Ebene 2 (von Hand gewählt)."""
DECISION_OBSERVATIONS = 30
"""So viele Schritte sieht der Agent von einer neuen Situation, bevor er entscheidet."""
EXPERIENCE_LENGTHS = (15, 30, 50, 100, TRAINING_LENGTH)
"""Wie viele Schritte jeder Situation der Agent vor dem Schlaf erlebt (H13)."""

FAMILIES = {
    "arzt": "Warten",
    "ubahn": "Warten",
    "bäcker": "Anstehen",
    "post": "Anstehen",
    "nachbar": "Gespräch",
    "kollege": "Gespräch",
}
EXPECTED_SCHEMAS = [{"arzt", "ubahn"}, {"bäcker", "post"}, {"nachbar", "kollege"}]
EXPECTED_META_SCHEMAS = [{"arzt", "ubahn", "bäcker", "post"}, {"nachbar", "kollege"}]
LAYERS = ("Ebene 2", "Ebene 3", "Ebene 3 ohne Prüfung")


@dataclass(frozen=True)
class MetaRow:
    """Ergebnis für eine Menge an Erfahrung vor dem Schlaf, gemittelt über alle Läufe."""

    experience: int
    """Erlebte Schritte pro Situation vor dem Verschmelzen."""
    schemas_as_expected: float
    """Anteil der Läufe, in denen Ebene 2 genau die drei Familien bildet."""
    families_mixed: float
    """Anteil der Läufe, in denen ein Schema der Ebene 2 Familien vermischt."""
    meta_as_expected: float
    """Anteil der Läufe, in denen Ebene 3 Warten und Anstehen vereint, Gespräch aber nicht."""
    unchecked_all_in_one: float
    """Ohne Prüfung des Handlungswissens: Anteil der Läufe, in denen alles in eine Scheibe fällt."""
    slices: dict[str, float]
    """Mittlere Zahl der Scheiben pro Ebene."""
    right_decisions: dict[str, dict[str, float]]
    """Pro Ebene und neuer Situation: Anteil der Läufe, in denen der Agent genau im
    richtigen Moment handeln würde."""


def run_meta_schema(seeds: int = 20, lengths: Sequence[int] = EXPERIENCE_LENGTHS) -> list[MetaRow]:
    """Baut den Stapel nach unterschiedlich viel Erfahrung und prüft ihn."""
    return [_run_for_length(length, seeds) for length in lengths]


def everyday_situations() -> dict[str, Situation]:
    """Die sechs erlebten Situationen in der Reihenfolge von `FAMILIES`."""
    known = {**waiting_situations(), **queue_situations(), **conversation_situations()}
    return {name: known[name] for name in FAMILIES}


def new_situations() -> dict[str, Situation]:
    """Neue Situationen aus bekannten Familien, in denen der Agent entscheiden muss."""
    return {"Gate": waiting_situations()["gate"], "Kantine": queue_situations()["kantine"]}


def build_stack(length: int, rng: random.Random) -> dict[str, list[Group]]:
    """Erlebt jede Alltagssituation `length` Schritte lang und verdichtet zweimal."""
    lived = [experience(n, s, length, rng) for n, s in everyday_situations().items()]
    schemas = consolidate(lived, DEFAULT_MERGE_THRESHOLD, "Schema")
    return {
        "Ebene 2": schemas,
        "Ebene 3": consolidate(schemas, META_THRESHOLD, "Meta-Schema"),
        "Ebene 3 ohne Prüfung": consolidate(
            schemas, META_THRESHOLD, "Meta-Schema", check_decisions=False
        ),
    }


def acts_at(schemas: Sequence[Schema], model: MarkovModel) -> set[str]:
    """Wo würde der Agent in einer neuen Situation handeln?

    Er sucht die Scheibe, deren Struktur am besten passt, und leiht sich ihr Handlungswissen:
    Gehandelt wird in jedem Zustand, dessen Rolle dort erfolgreich war.
    """
    matches = [(best_match(model, s.model), s) for s in schemas]
    found = [(m, s) for m, s in matches if m is not None]
    if not found:
        raise ValueError("Keine Scheibe passt zur Zahl der Symbole der neuen Situation.")
    match, schema = min(found, key=lambda pair: pair[0].distance)
    knowledge = schema.action_knowledge
    return {
        symbol
        for symbol, role in match.binding.items()
        if role in knowledge and knowledge[role].looks_successful()
    }


def _run_for_length(length: int, seeds: int) -> MetaRow:
    as_expected: list[bool] = []
    mixed: list[bool] = []
    meta_expected: list[bool] = []
    all_in_one: list[bool] = []
    slices: dict[str, list[int]] = {layer: [] for layer in LAYERS}
    right: dict[str, dict[str, list[bool]]] = {
        layer: {name: [] for name in new_situations()} for layer in LAYERS
    }
    for seed in range(seeds):
        rng = random.Random(seed)
        stack = build_stack(length, rng)
        as_expected.append(_groups_are(stack["Ebene 2"], EXPECTED_SCHEMAS))
        mixed.append(any(len(_families(g)) > 1 for g in stack["Ebene 2"]))
        meta_expected.append(_groups_are(stack["Ebene 3"], EXPECTED_META_SCHEMAS))
        all_in_one.append(len(stack["Ebene 3 ohne Prüfung"]) == 1)
        for name, situation in new_situations().items():
            model = MarkovModel(situation.alphabet)
            model.observe_sequence(situation.sample(DECISION_OBSERVATIONS, rng))
            for layer, groups in stack.items():
                chosen = acts_at([g.schema for g in groups], model)
                right[layer][name].append(chosen == set(situation.action_symbols))
        for layer, groups in stack.items():
            slices[layer].append(len(groups))
    return MetaRow(
        experience=length,
        schemas_as_expected=mean(as_expected),
        families_mixed=mean(mixed),
        meta_as_expected=mean(meta_expected),
        unchecked_all_in_one=mean(all_in_one),
        slices={layer: mean(counts) for layer, counts in slices.items()},
        right_decisions={
            layer: {name: mean(values) for name, values in per_situation.items()}
            for layer, per_situation in right.items()
        },
    )


def _families(group: Group) -> set[str]:
    return {FAMILIES[member] for member in group.members}


def _groups_are(groups: Sequence[Group], expected: Sequence[set[str]]) -> bool:
    found = sorted(sorted(g.members) for g in groups)
    return found == sorted(sorted(e) for e in expected)
