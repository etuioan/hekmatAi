"""Teilziele: Wie komme ich dahin, dass eine Aussage gilt? (ab 0.18, H25 und H26)

Der Agent stellt sich vor, was seine Tasten bewirken (`imagine`), und sucht in diesen
vorgestellten Beobachtungen einen Weg (`search`). Anders als `planner.plan_model` braucht er
dafür kein vollständiges Modell: Größen, die er nicht vorhersagen kann, sind in der
Vorstellung unbekannt, und für das Ziel zählen nur die Größen, um die es geht. So kann er
planen, wenn ein Sichtfeld mitwandert: Nach einem Schritt nach links übernimmt jedes Feld den
Wert seines Nachbarn (der Baustein `Copy`), nur am Rand kommt Unbekanntes herein (H26).

Ist das Ziel so nicht erreichbar, sucht er eine Ursache (`causes`), deren Bedingung er
herstellen kann, und macht die fehlenden Teile der Bedingung zu Teilzielen: Mittel-Ziel-
Analyse (Newell & Simon 1961), wie bei STRIPS (Fikes & Nilsson 1971). Optionen mit
Abbruchbedingung (Sutton, Precup, Singh 1999) entstehen so von selbst: „Gehe, bis das Feld
vor dir den Wert 6 hat“ ist ein Teilziel mit Weg.

Grundlage für das Vorstellen: Weltmodell als Programm und Planen darin (Schema 2026,
TheoryCoder-2 2026, MAP 2026), Raum aus der Verschiebung der Sinneseindrücke durch eigene
Bewegung (Philipona 2003, Laflaquière 2019).
"""

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from hekmatki.general.causes import Cause, CauseBook, Change, Event, Kind, Literal, Partial
from hekmatki.general.knowledge import Knowledge
from hekmatki.general.programs import (
    Becomes,
    Copy,
    Cycle,
    Keep,
    Program,
    Shift,
    When,
)

SEARCH_LIMIT: Final = 200
"""Höchstens so viele vorgestellte Beobachtungen je Suche (von Hand gewählt, ohne Grundlage)."""
DEPTH: Final = 3
"""So tief schachtelt der Agent Teilziele (von Hand gewählt, ohne Grundlage)."""
BRANCH: Final = 3
WEAK: Final = 0.05
"""Auch eine Ursache, die nur so oft wirkt, ist ein Weg, wenn es keinen besseren gibt."""
"""So viele Ursachen probiert er je Teilziel."""

type Model = dict[int, list[tuple[int, Program | None]]]
"""Taste → die Größen, die sie ändern kann, mit ihrer Regel (None: unvorhersagbar)."""


@dataclass(frozen=True)
class Target:
    """Wohin die Suche will: eine Lage, in der alle Literale gelten, und dann diese Taste."""

    literals: tuple[Literal, ...]
    action: int | None = None


def model(knowledge: Knowledge, actions: int) -> Model:
    """Für jede bekannte Taste die Größen, die sie nicht sicher gleich lässt."""
    rules = knowledge.rules
    found: Model = {}
    for action in range(actions):
        if action not in rules.examples:
            continue  # Nie gedrückt: Was sie tut, ist ganz unbekannt.
        moving: list[tuple[int, Program | None]] = []
        for component in range(rules.width):
            rule = rules.found.get((action, component))
            program = None if rule is None else rule.program
            if not isinstance(program, Keep):
                moving.append((component, program))
        found[action] = moving
    return found


def imagine(world: Model, observation: Partial, action: int) -> Partial:
    """Die vorgestellte Beobachtung nach dieser Taste; Unvorhersagbares wird unbekannt."""
    after = list(observation)
    for component, program in world[action]:
        after[component] = _predict(program, observation, component)
    return tuple(after)


def search(
    world: Model, start: Partial, targets: Sequence[Target], limit: int = SEARCH_LIMIT
) -> int | None:
    """Breitensuche zu einem Ziel; gibt die erste Taste zurück (None: kein Weg gefunden)."""
    first: dict[Partial, int | None] = {start: None}
    frontier = deque([start])
    while frontier and len(first) <= limit:
        here = frontier.popleft()
        for target in targets:
            if all(literal.holds(here) for literal in target.literals):
                step = first[here]
                if step is not None:
                    return step
                if target.action is not None:
                    return target.action
        for action in world:
            nxt = imagine(world, here, action)
            if nxt == here or nxt in first:
                continue
            start_action = first[here]
            first[nxt] = action if start_action is None else start_action
            frontier.append(nxt)
    return None


def achieve(
    knowledge: Knowledge,
    world: Model,
    observation: Partial,
    goal: Literal,
    depth: int = DEPTH,
    memo: dict[tuple[Literal, int], int | None] | None = None,
) -> int | None:
    """Die nächste Taste auf dem Weg dahin, dass `goal` gilt (None: kein Weg bekannt).

    `memo` merkt sich Antworten für dieselbe Beobachtung, damit dasselbe Teilziel in einem
    Schritt nicht zweimal gesucht wird."""
    if goal.holds(observation):
        return None
    if memo is not None and (goal, depth) in memo:
        return memo[goal, depth]
    step = _achieve(knowledge, world, observation, goal, depth, memo)
    if memo is not None:
        memo[goal, depth] = step
    return step


def _achieve(
    knowledge: Knowledge,
    world: Model,
    observation: Partial,
    goal: Literal,
    depth: int,
    memo: dict[tuple[Literal, int], int | None] | None,
) -> int | None:
    causes = causes_for(knowledge.causes, goal)
    targets = [Target((goal,)), *(Target(cause.literals, cause.action) for cause in causes)]
    step = search(world, observation, targets)
    if step is not None or depth == 0:
        return step
    for cause in causes[:BRANCH]:
        for literal in cause.literals:
            if literal.holds(observation) or literal == goal:
                continue
            step = achieve(knowledge, world, observation, literal, depth - 1, memo)
            if step is not None:
                return step
    return None


def causes_for(book: CauseBook, goal: Literal) -> list[Cause]:
    """Die Ursachen, die das Literal wahr machen können. Gibt es keine verlässliche, auch
    solche, die nur selten wirken (`WEAK`): Wer oft genug probiert, kommt auch so ans Ziel."""
    if goal.kind is Kind.AT_LEAST:
        event = Event(goal.component, Change.RISES)
    else:
        event = Event(goal.component, Change.BECOMES, goal.value)
    return book.causes(event) or book.causes(event, WEAK)


def _predict(program: Program | None, observation: Partial, component: int) -> int | None:
    """Der vorhergesagte Wert, oder None, wenn er unbekannt ist."""
    while isinstance(program, When):
        sensor = observation[program.sensor]
        if sensor is None:
            return None
        program = program.then if sensor == program.value else program.otherwise
    old = observation[component]
    match program:
        case Keep():
            return old
        case Shift(by):
            return None if old is None else old + by
        case Copy(source):
            return observation[source]
        case Becomes(value):
            return value
        case Cycle(by, modulus):
            return None if old is None else (old + by) % modulus
        case _:
            return None
