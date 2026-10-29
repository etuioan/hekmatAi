"""Pläne im Weltmodell suchen: zum Sieg, oder zur nächsten offenen Frage.

Suche über Szenen, mit dem Simulator als Regelwerk. Am billigsten ist ein Weg, der keine
Kiste in eine Ecke schiebt, dann möglichst wenige Kisten verschiebt und dann möglichst kurz
ist: Eine Kiste in der Ecke sitzt für immer fest, eine verschobene vielleicht, ein Schritt
mehr schadet nie. Gefunden wird der billigste Weg zum Sieg. Gibt es keinen, ist
der Plan der billigste Weg zu einem Schritt, dessen Ausgang das Modell nicht kennt:
hingehen und ausprobieren.

Schritte, die die Figur zum Start zurückschicken (Fallen und die Neustart-Taste), nutzt die
Suche nur, wenn man es ihr erlaubt; dann dienen sie als Neustart, etwa wenn eine Kiste
festsitzt.
"""

import heapq
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import count

from hekmatki.grid.simulation import Prediction, Scene, Simulator

SEARCH_LIMIT = 30_000
"""So viele Szenen untersucht die Suche höchstens."""


class Goal(StrEnum):
    """Wozu ein Plan dient."""

    WIN = "gewinnen"
    LEARN = "etwas herausfinden"


@dataclass(frozen=True)
class Plan:
    """Eine Tastenfolge und was das Modell nach jedem Druck erwartet."""

    goal: Goal
    buttons: tuple[str, ...]
    expected: tuple[Scene | None, ...]
    """Die erwartete Szene nach jedem Druck; `None` nach Sieg oder offener Frage."""
    question: str | None = None
    restarts: bool = False
    """Der Plan nutzt eine Falle oder die Neustart-Taste als Neustart."""


@dataclass(frozen=True)
class SearchResult:
    """Der gefundene Plan (oder keiner) und ob die Suche alles Erreichbare untersucht hat."""

    plan: Plan | None
    complete: bool


Cost = tuple[int, int, int]
"""(Kisten in Ecken, verschobene Kisten, Schritte)."""
_Link = tuple[Scene, str, Prediction]
"""Woher eine Szene kam: vorige Szene, Taste, Vorhersage."""
_Entry = tuple[Cost, int, Scene, Plan | None]
"""Warteschlange: Kosten, laufende Nummer, Szene, fertiger Plan (bei Sieg oder Frage)."""


def search(
    simulator: Simulator,
    scene: Scene,
    buttons: Sequence[str],
    allow_reset: bool = False,
    limit: int = SEARCH_LIMIT,
) -> SearchResult:
    """Billigster Plan zum Sieg; sonst der billigste zu einer offenen Frage; sonst keiner."""
    best: dict[Scene, Cost] = {scene: (0, 0, 0)}
    links: dict[Scene, _Link] = {}
    order = count()
    queue: list[_Entry] = [((0, 0, 0), next(order), scene, None)]
    question: Plan | None = None
    expanded = 0
    while queue:
        spent, _, current, plan = heapq.heappop(queue)
        if plan is not None:
            if plan.goal is Goal.WIN:
                return SearchResult(plan, complete=True)
            question = question or plan
            continue
        if best[current] < spent:
            continue
        expanded += 1
        if expanded > limit:
            return SearchResult(question, complete=False)
        for button in sorted(buttons):
            prediction = simulator.predict(current, button)
            if prediction.reset and not allow_reset:
                continue
            corners, pushes, steps = spent
            cost = (
                corners + prediction.cornered,
                pushes + prediction.disturbs,
                steps + 1,
            )
            if prediction.won or prediction.question is not None:
                goal = Goal.WIN if prediction.won else Goal.LEARN
                done = _plan(goal, links, current, button, prediction)
                heapq.heappush(queue, (cost, next(order), current, done))
                continue
            following = prediction.scene
            if following is None or following is current:
                continue
            if following not in best or cost < best[following]:
                best[following] = cost
                links[following] = (current, button, prediction)
                heapq.heappush(queue, (cost, next(order), following, None))
    return SearchResult(question, complete=True)


def _plan(
    goal: Goal, links: dict[Scene, _Link], last: Scene, button: str, prediction: Prediction
) -> Plan:
    """Setzt den Weg bis `last` und den letzten Druck zu einem Plan zusammen."""
    steps = [(button, prediction)]
    while last in links:
        last, earlier, step = links[last]
        steps.append((earlier, step))
    steps.reverse()
    return Plan(
        goal=goal,
        buttons=tuple(b for b, _ in steps),
        expected=tuple(p.scene for _, p in steps),
        question=prediction.question,
        restarts=any(p.reset for _, p in steps),
    )
