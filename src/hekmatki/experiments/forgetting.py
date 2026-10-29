"""Experiment H12: Vergisst der Agent weniger, wenn er Kontexte unterscheidet?"""

import random
from dataclasses import dataclass
from statistics import mean

from hekmatki.context import ContextInference
from hekmatki.evaluation import geometric_mean
from hekmatki.experiments.blocks import block_stream, first_steps, flatten, true_first_steps
from hekmatki.online import SingleModelLearner
from hekmatki.situations import commuting_situations


@dataclass(frozen=True)
class H12Result:
    """Trefferwahrscheinlichkeit direkt nach der Rückkehr in eine schon bekannte Situation."""

    single_model: float
    with_contexts: float
    optimum: float
    contexts_found: float


def run_h12(
    seeds: int = 20,
    blocks: int = 8,
    block_length: int = 150,
    window: int = 30,
) -> H12Result:
    """Wechselt blockweise zwischen Hin- und Rückweg und misst das Vergessen."""
    if blocks < 3:
        raise ValueError(
            "Für eine Rückkehr in eine bekannte Situation braucht es mindestens 3 Blöcke."
        )
    situations = commuting_situations()
    order = [situations["hinweg"], situations["rueckweg"]]
    plan = [order[b % 2] for b in range(blocks)]
    single_scores: list[float] = []
    context_scores: list[float] = []
    optimum_scores: list[float] = []
    contexts_found: list[int] = []

    for seed in range(seeds):
        rng = random.Random(seed)
        stream = block_stream(plan, block_length, rng)
        single = SingleModelLearner(order[0].alphabet)
        contextual = ContextInference(order[0].alphabet)
        returns = slice(2, None)
        single_scores.extend(flatten(first_steps(single, stream, window)[returns]))
        context_scores.extend(flatten(first_steps(contextual, stream, window)[returns]))
        optimum_scores.extend(flatten(true_first_steps(plan, stream, window)[returns]))
        contexts_found.append(len(contextual.contexts))

    return H12Result(
        geometric_mean(single_scores),
        geometric_mean(context_scores),
        geometric_mean(optimum_scores),
        mean(contexts_found),
    )
