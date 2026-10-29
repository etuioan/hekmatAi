"""Ein Spieler für das Ampelspiel, der lernt, wann Laufen zum Ziel führt.

Er baut sein eigenes Spielmodell: was nach welchem Zustand kam und wie oft Laufen dort
geklappt hat. Kennt er Schemata, sucht er nach jeder Runde eine Schnittmenge zwischen
seinem Spielmodell und ihnen. Findet er eine, leiht er sich das Handlungswissen des
Schemas: Wo im Alltag Handeln klappte, wird auch Laufen erwartet. Schema und Spielmodell
werden nie verschmolzen.
"""

import random
from collections.abc import Iterable, Sequence

from hekmatki.action import ActionRecord
from hekmatki.game import Action
from hekmatki.markov import MarkovModel
from hekmatki.overlap import Overlap, find_overlap
from hekmatki.schema import Schema

RUN_PRIOR_STRENGTH = 5.0
"""So vielen Laufversuchen entspricht das Vorwissen aus dem Schema."""
EXPLORATION_RATE = 0.2
"""Wahrscheinlichkeit, in einem kaum erprobten Zustand das Laufen auszuprobieren."""
ENOUGH_TRIES = 3.0
"""Ab so vielen (auch geliehenen) Versuchen gilt ein Zustand als erprobt."""
MIN_OBSERVATIONS_FOR_OVERLAP = 20
"""Erst ab so vielen Beobachtungen sucht der Spieler nach einer Schnittmenge."""


class GamePlayer:
    """Spielt, lernt aus jedem Zug und sucht nach jeder Runde eine Schnittmenge."""

    def __init__(self, symbols: Iterable[str], goal: str, schemas: Sequence[Schema] = ()) -> None:
        self.observations = MarkovModel(symbols)
        if goal not in self.observations.alphabet:
            raise ValueError(f"Das Ziel {goal!r} ist kein Symbol des Spiels.")
        self.goal = goal
        self.schemas = tuple(schemas)
        self.overlap: Overlap | None = None
        self._runs = {symbol: ActionRecord() for symbol in self.observations.alphabet}

    def choose(self, state: str, rng: random.Random) -> Action:
        """Laufen, wenn es wahrscheinlich klappt; in kaum erprobten Zuständen manchmal testen."""
        record = self._runs[state]
        if record.looks_successful():
            return Action.RUN
        if record.tries < ENOUGH_TRIES and rng.random() < EXPLORATION_RATE:
            return Action.RUN
        return Action.WAIT

    def learn(self, state: str, action: Action, outcome: str) -> None:
        """Merkt sich, was auf den Zustand folgte und ob Laufen zum Ziel führte."""
        self.observations.observe(state, outcome)
        if action is Action.RUN:
            self._runs[state] = self._runs[state].after(outcome == self.goal)

    def reflect(self) -> None:
        """Nach einer Runde: Schnittmenge mit den Schemata suchen, falls noch keine bekannt ist."""
        if self.overlap is not None or not self.schemas:
            return
        if self.observations.total_count() < MIN_OBSERVATIONS_FOR_OVERLAP:
            return
        self.overlap = find_overlap(self.observations, self.schemas)
        if self.overlap is not None:
            self._borrow_run_experience(self.overlap)

    def _borrow_run_experience(self, overlap: Overlap) -> None:
        """Übernimmt das Handlungswissen des Schemas für jeden Zustand der Schnittmenge.

        Pro Zustand wird Erfahrung im Umfang von `RUN_PRIOR_STRENGTH` Versuchen geliehen,
        mit der Erfolgsquote, die das Schema für die zugeordnete Rolle gelernt hat.
        """
        knowledge = overlap.schema.action_knowledge
        for symbol, role in overlap.binding.items():
            if role not in knowledge:
                continue
            expected = knowledge[role].success_probability()
            borrowed = ActionRecord(RUN_PRIOR_STRENGTH * expected, RUN_PRIOR_STRENGTH)
            self._runs[symbol] = self._runs[symbol].plus(borrowed)
