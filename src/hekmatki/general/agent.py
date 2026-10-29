"""Der allgemeine Agent: eine Routine für jede Umgebung (ab 0.16).

Er bekommt nur die Zahl der Tasten. Nach jedem Schritt sucht er Regeln (`knowledge`), liest
daraus die Form der Umgebung ab (`form`) und plant danach (`planner`). Weiß er keinen Rat,
erkundet er: Er drückt die Taste, die er hier am seltensten probiert hat.

Ab 0.17 kennt er mehr Bausteine (Übernehmen, Ring, Schleife) und sucht, wo keine Form passt,
direkt in seinem Modell (`extended`, `search_model`; beide aus für den Stand von 0.16).

Mit einem `Detector` hält er mehrere Karten und erkennt, wann er in einer anderen Umgebung
ist (H18). Eine neue Karte beginnt leer, ab 0.17 auch ohne das alte Ziel: In einer ganz
anderen Welt führte das alte Ziel in die Irre (Ergebnis 21), und eine neue Welt ist eine neue
verborgene Ursache (Gershman 2017).

Grundlage: dieselbe Routine für jede Art von Raum (Constantinescu 2016, Aronov 2017,
Thousand-Brains-Systeme 2025), Kernwissen als wenige allgemeine Bausteine (Spelke 2022).
"""

import random
from collections import Counter, deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from hekmatki.general.detector import Decision, Detector, Kind
from hekmatki.general.env import Observation, Transition
from hekmatki.general.form import Form, find_form
from hekmatki.general.knowledge import Knowledge, RuleBook
from hekmatki.general.library import Library
from hekmatki.general.planner import plan, plan_greedy

STUCK: Final = 3
"""Hat er dieselbe Taste in derselben Lage in dieser Runde so oft gedrückt, erkundet er
stattdessen: Der Plan führt offenbar im Kreis (von Hand gewählt, ohne Grundlage)."""
NOISE_MARGIN: Final = 0.01
"""Für die Form zählen Regeln mit höchstens doppelt so viel Ausnahmen wie die beste
Bewegungsregel, plus dieser Rand (von Hand gewählt, ohne Grundlage)."""


class Planning(StrEnum):
    """Wie der Agent plant."""

    FORM = "Form + Regeln"
    GREEDY = "Regeln ohne Form"


@dataclass(frozen=True)
class MapEvent:
    """Ein Wechsel der Karte: wann, welche Art, zu welcher Karte."""

    step: int
    kind: Kind
    target: int


