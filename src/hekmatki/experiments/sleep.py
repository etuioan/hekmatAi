"""Experimente zu Kontextwechsel, Schemata und Schlaf in der Lampenwelt."""

import random
from dataclasses import dataclass
from statistics import mean

from hekmatki.context import ContextInference
from hekmatki.experiments.blocks import (
    KNOWN,
    Scores,
    block_labels,
    block_stream,
    first_steps,
    true_first_steps,
)
from hekmatki.online import SingleModelLearner
from hekmatki.situations import lamp_conversations, lamp_situations
from hekmatki.wake_sleep import WakeSleepAgent

TRAINING_ORDER = ("arzt", "ubahn", "arzt", "ubahn")
TEST_ORDER = ("gate", "arzt", "ubahn", "gate")


@dataclass(frozen=True)
class CombinedRow:
    """Ein Agent im Experiment „Kontextwechsel + Scheiben“."""

    agent: str
    new_situation: float
    known_situations: float
    contexts_found: float | None
    """Mittlere Zahl selbst gefundener Kontexte; `None` bei Agenten ohne Kontexte."""


def run_combined(seeds: int = 20, block_length: int = 150, window: int = 30) -> list[CombinedRow]:
    """Kontextwechsel und Scheiben zusammen, mit einer festen Schlafphase.

    1. Wachphase: Der Agent erlebt Arzt und U-Bahn im Wechsel und erkennt die Kontexte selbst.
    2. Schlafphase: Er verschmilzt seine eigenen Kontexte zum Schema „Warten“.
    3. Neue Wachphase: Das Gate kommt hinzu. Neue Kontexte starten jetzt aus dem Schema.

    Gemessen werden die ersten `window` Schritte jedes Testblocks: einmal beim ersten
    Auftauchen des Gates (neue Situation), sonst bei Rückkehr in eine bekannte Situation.
    """
    situations = lamp_situations()
    alphabet = situations["arzt"].alphabet
    training_plan = [situations[n] for n in TRAINING_ORDER]
    test_plan = [situations[n] for n in TEST_ORDER]
    labels = block_labels(TEST_ORDER, measured=("gate",), already_seen=TRAINING_ORDER)
    names = ("ein Modell", "Kontexte", "Kontexte + Schema", "Optimum")
    scores = {name: Scores() for name in names}
    found: dict[str, list[int]] = {"Kontexte": [], "Kontexte + Schema": []}

    for seed in range(seeds):
        rng = random.Random(seed)
        training = block_stream(training_plan, block_length, rng)
        last_symbol = training[-1][-1]
        test = block_stream(test_plan, block_length, rng, start=last_symbol)
        single = SingleModelLearner(alphabet)
        contexts = ContextInference(alphabet)
        with_schema = WakeSleepAgent(alphabet, maturity=None)
        for agent in (single, contexts, with_schema):
            first_steps(agent, training, window)

        with_schema.sleep()
        if not with_schema.schemas:
            raise RuntimeError("Die Schlafphase hat kein Schema „Warten“ gebildet.")

        scores["ein Modell"].add(first_steps(single, test, window, last_symbol), labels)
        scores["Kontexte"].add(first_steps(contexts, test, window, last_symbol), labels)
        scores["Kontexte + Schema"].add(first_steps(with_schema, test, window, last_symbol), labels)
        scores["Optimum"].add(true_first_steps(test_plan, test, window, last_symbol), labels)
        found["Kontexte"].append(len(contexts.contexts))
        found["Kontexte + Schema"].append(with_schema.context_count)

    return [
        CombinedRow(
            name,
            scores[name].typical("gate"),
            scores[name].typical(KNOWN),
            mean(found[name]) if name in found else None,
        )
        for name in names
    ]


WAKE_SLEEP_ORDER = (
    *TRAINING_ORDER,
    "gate",
    "arzt",
    "gate",
    "kasse",
    "ubahn",
    "kasse",
)


@dataclass(frozen=True)
class WakeSleepRow:
    """Ein Agent im Experiment „selbst gesteuerter Schlaf“."""

    agent: str
    new_gate: float
    new_checkout: float
    known_situations: float
    sleeps: float | None
    contexts_in_schema: float | None
    """Mittlere Zahl der Kontexte im Schema am Ende; `None` bei Agenten ohne Schlaf."""


