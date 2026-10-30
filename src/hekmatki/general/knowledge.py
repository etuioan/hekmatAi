"""Was der allgemeine Agent über eine Umgebung weiß (ab 0.16).

- `RuleBook`: für jede Taste und Größe eine Regel (ein Programm), aus eigenen Schritten
  gesucht. Eine Regel wird neu gesucht, wenn sie noch fehlt, wenn eine Regel ohne Ausnahme
  plötzlich danebenliegt oder wenn sich die Daten seit der letzten Suche verdoppelt haben.
- `GoalBook`: woran man erkennt, dass das Ziel erreicht ist. Die Grammatik der Ziele ist
  klein: Bestimmte Größen stimmen paarweise überein (Position = Zielposition,
  Schlüssel = gesuchter Schlüssel). Ohne Grundlage, siehe docs/PAPER_ZUORDNUNG.md.
- `Knowledge`: beides zusammen, dazu die besuchten Beobachtungen (die Karte) und welche Regeln
  einen Schritt richtig vorausgesagt haben (für H18, siehe `detector`). Ab 0.17 auch die
  Stellen, über die eine Schleife hinweggelaufen ist: Lief „+1 bis Schalter“ fünfmal, war der
  Schalter an den vier Zwischenstellen nicht gesetzt. Das folgt aus der Bedeutung der Schleife,
  nicht aus der Welt (Programmspur wie bei Ellis 2018 und Cropper 2020). Ab 0.18 auch die
  Ursachen: unter welcher Bedingung eine Taste etwas bewirkt (siehe `causes`).
"""

import copy
import math
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations
from statistics import median
from typing import Final

from hekmatki.general.causes import CauseBook
from hekmatki.general.env import Observation, Transition
from hekmatki.general.library import Library
from hekmatki.general.programs import Cycle, Keep, Program, Shift, Until, core, fits
from hekmatki.general.space import Space
from hekmatki.general.synthesis import Example, Found, description_bits, synthesize

MAX_EXAMPLES: Final = 300
"""So viele Schritte je Taste merkt sich der Agent für die Regelsuche (die neuesten)."""

REFRESH: Final = 200
"""Eine Regel mit Ausnahmen sucht der Agent spätestens nach so vielen neuen Schritten der
Taste neu (ab 0.18; vorher erst, wenn sich die Daten verdoppelt hatten)."""

MIN_FOR_NOISE: Final = 20
"""Erst ab so vielen Beispielen zählt eine Regel für die Schätzung des Rauschens."""

type Slot = tuple[int, int]
"""(Taste, Größe)"""
type Pair = tuple[int, int]


