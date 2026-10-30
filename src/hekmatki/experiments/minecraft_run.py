"""Minecraft (nach 0.20): Was schafft der allgemeine Agent in der echten offenen Welt?

Der Agent spielt Minecraft über den Adapter `hekmatki.adapters.minecraft`, sieht also nur
gemischte Zahlen und Tasten ohne Namen, genau wie bei Crafter. Er spielt mehrere Runden
hintereinander und behält sein Wissen; jede Runde beginnt an einem neuen Ort der Welt.

Gemessen wird wie bei Crafter (Hafner 2021): für jeden Fortschritt der Liste `ADVANCEMENTS` der
Anteil der Runden, in denen er kommt, und daraus die Wertung (geometrisches Mittel). Die Liste
enthält die Fortschritte, die man in den ersten Minuten ohne Reise schaffen kann. Sie dient nur
der Auswertung; der Agent erfährt nur „ein neuer Fortschritt kam“.

Eine Messung läuft in Teilen, weil jeder Teil einen eigenen Minecraft-Server braucht:
`python -m hekmatki.experiments.minecraft_run play "Stand 0.22" 7 teil.json --port 25565`
`python -m hekmatki.experiments.minecraft_run merge messung.json teil-*.json`
"""

import argparse
import json
import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Final, Literal, get_args

from hekmatki.adapters.minecraft import LENGTH, BridgeProcess, Connection, MinecraftWorld
from hekmatki.general.agent import GeneralAgent
from hekmatki.general.env import Transition
from hekmatki.general.run import Learner, RandomAgent, TableAgent

ADVANCEMENTS: Final = (
    "minecraft:story/root",
    "minecraft:story/mine_stone",
    "minecraft:story/upgrade_tools",
    "minecraft:story/smelt_iron",
    "minecraft:story/iron_tools",
    "minecraft:adventure/root",
    "minecraft:adventure/kill_a_mob",
    "minecraft:adventure/sleep_in_bed",
    "minecraft:husbandry/root",
    "minecraft:husbandry/plant_seed",
)
"""Werkbank, Stein, Steinspitzhacke, Eisen, Eisenspitzhacke, ein Wesen besiegt oder von einem
besiegt, ein Monster besiegt, im Bett geschlafen, etwas gegessen, etwas gepflanzt."""
EPISODES: Final = 12
WARMUP: Final = 4
"""Die ersten Runden zählen nicht: Da lernt der Agent erst."""

Agent = Literal["Zufall", "Tabelle", "Stand 0.20", "Stand 0.21", "Stand 0.22"]
"""„Stand 0.20“ und „Stand 0.21“ nur zum Lesen alter Messungen; gespielt wird der aktuelle
Stand."""
MAKERS: Final[dict[Agent, Callable[[int], Learner]]] = {
    "Zufall": RandomAgent,
    "Tabelle": TableAgent,
    "Stand 0.22": lambda actions: GeneralAgent(actions, own_goals=True),
}


@dataclass(frozen=True)
class Round:
    """Eine Runde: wie lange sie dauerte und welche Fortschritte in welchem Schritt kamen."""

    steps: int
    unlocked: tuple[tuple[int, str], ...]
    looking: int = 0
    """In wie vielen Schritten ein Block im Fadenkreuz war (Zwischenstand, ab 0.22)."""
    items: int = 0
    """Wie viele verschiedene Dinge er in der Schnellleiste hatte (Zwischenstand, ab 0.22)."""

    @property
    def names(self) -> set[str]:
        """Die Fortschritte dieser Runde."""
        return {name for _, name in self.unlocked}


@dataclass
class Career:
    """Alle Runden eines Agenten mit einem Startwert."""

    agent: Agent
    seed: int
    rounds: list[Round] = field(default_factory=list)
    seconds: float = 0.0


def play(
    agent: Agent, world: MinecraftWorld, episodes: int = EPISODES, replay: Path | None = None
) -> Career:
    """Spielt `episodes` Runden mit einem Agenten, der von Runde zu Runde weiterlernt.

    Mit `replay` schreibt die letzte Runde Bilder der Lage für die Wiedergabe-Seite mit.
    """
    rng = random.Random(world.seed)
    learner = MAKERS[agent](world.actions)
    career = Career(agent, world.seed)
    start = time.perf_counter()
    for episode in range(episodes):
        world.record = replay is not None and episode == episodes - 1
        career.rounds.append(play_round(learner, world, rng))
        if world.record and replay is not None:
            save_replay(agent, world, episode + 1, replay)
    career.seconds = time.perf_counter() - start
    return career


def play_round(learner: Learner, world: MinecraftWorld, rng: random.Random) -> Round:
    """Eine Runde, bis die Figur stirbt oder die Zeit um ist; der Agent lernt dabei weiter."""
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
    return Round(steps, tuple(world.unlocked), world.looking, len(world.items))


