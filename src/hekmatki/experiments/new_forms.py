"""Neue Formen (ab 0.17, H21 und H22): Kommt der Agent mit Welten zurecht, die 0.16 nicht kannte?

In 0.16 kannte der Agent zwei Formen, Raum und Ordnung, aus einer festen Liste, und er hatte
keinen Baustein „wiederholen“. Drei Welten prüfen, ob die Grammatik der Formen (H21) und die
Schleife „bis Schalter“ (H22) diese Grenzen überwinden:
- „Eis-Raum“: Raster aus Eis. Die Figur rutscht, bis sie an eine Wand stößt. Ohne Schleife
  lässt sich das nicht in einer Regel sagen (in 0.15 hat es kein Agent geschafft).
- „Drehscheiben“: drei Scheiben wie bei einem Zahlenschloss. Nach dem letzten Wert kommt der
  erste: eine Form aus Ringen, die nicht in der Liste von 0.16 stand.
- „Tauschen“: sechs Steine, die man nur mit dem Nachbarn tauschen kann, bis die Reihenfolge
  stimmt. Diese Welt hat keine Achsen, also keine Form mit Namen. Hier muss der Agent ohne
  Form planen, nur mit seinem Modell.

Agenten (alle mit demselben Lehrplan wie in `general_worlds`):
- „Zufall“ und „Tabelle“ wie dort
- „Stand 0.16“: Bausteine und Planer von 0.16 (ohne Übernehmen, Ring, Schleife und ohne Suche
  im Modell)
- „neue Bausteine“: dazu Übernehmen, Ring und Schleife, aber ohne Suche im Modell
- „Stand 0.17“: alles zusammen

Die Ringgröße der Drehscheiben und die Zahl der Steine sind in Lehrplan und Prüfung gleich,
denn die Zahl der Tasten ist für einen Agenten fest. Auf Eis wächst der Raum wie in 0.16.

Grundlage: Formen aus einer Grammatik (Grosse 2012, Kemp & Tenenbaum 2008), Schleifen in
Programmen (Ellis 2018, Cropper 2020), Planen im gelernten Modell ohne Form (MAP 2026,
Mahadevan & Maggioni 2007). Siehe docs/PAPER_ZUORDNUNG.md.
"""

import random
from dataclasses import dataclass
from statistics import mean
from typing import Final, Literal

from hekmatki.experiments.general_worlds import WorldSpec, run_world, same_tasks
from hekmatki.general.agent import GeneralAgent, Planning
from hekmatki.general.env import Environment, Wiring
from hekmatki.general.run import Learner, RandomAgent, TableAgent
from hekmatki.general.worlds import Dials, Shuffle, random_lattice

DIALS: Final = 3
DIAL_SIZE: Final = 12
TOKENS: Final = 6

Agent = Literal["Zufall", "Tabelle", "Stand 0.16", "neue Bausteine", "Stand 0.17"]
AGENTS: tuple[Agent, ...] = ("Zufall", "Tabelle", "Stand 0.16", "neue Bausteine", "Stand 0.17")
GENERAL: tuple[Agent, ...] = ("Stand 0.16", "neue Bausteine", "Stand 0.17")
"""Die Agenten mit Regeln und Form."""


def _ice(size: int, wiring: Wiring, rng: random.Random) -> Environment:
    return random_lattice(2, size, wiring, rng, ice=True)


def _dials(size: int, wiring: Wiring, rng: random.Random) -> Environment:
    return Dials(DIALS, size, wiring)


def _shuffle(tokens: int, wiring: Wiring, rng: random.Random) -> Environment:
    return Shuffle(tokens, wiring)


NEW_WORLDS: Final = (
    WorldSpec(
        "Eis-Raum",
        8,
        4,
        (5, 6, 7),
        12,
        "Rutschbahn mit 2 Dimensionen",
        _ice,
        lambda s: f"{s}×{s} Eis",
    ),
    WorldSpec(
        "Drehscheiben",
        2 * DIALS,
        2 * DIALS,
        (DIAL_SIZE,) * 3,
        DIAL_SIZE,
        "Ring × Ring × Ring",
        _dials,
        lambda s: f"{DIALS} Scheiben mit je {s} Stellungen",
    ),
    WorldSpec(
        "Tauschen",
        2 * TOKENS,
        TOKENS - 1,
        (TOKENS,) * 3,
        TOKENS,
        "keine bekannte Form",
        _shuffle,
        lambda t: f"{t} Steine",
    ),
)


@dataclass(frozen=True)
class FormRow:
    """Ergebnis einer neuen Welt über alle Läufe."""

    world: str
    size: str
    expected: str
    steps: dict[Agent, float]
    """Mittlere Schritte bis zum Ziel in der Prüfung (nicht erreicht zählt als Höchstzahl)."""
    reached: dict[Agent, float]
    """Anteil der Prüfrunden, in denen das Ziel erreicht wurde."""
    best: float
    """Mittlerer kürzester Weg."""
    forms: dict[Agent, tuple[str, ...]]
    """Die gefundenen Formen der Agenten mit Regeln, je Lauf."""

    def form_found(self, agent: Agent) -> float:
        """Anteil der Läufe, in denen der Agent die erwartete Form gefunden hat."""
        return mean(form == self.expected for form in self.forms[agent])


def make_agent(agent: Agent, spec: WorldSpec) -> Learner:
    """Baut einen Agenten für diese Welt."""
    match agent:
        case "Zufall":
            return RandomAgent(spec.actions)
        case "Tabelle":
            return TableAgent(spec.actions)
        case "Stand 0.16":
            return GeneralAgent(spec.actions, Planning.FORM, extended=False, search_model=False)
        case "neue Bausteine":
            return GeneralAgent(spec.actions, Planning.FORM, search_model=False)
        case "Stand 0.17":
            return GeneralAgent(spec.actions, Planning.FORM)


def run_new_forms(seeds: int = 10) -> list[FormRow]:
    """Alle neuen Welten, alle Agenten."""
    return [_row(spec, seeds) for spec in NEW_WORLDS]


def _row(spec: WorldSpec, seeds: int) -> FormRow:
    steps: dict[Agent, float] = {}
    reached: dict[Agent, float] = {}
    forms: dict[Agent, tuple[str, ...]] = {}
    least: dict[Agent, list[int]] = {}
    for agent in AGENTS:
        runs = [run_world(spec, make_agent(agent, spec), seed) for seed in range(seeds)]
        steps[agent] = mean(s for run in runs for s in run.test_steps)
        reached[agent] = mean(r for run in runs for r in run.test_reached)
        least[agent] = [shortest for run in runs for shortest in run.test_least]
        if agent in GENERAL:
            forms[agent] = tuple(_form_name(run.agent) for run in runs)
    best = same_tasks(least)
    return FormRow(
        spec.name, spec.size_text(spec.test), spec.expected_form, steps, reached, mean(best), forms
    )


def _form_name(learner: Learner) -> str:
    if not isinstance(learner, GeneralAgent):
        raise TypeError("Nur der allgemeine Agent hat eine Form.")
    return learner.form().name
