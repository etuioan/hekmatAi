"""Schemata: übergeordnete Scheiben, die mehrere ähnliche Situationsmodelle zusammenfassen.

Ein Schema ist ein Markov-Modell über abstrakten Rollen. Eine Bindung setzt die konkreten
Symbole einer Situation in die Rollen ein (Struktur von Inhalt getrennt, wie im
Tolman-Eichenbaum-Modell).
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise

from hekmatki.action import ActionKnowledge, by_role, combined, decisions_conflict
from hekmatki.markov import MarkovModel
from hekmatki.online import LearningPredictor
from hekmatki.structure import best_match, embeddings

Binding = Mapping[str, str]
"""Eindeutige Zuordnung Symbol → Rolle."""

DEFAULT_MERGE_THRESHOLD = 0.1


@dataclass(frozen=True)
class Schema:
    """Eine übergeordnete Scheibe: Struktur ohne konkreten Inhalt."""

    name: str
    model: MarkovModel
    action_knowledge: ActionKnowledge = field(default_factory=dict)
    """Pro Rolle: wie oft eigenes Handeln dort versucht wurde und wie oft es klappte."""

    def __post_init__(self) -> None:
        unknown = set(self.action_knowledge) - set(self.model.alphabet)
        if unknown:
            raise ValueError(
                f"Schema {self.name!r}: Handlungswissen für unbekannte Rollen {sorted(unknown)}."
            )

    @property
    def roles(self) -> tuple[str, ...]:
        """Die abstrakten Rollen des Schemas."""
        return self.model.alphabet


@dataclass(frozen=True)
class BoundSchema:
    """Ein Schema mit eingesetztem Inhalt. Sagt Symbole voraus."""

    schema: Schema
    binding: Binding

    def probability(self, previous: str, following: str) -> float:
        """Wahrscheinlichkeit laut Schema, nachdem beide Symbole in Rollen übersetzt wurden."""
        if previous not in self.binding or following not in self.binding:
            raise ValueError(f"Symbol ohne Bindung: ({previous!r}, {following!r}).")
        return self.schema.model.probability(self.binding[previous], self.binding[following])

    def observe(self, previous: str, following: str) -> None:
        """Ein starres Schema lernt nicht. Die Methode ändert deshalb absichtlich nichts."""


def role_names(symbols: Sequence[str]) -> dict[str, str]:
    """Gibt jedem Symbol in der gegebenen Reihenfolge einen neutralen Rollennamen."""
    return {symbol: f"rolle_{i + 1}" for i, symbol in enumerate(symbols)}


def all_bindings(symbols: Sequence[str], roles: Sequence[str]) -> list[dict[str, str]]:
    """Alle eindeutigen Zuordnungen von gleich vielen Symbolen zu Rollen."""
    if len(symbols) != len(roles):
        raise ValueError(
            f"Dieser Prototyp bindet nur gleich viele Symbole und Rollen: "
            f"{len(symbols)} Symbole, {len(roles)} Rollen."
        )
    return list(embeddings(symbols, roles))


@dataclass(frozen=True)
class MergeResult:
    """Ergebnis eines Verschmelzungsversuchs, auch wenn keiner zustande kam."""

    schema: Schema | None
    distance: float
    """Abstand der besten erlaubten Zuordnung; unendlich, wenn keine erlaubt war."""
    first_binding: Mapping[str, str]
    """Symbol (oder Rolle) der ersten Scheibe → Rolle des Schemas."""
    second_binding: Mapping[str, str]
    """Symbol (oder Rolle) der zweiten Scheibe → Rolle des Schemas; leer ohne Zuordnung."""


def merge(
    first: MarkovModel,
    second: MarkovModel,
    name: str,
    threshold: float = DEFAULT_MERGE_THRESHOLD,
) -> MergeResult:
    """Versucht, zwei Situationsmodelle ohne Handlungswissen zu einem Schema zu verschmelzen.

    Kurzform von `merge_schemas` für Modelle, die nur Übergänge kennen.
    """
    return merge_schemas(Schema(name, first), Schema(name, second), name, threshold)


def merge_schemas(
    first: Schema,
    second: Schema,
    name: str,
    threshold: float = DEFAULT_MERGE_THRESHOLD,
    check_decisions: bool = True,
) -> MergeResult:
    """Verschmilzt zwei Scheiben derselben Ebene samt Handlungswissen. Gleich für jede Ebene.

    Eine Scheibe kann eine erlebte Situation sein, ein Schema oder ein Meta-Schema. Alle
    Zuordnungen von `second` auf die Rollen von `first` werden ausprobiert (Strukturabbildung,
    `structure.best_match`). Ist die beste nah genug, entsteht ein Schema aus den Zählungen
    und dem Handlungswissen beider.

    Mit `check_decisions` sind Zuordnungen verboten, unter denen sich das Handlungswissen
    widerspricht (`action.decisions_conflict`). So bleiben Unterschiede erhalten, die für
    Entscheidungen wichtig sind, auch wenn die Abläufe ähnlich aussehen.
    """
    if len(first.roles) != len(second.roles):
        raise ValueError(
            f"Verschmelzen braucht gleich viele Symbole: "
            f"{len(first.roles)} gegen {len(second.roles)}. Für Teile: Schnittmenge."
        )
    first_roles = role_names(first.roles)
    reference = first.model.relabeled(first_roles)
    first_knowledge = by_role(first.action_knowledge, first_roles)

    def compatible(binding: Mapping[str, str]) -> bool:
        second_knowledge = by_role(second.action_knowledge, binding)
        return not decisions_conflict(first_knowledge, second_knowledge)

    match = best_match(second.model, reference, compatible if check_decisions else None)
    if match is None:
        return MergeResult(None, math.inf, first_roles, {})
    schema = None
    if match.distance <= threshold:
        knowledge = combined(first_knowledge, by_role(second.action_knowledge, match.binding))
        model = reference.merged_with(second.model.relabeled(match.binding))
        schema = Schema(name, model, knowledge)
    return MergeResult(schema, match.distance, first_roles, match.binding)


DEFAULT_PRIOR_STRENGTH = 10.0


class OnlineMixture:
    """Mittelt mehrere Modelle, gewichtet nach ihrer bisherigen Vorhersagekraft.

    So rechnet der Agent seine Unsicherheit mit, etwa welche Bindung richtig ist oder ob
    das Schema überhaupt passt, statt sich blind festzulegen (Bayessche Modellmittelung).
    Jede Beobachtung wird erst vorhergesagt und bewertet, dann gelernt. Die Bewertung misst
    so ehrlich, wie gut jedes Modell Unbekanntes vorhersagt.
    """

    def __init__(
        self, models: Sequence[LearningPredictor], log_priors: Sequence[float] | None = None
    ) -> None:
        if not models:
            raise ValueError("Eine Mischung braucht mindestens ein Modell.")
        priors = [0.0] * len(models) if log_priors is None else list(log_priors)
        if len(priors) != len(models):
            raise ValueError("Jedes Modell braucht genau eine Vorab-Gewichtung.")
        self._models = list(models)
        self._log_weights = priors
        self._weights = _normalized_weights(priors)

    def probability(self, previous: str, following: str) -> float:
        """Gewichteter Mittelwert der Vorhersagen aller Modelle."""
        return sum(
            w * m.probability(previous, following)
            for m, w in zip(self._models, self._weights, strict=True)
        )

    def observe(self, previous: str, following: str) -> None:
        """Bewertet jedes Modell an dieser Beobachtung und lässt es danach lernen."""
        for i, model in enumerate(self._models):
            p = model.probability(previous, following)
            self._log_weights[i] += math.log(p) if p > 0.0 else -math.inf
            model.observe(previous, following)
        self._weights = _normalized_weights(self._log_weights)

    def observe_sequence(self, sequence: Sequence[str]) -> None:
        """Lernt alle Übergänge einer Folge."""
        for previous, following in pairwise(sequence):
            self.observe(previous, following)


def fixed_schema_predictor(
    schema: Schema, alphabet: Iterable[str], observations: Sequence[str]
) -> OnlineMixture:
    """Starres Schema: Die neue Situation wird genau wie das Schema vorhergesagt.

    Die Beobachtungen dienen nur dazu, die Bindung zu finden.
    """
    bound = [BoundSchema(schema, b) for b in _bindings_for(schema, alphabet)]
    return _trained(OnlineMixture(bound), alphabet, observations)


def adaptive_schema_model(
    schema: Schema, alphabet: Iterable[str], prior_strength: float = DEFAULT_PRIOR_STRENGTH
) -> OnlineMixture:
    """Lernendes Schema: Das Schema ist nur Vorwissen, Beobachtungen korrigieren es."""
    return OnlineMixture(_schema_models(schema, alphabet, prior_strength))


def schema_or_flat_model(
    schema: Schema, alphabet: Iterable[str], prior_strength: float = DEFAULT_PRIOR_STRENGTH
) -> OnlineMixture:
    """Lernendes Schema mit Prüfung: Der Agent entscheidet selbst, ob das Schema passt.

    Kurzform von `schemas_or_flat_model` für genau ein Schema.
    """
    return schemas_or_flat_model([schema], alphabet, prior_strength)


def schemas_or_flat_model(
    schemas: Sequence[Schema],
    alphabet: Iterable[str],
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
) -> OnlineMixture:
    """Lernende Schemata mit Prüfung: Der Agent entscheidet selbst, welches Schema passt.

    Neben allen Bindungen aller Schemata steht ein Modell ohne Vorwissen zur Wahl. Vorab gilt:
    die Hälfte für „ein Schema passt“ (gleich aufgeteilt auf die Schemata und dann auf deren
    Bindungen), die Hälfte für „kein Schema passt“. Danach entscheiden die Daten.
    """
    if not schemas:
        raise ValueError("Es wird mindestens ein Schema gebraucht.")
    symbols = tuple(sorted(set(alphabet)))
    models: list[LearningPredictor] = []
    log_priors: list[float] = []
    for schema in schemas:
        schema_models = _schema_models(schema, symbols, prior_strength)
        share = 0.5 / len(schemas) / len(schema_models)
        models.extend(schema_models)
        log_priors.extend([math.log(share)] * len(schema_models))
    models.append(MarkovModel(symbols, schemas[0].model.pseudocount))
    log_priors.append(math.log(0.5))
    return OnlineMixture(models, log_priors)


def adaptive_schema_predictor(
    schema: Schema,
    alphabet: Iterable[str],
    observations: Sequence[str],
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
) -> OnlineMixture:
    """`adaptive_schema_model`, das bereits aus `observations` gelernt hat."""
    model = adaptive_schema_model(schema, alphabet, prior_strength)
    return _trained(model, alphabet, observations)


def schema_or_flat_predictor(
    schema: Schema,
    alphabet: Iterable[str],
    observations: Sequence[str],
    prior_strength: float = DEFAULT_PRIOR_STRENGTH,
) -> OnlineMixture:
    """`schema_or_flat_model`, das bereits aus `observations` gelernt hat."""
    model = schema_or_flat_model(schema, alphabet, prior_strength)
    return _trained(model, alphabet, observations)


def _trained(
    mixture: OnlineMixture, alphabet: Iterable[str], observations: Sequence[str]
) -> OnlineMixture:
    unknown = set(observations) - set(alphabet)
    if unknown:
        raise ValueError(f"Beobachtungen enthalten Symbole außerhalb des Alphabets: {unknown}.")
    mixture.observe_sequence(observations)
    return mixture


def _schema_models(
    schema: Schema, alphabet: Iterable[str], prior_strength: float
) -> list[MarkovModel]:
    """Ein Situationsmodell pro möglicher Bindung, jeweils mit dem Schema als Vorwissen."""
    return [instantiate(schema, b, prior_strength) for b in _bindings_for(schema, alphabet)]


def instantiate(schema: Schema, binding: Binding, prior_strength: float) -> MarkovModel:
    """Erzeugt ein Situationsmodell, das mit dem Schema als Vorwissen startet.

    `prior_strength` sagt, wie vielen Beobachtungen pro Zustand das Vorwissen entspricht.
    """
    if prior_strength <= 0.0:
        raise ValueError(f"Die Stärke des Vorwissens muss positiv sein, war {prior_strength}.")
    if set(binding.values()) != set(schema.roles):
        raise ValueError("Die Bindung muss jede Rolle des Schemas genau einmal belegen.")
    symbol_of = {role: symbol for symbol, role in binding.items()}
    model = MarkovModel(binding.keys(), schema.model.pseudocount)
    for a in schema.roles:
        for b in schema.roles:
            prior_count = prior_strength * schema.model.probability(a, b)
            model.observe(symbol_of[a], symbol_of[b], prior_count)
    return model


def _bindings_for(schema: Schema, alphabet: Iterable[str]) -> list[dict[str, str]]:
    return all_bindings(tuple(sorted(set(alphabet))), schema.roles)


def _normalized_weights(log_scores: Sequence[float]) -> list[float]:
    """Wandelt Log-Bewertungen in Gewichte um, die sich zu 1 addieren (Softmax)."""
    highest = max(log_scores)
    if highest == -math.inf:
        raise ValueError("Kein Modell der Mischung erklärt die Beobachtungen.")
    exponentials = [math.exp(s - highest) for s in log_scores]
    total = sum(exponentials)
    return [e / total for e in exponentials]
