"""Spiel-Schemata: Was der Agent über ein Spiel gelernt hat, ohne dessen Aussehen.

Ein Spielmodell zählt keine Wahrscheinlichkeiten, sondern merkt sich, wohin jede Taste in
jedem Zustand geführt hat (die Spiele sind deterministisch). Ein Schema ist dasselbe mit
neutralen Namen für Zustände und Tasten.

In einem neuen Spiel kennt der Agent weder die Symbole noch die Tasten. Er hält deshalb
mehrere Deutungen bereit: für jede mögliche Tastenbelegung eine. Eine Deutung ordnet jedem
neuen Symbol den Zustand des Schemas zu, den sie vorhergesagt hat. Widerspricht eine
Beobachtung der Deutung, fällt sie weg. Das ist Strukturabbildung, wie in `structure.py`,
nur schrittweise: Weil der Start bekannt ist, folgt jede weitere Zuordnung aus dem Ablauf.
"""

import random
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import permutations

from hekmatki.advisor import majority
from hekmatki.puzzle import WIN

Transitions = Mapping[tuple[str, str], str]
"""(Zustand, Taste) → Folgezustand oder `WIN`."""


def shortest_paths(transitions: Transitions, start: str) -> dict[str, list[str]]:
    """Kürzeste bekannte Tastenfolge von `start` zu jedem erreichbaren Zustand.

    Die Reihenfolge der Einträge ist die Reihenfolge der Breitensuche: nähere zuerst.
    """
    neighbors: dict[str, list[tuple[str, str]]] = {}
    for (source, button), target in sorted(transitions.items()):
        neighbors.setdefault(source, []).append((button, target))
    paths: dict[str, list[str]] = {start: []}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for button, target in neighbors.get(state, []):
            if target not in paths:
                paths[target] = [*paths[state], button]
                queue.append(target)
    return paths


def path_to(
    transitions: Transitions, start: str, is_target: Callable[[str], bool]
) -> list[str] | None:
    """Kürzeste bekannte Tastenfolge von `start` zu einem Zustand, der `is_target` erfüllt.

    Leere Liste, wenn `start` schon passt; `None`, wenn kein Weg bekannt ist.
    """
    paths = shortest_paths(transitions, start)
    return next((path for state, path in paths.items() if is_target(state)), None)


def is_win(state: str) -> bool:
    """True für den Sieg."""
    return state == WIN


@dataclass(frozen=True)
class GameSchema:
    """Ein Spiel ohne Aussehen: neutrale Zustände, neutrale Tasten, gelernte Übergänge."""

    name: str
    start: str
    buttons: tuple[str, ...]
    transitions: Transitions

    def __post_init__(self) -> None:
        unknown = {button for _, button in self.transitions} - set(self.buttons)
        if unknown:
            raise ValueError(f"Schema {self.name!r}: Übergänge mit unbekannten Tasten {unknown}.")

    def plan(self, state: str) -> list[str] | None:
        """Kürzester Weg zum Sieg laut Schema."""
        return path_to(self.transitions, state, is_win)


def schema_from_model(
    name: str, model: Transitions, start: str, buttons: Sequence[str]
) -> GameSchema:
    """Macht aus einem Spielmodell ein Schema, indem es alles neutral umbenennt."""
    seen = {start} | {s for s, _ in model} | set(model.values())
    symbols = sorted(seen - {WIN})
    state_names = {s: f"zustand_{i}" for i, s in enumerate(symbols, start=1)} | {WIN: WIN}
    button_names = {b: f"aktion_{i}" for i, b in enumerate(sorted(buttons), start=1)}
    transitions = {(state_names[s], button_names[b]): state_names[t] for (s, b), t in model.items()}
    return GameSchema(name, state_names[start], tuple(button_names.values()), transitions)


@dataclass(frozen=True)
class Interpretation:
    """Eine Deutung des neuen Spiels: welche Taste welche Aktion ist und welches Symbol
    welcher Zustand des Schemas."""

    buttons: Mapping[str, str]
    """Taste des Spiels → Aktion des Schemas."""
    states: Mapping[str, str]
    """Symbol des Spiels → Zustand des Schemas."""

    def button_for(self, action: str) -> str:
        """Die Taste, die laut dieser Deutung die Aktion `action` auslöst."""
        for button, mapped in self.buttons.items():
            if mapped == action:
                return button
        raise ValueError(f"Keine Taste für die Aktion {action!r}.")


