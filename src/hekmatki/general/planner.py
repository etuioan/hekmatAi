"""Planen mit dem, was der Agent gelernt hat (ab 0.16).

- `plan_space`: In einem Raum sucht der Agent einen Weg auf seiner Karte (A*-Suche). Wo er
  schon war, weiß er aus seinen Regeln, welche Schritte gesperrt sind; wo er noch nicht war,
  nimmt er an, dass es frei ist, und plant neu, wenn er es besser weiß. Gitterzellen-Idee:
  Position als Koordinaten, Wege als Vektoren (Bellmund 2018, Constantinescu 2016).
- `plan_order`: In einer Ordnung grenzt der Agent ein: Ist der Wert zu klein, die Taste, die
  ihn steigen lässt, sonst die andere. Das ist binäre Suche, ohne dass sie programmiert wurde.
- `plan_greedy`: der Vergleich ohne Form. Der Agent sagt für jede Taste den nächsten Schritt
  mit seinen Regeln voraus und nimmt die, die dem Ziel am nächsten kommt.

Alle drei geben None zurück, wenn sie keinen Rat wissen; dann erkundet der Agent.
"""

import heapq
import random
from collections.abc import Mapping, Sequence

from hekmatki.general.env import Observation
from hekmatki.general.form import Axis, AxisKind, Form
from hekmatki.general.knowledge import Knowledge, Pair
from hekmatki.general.programs import Keep, Shift, branch, core, predict

type Point = tuple[int, ...]

SEARCH_LIMIT = 50_000
"""Höchstens so viele Punkte untersucht die Wegsuche."""


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


def plan(form: Form, knowledge: Knowledge, observation: Observation) -> int | None:
    """Der nächste Schritt nach der Form, oder None."""
    pairs = knowledge.goal.pairs
    if not pairs:
        return None
    wanted = targets(form, pairs, observation)
    if not wanted:
        return None
    order = [a for a in form.of_kind(AxisKind.ORDER) if a.component in wanted]
    if order:
        return plan_order(order, wanted, knowledge, observation)
    return plan_space(form.of_kind(AxisKind.SPACE), wanted, knowledge, observation)


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
    bounds = _bounds(axes, places, wanted)
    goal = {index: wanted[a.component] for index, a in enumerate(axes) if a.component in wanted}

    def distance(point: Point) -> int:
        return sum(abs(point[index] - value) for index, value in goal.items())

    queue = [(distance(start), 0, start, -1)]
    first_action: dict[Point, int] = {start: -1}
    for _ in range(SEARCH_LIMIT):
        if not queue:
            return None
        _, steps, point, first = heapq.heappop(queue)
        if distance(point) == 0:
            return None if first < 0 else first
        known = places.get(point)
        for index, action, step in moves:
            if known is not None and _blocked(knowledge, action, axes[index], known):
                continue
            nxt = (*point[:index], point[index] + step, *point[index + 1 :])
            low, high = bounds[index]
            if nxt in first_action or not low <= nxt[index] <= high:
                continue
            first_action[nxt] = action if first < 0 else first
            heapq.heappush(queue, (steps + 1 + distance(nxt), steps + 1, nxt, first_action[nxt]))
    return None


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


def _moves(axes: Sequence[Axis], knowledge: Knowledge) -> list[tuple[int, int, int]]:
    """(Achse, Taste, Schritt) für jede Bewegung im Raum."""
    moves = []
    for index, axis in enumerate(axes):
        for action in (axis.up, axis.down):
            rule = knowledge.rules.rule(action, axis.component)
            effect = None if rule is None else core(rule)
            if isinstance(effect, Shift):
                moves.append((index, action, effect.by))
    return moves


def _blocked(knowledge: Knowledge, action: int, axis: Axis, observation: Observation) -> bool:
    rule = knowledge.rules.rule(action, axis.component)
    return rule is None or isinstance(branch(rule, observation), Keep)


def _point(axes: Sequence[Axis], observation: Observation) -> Point:
    return tuple(observation[axis.component] for axis in axes)


def _bounds(
    axes: Sequence[Axis], places: Mapping[Point, Observation], wanted: Mapping[int, int]
) -> list[tuple[int, int]]:
    """Suchgebiet: alles, was gesehen wurde, plus ein Feld Rand, und das Ziel."""
    bounds = []
    for index, axis in enumerate(axes):
        values = [point[index] for point in places]
        if axis.component in wanted:
            values.append(wanted[axis.component])
        bounds.append((min(values) - 1, max(values) + 1))
    return bounds
