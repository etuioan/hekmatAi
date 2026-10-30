"""Ursachen: Wann bewirkt eine Taste etwas? (ab 0.18, H25)

Die Regeln in `knowledge` sagen für jede Größe einzeln, wie sie sich ändert. Manche Wirkung
hängt aber an einer Lage, die sich mit einem Schalter nicht sagen lässt: Eine Taste lässt
Größe 7 nur steigen, wenn Größe 3 den Wert 6 hat und Größe 9 mindestens 1 ist. Solche
Bedingungen lernt dieses Modul.

- Ein `Literal` ist eine Aussage über eine Größe: „G3 = 6“ oder „G9 ≥ 1“. Ab 0.19 auch
  über eine Gruppe von Feldern: „irgendwo in Abstand ≤ 1 steht 15“ (die Gruppen kommen aus
  `space`; eine Lage, die auf jeder Seite gleich ist).
- Ein `Event` ist, was passieren soll (oder nicht): „G7 steigt“, „G7 sinkt“, „G4 wird 11“.
- Eine `Cause` ist eine Taste mit einer Bedingung aus wenigen Literalen. Wie verlässlich sie
  ist, zählt der Agent an seinen eigenen Schritten mit.

Gelernt wird mit schrittweiser Überdeckung (Michalski 1969, Clark & Niblett 1989, Fürnkranz
1999): Erst die Bedingung, die möglichst viele Erfolge und möglichst keinen Misserfolg
abdeckt, dann für die übrigen Erfolge eine weitere. So kann ein Ereignis mehrere Ursachen
haben (Trinken am Wasser links oder am Wasser oben). Die Bedingungen sind die Teilziele für
`subgoals` (Mittel-Ziel-Analyse nach Newell & Simon 1961, STRIPS nach Fikes & Nilsson 1971).
Gezählt wird mit Bitmengen, damit es auch bei vielen Größen schnell bleibt.
"""

from collections import deque
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from hekmatki.general.env import Observation, Transition

type Partial = tuple[int | None, ...]
type Groups = tuple[tuple[int, ...], ...]
"""Gruppen von Größen, über die es Literale „eine von ihnen hat den Wert“ gibt."""
"""Eine Beobachtung, in der manche Größen unbekannt sind (vorgestellt, nicht gesehen)."""

HISTORY: Final = 400
"""So viele Schritte je Taste merkt sich das Modul als mögliche Misserfolge."""
POSITIVES: Final = 60
"""So viele Erfolge je Ereignis merkt es sich, damit seltene Erfolge nicht verloren gehen."""
RELEARN: Final = 100
"""Ohne neuen Erfolg lernt es eine Ursache erst nach so vielen neuen Schritten neu."""
MAX_LITERALS: Final = 3
"""Höchstens so viele Literale hat eine Bedingung (von Hand gewählt, ohne Grundlage)."""
MAX_CAUSES: Final = 4
"""Höchstens so viele Ursachen je Ereignis und Taste (von Hand gewählt, ohne Grundlage)."""
POOLED_RELEARN: Final = 250
"""Lagen über alle Tasten lernt es ohne neuen Erfolg erst nach so vielen Schritten neu."""
POOLED_PER_ACTION: Final = 100
"""So viele der neuesten Schritte je Taste zählen als Misserfolge (Rechenzeit)."""
POOLED_CAUSES: Final = 8
"""Höchstens so viele Lagen je Ereignis, wenn alle Tasten zusammen zählen."""
MIN_PRECISION: Final = 0.34
"""So oft muss eine Ursache mindestens wirken, vorsichtig geschätzt (von Hand gewählt)."""
MIN_HITS: Final = 2
"""Eine Ursache braucht mindestens so viele Erfolge; einer allein ist oft Zufall."""


class Kind(StrEnum):
    """Die Arten von Aussagen über eine Größe."""

    EQUAL = "="
    AT_LEAST = "≥"
    SOME = "∋"
    """Eine der Größen in `among` hat den Wert (ab 0.19)."""


