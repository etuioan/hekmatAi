"""Die Schnittstelle für jede Umgebung (ab 0.16): nur Zahlen, keine Namen.

Der allgemeine Agent weiß nicht, ob er in einem Raum, einem Würfel oder einem Datenbestand
steckt. Er sieht eine Beobachtung aus ganzen Zahlen und hat ein paar Tasten. Welche Zahl
was bedeutet und welche Taste was tut, muss er selbst herausfinden.

Damit er sich nicht auf eine Reihenfolge verlassen kann, mischt jede Welt ihre Größen und
Tasten mit einer eigenen, zufälligen `Wiring`. Dieselbe Welt in einer anderen Größe behält
ihre Mischung, so wie ein Spiel in einem größeren Level dieselben Tasten hat.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

type Observation = tuple[int, ...]


@dataclass(frozen=True)
class Outcome:
    """Was nach einem Tastendruck zu sehen ist und ob das Ziel erreicht ist."""

    observation: Observation
    reached: bool


@dataclass(frozen=True)
class Transition:
    """Ein erlebter Schritt: vorher, Taste, nachher, Ziel erreicht."""

    before: Observation
    action: int
    after: Observation
    reached: bool


class Environment(Protocol):
    """Eine Umgebung, wie der allgemeine Agent sie sieht."""

    @property
    def actions(self) -> int:
        """Anzahl der Tasten."""
        ...

    def reset(self, rng: random.Random) -> Observation:
        """Beginnt eine neue Runde (neues Ziel) und gibt die erste Beobachtung zurück."""
        ...

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Drückt eine Taste."""
        ...

    def least_steps(self) -> int:
        """Kürzester Weg zum Ziel dieser Runde, nur zum Vergleich (der Agent sieht das nie)."""
        ...


@dataclass(frozen=True)
class Wiring:
    """Die Mischung einer Welt: welche innere Größe an welcher Stelle, welche Taste was ist."""

    components: tuple[int, ...]
    """An Stelle i der Beobachtung steht die innere Größe `components[i]`."""
    actions: tuple[int, ...]
    """Taste i löst die innere Handlung `actions[i]` aus."""

    def __post_init__(self) -> None:
        for name, order in (("Größen", self.components), ("Tasten", self.actions)):
            if sorted(order) != list(range(len(order))):
                raise ValueError(f"Die {name} müssen eine Umordnung von 0 bis n-1 sein: {order}.")

    @classmethod
    def shuffled(cls, components: int, actions: int, rng: random.Random) -> "Wiring":
        """Eine zufällige Mischung."""
        return cls(_permutation(components, rng), _permutation(actions, rng))

    @classmethod
    def plain(cls, components: int, actions: int) -> "Wiring":
        """Keine Mischung (für Tests und zum Nachvollziehen)."""
        return cls(tuple(range(components)), tuple(range(actions)))

    def observe(self, inner: Sequence[int]) -> Observation:
        """Die innere Beobachtung in der Reihenfolge, die der Agent sieht."""
        if len(inner) != len(self.components):
            raise ValueError(f"Erwartet {len(self.components)} Größen, bekommen {len(inner)}.")
        return tuple(inner[index] for index in self.components)

    def inner_action(self, action: int) -> int:
        """Die innere Handlung hinter einer Taste."""
        if not 0 <= action < len(self.actions):
            raise ValueError(f"Taste {action} gibt es nicht (0 bis {len(self.actions) - 1}).")
        return self.actions[action]


def _permutation(size: int, rng: random.Random) -> tuple[int, ...]:
    order = list(range(size))
    rng.shuffle(order)
    return tuple(order)


class Padded:
    """Eine Umgebung mit mehr Größen und Tasten, als sie braucht (ab 0.17).

    So passen ganz verschiedene Welten an dieselbe Schnittstelle, damit ein Agent sie
    nacheinander erleben kann: Fehlende Größen sind immer 0, überzählige Tasten tun nichts.
    Ein Spiel mit festem Bildschirm und fester Tastatur ist genauso: Nicht jede Taste hat in
    jedem Level eine Wirkung.
    """

    def __init__(self, env: Environment, width: int, actions: int) -> None:
        if actions < env.actions:
            raise ValueError(f"Mindestens {env.actions} Tasten nötig, nicht {actions}.")
        self.env, self.width, self._actions = env, width, actions
        self._last: Observation = ()

    @property
    def actions(self) -> int:
        """Anzahl der Tasten, auch der wirkungslosen."""
        return self._actions

    def reset(self, rng: random.Random) -> Observation:
        """Neue Runde in der inneren Umgebung."""
        self._last = self._pad(self.env.reset(rng))
        return self._last

    def step(self, action: int, rng: random.Random) -> Outcome:
        """Eine überzählige Taste lässt alles, wie es ist."""
        if not 0 <= action < self._actions:
            raise ValueError(f"Taste {action} gibt es nicht (0 bis {self._actions - 1}).")
        if action >= self.env.actions:
            return Outcome(self._last, False)
        outcome = self.env.step(action, rng)
        self._last = self._pad(outcome.observation)
        return Outcome(self._last, outcome.reached)

    def least_steps(self) -> int:
        """Wie in der inneren Umgebung."""
        return self.env.least_steps()

    def _pad(self, observation: Observation) -> Observation:
        if len(observation) > self.width:
            raise ValueError(f"Die Welt hat {len(observation)} Größen, Platz ist für {self.width}.")
        return (*observation, *(0,) * (self.width - len(observation)))