class RuleBook:
    """Die Regeln einer Umgebung, eine je Taste und Größe."""

    def __init__(
        self, library: Library | None = None, budget: int | None = None, extended: bool = True
    ) -> None:
        self.library, self.budget, self.extended = library, budget, extended
        self.examples: dict[int, deque[Example]] = {}
        self.found: dict[Slot, Found] = {}
        self.searches: list[tuple[Slot, Found]] = []
        """Jede Suche mit ihrem Ergebnis, für den Aufwand."""
        self._seen: dict[int, int] = {}
        self._searched_at: dict[Slot, int] = {}
        self._fresh: dict[int, list[Example]] = {}
        self._values: dict[int, set[int]] = {}

    def add(self, transition: Transition) -> None:
        """Merkt sich einen Schritt; gesucht wird erst bei `update`."""
        example = Example(transition.before, transition.after)
        action = transition.action
        self.examples.setdefault(action, deque(maxlen=MAX_EXAMPLES)).append(example)
        self._fresh.setdefault(action, []).append(example)
        self._seen[action] = self._seen.get(action, 0) + 1
        for observation in (transition.before, transition.after):
            for component, value in enumerate(observation):
                values = self._values.setdefault(component, set())
                if len(values) < 3:
                    values.add(value)

    def update(self) -> None:
        """Sucht die Regeln neu, die es nötig haben."""
        for action, examples in self.examples.items():
            for component in range(len(examples[0].before)):
                slot = (action, component)
                if self._stale(slot):
                    found = self.search(examples, component)
                    self.found[slot] = found
                    self.searches.append((slot, found))
                    self._searched_at[slot] = self._seen[action]
            self._fresh[action] = []

    @property
    def width(self) -> int:
        """Zahl der Größen einer Beobachtung (0, solange nichts gesehen wurde)."""
        return len(self._values)

    def sensors(self) -> dict[int, tuple[int, int]]:
        """Schalter: Größen, die bisher genau zwei Werte hatten."""
        found = {}
        for component, values in self._values.items():
            if len(values) == 2:
                low, high = sorted(values)
                found[component] = (low, high)
        return found

    def noise_floor(self) -> float:
        """Geschätztes Rauschen der Welt: typische Fehlerquote der Regeln, die etwas bewegen.

        Die erwartete Unsicherheit (Yu & Dayan 2005) als eine Zahl: Wenn die Bewegungsregeln
        typischerweise in 8 % der Fälle danebenliegen, ist die Welt wohl so rutschig.
        """
        rates = [
            f.errors / f.examples
            for f in self.found.values()
            if f.program is not None
            and f.examples >= MIN_FOR_NOISE
            and not isinstance(core(f.program), Keep)
        ]
        return median(rates) if rates else 0.0

    def rule(self, action: int, component: int) -> Program | None:
        """Die Regel für diese Taste und Größe, falls es eine gibt."""
        found = self.found.get((action, component))
        return None if found is None else found.program

    def programs(self, max_error_rate: float = 1.0) -> dict[Slot, Program]:
        """Alle Regeln, die höchstens so oft danebenliegen (0: nur Regeln ohne Ausnahme)."""
        return {
            slot: f.program
            for slot, f in self.found.items()
            if f.program is not None and f.errors <= max_error_rate * f.examples
        }

    def blocked_moves(self, max_error_rate: float) -> dict[Slot, Program]:
        """Bewegungen, die nur danebenliegen, weil die Größe blieb (ab 0.18).

        Ein Schritt nach rechts, der gegen einen Baum läuft, bleibt stehen. Das ist keine
        Ausnahme vom Raum, sondern eine Sperre, wie die Wand, die `planner` schon kennt. Hier
        zählen nur die Fehler, bei denen sich die Größe anders änderte als vorhergesagt.
        """
        found = {}
        for (action, component), f in self.found.items():
            program = f.program
            if program is None or f.exact or not isinstance(core(program), Shift | Cycle | Until):
                continue
            moved = [e for e in self.examples[action] if e.after[component] != e.before[component]]
            wrong = sum(not fits(program, e.before, e.after, component) for e in moved)
            if moved and wrong <= max_error_rate * len(moved):
                found[action, component] = program
        return found

    def refine(self, slot: Slot, extra: Sequence[Example]) -> Found | None:
        """Gibt es eine Regel, die die alten Schritte so gut erklärt wie die jetzige und die
        neuen ebenso? Dann war die Regel nur unvollständig, die Welt ist dieselbe (H16)."""
        current = self.found.get(slot)
        if current is None:
            return None
        old = list(self.examples.get(slot[0], ()))
        trial = self.search([*old, *extra], slot[1])
        rate = current.errors / max(current.examples, 1)
        if explains(trial.program, old, slot[1], rate) and explains(
            trial.program, extra, slot[1], rate
        ):
            return trial
        return None

    def fit_alone(self, slot: Slot, extra: Sequence[Example]) -> Found | None:
        """Erklärt eine andere Regel allein die neuen Schritte gut, und zwar kürzer als die alte
        Regel mit ihren Ausnahmen? Das spricht für eine andere Welt (Vergleich der
        Beschreibungslängen, damit nicht jede Handvoll Schritte eine eigene Regel bekommt)."""
        current = self.found.get(slot)
        if current is None or current.program is None:
            return None
        trial = self.search(extra, slot[1])
        rate = current.errors / max(current.examples, 1)
        old_errors = sum(not fits(current.program, e.before, e.after, slot[1]) for e in extra)
        shorter = description_bits(trial.program, trial.errors, len(extra)) < description_bits(
            None, old_errors, len(extra)
        )
        return trial if shorter and explains(trial.program, extra, slot[1], rate) else None

    def replace(self, slot: Slot, found: Found) -> None:
        """Setzt eine verfeinerte Regel ein."""
        self.found[slot] = found
        self.searches.append((slot, found))
        self._searched_at[slot] = self._seen.get(slot[0], 0)

    def search(self, examples: Sequence[Example], component: int) -> Found:
        """Sucht eine Regel für diese Beispiele, mit dem Wissen dieser Karte."""
        return synthesize(
            examples, component, self.sensors(), self.library, self.budget, self.extended
        )

    def _stale(self, slot: Slot) -> bool:
        action, component = slot
        last = self._searched_at.get(slot)
        if last is None:
            return True
        if self._seen[action] >= 2 * last:
            return True
        found = self.found[slot]
        if not found.exact and self._seen[action] - last >= REFRESH:
            return True  # Eine Regel mit Ausnahmen: ab und zu neu suchen, ob es Besseres gibt.
        fresh = self._fresh.get(action, [])
        return found.exact and any(
            found.program is not None and not fits(found.program, e.before, e.after, component)
            for e in fresh
        )


