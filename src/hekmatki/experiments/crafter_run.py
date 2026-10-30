"""Crafter (ab 0.18): Was schafft der allgemeine Agent in einem kleinen 2D-Minecraft?

Der Agent spielt Crafter über den Adapter `hekmatki.adapters.crafter`, sieht also nur
gemischte Zahlen und Tasten ohne Namen. Er spielt viele Runden hintereinander und behält sein
Wissen von Runde zu Runde; jede Runde ist eine neue Karte. Gemessen wird wie im Crafter-Paper
(Hafner 2021): für jeden der 22 Erfolge der Anteil der Runden, in denen er ihn schafft, und
daraus die Crafter-Wertung (geometrisches Mittel über alle Erfolge, in Prozent). Gezählt
werden nur die späteren Runden, nachdem der Agent schon gelernt hat (`WARMUP`).

Agenten:
- „Zufall“: zufällige Tasten
- „Tabelle“: Q-Lernen mit einer Tabelle (lernt aus „Ziel erreicht“)
- „Stand 0.17“: der allgemeine Agent ohne eigene Ziele
- „Stand 0.18“: mit eigenen Zielen (`own_goals`). Den Code von 0.18 gibt es nur noch in der
  Geschichte des Repos; seine Runden kommen aus der gespeicherten Messung von 0.18.
- „Stand 0.19“: mit eigenen Zielen und dem Raum aus eigener Bewegung (`space`); seine Runden
  kommen ebenfalls aus der gespeicherten Messung.
- „Stand 0.20“: dazu Abwehr als Option, neuer Besitz, neuer Versuch, und Wege um Hindernisse

Braucht das Zusatzpaket `crafter` (`pip install -e ".[crafter]"`). Aufruf:
`PYTHONPATH=src python -m hekmatki.experiments.crafter_run [messung.json [Startwerte]]`
"""

import json
import math
import random
import sys
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Final, Literal, get_args

from hekmatki.adapters.crafter import ACTIONS, CrafterWorld
from hekmatki.general.agent import GeneralAgent
from hekmatki.general.env import Transition
from hekmatki.general.run import Learner, RandomAgent, TableAgent

ACHIEVEMENTS: Final = (
    "collect_coal",
    "collect_diamond",
    "collect_drink",
    "collect_iron",
    "collect_sapling",
    "collect_stone",
    "collect_wood",
    "defeat_skeleton",
    "defeat_zombie",
    "eat_cow",
    "eat_plant",
    "make_iron_pickaxe",
    "make_iron_sword",
    "make_stone_pickaxe",
    "make_stone_sword",
    "make_wood_pickaxe",
    "make_wood_sword",
    "place_furnace",
    "place_plant",
    "place_stone",
    "place_table",
    "wake_up",
)
EPISODES: Final = 30
WARMUP: Final = 10
"""Die ersten Runden zählen nicht: Da lernt der Agent erst."""

Agent = Literal["Zufall", "Tabelle", "Stand 0.17", "Stand 0.18", "Stand 0.19", "Stand 0.20"]
AGENTS: tuple[Agent, ...] = ("Zufall", "Tabelle", "Stand 0.17", "Stand 0.20")
"""Wer bei einer neuen Messung spielt."""
MAKERS: Final[dict[Agent, Callable[[], Learner]]] = {
    "Zufall": lambda: RandomAgent(ACTIONS),
    "Tabelle": lambda: TableAgent(ACTIONS),
    "Stand 0.17": lambda: GeneralAgent(ACTIONS),
    "Stand 0.20": lambda: GeneralAgent(ACTIONS, own_goals=True),
}


@dataclass(frozen=True)
class Round:
    """Eine Runde: wie lange sie dauerte und welche Erfolge in welchem Schritt kamen."""

    steps: int
    unlocked: tuple[tuple[int, str], ...]

    @property
    def names(self) -> set[str]:
        """Die Erfolge dieser Runde."""
        return {name for _, name in self.unlocked}


@dataclass
class Career:
    """Alle Runden eines Agenten mit einem Startwert."""

    agent: Agent
    seed: int
    rounds: list[Round] = field(default_factory=list)
    seconds: float = 0.0


def play(agent: Agent, seed: int, episodes: int = EPISODES, length: int | None = None) -> Career:
    """Spielt `episodes` Runden mit einem Agenten, der von Runde zu Runde weiterlernt."""
    world = CrafterWorld(seed) if length is None else CrafterWorld(seed, length)
    rng = random.Random(seed)
    learner = MAKERS[agent]()
    career = Career(agent, seed)
    start = time.perf_counter()
    for _ in range(episodes):
        observation = world.reset(rng)
        learner.new_place()
        learner.begin(observation)
        steps = 0
        while not world.finished:
            action = learner.act(observation, rng)
            outcome = world.step(action, rng)
            learner.learn(Transition(observation, action, outcome.observation, outcome.reached))
            observation = outcome.observation
            steps += 1
        career.rounds.append(Round(steps, tuple(world.unlocked)))
    career.seconds = time.perf_counter() - start
    return career


