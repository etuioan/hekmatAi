"""Regel-Schemata: Was ein Spiel ausmacht, unabhängig von seiner Größe.

Ein Zustands-Schema (`game_schema.py`) merkt sich einzelne Zustände und passt deshalb nur
auf gleich große Spiele. Ein Regel-Schema beschreibt stattdessen, *wo* etwas passiert:
„Benutzen an der Wand in der einen Richtung wechselt den Modus (Schlüssel nehmen), danach
gewinnt Benutzen an der Wand in der anderen Richtung.“

Grundannahme, wie ein Kernwissen bei ARC: Das Spiel ist ein Gang mit zwei Tasten zum
Bewegen und einer zum Benutzen. Welche Taste welche ist, weiß der Agent nicht. Für jede
mögliche Belegung (`Controls`) zeichnet er eine Karte (`CorridorMap`): Position und Modus
jedes Symbols, gezählt vom Start. Widerspricht sich die Karte, ist die Belegung falsch.

Orte werden auf zwei Arten beschrieben (`Place`): als Wand in einer Richtung oder als feste
Schrittzahl vom Start. Aus einem Spiel lassen sich oft beide ablesen. Erst ein Spiel mit
anderer Größe zeigt, welche Beschreibung trägt (`revised`).

Vorwärts und rückwärts sind nur Namen: Eine gespiegelte Deutung erklärt jedes Spiel genauso
gut. Deshalb vergleicht `revised` neue Regeln in beiden Richtungen mit den alten, und der
Ratgeber folgt immer einer Deutung, bis sie widerlegt ist. Würde er stattdessen abstimmen,
stünden gespiegelte Deutungen stets gegeneinander und er liefe hin und her.
"""

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import permutations, product
from typing import Literal

from hekmatki.game_schema import Transitions
from hekmatki.puzzle import WIN

FORWARD = 1
BACKWARD = -1

Spot = tuple[int, int]
"""Position im Gang (vom Start aus gezählt) und Modus (wie oft schon etwas wechselte)."""


class Effect(StrEnum):
    """Was Benutzen an einem Ort bewirkt."""

    NOTHING = "nichts"
    SWITCH = "wechsel"
    WIN = "sieg"


@dataclass(frozen=True)
class Controls:
    """Eine Deutung der Tasten: vorwärts, rückwärts, benutzen."""

    forward: str
    backward: str
    use: str

    def direction(self, button: str) -> int | None:
        """+1 oder -1 für Bewegungstasten, `None` für Benutzen."""
        directions = {self.forward: FORWARD, self.backward: BACKWARD, self.use: None}
        if button not in directions:
            raise ValueError(f"Unbekannte Taste {button!r}.")
        return directions[button]

    def toward(self, direction: int) -> str:
        """Die Taste, die in Richtung `direction` bewegt."""
        return self.forward if direction == FORWARD else self.backward


def all_controls(buttons: Sequence[str]) -> list[Controls]:
    """Alle Deutungen von drei Tasten."""
    if len(buttons) != 3:
        raise ValueError(f"Ein Gang hat genau drei Tasten, gegeben waren {len(buttons)}.")
    return [Controls(*order) for order in permutations(sorted(buttons))]


@dataclass(frozen=True)
class CorridorMap:
    """Die Karte eines Spiels unter einer Tastendeutung."""

    spots: Mapping[str, Spot]
    """Symbol → (Position, Modus)."""
    walls: frozenset[tuple[int, int]]
    """(Position, Richtung), in der es nicht weitergeht."""
    uses: Mapping[Spot, Effect]
    """Was Benutzen an einem Ort bewirkt hat."""

    def has_position(self, position: int) -> bool:
        """True, wenn an dieser Position schon ein Symbol gesehen wurde (in irgendeinem Modus)."""
        return any(p == position for p, _ in self.spots.values())