@dataclass(frozen=True)
class Literal:
    """Eine Aussage über eine Größe: `G component = value` oder `G component ≥ value`; oder
    über eine Gruppe: Eine der Größen `among` hat den Wert `value` (dann ist `component` die
    erste von ihnen)."""

    component: int
    value: int
    kind: Kind = Kind.EQUAL
    among: tuple[int, ...] = ()

    @staticmethod
    def some(among: tuple[int, ...], value: int) -> "Literal":
        """„Irgendwo in dieser Gruppe steht `value`.“"""
        return Literal(among[0], value, Kind.SOME, among)

    def holds(self, observation: Partial) -> bool:
        """Gilt sie? Eine unbekannte Größe erfüllt nichts."""
        if self.kind is Kind.SOME:
            return any(observation[c] == self.value for c in self.among)
        seen = observation[self.component]
        if seen is None:
            return False
        return seen == self.value if self.kind is Kind.EQUAL else seen >= self.value

    def where(self, observation: Partial) -> list[int]:
        """Die Größen, an denen sie gerade gilt."""
        if self.kind is Kind.SOME:
            return [c for c in self.among if observation[c] == self.value]
        return [self.component] if self.holds(observation) else []

    def __str__(self) -> str:
        if self.kind is Kind.SOME:
            return f"eine von {len(self.among)} Größen = {self.value}"
        return f"G{self.component} {self.kind} {self.value}"


class Change(StrEnum):
    """Wie sich eine Größe bei einem Ereignis ändert."""

    RISES = "steigt"
    FALLS = "sinkt"
    BECOMES = "wird"


@dataclass(frozen=True)
class Event:
    """Was passieren soll: Größe `component` steigt, oder sie wird `value`."""

    component: int
    change: Change
    value: int = 0

    def happened(self, before: Observation, after: Observation) -> bool:
        """Ist es bei diesem Schritt passiert?"""
        old, new = before[self.component], after[self.component]
        match self.change:
            case Change.RISES:
                return new > old
            case Change.FALLS:
                return new < old
            case Change.BECOMES:
                return new == self.value != old


@dataclass(frozen=True)
class Cause:
    """Eine Taste, die das Ereignis bewirkt, wenn alle Literale gelten."""

    action: int
    literals: tuple[Literal, ...]
    hits: int
    """Wie oft das Ereignis folgte, als die Bedingung galt und die Taste gedrückt wurde."""
    uses: int
    """Wie oft die Bedingung galt und die Taste gedrückt wurde."""

    @property
    def precision(self) -> float:
        """Wie oft sie wirkt, vorsichtig geschätzt (Laplace: +1 / +2)."""
        return (self.hits + 1) / (self.uses + 2)

    def ready(self, observation: Partial) -> bool:
        """Gilt die ganze Bedingung?"""
        return all(literal.holds(observation) for literal in self.literals)


def events_of(transition: Transition) -> Iterator[Event]:
    """Alle Ereignisse eines Schritts: was stieg, was sank und was welchen neuen Wert bekam."""
    for component, (old, new) in enumerate(zip(transition.before, transition.after, strict=True)):
        if new != old:
            yield Event(component, Change.BECOMES, new)
            yield Event(component, Change.RISES if new > old else Change.FALLS)


