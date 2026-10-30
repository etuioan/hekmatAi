"""Runden spielen und messen, für jeden Agenten mit derselben Schnittstelle (ab 0.16).

Seit dem Review nach 0.21 haben Welt und Agent getrennte Zufallsquellen (`Chance`): Jede
Runde bekommt ihren eigenen Zufall für die Welt, vorab aus einem festen Startwert gezogen. So
spielen alle Agenten mit gleichem Startwert dieselben Aufgaben, egal wie oft sie selbst würfeln
oder wie lange eine Runde dauert. Vorher teilten sich beide einen Zufall, und die Aufgaben
hingen vom Agenten ab.

Zum Vergleich gibt es zwei Agenten ohne Regeln:
- `RandomAgent`: drückt zufällige Tasten.
- `TableAgent`: lernt für jede gesehene Beobachtung, welche Taste sich lohnt (Q-Lernen mit
  Tabelle, Watkins 1989). Er kann nichts auf Beobachtungen übertragen, die er nie gesehen hat.
"""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Final, Protocol

from hekmatki.general.env import Environment, Observation, Transition

LEARNING_RATE: Final = 0.5
DISCOUNT: Final = 0.95
CURIOSITY: Final = 0.1


@dataclass(frozen=True)
class Chance:
    """Getrennte Zufallsquellen: eine legt die Aufgaben der Runden fest, eine gehört dem Agenten."""

    tasks: random.Random
    agent: random.Random

    @classmethod
    def seeded(cls, seed: int) -> "Chance":
        """Beide Quellen aus einem Startwert, aber unabhängig voneinander."""
        return cls(random.Random(f"aufgaben {seed}"), random.Random(f"agent {seed}"))

    def next_task(self) -> random.Random:
        """Der Zufall der Welt für die nächste Runde: Start, Ziel und Rutschen. Er hängt nur
        davon ab, die wievielte Runde es ist, nicht davon, was der Agent tut."""
        return random.Random(self.tasks.getrandbits(64))


class Learner(Protocol):
    """Was ein Agent können muss, um Runden zu spielen."""

    def new_place(self) -> None:
        """Eine neue Umgebung derselben Art beginnt."""
        ...

    def begin(self, observation: Observation) -> None:
        """Eine Runde beginnt."""
        ...

    def act(self, observation: Observation, rng: random.Random) -> int:
        """Wählt eine Taste."""
        ...

    def learn(self, transition: Transition) -> None:
        """Lernt aus einem Schritt."""
        ...


@dataclass(frozen=True)
class Episode:
    """Eine gespielte Runde."""

    steps: int
    reached: bool
    least: int
    """Kürzester möglicher Weg."""
    trace: tuple[Observation, ...] = ()
    """Alle Beobachtungen der Runde, falls aufgezeichnet."""
    pressed: tuple[int, ...] = ()
    """Alle gedrückten Tasten der Runde, falls aufgezeichnet."""


def play_episode(
    env: Environment, agent: Learner, chance: Chance, limit: int, record: bool = False
) -> Episode:
    """Spielt eine Runde, bis das Ziel erreicht ist oder `limit` Schritte vorbei sind."""
    world = chance.next_task()
    observation = env.reset(world)
    least = env.least_steps()
    agent.begin(observation)
    trace = [observation]
    pressed: list[int] = []
    for step in range(1, limit + 1):
        action = agent.act(observation, chance.agent)
        outcome = env.step(action, world)
        agent.learn(Transition(observation, action, outcome.observation, outcome.reached))
        observation = outcome.observation
        if record:
            trace.append(observation)
            pressed.append(action)
        if outcome.reached:
            return Episode(step, True, least, tuple(trace) if record else (), tuple(pressed))
    return Episode(limit, False, least, tuple(trace) if record else (), tuple(pressed))


class RandomAgent:
    """Drückt zufällige Tasten."""

    def __init__(self, actions: int) -> None:
        self.actions = actions

    def new_place(self) -> None:
        """Nichts zu tun."""

    def begin(self, observation: Observation) -> None:
        """Nichts zu tun."""

    def act(self, observation: Observation, rng: random.Random) -> int:
        """Eine zufällige Taste."""
        return rng.randrange(self.actions)

    def learn(self, transition: Transition) -> None:
        """Lernt nichts."""


class TableAgent:
    """Q-Lernen mit einer Tabelle: ein Wert je (Beobachtung, Taste)."""

    def __init__(self, actions: int) -> None:
        self.actions = actions
        self.values: defaultdict[Observation, list[float]] = defaultdict(
            lambda: [1.0] * actions  # Optimistisch: Unbekanntes lohnt sich auszuprobieren.
        )

    def new_place(self) -> None:
        """Die Tabelle bleibt; sie hilft nur, wo dieselben Beobachtungen wiederkommen."""

    def begin(self, observation: Observation) -> None:
        """Nichts zu tun."""

    def act(self, observation: Observation, rng: random.Random) -> int:
        """Meist die Taste mit dem höchsten Wert, manchmal eine zufällige."""
        if rng.random() < CURIOSITY:
            return rng.randrange(self.actions)
        values = self.values[observation]
        best = max(values)
        return rng.choice([a for a, value in enumerate(values) if value == best])

    def learn(self, transition: Transition) -> None:
        """Q-Lernen: Belohnung 1 am Ziel, sonst 0."""
        later = 0.0 if transition.reached else DISCOUNT * max(self.values[transition.after])
        target = float(transition.reached) + later
        values = self.values[transition.before]
        values[transition.action] += LEARNING_RATE * (target - values[transition.action])
