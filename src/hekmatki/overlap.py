"""Schnittmenge: Steckt die Struktur eines Schemas in einem Teil eines größeren Modells?

Anders als beim Verschmelzen müssen nicht alle Symbole des Modells passen. Gesucht wird eine
Teilmenge von Symbolen, deren Übergänge untereinander zu allen Rollen eines Schemas passen.
Modell und Schema bleiben dabei getrennt; gespeichert wird nur die Zuordnung, wie eine
Analogie. Die Suche selbst ist dieselbe wie beim Verschmelzen (`structure.best_match`).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from hekmatki.markov import MarkovModel
from hekmatki.schema import DEFAULT_MERGE_THRESHOLD, Schema
from hekmatki.structure import best_match


@dataclass(frozen=True)
class Overlap:
    """Eine gefundene Schnittmenge zwischen einem Modell und einem Schema."""

    schema: Schema
    binding: Mapping[str, str]
    """Symbol des Modells → Rolle des Schemas, nur für den gemeinsamen Teil."""
    distance: float


def find_overlap(
    model: MarkovModel, schemas: Sequence[Schema], threshold: float = DEFAULT_MERGE_THRESHOLD
) -> Overlap | None:
    """Sucht das Schema, dessen Struktur am besten in einem Teil des Modells steckt.

    Die strukturell nächste Zuordnung über alle Schemata gewinnt, wenn sie nah genug ist.
    Sonst gibt es keine Schnittmenge: `None`.
    """
    candidates = [
        Overlap(schema, match.binding, match.distance)
        for schema in schemas
        if (match := best_match(model, schema.model)) is not None
    ]
    best = min(candidates, key=lambda candidate: candidate.distance, default=None)
    return best if best is not None and best.distance <= threshold else None
