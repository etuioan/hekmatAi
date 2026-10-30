"""Hinweisreize auf Schaden (ab 0.21): Welche Aussage über das, was er sieht, kündigt an, dass
eine Größe wie Gesundheit sinkt?

Für jede einzelne Aussage (Literal) zählt er, wie oft sie galt und wie oft danach eine Größe
sank. Die Schadensquote einer Aussage kennt er nur ungefähr; er rechnet sie als
Beta-Verteilung (Tzovara, Korn & Bach 2018: Angstlernen beim Menschen folgt einem
Beta-Binomial-Modell mit Unsicherheit). Gefährlich ist eine Aussage, sobald die Quote mit
großer Sicherheit über einer Schwelle liegt: Zweimal Schaden in zwei Fällen reicht, viermal in
dreißig nicht.

Bis 0.20 galt eine Lage erst als gefährlich, wenn das Abdecken (`causes.cover`) sie als
Bedingung wählte und sie mindestens 5 Treffer hatte. Dabei gewann oft eine zufällige Lage aus
Gras, die viele Schäden durch Hunger abdeckt, und die Lage „ein Gegner direkt neben mir“ fehlte.
"""

import math
from collections import Counter
from typing import Final

from hekmatki.general.causes import MIN_HITS, Groups, Kind, Literal
from hekmatki.general.env import Observation

CONFIDENCE: Final = 0.95
"""So sicher muss er sein, dass die Schadensquote über der Schwelle liegt (ohne Grundlage)."""


class Cues:
    """Zählt für jedes Literal, wie oft es galt und wie oft danach welche Größe sank."""

    def __init__(self) -> None:
        self._held: Counter[Literal] = Counter()
        self._fell: Counter[tuple[int, Literal]] = Counter()
        self._falls: Counter[int] = Counter()
        self._cache: dict[tuple[int, float, frozenset[int], Groups], tuple[int, list[Literal]]] = {}

    def observe(self, before: Observation, after: Observation, groups: Groups) -> None:
        """Merkt sich einen Schritt: was galt, und welche Größen danach sanken."""
        held = literals(before, groups)
        self._held.update(held)
        for component, (old, new) in enumerate(zip(before, after, strict=True)):
            if new < old:
                self._falls[component] += 1
                self._fell.update((component, literal) for literal in held)

    def alarms(
        self, component: int, threshold: float, only: frozenset[int], groups: Groups
    ) -> list[Literal]:
        """Die Literale über die Größen `only` (oder die Gruppen `groups`), nach denen
        `component` mit Sicherheit `CONFIDENCE` öfter als `threshold` sank, das Gefährlichste
        zuerst. Neu gerechnet wird nur, wenn sie wieder gesunken ist."""
        key = (component, threshold, only, groups)
        cached = self._cache.get(key)
        if cached is not None and cached[0] == self._falls[component]:
            return cached[1]
        current = set(groups)
        found: list[tuple[float, Literal]] = []
        for (fallen, literal), hits in self._fell.items():
            if fallen != component or hits < MIN_HITS:
                continue
            if literal.kind is Kind.SOME:
                if literal.among not in current:
                    continue
            elif literal.component not in only:
                continue
            uses = self._held[literal]
            mean = (hits + 1) / (uses + 2)
            if mean >= threshold and above(hits, uses, threshold) >= CONFIDENCE:
                found.append((mean, literal))
        found.sort(key=lambda pair: (-pair[0], str(pair[1])))
        result = [literal for _, literal in found]
        self._cache[key] = (self._falls[component], result)
        return result


def literals(observation: Observation, groups: Groups) -> list[Literal]:
    """Alles, was gerade gilt: jede Größe hat ihren Wert, und jede Gruppe enthält ihre Werte."""
    found = [Literal(component, value) for component, value in enumerate(observation)]
    for group in groups:
        for value in sorted({observation[component] for component in group}):
            found.append(Literal.some(group, value))
    return found


def above(hits: int, uses: int, threshold: float) -> float:
    """Wie sicher die Quote über `threshold` liegt, nach `hits` Treffern in `uses` Fällen: die
    Wahrscheinlichkeit, dass eine Beta(hits + 1, uses − hits + 1)-verteilte Quote größer ist.

    Für ganze Zahlen gilt P(Beta(a, b) > p) = P(Binomial(a + b − 1, p) ≤ a − 1); das rechnet
    sich genau, ohne Zusatzpaket."""
    if not 0 <= hits <= uses:
        raise ValueError(f"Treffer ({hits}) müssen zwischen 0 und den Fällen ({uses}) liegen.")
    if not 0 < threshold < 1:
        raise ValueError(f"Die Schwelle muss zwischen 0 und 1 liegen, nicht {threshold}.")
    trials = uses + 1
    log_p, log_q = math.log(threshold), math.log1p(-threshold)
    log_choose = 0.0
    total = 0.0
    for k in range(hits + 1):
        if k > 0:
            log_choose += math.log(trials - k + 1) - math.log(k)
        total += math.exp(log_choose + k * log_p + (trials - k) * log_q)
    return min(1.0, total)