def success_rates(rounds: list[Round]) -> dict[str, float]:
    """Für jeden Erfolg der Anteil der Runden, in denen er kam."""
    return {name: mean(name in r.names for r in rounds) for name in ACHIEVEMENTS}


def score(rates: dict[str, float]) -> float:
    """Crafter-Wertung in Prozent: exp(Mittel von ln(1 + Erfolgsquote in %)) − 1."""
    return math.exp(mean(math.log(1 + 100 * rate) for rate in rates.values())) - 1


@dataclass(frozen=True)
class CrafterRow:
    """Ergebnis eines Agenten über alle Startwerte (nur die gezählten Runden)."""

    agent: Agent
    score: float
    rates: dict[str, float]
    length: float
    """Mittlere Länge einer Runde (wie lange er überlebt)."""
    per_round: float
    """Mittlere Zahl verschiedener Erfolge je Runde."""
    curve: tuple[float, ...]
    """Erfolge je Runde, gemittelt über die Startwerte, für jede Runde (auch die ersten)."""
    ms_per_step: float


def careers(
    seeds: int = 3, episodes: int = EPISODES, agents: tuple[Agent, ...] = AGENTS, workers: int = 4
) -> list[Career]:
    """Alle Agenten mit denselben Startwerten, auf `workers` Prozesse verteilt."""
    jobs = [(agent, seed, episodes) for agent in agents for seed in range(seeds)]
    with ProcessPoolExecutor(workers) as pool:
        return list(pool.map(_play_job, jobs))


def _play_job(job: tuple[Agent, int, int]) -> Career:
    return play(*job)


def rows(found: list[Career], warmup: int = WARMUP) -> list[CrafterRow]:
    """Für jeden Agenten das Ergebnis über alle Startwerte."""
    result = []
    for agent in dict.fromkeys(c.agent for c in found):
        mine = [c for c in found if c.agent == agent]
        counted = [r for c in mine for r in c.rounds[warmup:]]
        rates = success_rates(counted)
        episodes = min(len(c.rounds) for c in mine)
        curve = tuple(mean(len(c.rounds[i].names) for c in mine) for i in range(episodes))
        steps = sum(r.steps for c in mine for r in c.rounds)
        result.append(
            CrafterRow(
                agent,
                score(rates),
                rates,
                mean(r.steps for r in counted),
                mean(len(r.names) for r in counted),
                curve,
                1000 * sum(c.seconds for c in mine) / steps,
            )
        )
    return result


def run_crafter(seeds: int = 3, episodes: int = EPISODES, warmup: int = WARMUP) -> list[CrafterRow]:
    """Alle Agenten, jeder mit denselben Startwerten."""
    return rows(careers(seeds, episodes), warmup)


def save_careers(found: list[Career], path: Path) -> None:
    """Speichert alle Runden als JSON, damit Auswertung und Seite nicht neu spielen müssen."""
    data = [
        {
            "agent": c.agent,
            "seed": c.seed,
            "seconds": c.seconds,
            "rounds": [{"steps": r.steps, "unlocked": list(r.unlocked)} for r in c.rounds],
        }
        for c in found
    ]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_careers(path: Path) -> list[Career]:
    """Liest, was `save_careers` geschrieben hat."""
    found = []
    for entry in json.loads(path.read_text(encoding="utf-8")):
        if entry["agent"] not in get_args(Agent):
            raise ValueError(f"Unbekannter Agent in {path}: {entry['agent']}")
        rounds = [
            Round(r["steps"], tuple((int(at), str(name)) for at, name in r["unlocked"]))
            for r in entry["rounds"]
        ]
        found.append(Career(entry["agent"], int(entry["seed"]), rounds, float(entry["seconds"])))
    return found


def report_crafter(rows: list[CrafterRow]) -> None:
    """Druckt die Tabelle."""
    print("Crafter: 22 Erfolge, Wertung wie bei Hafner 2021 (nur die späteren Runden)\n")
    columns = ("Wertung", "Erfolge/Runde", "Länge", "ms/Schritt")
    print(f"{'Agent':<12} | " + " | ".join(columns))
    print("-" * 62)
    for row in rows:
        print(
            f"{row.agent:<12} | {row.score:>6.1f}% | {row.per_round:>13.2f} | "
            f"{row.length:>6.0f} | {row.ms_per_step:>10.1f}"
        )
    print("\nErfolgsquote je Erfolg (in Prozent der Runden):\n")
    print(f"{'Erfolg':<20} | " + " | ".join(f"{row.agent:>10}" for row in rows))
    for name in ACHIEVEMENTS:
        print(f"{name:<20} | " + " | ".join(f"{100 * row.rates[name]:>9.0f}%" for row in rows))
    print()


if __name__ == "__main__":
    # Aufruf: python -m hekmatki.experiments.crafter_run [messung.json [Startwerte]]
    measured = careers(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    if len(sys.argv) > 1:
        save_careers(measured, Path(sys.argv[1]))
    report_crafter(rows(measured))