class GeneralAgent:
    """Ein Agent, der nichts über seine Umgebung weiß außer der Zahl der Tasten."""

    def __init__(
        self,
        actions: int,
        planning: Planning = Planning.FORM,
        library: Library | None = None,
        budget: int | None = None,
        detector: Detector | None = None,
        extended: bool = True,
        search_model: bool = True,
    ) -> None:
        if actions < 1:
            raise ValueError("Der Agent braucht mindestens eine Taste.")
        self.actions, self.planning = actions, planning
        self.library, self.budget, self.detector = library, budget, detector
        self.extended, self.search_model = extended, search_model
        self.maps = [self._fresh_map()]
        self.current = 0
        self.events: list[MapEvent] = []
        self.steps = 0
        self._tried: Counter[tuple[Observation, int]] = Counter()
        self._this_round: Counter[tuple[Observation, int]] = Counter()
        self._held: deque[tuple[int, Transition]] = deque()
        self._trial: tuple[int, RuleBook, int] | None = None
        """Verfeinerung auf Probe: Karte, Regeln davor, Schritt. Folgt binnen eines Fensters
        doch ein Kartenwechsel, war es keine Verfeinerung, und die alten Regeln gelten wieder."""
        """Überraschende Schritte, aus denen noch keine Karte gelernt hat (mit Schrittnummer)."""

    @property
    def knowledge(self) -> Knowledge:
        """Die Karte, die gerade gilt."""
        return self.maps[self.current]

    def form(self) -> Form:
        """Die Form der Umgebung nach den verlässlichen Regeln der jetzigen Karte."""
        rules = self.knowledge.rules
        tolerance = 2.0 * rules.noise_floor() + NOISE_MARGIN
        reliable = rules.programs(max_error_rate=tolerance)
        exact = rules.programs(max_error_rate=0.0)
        return find_form(reliable, exact, self.actions, rules.width, set(rules.sensors()))

    def new_place(self) -> None:
        """Eine neue Umgebung derselben Art (zum Beispiel größer): Regeln bleiben, Karte nicht."""
        self._tried.clear()
        for knowledge in self.maps:
            knowledge.forget_place()

    def begin(self, observation: Observation) -> None:
        """Beginn einer Runde."""
        self._this_round.clear()
        self.knowledge.start(observation)

    def act(self, observation: Observation, rng: random.Random) -> int:
        """Wählt eine Taste."""
        if self.planning is Planning.FORM:
            choice = plan(self.form(), self.knowledge, observation, self.actions, self.search_model)
        else:
            choice = plan_greedy(self.knowledge, observation, self.actions, rng)
        if choice is None or self._this_round[observation, choice] >= STUCK:
            choice = self._explore(observation, rng)  # Kein Rat, oder der Rat führt im Kreis.
        self._tried[observation, choice] += 1
        self._this_round[observation, choice] += 1
        return choice

    def learn(self, transition: Transition) -> None:
        """Lernt aus einem Schritt, nachdem er geprüft hat, ob die Karte noch gilt."""
        self.steps += 1
        if self.detector is None:
            self.knowledge.learn(transition)
            return
        decision = self.detector.judge(self.maps, self.current, transition)
        if decision is not None:
            self._apply(decision, transition)
            held = [*(t for _, t in self._held), transition]
            self._held.clear()
            # Die Karte, die jetzt gilt, lernt die zurückgehaltenen Schritte. Ist es eine
            # andere Karte, erfährt sie auch, wohin sie führten und ob das Ziel erreicht war.
            seen = [transition] if decision.kind == "verfeinern" else held
            for step in seen:
                self.knowledge.notice(step)
            for step in held:
                self.knowledge.learn_rules(step)
            return
        self.knowledge.notice(transition)
        if self._trial is not None and self._trial[2] <= self.steps - self.detector.window:
            self._trial = None  # Die Verfeinerung hat sich ein Fenster lang gehalten.
        if self.detector.doubts(self.knowledge, transition):
            self._held.append((self.steps, transition))
        else:
            self.knowledge.learn_rules(transition)
        while (
            self._held
            and not self.detector.deciding
            and self._held[0][0] <= self.steps - self.detector.window
        ):
            self.knowledge.learn_rules(self._held.popleft()[1])  # Doch nur Rauschen.

    def _apply(self, decision: Decision, transition: Transition) -> None:
        if decision.kind == "verfeinern":
            if self._trial is None:
                self._trial = (self.current, self.knowledge.rules.snapshot(), self.steps)
            for slot, found in decision.refined.items():
                self.knowledge.rules.replace(slot, found)
            self.events.append(MapEvent(self.steps, decision.kind, self.current))
            return
        if self._trial is not None:
            index, rules, _ = self._trial  # Doch eine andere Welt: Verfeinerung zurücknehmen.
            self.maps[index].rules = rules
            self._trial = None
        if decision.kind == "zurück":
            self.current = decision.target
        else:
            fresh = self._fresh_map()
            fresh.start(transition.before)
            if decision.kind == "neu":
                self.maps.append(fresh)
            else:
                self.maps[decision.target] = fresh
            self.current = decision.target
        self.events.append(MapEvent(self.steps, decision.kind, self.current))

    def _fresh_map(self) -> Knowledge:
        return Knowledge(self.library, self.budget, self.extended)

    def _explore(self, observation: Observation, rng: random.Random) -> int:
        counts = [self._tried[observation, action] for action in range(self.actions)]
        fewest = min(counts)
        return rng.choice([a for a, count in enumerate(counts) if count == fewest])