def corridor_map(model: Transitions, start: str, controls: Controls) -> CorridorMap | None:
    """Zeichnet die Karte aus allen bekannten Übergängen. `None`, wenn sie sich widerspricht."""
    spots: dict[str, Spot] = {start: (0, 0)}
    walls: set[tuple[int, int]] = set()
    uses: dict[Spot, Effect] = {}
    pending = sorted(model.items())
    while ready := [item for item in pending if item[0][0] in spots]:
        pending = [item for item in pending if item[0][0] not in spots]
        for (state, button), outcome in ready:
            position, mode = spots[state]
            direction = controls.direction(button)
            target: Spot | None = None
            if direction is None:
                effect = _use_effect(state, outcome)
                uses[(position, mode)] = effect
                target = (position, mode + 1) if effect is Effect.SWITCH else None
            elif outcome == WIN:
                return None
            elif outcome == state:
                walls.add((position, direction))
            else:
                target = (position + direction, mode)
            if target is not None and not _place(spots, outcome, target):
                return None
    if not _walls_hold(walls, spots.values()):
        return None
    return CorridorMap(spots, frozenset(walls), uses)


def _use_effect(state: str, outcome: str) -> Effect:
    if outcome == WIN:
        return Effect.WIN
    return Effect.NOTHING if outcome == state else Effect.SWITCH


def _place(spots: dict[str, Spot], symbol: str, spot: Spot) -> bool:
    """Trägt ein Symbol ein. False, wenn es schon woanders steht oder der Ort belegt ist."""
    if symbol in spots:
        return spots[symbol] == spot
    if spot in spots.values():
        return False
    spots[symbol] = spot
    return True


def _walls_hold(walls: Iterable[tuple[int, int]], spots: Iterable[Spot]) -> bool:
    """Hinter einer Wand darf kein Symbol liegen."""
    positions = [position for position, _ in spots]
    return all(all((p - wall) * direction <= 0 for p in positions) for wall, direction in walls)


@dataclass(frozen=True, order=True)
class Place:
    """Eine Beschreibung eines Ortes im Gang, die nicht an Symbole gebunden ist."""

    kind: Literal["wand", "start"]
    direction: int
    steps: int = 0
    """Nur für „start“: so viele Schritte in `direction` vom Start."""

    def matches(self, position: int, corridor: CorridorMap) -> bool | None:
        """Liegt `position` an diesem Ort? `None`, wenn die Karte das noch nicht verrät."""
        if self.kind == "start":
            return position == self.direction * self.steps
        if (position, self.direction) in corridor.walls:
            return True
        if corridor.has_position(position + self.direction):
            return False
        return None

    def reachable(self, corridor: CorridorMap) -> bool:
        """False, wenn der Ort laut Karte hinter einer Wand läge."""
        if self.kind == "wand":
            return True
        return _walls_hold(corridor.walls, [(self.direction * self.steps, 0)])

    def mirrored(self) -> "Place":
        """Derselbe Ort, wenn vorwärts und rückwärts vertauscht werden."""
        return Place(self.kind, -self.direction, self.steps)

    @property
    def undirected(self) -> str:
        """Die Beschreibung ohne Richtung, etwa „Wand“ oder „2 Schritte vom Start“."""
        if self.kind == "wand":
            return "Wand"
        unit = "Schritt" if self.steps == 1 else "Schritte"
        return f"{self.steps} {unit} vom Start"

    def __str__(self) -> str:
        way = "vorwärts" if self.direction == FORWARD else "rückwärts"
        return f"{self.undirected} ({way})"


def places_of(position: int, corridor: CorridorMap) -> frozenset[Place]:
    """Alle Beschreibungen, denen die Karte für diese Position nicht widerspricht.

    Eine Wand, die der Agent nie angestoßen hat, kann trotzdem da sein. Nur ein Symbol
    dahinter schließt sie aus.
    """
    direction = FORWARD if position >= 0 else BACKWARD
    walls = (Place("wand", d) for d in (FORWARD, BACKWARD))
    possible = {wall for wall in walls if wall.matches(position, corridor) is not False}
    return frozenset({Place("start", direction, abs(position))} | possible)


