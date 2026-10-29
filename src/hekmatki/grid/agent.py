"""Der Objekt-Agent: sieht Farbraster und lernt Figur, Tasten und Farbwirkungen selbst.

Pro Schritt entscheidet er in dieser Reihenfolge:
1. Gibt es eine Taste, deren Richtung er nicht kennt und die er hier noch nicht gedrückt hat,
   probiert er sie aus.
2. Kennt er einen Weg zum Ziel, geht er ihn.
3. Hat er Vorwissen (`ColorAdvisor`), plant er mit dessen Vermutungen über unbekannte Farben.
4. Sonst geht er zur nächsten Farbe, deren Wirkung er nicht kennt (und, mit Vorwissen, auch
   nicht vermutet), und betritt sie (Neugier). Hilft das Vorwissen gar nicht weiter, testet
   er auch Farben, über die es nur Vermutungen gibt.
5. Sonst drückt er eine zufällige Taste.

Weil er über Farben lernt statt über ganze Bilder, gilt alles Gelernte sofort überall im
Labyrinth: Einmal gegen eine Wand gelaufen, kennt er alle Wände.
"""

import random
from collections.abc import Iterator, Sequence
from enum import StrEnum
from typing import Protocol

from hekmatki.grid.effects import Effect
from hekmatki.grid.knowledge import Knowledge
from hekmatki.grid.planner import EffectOf, Wanted, find_path, is_unknown, is_win
from hekmatki.grid.world import Color, Grid


class Reason(StrEnum):
    """Warum der Agent eine Taste gewählt hat."""

    TRY = "probiert eine Taste aus"
    PLAN = "geht seinen Weg zum Ziel"
    GUESS = "folgt einer Vermutung aus dem Schema"
    EXPLORE = "testet eine unbekannte Farbe"
    WANDER = "drückt eine zufällige Taste"


class ColorAdvisor(Protocol):
    """Vorwissen, das Vermutungen über die Wirkung unbekannter Farben liefert."""

    def pick(self, rng: random.Random) -> None:
        """Wählt eine neue Deutung, falls die bisherige widerlegt ist."""
        ...

    def effect(self, color: Color, knowledge: Knowledge) -> Effect | None:
        """Die vermutete Wirkung einer Farbe, oder `None`."""
        ...

    def learn(self, knowledge: Knowledge) -> None:
        """Streicht Deutungen, die dem Gelernten widersprechen."""
        ...

    def guesses(self, knowledge: Knowledge) -> dict[Color, str]:
        """Vermutete Rollen der Farben, deren Wirkung der Agent noch nicht kennt."""
        ...


class ObjectAgent:
    """Ein Agent, der über Farben und Bewegung lernt statt über ganze Bilder."""

    def __init__(self, buttons: Sequence[str], advisor: ColorAdvisor | None = None) -> None:
        if not buttons:
            raise ValueError("Der Agent braucht mindestens eine Taste.")
        self.buttons = tuple(sorted(buttons))
        self.advisor = advisor
        self.knowledge = Knowledge()
        self._reason = Reason.TRY
        self._tried: set[tuple[Grid, str]] = set()

    @property
    def reason(self) -> str:
        """Warum der Agent zuletzt seine Taste gewählt hat."""
        return self._reason

    def choose(self, grid: Grid, rng: random.Random, steps_left: int) -> str:
        """Wählt die nächste Taste. `steps_left` braucht dieser Agent nicht."""
        self._reason, button = self._decide(grid, rng)
        return button

    def learn(self, before: Grid, button: str, after: Grid, won: bool) -> None:
        """Lernt aus einem Tastendruck und gibt das Gelernte an sein Vorwissen weiter."""
        if button not in self.buttons:
            raise ValueError(f"Unbekannte Taste {button!r}.")
        if button not in self.knowledge.controls:
            self._tried.add((before, button))
        self.knowledge.observe(before, button, after, won)
        if self.advisor is not None:
            self.advisor.learn(self.knowledge)

    def beliefs(self) -> dict[Color, str]:
        """Was der Agent über jede Farbe weiß oder vermutet, als kurzer Text."""
        known = self.knowledge
        found = {color: str(effect.kind) for color, effect in known.effects.items()}
        if known.player is not None:
            found[known.player] = "ich"
        if self.advisor is not None:
            guessed = self.advisor.guesses(known)
            found |= {c: f"vermutlich {role}" for c, role in guessed.items() if c not in found}
        return found

    def _decide(self, grid: Grid, rng: random.Random) -> tuple[Reason, str]:
        controls = self.knowledge.controls
        untried = [b for b in self.buttons if b not in controls and (grid, b) not in self._tried]
        if untried:
            return Reason.TRY, rng.choice(untried)
        origin = self.knowledge.position(grid)
        if origin is not None:
            for reason, effect_of, wanted in self._searches(rng):
                path = find_path(grid, origin, controls, effect_of, wanted)
                if path:
                    return reason, path[0]
        return Reason.WANDER, rng.choice(self.buttons)

    def _searches(self, rng: random.Random) -> Iterator[tuple[Reason, EffectOf, Wanted]]:
        """Die Suchen in der Reihenfolge, in der der Agent sie versucht."""
        own = self.knowledge.effects.get
        yield Reason.PLAN, own, is_win
        if self.advisor is None:
            yield Reason.EXPLORE, own, is_unknown
            return
        self.advisor.pick(rng)
        yield Reason.GUESS, self._with_guesses, is_win
        yield Reason.EXPLORE, self._with_guesses, is_unknown
        yield Reason.EXPLORE, own, is_unknown

    def _with_guesses(self, color: Color) -> Effect | None:
        """Eigenes Wissen, wo vorhanden; sonst die Vermutung des Vorwissens."""
        known = self.knowledge.effects.get(color)
        if known is not None or self.advisor is None:
            return known
        return self.advisor.effect(color, self.knowledge)
