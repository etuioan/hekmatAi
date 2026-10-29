"""Der Entdecker: lernt ein unbekanntes Spiel, indem er gezielt Unbekanntes ausprobiert.

In jedem Schritt entscheidet er in dieser Reihenfolge:
1. Kennt er selbst schon einen Weg zum Sieg, geht er ihn. Ist er neugierig (`Curiosity`),
   prüft er vorher, ob sich ein Abstecher zu einer nie probierten Taste lohnt.
2. Sonst fragt er seinen Ratgeber (falls er Vorwissen hat, `advisor.py`): Welche Taste
   empfehlen die noch möglichen Deutungen?
3. Sonst probiert er eine Taste, die er im aktuellen Zustand noch nie gedrückt hat, oder
   geht zum nächsten Zustand, in dem es noch etwas Unbekanntes gibt (Neugier).

Widersprechen alle Deutungen den Beobachtungen, passt das Vorwissen nicht. Dann bleibt nur
noch das eigene Entdecken, ohne dass das Vorwissen weiter stört.
"""

import random
from collections.abc import Sequence

from hekmatki.advisor import Advisor
from hekmatki.curiosity import Curiosity, Detour
from hekmatki.game_schema import is_win, path_to, shortest_paths
from hekmatki.puzzle import WIN


class Explorer:
    """Ein Agent für Spiele mit unbekannten Symbolen und Tasten."""

    def __init__(
        self,
        buttons: Sequence[str],
        start: str,
        advisor: Advisor | None = None,
        curiosity: Curiosity | None = None,
    ) -> None:
        if not buttons:
            raise ValueError("Der Entdecker braucht mindestens eine Taste.")
        self.buttons = tuple(sorted(buttons))
        self.start = start
        self.advisor = advisor
        self.curiosity = curiosity
        self.model: dict[tuple[str, str], str] = {}

    def choose(self, state: str, rng: random.Random, steps_left: int) -> str:
        """Wählt die nächste Taste. `steps_left` sagt, wie lange das Spiel noch dauert."""
        own_plan = path_to(self.model, state, is_win)
        if own_plan:
            detour = self._worthwhile_detour(state, own_plan, steps_left)
            return own_plan[0] if detour is None else detour
        advice = None if self.advisor is None else self.advisor.advice(state, rng)
        if advice is not None:
            return advice
        return self._explore(state, rng)

    def learn(self, state: str, button: str, outcome: str) -> None:
        """Merkt sich den Übergang und gibt ihn an den Ratgeber weiter."""
        if button not in self.buttons:
            raise ValueError(f"Unbekannte Taste {button!r}.")
        self.model[(state, button)] = outcome
        if self.advisor is not None:
            self.advisor.learn(state, button, outcome)

    def _worthwhile_detour(self, state: str, own_plan: list[str], steps_left: int) -> str | None:
        """Der erste Schritt zum lohnendsten Abstecher, falls sich überhaupt einer lohnt."""
        if self.curiosity is None:
            return None
        round_trip = path_to(self.model, self.start, is_win)
        if not round_trip:
            return None
        from_here = shortest_paths(self.model, state)
        from_start = shortest_paths(self.model, self.start)
        best_value, best_step = 0.0, None
        for target in self._known_states():
            way = from_here.get(target)
            onward = path_to(self.model, target, is_win)
            if way is None or target not in from_start or onward is None:
                continue
            detour = Detour(
                len(way), len(from_start[target]), len(onward), len(own_plan), len(round_trip)
            )
            for button in self._untried(target):
                surprise = self.curiosity.surprise
                if self.advisor is not None and self.advisor.predicts(target, button):
                    surprise = self.curiosity.schema_surprise
                value = detour.value(surprise, steps_left)
                if value > best_value:
                    best_value, best_step = value, way[0] if way else button
        return best_step

    def _known_states(self) -> list[str]:
        """Alle Zustände, die der Agent schon gesehen hat, außer dem Sieg."""
        seen = {self.start} | {s for s, _ in self.model} | set(self.model.values())
        return sorted(seen - {WIN})

    def _explore(self, state: str, rng: random.Random) -> str:
        """Neugier: Unbekanntes hier ausprobieren oder zum nächsten Unbekannten gehen."""
        untried = self._untried(state)
        if untried:
            return rng.choice(untried)
        way = path_to(self.model, state, self._has_untried)
        if way:
            return way[0]
        return rng.choice(self.buttons)

    def _has_untried(self, state: str) -> bool:
        return state != WIN and bool(self._untried(state))

    def _untried(self, state: str) -> list[str]:
        return [b for b in self.buttons if (state, b) not in self.model]