@dataclass(frozen=True)
class Event:
    """Was im jeweiligen Modus passiert und an welchem Ort (mögliche Beschreibungen)."""

    effect: Effect
    places: frozenset[Place]

    def mirrored(self) -> "Event":
        """Dasselbe Ereignis mit vertauschten Richtungen."""
        return Event(self.effect, frozenset(place.mirrored() for place in self.places))


@dataclass(frozen=True)
class RuleSchema:
    """Die Regeln eines Spiels: pro Modus ein Ereignis, das letzte ist der Sieg."""

    name: str
    events: tuple[Event, ...]

    def __post_init__(self) -> None:
        if not self.events or self.events[-1].effect is not Effect.WIN:
            raise ValueError(f"Regel-Schema {self.name!r} muss mit einem Sieg enden.")
        if any(not event.places for event in self.events):
            raise ValueError(f"Regel-Schema {self.name!r}: Jedes Ereignis braucht einen Ort.")

    @property
    def effects(self) -> tuple[Effect, ...]:
        """Die Wirkungen der Ereignisse in ihrer Reihenfolge."""
        return tuple(event.effect for event in self.events)

    def mirrored(self) -> "RuleSchema":
        """Dieselben Regeln mit vertauschten Richtungen."""
        return RuleSchema(self.name, tuple(event.mirrored() for event in self.events))


def rules_from_map(name: str, corridor: CorridorMap) -> RuleSchema | None:
    """Liest die Regeln aus einer Karte ab. `None`, wenn sie dafür nicht reicht.

    Pro Modus muss genau ein Ort bekannt sein, an dem Benutzen etwas bewirkt hat.
    """
    events: list[Event] = []
    for mode in range(len(corridor.uses) + 1):
        effects = [
            (s, e) for s, e in corridor.uses.items() if s[1] == mode and e is not Effect.NOTHING
        ]
        if len(effects) != 1:
            return None
        (position, _), effect = effects[0]
        events.append(Event(effect, places_of(position, corridor)))
        if effect is Effect.WIN:
            return RuleSchema(name, tuple(events))
    return None


def learn_rules(
    name: str, model: Transitions, start: str, buttons: Sequence[str]
) -> RuleSchema | None:
    """Regeln aus einem gespielten Spiel: unter der ersten Tastendeutung, die passt."""
    for controls in all_controls(buttons):
        corridor = corridor_map(model, start, controls)
        rules = None if corridor is None else rules_from_map(name, corridor)
        if rules is not None:
            return rules
    return None


def revised(old: RuleSchema, new: RuleSchema) -> RuleSchema:
    """Verbindet bisherige Regeln mit den Regeln eines weiteren Spiels.

    Die neuen Regeln werden in der Richtung genommen, in der sie am meisten mit den alten
    gemeinsam haben. Pro Ereignis bleiben die Beschreibungen, die zu beiden passen. Passt
    keine, war das alte Wissen zu eng, und die neue Beschreibung gilt. Haben die Spiele
    verschiedene Abläufe, gelten ganz die neuen Regeln.
    """
    if old.effects != new.effects:
        return new
    candidates = (new, new.mirrored())
    aligned = max(candidates, key=lambda rules: _overlap(old, rules))
    events = tuple(
        Event(was.effect, (was.places & now.places) or now.places)
        for was, now in zip(old.events, aligned.events, strict=True)
    )
    return RuleSchema(old.name, events)


def rules_after_game(
    name: str,
    rules: RuleSchema | None,
    model: Transitions,
    start: str,
    buttons: Sequence[str],
) -> RuleSchema | None:
    """Nach einem Spiel: Regeln ablesen und mit den bisherigen verbinden.

    Lassen sich aus dem Spiel keine Regeln ablesen (etwa weil der Agent nie gewann),
    bleiben die bisherigen.
    """
    new = learn_rules(name, model, start, buttons)
    if new is None:
        return rules
    return new if rules is None else revised(rules, new)


