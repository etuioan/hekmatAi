"""Schema-Stapel: Aus erlebten Situationen werden Schemata, aus Schemata Meta-Schemata.

Jede Ebene entsteht mit derselben Routine (`consolidate`), wie im Schlaf: Das ähnlichste
Paar einer Ebene verschmilzt, solange eines nah genug ist und sich das Handlungswissen nicht
widerspricht. Nach oben wird der Schwellenwert großzügiger, die Scheiben werden allgemeiner.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import combinations

from hekmatki.action import DEFAULT_TRY_RATE, try_actions
from hekmatki.markov import MarkovModel
from hekmatki.schema import Schema, merge_schemas
from hekmatki.situations import Situation


@dataclass(frozen=True)
class Group:
    """Eine Scheibe und aus welchen erlebten Situationen sie entstanden ist."""

    schema: Schema
    members: tuple[str, ...]

    @property
    def is_merged(self) -> bool:
        """True, wenn die Scheibe aus mehr als einer Situation verdichtet wurde."""
        return len(self.members) > 1


def experience(
    name: str,
    situation: Situation,
    length: int,
    rng: random.Random,
    try_rate: float = DEFAULT_TRY_RATE,
) -> Group:
    """Erlebt eine Situation: Übergänge zählen und ab und zu selbst handeln.

    Ergebnis ist die unterste Scheibe des Stapels. Ihre Rollen sind noch die Symbole selbst.
    """
    sequence = situation.sample(length, rng)
    model = MarkovModel(situation.alphabet)
    model.observe_sequence(sequence)
    knowledge = try_actions(sequence, situation.action_symbols, rng, try_rate)
    return Group(Schema(name, model, knowledge), (name,))


def consolidate(
    groups: Sequence[Group],
    threshold: float,
    prefix: str,
    check_decisions: bool = True,
) -> list[Group]:
    """Verdichtet eine Ebene zur nächsten: Das ähnlichste passende Paar verschmilzt, immer
    wieder, bis keines mehr nah genug ist.

    Was zu nichts passt, bleibt als eigene Scheibe erhalten. Verschmolzene Scheiben heißen
    `prefix` plus Nummer, etwa „Schema 1“ oder „Meta-Schema 1“.
    """
    current = list(groups)
    while (closest := _closest_pair(current, threshold, check_decisions)) is not None:
        first, second, schema = closest
        current = [g for g in current if g is not first and g is not second]
        current.append(Group(schema, first.members + second.members))
    return _numbered(current, prefix)


def _closest_pair(
    groups: Sequence[Group], threshold: float, check_decisions: bool
) -> tuple[Group, Group, Schema] | None:
    """Das Paar mit dem kleinsten Abstand, das verschmelzen darf, samt neuem Schema."""
    best: tuple[float, Group, Group, Schema] | None = None
    for first, second in combinations(groups, 2):
        result = merge_schemas(
            first.schema, second.schema, "neu", threshold, check_decisions=check_decisions
        )
        if result.schema is not None and (best is None or result.distance < best[0]):
            best = (result.distance, first, second, result.schema)
    return None if best is None else best[1:]


def _numbered(groups: Sequence[Group], prefix: str) -> list[Group]:
    """Gibt den verschmolzenen Scheiben fortlaufende Namen; die anderen behalten ihren."""
    merged = [g for g in groups if g.is_merged]
    named = [
        Group(replace(g.schema, name=f"{prefix} {i}"), g.members)
        for i, g in enumerate(merged, start=1)
    ]
    return named + [g for g in groups if not g.is_merged]