def explains(
    program: Program | None, examples: Sequence[Example], component: int, rate: float
) -> bool:
    """Liegt die Regel nicht öfter daneben, als bei Fehlerquote `rate` zu erwarten ist?

    Mit zwei Standardabweichungen Spielraum (Poisson-Näherung) und einem Fehler Vorschuss.
    """
    if program is None:
        return False
    errors = sum(not fits(program, e.before, e.after, component) for e in examples)
    expected = rate * len(examples)
    return errors <= expected + 2.0 * math.sqrt(expected) + 1.0


def learn_goal(
    reached: Sequence[Observation], missed: Iterable[Observation]
) -> tuple[Pair, ...] | None:
    """Die kleinste Menge von Größenpaaren, die bei jedem Erfolg übereinstimmen und bei jedem
    Misserfolg nicht alle (gierige Mengenüberdeckung). None, wenn es keine solche gibt."""
    if not reached:
        return None
    width = len(reached[0])
    pairs = [
        (i, j)
        for i, j in combinations(range(width), 2)
        if all(seen[i] == seen[j] for seen in reached)
    ]
    successes = set(reached)
    uncovered = [seen for seen in missed if seen not in successes]
    chosen: list[Pair] = []
    while uncovered:
        if not pairs:
            return None
        best = max(pairs, key=lambda p: sum(seen[p[0]] != seen[p[1]] for seen in uncovered))
        covered = [seen for seen in uncovered if seen[best[0]] != seen[best[1]]]
        if not covered:
            return None
        chosen.append(best)
        uncovered = [seen for seen in uncovered if seen[best[0]] == seen[best[1]]]
    return tuple(sorted(chosen))


class GoalBook:
    """Woran der Agent erkennt, dass er am Ziel ist."""

    def __init__(self) -> None:
        self.reached: list[Observation] = []
        self.missed: deque[Observation] = deque(maxlen=MAX_EXAMPLES)
        self.pairs: tuple[Pair, ...] | None = None

    def add(self, observation: Observation, reached: bool) -> None:
        """Merkt sich eine Beobachtung und lernt das Ziel neu, wenn es nötig ist."""
        if reached:
            self.reached.append(observation)
        else:
            self.missed.append(observation)
        if reached or self.holds(observation):
            self.pairs = learn_goal(self.reached, self.missed)

    def holds(self, observation: Observation) -> bool:
        """Sagt das gelernte Ziel „erreicht“?"""
        if self.pairs is None:
            return False
        return all(observation[i] == observation[j] for i, j in self.pairs)