def save_replay(agent: Agent, world: MinecraftWorld, episode: int, path: Path) -> None:
    """Speichert die Bilder einer Runde für `minecraft_replay`."""
    data = {
        "agent": agent,
        "seed": world.seed,
        "episode": episode,
        "unlocked": world.unlocked,
        "scenes": world.scenes,
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@dataclass(frozen=True)
class MinecraftRow:
    """Ergebnis eines Agenten über alle Startwerte (nur die gezählten Runden)."""

    agent: Agent
    score: float
    rates: dict[str, float]
    others: dict[str, float]
    """Fortschritte außerhalb der Liste, die trotzdem kamen, mit ihrem Anteil der Runden."""
    length: float
    per_round: float
    seeds: int
    looking: float
    """Anteil der Schritte mit einem Block im Fadenkreuz."""
    items: float
    """Verschiedene Dinge in der Schnellleiste je Runde."""


def score(rates: dict[str, float]) -> float:
    """Wertung in Prozent wie bei Crafter: exp(Mittel von ln(1 + Quote in %)) − 1."""
    return math.exp(mean(math.log(1 + 100 * rate) for rate in rates.values())) - 1


def rows(found: list[Career], warmup: int = WARMUP) -> list[MinecraftRow]:
    """Für jeden Agenten das Ergebnis über alle Startwerte."""
    result = []
    for agent in dict.fromkeys(c.agent for c in found):
        mine = [c for c in found if c.agent == agent]
        counted = [r for c in mine for r in c.rounds[warmup:]]
        if not counted:
            raise ValueError(f"{agent}: keine Runde nach den {warmup} Lernrunden.")
        rates = {name: mean(name in r.names for r in counted) for name in ADVANCEMENTS}
        seen = sorted({name for r in counted for name in r.names} - set(ADVANCEMENTS))
        others = {name: mean(name in r.names for r in counted) for name in seen}
        result.append(
            MinecraftRow(
                agent,
                score(rates),
                rates,
                others,
                mean(r.steps for r in counted),
                mean(len(r.names) for r in counted),
                len(mine),
                sum(r.looking for r in counted) / max(1, sum(r.steps for r in counted)),
                mean(r.items for r in counted),
            )
        )
    return result


def save_careers(found: list[Career], path: Path) -> None:
    """Speichert alle Runden als JSON."""
    data = [
        {
            "agent": c.agent,
            "seed": c.seed,
            "seconds": c.seconds,
            "rounds": [
                {
                    "steps": r.steps,
                    "unlocked": list(r.unlocked),
                    "looking": r.looking,
                    "items": r.items,
                }
                for r in c.rounds
            ],
        }
        for c in found
    ]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_careers(paths: list[Path]) -> list[Career]:
    """Liest Teil-Dateien von `save_careers`; jeder Agent darf je Startwert nur einmal kommen."""
    found: list[Career] = []
    for path in paths:
        for entry in json.loads(path.read_text(encoding="utf-8")):
            if entry["agent"] not in get_args(Agent):
                raise ValueError(f"Unbekannter Agent in {path}: {entry['agent']}")
            rounds = [
                Round(
                    r["steps"],
                    tuple((int(at), str(name)) for at, name in r["unlocked"]),
                    int(r.get("looking", 0)),
                    int(r.get("items", 0)),
                )
                for r in entry["rounds"]
            ]
            found.append(
                Career(entry["agent"], int(entry["seed"]), rounds, float(entry["seconds"]))
            )
    keys = [(c.agent, c.seed) for c in found]
    if len(keys) != len(set(keys)):
        raise ValueError("Ein Agent ist mit demselben Startwert doppelt gemessen.")
    return found


def report(found: list[Career]) -> None:
    """Druckt die Tabelle."""
    table = rows(found)
    print(f"Minecraft: {len(ADVANCEMENTS)} frühe Fortschritte (nur die späteren Runden)\n")
    print(f"{'Agent':<12} | Wertung | Fortschritte/Runde | Länge | Karten | Block im Blick | Dinge")
    print("-" * 89)
    for row in table:
        print(
            f"{row.agent:<12} | {row.score:>6.1f}% | {row.per_round:>18.2f} | "
            f"{row.length:>5.0f} | {row.seeds:>6} | {100 * row.looking:>13.0f}% | "
            f"{row.items:>5.1f}"
        )
    print(
        "\nZwischenstände: „Block im Blick“ ist der Anteil der Schritte mit einem Block im "
        "Fadenkreuz,\n„Dinge“ die Zahl verschiedener Dinge in der Schnellleiste je Runde."
    )
    print("\nQuote je Fortschritt (in Prozent der Runden):\n")
    print(f"{'Fortschritt':<34} | " + " | ".join(f"{row.agent:>10}" for row in table))
    names = list(ADVANCEMENTS) + sorted({n for row in table for n in row.others})
    for name in names:
        cells = [100 * (row.rates.get(name) or row.others.get(name, 0.0)) for row in table]
        print(f"{name:<34} | " + " | ".join(f"{cell:>9.0f}%" for cell in cells))
    print()


def _connect(arguments: argparse.Namespace) -> Connection:
    return BridgeProcess(arguments.host, arguments.port, arguments.username)


def main() -> None:
    """Befehlszeile: `play` misst einen Teil, `merge` führt Teile zusammen."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    playing = commands.add_parser("play")
    playing.add_argument("agent", choices=list(MAKERS))
    playing.add_argument("seed", type=int)
    playing.add_argument("out", type=Path)
    playing.add_argument("--episodes", type=int, default=EPISODES)
    playing.add_argument("--length", type=int, default=LENGTH)
    playing.add_argument("--host", default="localhost")
    playing.add_argument("--port", type=int, default=25565)
    playing.add_argument("--username", default="hekmat")
    playing.add_argument("--wiedergabe", type=Path, default=None, dest="replay")
    merging = commands.add_parser("merge")
    merging.add_argument("out", type=Path)
    merging.add_argument("parts", type=Path, nargs="+")
    arguments = parser.parse_args()

    if arguments.command == "play":
        connection = _connect(arguments)
        try:
            world = MinecraftWorld(arguments.seed, connection, arguments.length)
            career = play(arguments.agent, world, arguments.episodes, arguments.replay)
        finally:
            connection.close()
        save_careers([career], arguments.out)
        if arguments.episodes > WARMUP:
            report([career])
    else:
        found = load_careers(arguments.parts)
        save_careers(found, arguments.out)
        report(found)


if __name__ == "__main__":
    main()
