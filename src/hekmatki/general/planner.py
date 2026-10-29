"""Planen mit dem, was der Agent gelernt hat (ab 0.16; Ring, Rutschen und Modell ab 0.17).

- `plan_space`: Auf Achsen mit festem Schritt (Kette, Ring, Rutschbahn) sucht der Agent einen
  Weg auf seiner Karte (A*-Suche). Wo er schon war, weiß er aus seinen Regeln, welche Schritte
  gesperrt sind und wo eine Rutschpartie endet; wo er noch nicht war, nimmt er an, dass es frei
  ist (und dass er dort halten kann), und plant neu, wenn er es besser weiß.
  Gitterzellen-Idee: Position als Koordinaten, Wege als Vektoren (Bellmund 2018,
  Constantinescu 2016).
- `plan_order`: In einer Ordnung grenzt der Agent ein: Ist der Wert zu klein, die Taste, die
  ihn steigen lässt, sonst die andere. Das ist binäre Suche, ohne dass sie programmiert wurde.
- `plan_model` (ab 0.17, H21): Passt keine Form, sucht der Agent in seinem Modell selbst: Er
  stellt sich vor, was jede Taste bewirkt, und sucht in diesen vorgestellten Beobachtungen
  den kürzesten Weg zum Ziel (Breitensuche). Das geht in jeder Welt, deren Regeln den
  nächsten Schritt ganz festlegen, auch ohne Namen für ihre Form (Karte als Graph:
  Mahadevan 2007, Stachenfeld 2017; erst Karte, dann handeln: MAP 2026).
- `plan_greedy`: der Vergleich ohne Form. Der Agent sagt für jede Taste den nächsten Schritt
  mit seinen Regeln voraus und nimmt die, die dem Ziel am nächsten kommt.

Alle geben None zurück, wenn sie keinen Rat wissen; dann erkundet der Agent.
"""

import heapq
import random
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from typing import Final

from hekmatki.general.env import Observation
from hekmatki.general.form import STEPPED, Axis, AxisKind, Form
from hekmatki.general.knowledge import Knowledge, Pair, Passage
from hekmatki.general.programs import Cycle, Keep, Leaf, Shift, Until, branch, core, predict

type Point = tuple[int, ...]
type Move = tuple[int, int, Leaf]
"""(Achse, Taste, Baustein)"""
type Passages = dict[tuple[int, int, Point], list[tuple[int, int]]]
"""(Schalter, Achse, Punkt ohne diese Achse) -> Strecken (von, bis), über die eine Schleife
hinweglief, jeweils ohne die Enden."""

SEARCH_LIMIT: Final = 50_000
"""Höchstens so viele Punkte untersucht die Wegsuche."""
MODEL_LIMIT: Final = 5_000
"""Höchstens so viele vorgestellte Beobachtungen untersucht die Suche im Modell."""
MODEL_SUPPORT: Final = 3
"""Im Modell sucht der Agent nur mit Regeln, die schon so oft ohne Ausnahme stimmten
(von Hand gewählt, ohne Grundlage)."""


def targets(form: Form, pairs: Sequence[Pair], observation: Observation) -> dict[int, int]:
    """Zielwert je Achse: aus Paaren „Achse = feste Größe“ des gelernten Ziels."""
    axes = {axis.component for axis in form.axes}
    found = {}
    for first, second in pairs:
        if first in axes and second in form.fixed:
            found[first] = observation[second]
        elif second in axes and first in form.fixed:
            found[second] = observation[first]
    return found


def plan(
    form: Form,
    knowledge: Knowledge,
    observation: Observation,
    actions: int,
    search_model: bool = True,
) -> int | None:
    """Der nächste Schritt nach der Form, sonst nach dem Modell, oder None."""
    pairs = knowledge.goal.pairs
    if not pairs:
        return None
    wanted = targets(form, pairs, observation)
    order = [a for a in form.of_kind(AxisKind.ORDER) if a.component in wanted]
    if order:
        return plan_order(order, wanted, knowledge, observation)
    if wanted:
        return plan_space(form.of_kind(*STEPPED), wanted, knowledge, observation)
    return plan_model(knowledge, observation, actions) if search_model else None