@dataclass(frozen=True)
class Passage:
    """Eine Schleife lief von `start` aus über Größe `component` bis zum Wert `end`. An allen
    Stellen echt dazwischen war der Schalter `sensor` nicht gesetzt, sonst hätte sie dort
    gehalten. Von diesen Stellen weiß der Agent nur das: Die übrigen Größen sind die von
    `start`, ihre Schalter hat er nie gesehen."""

    sensor: int
    component: int
    start: Observation
    end: int


@dataclass(frozen=True)
class Check:
    """Hat eine Regel einen Schritt richtig vorausgesagt, und wie verlässlich ist sie sonst?"""

    slot: Slot
    reliability: float
    hit: bool


class Knowledge:
    """Regeln, Ziel und Karte einer Umgebung."""

    def __init__(
        self, library: Library | None = None, budget: int | None = None, extended: bool = True
    ) -> None:
        self.rules = RuleBook(library, budget, extended)
        self.goal = GoalBook()
        self.seen: set[Observation] = set()
        self.passed: set[Passage] = set()
        """Strecken, über die eine Schleife hinweglief (siehe `Passage`)."""
        self.causes = CauseBook()
        """Wann eine Taste etwas bewirkt (ab 0.18, siehe `causes`)."""
        self.space = Space()
        """Welches Sichtfeld neben welchem liegt (ab 0.19, siehe `space`)."""

    def forget_place(self) -> None:
        """Eine neue Umgebung: Die Karte gilt nicht mehr, Regeln und Ziel schon."""
        self.seen.clear()
        self.passed.clear()

    def start(self, observation: Observation) -> None:
        """Beginn einer Runde: die erste Beobachtung."""
        self.seen.add(observation)
        self.goal.add(observation, reached=False)

    def snapshot(self) -> "Knowledge":
        """Eine Kopie des ganzen Stands: Regeln, Ziel, Karte, Ursachen und Raum. Die
        Bibliothek wird geteilt, nicht kopiert: Sie gehört allen Karten."""
        library = self.rules.library
        return copy.deepcopy(self, memo={} if library is None else {id(library): library})

    def learn(self, transition: Transition) -> None:
        """Lernt aus einem Schritt: Regeln, Ziel und Karte. Ab 0.22 der einzige Weg, auf dem
        eine Karte lernt, damit alle Teile immer denselben Schritt kennen."""
        self._notice(transition)
        self._learn_rules(transition)

    def _notice(self, transition: Transition) -> None:
        """Nur Ziel und Karte: wo der Schritt hinführte und ob das Ziel erreicht ist."""
        self.goal.add(transition.after, transition.reached)
        self.seen.add(transition.after)
        self.passed.update(self._passed(transition))

    def _passed(self, transition: Transition) -> list[Passage]:
        """Die Strecken der Schleifen, die bei diesem Schritt mehr als einmal liefen."""
        before, after = transition.before, transition.after
        found = []
        for component, (old, new) in enumerate(zip(before, after, strict=True)):
            rule = self.rules.rule(transition.action, component)
            loop = None if rule is None else core(rule)
            if not isinstance(loop, Until) or abs(new - old) <= abs(loop.by):
                continue  # Keine Schleife, oder sie lief nur einmal.
            if fits(loop, before, after, component):
                found.append(Passage(loop.sensor, component, before, new))
        return found

    def _learn_rules(self, transition: Transition) -> None:
        """Nur die Regeln und Ursachen."""
        self.rules.add(transition)
        self.rules.update()
        self.causes.add(transition)
        self.space.observe(transition)

    def checks(self, transition: Transition) -> list[Check]:
        """Für jede Regel dieser Taste: lag sie richtig?"""
        found = []
        for component in range(len(transition.before)):
            slot = (transition.action, component)
            rule = self.rules.found.get(slot)
            if rule is None or rule.program is None:
                continue
            hit = fits(rule.program, transition.before, transition.after, component)
            found.append(Check(slot, rule.reliability, hit))
        return found