class CauseBook:
    """Erfolge und Misserfolge je Taste, daraus die Ursachen jedes Ereignisses."""

    def __init__(self) -> None:
        self.history: dict[int, deque[tuple[Observation, Observation]]] = {}
        self.positives: dict[tuple[Event, int], deque[Observation]] = {}
        self.events: dict[Event, set[int]] = {}
        """Ereignis → die Tasten, nach denen es schon passiert ist."""
        self._cache: dict[tuple[Event, int], tuple[tuple[int, int], tuple[Cause, ...]]] = {}
        self._pooled: dict[
            tuple[Event, frozenset[int] | None], tuple[tuple[int, int, Groups], tuple[Cause, ...]]
        ] = {}
        self._found: dict[tuple[Event, int], int] = {}
        """Wie oft jedes Ereignis nach jeder Taste schon passiert ist (auch ältere Fälle)."""
        self._pressed: dict[int, int] = {}
        """Wie oft jede Taste gedrückt wurde."""

    def add(self, transition: Transition) -> None:
        """Merkt sich einen Schritt."""
        action = transition.action
        steps = self.history.setdefault(action, deque(maxlen=HISTORY))
        steps.append((transition.before, transition.after))
        self._pressed[action] = self._pressed.get(action, 0) + 1
        for event in events_of(transition):
            self._found[event, action] = self._found.get((event, action), 0) + 1
            store = self.positives.setdefault((event, action), deque(maxlen=POSITIVES))
            store.append(transition.before)
            self.events.setdefault(event, set()).add(action)

    def causes(self, event: Event, min_precision: float = MIN_PRECISION) -> list[Cause]:
        """Alle verlässlichen Ursachen des Ereignisses, die verlässlichste zuerst."""
        found = [
            cause
            for action in sorted(self.events.get(event, ()))
            for cause in self._learned(event, action)
            if cause.hits >= MIN_HITS and cause.precision >= min_precision
        ]
        return sorted(found, key=lambda cause: -cause.precision)

    def conditions(
        self,
        event: Event,
        min_precision: float,
        only: frozenset[int] | None = None,
        groups: Groups = (),
    ) -> list[Cause]:
        """Lagen, nach denen das Ereignis passiert, egal welche Taste (Taste -1): für Ereignisse,
        die die Welt bewirkt, nicht der Agent (ein Angriff). `only`: nur Literale über diese
        Größen. `groups`: auch Literale „eine dieser Größen hat den Wert“."""
        actions = sorted(self.events.get(event, ()))
        stamp = (
            sum(self._found.get((event, a), 0) for a in actions),
            sum(self._pressed.values()) // POOLED_RELEARN,
            groups,
        )
        cached = self._pooled.get((event, only))
        if cached is None or cached[0] != stamp:
            positives = [before for a in actions for before in self.positives[event, a]]
            negatives = [
                before
                for steps in self.history.values()
                for before, after in list(steps)[-POOLED_PER_ACTION:]
                if not event.happened(before, after)
            ]
            learned = tuple(
                Cause(-1, literals, hits, uses)
                for literals, hits, uses in cover(positives, negatives, POOLED_CAUSES, only, groups)
            )
            cached = (stamp, learned)
            self._pooled[event, only] = cached
        return [
            cause
            for cause in cached[1]
            if cause.hits >= MIN_HITS and cause.precision >= min_precision and cause.literals
        ]

    def operands(self, action: int, components: set[int]) -> set[int]:
        """Woran die Taste wirkt: die Größen in den Bedingungen ihrer Ursachen, für alles, was
        sie an den Größen `components` steigen ließ.

        Auch Bedingungen aus einem einzigen Erfolg zählen: Sie sagen, wo es sich lohnt, die Taste
        noch einmal zu probieren."""
        found: set[int] = set()
        for event, actions in self.events.items():
            if action in actions and event.change is Change.RISES and event.component in components:
                found.update(
                    literal.component
                    for cause in self._learned(event, action)
                    for literal in cause.literals
                )
        return found

    def _learned(self, event: Event, action: int) -> tuple[Cause, ...]:
        """Alle Bedingungen für eine Taste, neu gelernt nur, wenn sich die Daten geändert haben."""
        steps = self.history.get(action, deque())
        stamp = (self._found[event, action], self._pressed[action] // RELEARN)
        cached = self._cache.get((event, action))
        if cached is not None and cached[0] == stamp:
            return cached[1]
        positives = list(self.positives[event, action])
        negatives = [before for before, after in steps if not event.happened(before, after)]
        learned = tuple(
            Cause(action, literals, hits, uses)
            for literals, hits, uses in cover(positives, negatives)
        )
        self._cache[event, action] = (stamp, learned)
        return learned


def cover(
    positives: Sequence[Observation],
    negatives: Sequence[Observation],
    most: int = MAX_CAUSES,
    only: frozenset[int] | None = None,
    groups: Groups = (),
) -> list[tuple[tuple[Literal, ...], int, int]]:
    """Schrittweise Überdeckung: Bedingungen, die Erfolge abdecken und Misserfolge meiden.

    Gibt je Bedingung die Literale, die abgedeckten Erfolge und alle Fälle zurück, in denen sie
    galt. Eine leere Bedingung (die Taste wirkt immer) ist erlaubt.
    """
    if not positives:
        return []
    table = _Table(positives, negatives, only, groups)
    rules: list[tuple[tuple[Literal, ...], int, int]] = []
    remaining = table.all_positives
    while remaining and len(rules) < most:
        literals, pos, neg = _grow(table, remaining)
        hits = _count(pos & table.all_positives)
        if hits == 0:
            break
        rules.append((literals, hits, hits + _count(neg)))
        remaining &= ~pos
    return rules


def _grow(table: "_Table", remaining: int) -> tuple[tuple[Literal, ...], int, int]:
    """Eine Bedingung, Literal für Literal, solange sie dadurch besser trennt.

    Gemessen wird, welcher Anteil der Erfolge drin bleibt, minus welcher Anteil der Misserfolge
    drin bleibt (gewichtete relative Genauigkeit, Lavrač, Flach & Zupan 1999). Das hält
    Bedingungen allgemein: Ein Literal, das zwei letzte Misserfolge ausschließt, aber die
    Hälfte der Erfolge verliert, kommt nicht dazu. Bei Zufall (ein Gegner trifft nur
    manchmal) bleibt die Bedingung so kurz und deckt viel ab.
    """
    literals: list[Literal] = []
    pos, neg = remaining, table.all_negatives
    total_pos, total_neg = _count(remaining), max(_count(neg), 1)

    def separation(p: int, n: int) -> float:
        return _count(p) / total_pos - _count(n) / total_neg

    while neg and len(literals) < MAX_LITERALS:
        best: tuple[float, int, Literal, int, int] | None = None
        for literal, mask in table.candidates(pos):
            new_pos, new_neg = pos & mask, neg & mask
            hits = _count(new_pos)
            if hits == 0:
                continue
            score = separation(new_pos, new_neg)
            if best is None or (score, hits) > (best[0], best[1]):
                best = (score, hits, literal, new_pos, new_neg)
        if best is None or best[0] <= separation(pos, neg):
            break
        literals.append(best[2])
        pos, neg = best[3], best[4]
    return tuple(literals), pos, neg


class _Table:
    """Die Fälle als Bitmengen: Bit i steht für Fall i (erst die Erfolge, dann die anderen)."""

    def __init__(
        self,
        positives: Sequence[Observation],
        negatives: Sequence[Observation],
        only: frozenset[int] | None = None,
        groups: Groups = (),
    ) -> None:
        cases = [*positives, *negatives]
        self.only = only
        self.groups = [g for g in groups if only is None or set(g) <= only]
        self.all_positives = (1 << len(positives)) - 1
        self.all_negatives = ((1 << len(cases)) - 1) & ~self.all_positives
        self.masks: list[dict[int, int]] = []
        size = (len(cases) + 7) // 8
        for column in zip(*cases, strict=True):
            bits: dict[int, bytearray] = {}
            for index, value in enumerate(column):
                if value not in bits:
                    bits[value] = bytearray(size)
                bits[value][index >> 3] |= 1 << (index & 7)
            self.masks.append({v: int.from_bytes(b, "little") for v, b in bits.items()})

    def candidates(self, pos: int) -> Iterator[tuple[Literal, int]]:
        """Literale, die mindestens einen der Erfolge `pos` abdecken, mit ihrer Bitmenge."""
        for component, masks in enumerate(self.masks):
            if self.only is not None and component not in self.only:
                continue
            values = sorted(masks)
            for value in values:
                if masks[value] & pos:
                    yield Literal(component, value), masks[value]
            present = [v for v in values if masks[v] & pos]
            if present and present[0] > values[0]:
                low = present[0]
                mask = 0
                for value in values:
                    if value >= low:
                        mask |= masks[value]
                yield Literal(component, low, Kind.AT_LEAST), mask
        for group in self.groups:
            shown: set[int] = set()
            for component in group:
                shown.update(v for v, m in self.masks[component].items() if m & pos)
            for value in sorted(shown):
                mask = 0
                for component in group:
                    mask |= self.masks[component].get(value, 0)
                yield Literal.some(group, value), mask


def _count(mask: int) -> int:
    return mask.bit_count()