def plan_order(
    axes: Sequence[Axis], wanted: Mapping[int, int], knowledge: Knowledge, observation: Observation
) -> int | None:
    """Eingrenzen: die Taste, die den Wert in Richtung Ziel bewegt, solange sie nicht sperrt."""
    for axis in axes:
        gap = wanted[axis.component] - observation[axis.component]
        if gap == 0:
            continue
        action = axis.up if gap > 0 else axis.down
        rule = knowledge.rules.rule(action, axis.component)
        if rule is None or isinstance(branch(rule, observation), Keep):
            return None  # Gesperrt: hier hilft Eingrenzen nicht weiter.
        return action
    return None


def plan_space(
    axes: Sequence[Axis], wanted: Mapping[int, int], knowledge: Knowledge, observation: Observation
) -> int | None:
    """Kürzester Weg auf der Karte (A*), unbekannte Stellen gelten als frei."""
    moves = _moves(axes, knowledge)
    places = {_point(axes, seen): seen for seen in knowledge.seen}
    start = _point(axes, observation)
    places[start] = observation  # Hier weiß er es genau.
    passed = _passages(axes, knowledge.passed)
    bounds = _bounds(axes, list(places), wanted)
    goal = {index: wanted[a.component] for index, a in enumerate(axes) if a.component in wanted}
    rings = {index: leaf.modulus for index, _, leaf in moves if isinstance(leaf, Cycle)}
    slides = {index for index, _, leaf in moves if isinstance(leaf, Until)}

    def distance(point: Point) -> int:
        """Untere Schranke der Schritte (Rutschen kann weit tragen: zählt höchstens 1)."""
        total = 0
        for index, value in goal.items():
            gap = abs(point[index] - value)
            if index in rings:
                gap = min(gap, rings[index] - gap)
            total += min(gap, 1) if index in slides else gap
        return total

    queue = [(distance(start), 0, start, -1)]
    first_action: dict[Point, int] = {start: -1}
    for _ in range(SEARCH_LIMIT):
        if not queue:
            return None
        _, steps, point, first = heapq.heappop(queue)
        if all(point[index] == value for index, value in goal.items()):
            return None if first < 0 else first
        for index, action, leaf in moves:
            nxt = _next(point, index, leaf, knowledge, action, axes[index], places, passed, bounds)
            if nxt is None or nxt in first_action:
                continue
            first_action[nxt] = action if first < 0 else first
            heapq.heappush(queue, (steps + 1 + distance(nxt), steps + 1, nxt, first_action[nxt]))
    return None


def plan_model(knowledge: Knowledge, observation: Observation, actions: int) -> int | None:
    """Breitensuche in vorgestellten Beobachtungen bis zum Ziel (ab 0.17, H21)."""
    if knowledge.goal.holds(observation):
        return None
    first_action: dict[Observation, int] = {observation: -1}
    frontier = deque([observation])
    while frontier and len(first_action) < MODEL_LIMIT:
        here = frontier.popleft()
        for action in range(actions):
            nxt = imagine(knowledge, here, action)
            if nxt is None or nxt in first_action:
                continue
            first_action[nxt] = action if first_action[here] < 0 else first_action[here]
            if knowledge.goal.holds(nxt):
                return first_action[nxt]
            frontier.append(nxt)
    return None


def imagine(knowledge: Knowledge, observation: Observation, action: int) -> Observation | None:
    """Die Beobachtung nach dieser Taste laut den Regeln ohne Ausnahme, falls sie sie ganz
    festlegen."""
    after = []
    for component in range(len(observation)):
        found = knowledge.rules.found.get((action, component))
        if found is None or not found.exact or found.examples < MODEL_SUPPORT:
            return None
        value = None if found.program is None else predict(found.program, observation, component)
        if value is None:
            return None
        after.append(value)
    return tuple(after)


def plan_greedy(
    knowledge: Knowledge, observation: Observation, actions: int, rng: random.Random
) -> int | None:
    """Ohne Form: die Taste, deren vorhergesagter nächster Schritt dem Ziel am nächsten ist."""
    pairs = knowledge.goal.pairs
    if not pairs:
        return None
    now = _gap(pairs, observation)
    scored = []
    for action in range(actions):
        after = list(observation)
        for component in range(len(observation)):
            rule = knowledge.rules.rule(action, component)
            value = None if rule is None else predict(rule, observation, component)
            after[component] = observation[component] if value is None else value
        scored.append((_gap(pairs, after), action))
    best = min(gap for gap, _ in scored)
    if best >= now:
        return None
    return rng.choice([action for gap, action in scored if gap == best])