def interpretations(schema: GameSchema, buttons: Sequence[str], start: str) -> list[Interpretation]:
    """Alle Deutungen, die vor dem ersten Schritt möglich sind: eine pro Tastenbelegung."""
    if len(buttons) != len(schema.buttons):
        raise ValueError(f"Das Spiel hat {len(buttons)} Tasten, das Schema {len(schema.buttons)}.")
    return [
        Interpretation(dict(zip(buttons, actions, strict=True)), {start: schema.start, WIN: WIN})
        for actions in permutations(schema.buttons)
    ]


def updated(
    interpretation: Interpretation,
    schema: GameSchema,
    state: str,
    button: str,
    outcome: str,
) -> Interpretation | None:
    """Prüft eine Deutung an einer Beobachtung. `None`, wenn sie ihr widerspricht.

    Sagt das Schema für diesen Schritt etwas vorher, muss das Ergebnis dazu passen. Ist das
    Ergebnis ein neues Symbol, bekommt es den vorhergesagten Zustand, sofern der noch frei ist.
    """
    role = interpretation.states.get(state)
    if role is None:
        return interpretation
    expected = schema.transitions.get((role, interpretation.buttons[button]))
    if expected is None:
        return interpretation
    known = interpretation.states.get(outcome)
    if known is not None:
        return interpretation if known == expected else None
    if expected in interpretation.states.values():
        return None
    return Interpretation(interpretation.buttons, {**interpretation.states, outcome: expected})


def merged_schema(
    schema: GameSchema, interpretation: Interpretation, model: Transitions
) -> GameSchema:
    """Ergänzt das Schema um alles, was im neuen Spiel unter der Deutung gelernt wurde.

    Übernommen werden nur Übergänge, deren Zustände die Deutung schon zuordnen kann.
    """
    learned = {
        (interpretation.states[s], interpretation.buttons[b]): interpretation.states[t]
        for (s, b), t in model.items()
        if s in interpretation.states and t in interpretation.states
    }
    return GameSchema(schema.name, schema.start, schema.buttons, {**schema.transitions, **learned})


class SchemaAdvisor:
    """Ratgeber aus einem Spiel-Schema: eine Deutung pro Tastenbelegung."""

    def __init__(self, schema: GameSchema, buttons: Sequence[str], start: str) -> None:
        self.schema = schema
        self.interpretations = interpretations(schema, sorted(buttons), start)

    def advice(self, state: str, rng: random.Random) -> str | None:
        """Die Taste, die die meisten noch möglichen Deutungen auf dem Weg zum Sieg drücken."""
        votes = []
        for interpretation in self.interpretations:
            role = interpretation.states.get(state)
            plan = None if role is None else self.schema.plan(role)
            if plan:
                votes.append(interpretation.button_for(plan[0]))
        return majority(votes, rng)

    def learn(self, state: str, button: str, outcome: str) -> None:
        """Streicht Deutungen, die der Beobachtung widersprechen."""
        checked = [updated(i, self.schema, state, button, outcome) for i in self.interpretations]
        self.interpretations = [i for i in checked if i is not None]

    def predicts(self, state: str, button: str) -> bool:
        """True, wenn alle noch möglichen Deutungen dasselbe Ergebnis vorhersagen."""
        if not self.interpretations:
            return False
        predictions: set[str] = set()
        for interpretation in self.interpretations:
            role = interpretation.states.get(state)
            action = interpretation.buttons[button]
            prediction = None if role is None else self.schema.transitions.get((role, action))
            if prediction is None:
                return False
            predictions.add(prediction)
        return len(predictions) == 1

    def fits(self) -> bool:
        """True, solange noch mindestens eine Deutung möglich ist."""
        return bool(self.interpretations)

    def best_interpretation(self) -> Interpretation | None:
        """Die noch mögliche Deutung, die die meisten Symbole zuordnen kann."""
        return max(self.interpretations, key=lambda i: len(i.states), default=None)