def _overlap(first: RuleSchema, second: RuleSchema) -> int:
    """Wie viele Ortsbeschreibungen beide Regel-Schemata teilen."""
    return sum(len(a.places & b.places) for a, b in zip(first.events, second.events, strict=True))


@dataclass(frozen=True)
class RuleHypothesis:
    """Eine Deutung: Tastenbelegung plus eine Ortsbeschreibung pro Ereignis."""

    controls: Controls
    places: tuple[Place, ...]


class RuleAdvisor:
    """Ratgeber aus einem Regel-Schema. Passt auch auf Gänge anderer Länge.

    Er folgt einer zufällig gewählten Deutung, bis sie widerlegt ist, und wählt dann die
    nächste. So prüft jeder Weg eine Deutung zu Ende, statt zwischen gespiegelten Deutungen
    hin und her zu pendeln.
    """

    def __init__(self, rules: RuleSchema, buttons: Sequence[str], start: str) -> None:
        self.rules = rules
        self.start = start
        self.model: dict[tuple[str, str], str] = {}
        choices = list(product(*(sorted(event.places) for event in rules.events)))
        self.hypotheses = [
            RuleHypothesis(controls, places)
            for controls, places in product(all_controls(buttons), choices)
        ]
        self.followed: RuleHypothesis | None = None
        self._maps = self._draw_maps()

    def advice(self, state: str, rng: random.Random) -> str | None:
        """Die Taste, die die verfolgte Deutung hier drücken würde."""
        if self.followed not in self.hypotheses:
            self.followed = rng.choice(self.hypotheses) if self.hypotheses else None
        if self.followed is None:
            return None
        return self._next_button(self.followed, state)

    def learn(self, state: str, button: str, outcome: str) -> None:
        """Zeichnet die Karten neu und streicht Deutungen, die ihnen widersprechen."""
        self.model[(state, button)] = outcome
        self._maps = self._draw_maps()
        self.hypotheses = [h for h in self.hypotheses if self._holds(h)]

    def predicts(self, state: str, button: str) -> bool:
        """Regel-Schemata legen sich nie auf ein einzelnes Ergebnis fest."""
        return False

    def fits(self) -> bool:
        """True, solange noch mindestens eine Deutung möglich ist."""
        return bool(self.hypotheses)

    def _draw_maps(self) -> dict[Controls, CorridorMap | None]:
        controls = {h.controls for h in self.hypotheses}
        return {c: corridor_map(self.model, self.start, c) for c in controls}

    def _holds(self, hypothesis: RuleHypothesis) -> bool:
        """Passt die Deutung zur Karte und zu allem, was Benutzen bisher bewirkt hat?"""
        corridor = self._maps[hypothesis.controls]
        if corridor is None or not all(p.reachable(corridor) for p in hypothesis.places):
            return False
        for (position, mode), effect in corridor.uses.items():
            if mode >= len(self.rules.events):
                return False
            expected = self.rules.events[mode].effect
            at_place = hypothesis.places[mode].matches(position, corridor)
            if effect is Effect.NOTHING and at_place is True:
                return False
            if effect is not Effect.NOTHING and (effect is not expected or at_place is False):
                return False
        return True

    def _next_button(self, hypothesis: RuleHypothesis, state: str) -> str | None:
        """Was die Deutung hier drücken würde: am Ort benutzen, sonst hingehen."""
        corridor = self._maps[hypothesis.controls]
        spot = None if corridor is None else corridor.spots.get(state)
        if corridor is None or spot is None or spot[1] >= len(hypothesis.places):
            return None
        position, mode = spot
        place = hypothesis.places[mode]
        if place.matches(position, corridor) is True:
            return hypothesis.controls.use
        if place.kind == "wand":
            return hypothesis.controls.toward(place.direction)
        target = place.direction * place.steps
        return hypothesis.controls.toward(FORWARD if target > position else BACKWARD)