def _gap(pairs: Sequence[Pair], observation: Sequence[int]) -> int:
    return sum(abs(observation[i] - observation[j]) for i, j in pairs)


def _moves(axes: Sequence[Axis], knowledge: Knowledge) -> list[Move]:
    """(Achse, Taste, Baustein) für jede Bewegung mit festem Schritt."""
    moves: list[Move] = []
    for index, axis in enumerate(axes):
        for action in (axis.up, axis.down):
            rule = knowledge.rules.rule(action, axis.component)
            effect = None if rule is None else core(rule)
            if isinstance(effect, Shift | Cycle | Until):
                moves.append((index, action, effect))
    return moves


def _next(
    point: Point,
    index: int,
    leaf: Leaf,
    knowledge: Knowledge,
    action: int,
    axis: Axis,
    places: Mapping[Point, Observation],
    passed: Passages,
    bounds: Sequence[tuple[int, int]],
) -> Point | None:
    """Wohin die Taste von hier führt, nach Karte und Regeln (None: gesperrt oder hinaus)."""
    known = places.get(point)
    if known is not None and _blocked(knowledge, action, axis, known):
        return None
    match leaf:
        case Cycle(by, modulus):
            return _moved(point, index, (point[index] + by) % modulus)
        case Until(by, sensor, value):
            return _slide(point, index, (by, sensor, value), places, passed, bounds)
        case Shift(by):
            low, high = bounds[index]
            target = point[index] + by
            return _moved(point, index, target) if low <= target <= high else None
        case _:
            return None


def _slide(
    point: Point,
    index: int,
    loop: tuple[int, int, int],
    places: Mapping[Point, Observation],
    passed: Passages,
    bounds: Sequence[tuple[int, int]],
) -> Point | None:
    """Rutschen im Kopf: weiter, solange die Karte zeigt, dass es weitergeht (dort war er, oder
    er ist dort schon durchgerutscht). An einer unbekannten Stelle nimmt er an, dass er hält."""
    by, sensor, value = loop
    low, high = bounds[index]
    here = point
    while low <= here[index] + by <= high:
        here = _moved(here, index, here[index] + by)
        seen = places.get(here)
        if seen is not None:
            if seen[sensor] == value:
                break
        elif not _passes(passed, sensor, index, here):
            break
    return None if here == point else here


def _passages(axes: Sequence[Axis], passages: Iterable[Passage]) -> Passages:
    """Die Strecken aus dem Wissen, auf die Achsen der Form umgerechnet."""
    index = {axis.component: i for i, axis in enumerate(axes)}
    found: Passages = {}
    for passage in passages:
        if passage.component not in index:
            continue
        axis = index[passage.component]
        start = _point(axes, passage.start)
        key = (passage.sensor, axis, _without(start, axis))
        low, high = sorted((start[axis], passage.end))
        found.setdefault(key, []).append((low, high))
    return found


def _passes(passed: Passages, sensor: int, index: int, point: Point) -> bool:
    """Lief hier schon eine Schleife durch, ohne dass der Schalter gesetzt war?"""
    lines = passed.get((sensor, index, _without(point, index)), [])
    return any(low < point[index] < high for low, high in lines)


def _without(point: Point, index: int) -> Point:
    return (*point[:index], *point[index + 1 :])


def _moved(point: Point, index: int, value: int) -> Point:
    return (*point[:index], value, *point[index + 1 :])


def _blocked(knowledge: Knowledge, action: int, axis: Axis, observation: Observation) -> bool:
    rule = knowledge.rules.rule(action, axis.component)
    if rule is None:
        return True
    effect = branch(rule, observation)
    if isinstance(effect, Until):
        return observation[effect.sensor] == effect.value
    return isinstance(effect, Keep)


def _point(axes: Sequence[Axis], observation: Observation) -> Point:
    return tuple(observation[axis.component] for axis in axes)


def _bounds(
    axes: Sequence[Axis], points: Sequence[Point], wanted: Mapping[int, int]
) -> list[tuple[int, int]]:
    """Suchgebiet: alles, was bekannt ist, plus ein Feld Rand, und das Ziel."""
    bounds = []
    for index, axis in enumerate(axes):
        values = [point[index] for point in points]
        if axis.component in wanted:
            values.append(wanted[axis.component])
        bounds.append((min(values) - 1, max(values) + 1))
    return bounds