def run_wake_sleep(
    seeds: int = 20, block_length: int = 150, window: int = 30
) -> list[WakeSleepRow]:
    """Vergleicht einen Agenten, der einmal fest schläft, mit einem, der selbst entscheidet.

    Der Strom: Arzt und U-Bahn im Wechsel, dann das Gate (neu), später die Kasse (neu).
    „fester Schlaf“ schläft genau einmal, nach den ersten vier Blöcken, wie in Version 0.3.
    „eigener Schlaf“ schläft, sobald ein Kontext genug Erfahrung gesammelt hat. So kann
    auch das Gate ins Schema wandern, bevor die Kasse auftaucht.
    """
    situations = lamp_situations()
    alphabet = situations["arzt"].alphabet
    plan = [situations[n] for n in WAKE_SLEEP_ORDER]
    labels = block_labels(WAKE_SLEEP_ORDER, measured=("gate", "kasse"))
    first_part = len(TRAINING_ORDER)
    names = ("Kontexte", "fester Schlaf", "eigener Schlaf", "Optimum")
    scores = {name: Scores() for name in names}
    sleeps: dict[str, list[int]] = {"fester Schlaf": [], "eigener Schlaf": []}
    in_schema: dict[str, list[int]] = {"fester Schlaf": [], "eigener Schlaf": []}

    for seed in range(seeds):
        rng = random.Random(seed)
        stream = block_stream(plan, block_length, rng)
        before, after = stream[:first_part], stream[first_part:]
        last_symbol = before[-1][-1]
        contexts = ContextInference(alphabet)
        fixed = WakeSleepAgent(alphabet, maturity=None)
        own = WakeSleepAgent(alphabet)
        fixed_scores = first_steps(fixed, before, window)
        fixed.sleep()
        fixed_scores += first_steps(fixed, after, window, last_symbol)

        scores["Kontexte"].add(first_steps(contexts, stream, window), labels)
        scores["fester Schlaf"].add(fixed_scores, labels)
        scores["eigener Schlaf"].add(first_steps(own, stream, window), labels)
        scores["Optimum"].add(true_first_steps(plan, stream, window), labels)
        for name, sleeper in (("fester Schlaf", fixed), ("eigener Schlaf", own)):
            sleeps[name].append(sleeper.sleeps)
            in_schema[name].append(sleeper.contexts_in_schemas)

    return [
        WakeSleepRow(
            name,
            scores[name].typical("gate"),
            scores[name].typical("kasse"),
            scores[name].typical(KNOWN),
            mean(sleeps[name]) if name in sleeps else None,
            mean(in_schema[name]) if name in in_schema else None,
        )
        for name in names
    ]


MULTI_SCHEMA_ORDER = (
    "arzt",
    "nachbar",
    "ubahn",
    "kollege",
    "arzt",
    "nachbar",
    "gate",
    "freund",
    "ubahn",
    "kollege",
    "gate",
    "freund",
)


@dataclass(frozen=True)
class MultiSchemaRow:
    """Ein Agent im Experiment „mehrere Schemata“."""

    agent: str
    new_gate: float
    new_friend: float
    known_situations: float
    schemas: float | None
    """Mittlere Zahl der Schemata am Ende; `None` bei Agenten ohne Schlaf."""


def run_multi_schema(
    seeds: int = 20, block_length: int = 150, window: int = 30
) -> list[MultiSchemaRow]:
    """Warten und Gespräche im Wechsel: Bildet der Agent für beides ein eigenes Schema?

    „ein Schema“ verhält sich wie Version 0.4: Gespräche passen nicht zu „Warten“ und
    bleiben ohne Schema. „mehrere Schemata“ darf im Schlaf ein zweites Schema gründen.
    Gemessen wird beim ersten Gate (neue Wartesituation) und beim ersten Gespräch mit dem
    Freund (neue Gesprächssituation).
    """
    situations = {**lamp_situations(), **lamp_conversations()}
    alphabet = situations["arzt"].alphabet
    plan = [situations[n] for n in MULTI_SCHEMA_ORDER]
    labels = block_labels(MULTI_SCHEMA_ORDER, measured=("gate", "freund"))
    names = ("Kontexte", "ein Schema", "mehrere Schemata", "Optimum")
    scores = {name: Scores() for name in names}
    schema_counts: dict[str, list[int]] = {"ein Schema": [], "mehrere Schemata": []}

    for seed in range(seeds):
        rng = random.Random(seed)
        stream = block_stream(plan, block_length, rng)
        sleepers = {
            "ein Schema": WakeSleepAgent(alphabet, max_schemas=1),
            "mehrere Schemata": WakeSleepAgent(alphabet),
        }
        scores["Kontexte"].add(first_steps(ContextInference(alphabet), stream, window), labels)
        for name, sleeper in sleepers.items():
            scores[name].add(first_steps(sleeper, stream, window), labels)
            schema_counts[name].append(len(sleeper.schemas))
        scores["Optimum"].add(true_first_steps(plan, stream, window), labels)

    return [
        MultiSchemaRow(
            name,
            scores[name].typical("gate"),
            scores[name].typical("freund"),
            scores[name].typical(KNOWN),
            mean(schema_counts[name]) if name in schema_counts else None,
        )
        for name in names
    ]
