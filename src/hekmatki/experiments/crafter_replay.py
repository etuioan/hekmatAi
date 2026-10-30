"""Seite „Crafter“ (ab 0.18): der allgemeine Agent in einem kleinen 2D-Minecraft zum Anschauen.

Ein Agent mit eigenen Zielen spielt viele Runden hintereinander. Eine späte Runde wird Schritt
für Schritt aufgezeichnet: was in Wahrheit um die Figur herum ist, sein Inventar, welche
Taste er drückt und warum (Bedürfnis, Rekord, Versuch, Abwehr, Erkunden). Dazu zeigt die
Seite, was er selbst herausgefunden hat, übersetzt in Crafters Namen, und die Messung aus
`crafter_run`. Die Namen kennt nur die Seite; der Agent sieht nur gemischte Zahlen.

Aufruf (braucht `pip install -e ".[crafter]"`):
`PYTHONPATH=src python -m hekmatki.experiments.crafter_replay docs/crafter.html [messung.json]`

`messung.json` kommt von `python -m hekmatki.experiments.crafter_run messung.json`; ohne sie
misst die Seite selbst (dauert lange).
"""

import json
import random
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

from hekmatki.adapters.crafter import ACTIONS, ITEMS, MATERIALS, CrafterWorld
from hekmatki.experiments.crafter_run import (
    ACHIEVEMENTS,
    CrafterRow,
    load_careers,
    rows,
    run_crafter,
)
from hekmatki.general.agent import GeneralAgent
from hekmatki.general.causes import Change, Event, Kind, Literal
from hekmatki.general.drives import Drives
from hekmatki.general.env import Transition
from hekmatki.general.space import Layout

REPLAY_SEED: Final = 0
TRAINING: Final = 25
"""So viele Runden spielt der Agent, bevor die Aufzeichnung beginnt."""
CANDIDATES: Final = 5
"""So viele Runden werden danach aufgezeichnet; gezeigt wird die mit den meisten Erfolgen."""
SHOWN_STEPS: Final = 600
"""Höchstens so viele Schritte zeigt die Seite (eine Runde dauert meist viel kürzer)."""
TEMPLATE: Final = Path(__file__).with_name("crafter_replay_template.html")
DATA_MARKER: Final = "/*CRAFTER_DATA*/null"
ANSWER_TRIES: Final = 3
"""Antworten auf eine Gefahr zeigt die Seite erst, wenn er sie so oft probiert hat."""


def record(seed: int = REPLAY_SEED, training: int = TRAINING) -> dict[str, Any]:
    """Spielt `training` Runden, zeichnet die nächsten `CANDIDATES` auf und zeigt die mit den
    meisten Erfolgen. Dazu, was er danach gelernt hat."""
    world = CrafterWorld(seed)
    rng = random.Random(seed)
    agent = GeneralAgent(ACTIONS, own_goals=True)
    grid_round: int | None = None
    for number in range(1, training + 1):
        _play(world, agent, rng, None)
        if grid_round is None and agent.knowledge.space.layout.centred:
            grid_round = number
    best: tuple[int, int, list[dict[str, Any]], list[list[Any]]] | None = None
    for number in range(training + 1, training + CANDIDATES + 1):
        steps: list[dict[str, Any]] = []
        _play(world, agent, rng, steps)
        unlocked = [list(pair) for pair in world.unlocked]
        if best is None or len(unlocked) > len(best[3]):
            best = (number, len(steps), steps, unlocked)
    if best is None:
        raise ValueError("Keine Runde aufgezeichnet.")
    components, actions = world.names()
    return {
        "round": best[0],
        "candidates": [training + 1, training + CANDIDATES],
        "steps": best[2],
        "unlocked": best[3],
        "learned": _learned(agent, components, actions),
        "grid": _grid(agent, components),
        "grid_round": grid_round,
    }


def _play(
    world: CrafterWorld, agent: GeneralAgent, rng: random.Random, steps: list[dict[str, Any]] | None
) -> None:
    """Eine Runde; mit `steps` wird jeder Schritt aufgeschrieben."""
    components, actions = world.names()
    observation = world.reset(rng)
    agent.new_place()
    agent.begin(observation)
    while not world.finished:
        action = agent.act(observation, rng)
        reason = agent.drives.reason if agent.drives is not None else ""
        if steps is not None and len(steps) < SHOWN_STEPS:
            steps.append(_frame(components, observation, actions[action], reason or "Plan"))
        outcome = world.step(action, rng)
        agent.learn(Transition(observation, action, outcome.observation, outcome.reached))
        observation = outcome.observation
        if steps is not None and len(steps) <= SHOWN_STEPS:
            steps[-1]["new"] = [name for at, name in world.unlocked if at == len(steps)]


def _frame(
    components: list[str], observation: tuple[int, ...], action: str, reason: str
) -> dict[str, Any]:
    """Was in Wahrheit los ist, entmischt: Sicht als Feld von Namen, Inventar, Taste, Grund."""
    named = dict(zip(components, observation, strict=True))
    view = [[MATERIALS[named[f"Sicht {x:+d},{y:+d}"]] for x in range(-4, 5)] for y in range(-3, 4)]
    return {
        "view": view,
        "front": MATERIALS[named["vorne"]],
        "inventory": {item: named[item] for item in ITEMS},
        "sleeping": bool(named["schläft"]),
        "action": action,
        "reason": reason,
    }


def _learned(agent: GeneralAgent, components: list[str], actions: list[str]) -> dict[str, Any]:
    """Seine eigenen Ziele und Ursachen, in Crafters Namen."""
    drives = agent.drives
    if not isinstance(drives, Drives):
        raise TypeError("Nur ein Agent mit eigenen Zielen hat Bedürfnisse.")
    knowledge = agent.knowledge
    layout = knowledge.space.layout
    form = drives.steady(knowledge, agent.form())
    own = drives.owned(knowledge, form)
    body = drives.body(knowledge, form)
    harmed = drives.harmed(knowledge, form)
    dangers = drives.dangers(knowledge, body, harmed)
    causes = []
    for component in sorted(own, key=lambda c: components[c]):
        for cause in knowledge.causes.causes(Event(component, Change.RISES))[:2]:
            causes.append(
                {
                    "effect": f"{components[component]} steigt",
                    "action": actions[cause.action],
                    "when": [_say(literal, components, layout) for literal in cause.literals],
                    "hits": cause.hits,
                    "uses": cause.uses,
                }
            )
    return {
        "form": form.name,
        "own": sorted(components[c] for c in own),
        "needs": [components[c] for c in drives.needs(knowledge, own)],
        "records": [components[c] for c in drives.records(knowledge, form, own)],
        "harmed": [components[c] for c in harmed],
        "dangers": [
            [_say(literal, components, layout) for literal in danger] for danger in dangers
        ],
        "answers": _answers(drives, dangers, actions),
        "causes": causes,
    }


def _say(literal: Literal, components: list[str], layout: Layout) -> str:
    """Ein Literal in Crafters Namen, etwa „vorne = tree“, „wood ≥ 1“ oder „irgendwo im
    Abstand ≤ 1 = zombie“."""
    if literal.kind is Kind.SOME:
        far = max(layout.distance(c) or 0 for c in literal.among)
        return f"irgendwo im Abstand ≤ {far} = {_material(literal.value)}"
    name = components[literal.component]
    seen = name.startswith("Sicht") or name == "vorne"
    value: object = _material(literal.value) if seen else literal.value
    sign = "=" if literal.kind is Kind.EQUAL else "≥"
    return f"{name} {sign} {value}"


def _material(value: int) -> object:
    return MATERIALS[value] if 0 <= value < len(MATERIALS) else value


def _answers(
    drives: Drives, dangers: list[tuple[Literal, ...]], actions: list[str]
) -> list[dict[str, Any]]:
    """Was er gegen die erste Gefahr gelernt hat: je Antwort der mittlere Schaden danach."""
    if not dangers:
        return []
    danger = dangers[0]
    found = []
    for (situation, answer), tried in drives.tried.items():
        if situation == danger and tried >= ANSWER_TRIES:
            found.append(
                {
                    "answer": _say_answer(answer, actions),
                    "cost": drives.cost(situation, answer),
                    "tried": tried,
                }
            )
    return sorted(found, key=lambda a: a["cost"])


def _say_answer(answer: str, actions: list[str]) -> str:
    """„hin“, „weg“, „quer“ bleiben; „Taste 7 daran“ wird „do an der Gefahr“."""
    if not answer.startswith("Taste "):
        return {"hin": "hingehen", "weg": "weggehen", "quer": "zur Seite gehen"}[answer]
    number, *rest = answer.removeprefix("Taste ").split(" ")
    name = actions[int(number)]
    return f"{name} an der Gefahr" if rest else name


def _grid(agent: GeneralAgent, components: list[str]) -> dict[str, Any]:
    """Das Gitter, das er sich gebaut hat, in seinen eigenen Koordinaten, mit den wahren
    Namen der Felder und ob jedes richtig liegt (bis auf Drehen und Spiegeln)."""
    layout = agent.knowledge.space.layout
    cells = []
    truth = {c: _true_place(components[c]) for c in layout.places}
    flip = _best_symmetry(layout.places, truth)
    for component, place in sorted(layout.places.items()):
        real = truth[component]
        cells.append(
            {
                "place": list(place),
                "name": components[component],
                "right": real is not None and flip(place) == real,
            }
        )
    return {"centred": layout.centred, "cells": cells}


def _true_place(name: str) -> tuple[int, int] | None:
    if not name.startswith("Sicht "):
        return None
    x, y = name.removeprefix("Sicht ").split(",")
    return int(x), int(y)


def _best_symmetry(
    places: dict[int, tuple[int, ...]], truth: dict[int, tuple[int, int] | None]
) -> Callable[[tuple[int, ...]], tuple[int, int] | None]:
    """Die Drehung oder Spiegelung, unter der die meisten Felder richtig liegen: Welche
    Richtung er „x“ nennt, ist seine Sache."""
    options: list[Callable[[tuple[int, ...]], tuple[int, int] | None]] = []
    for swap in (False, True):
        for sx in (1, -1):
            for sy in (1, -1):
                options.append(_symmetry(swap, sx, sy))
    return max(options, key=lambda f: sum(f(p) == truth[c] for c, p in places.items()))


def _symmetry(swap: bool, sx: int, sy: int) -> Callable[[tuple[int, ...]], tuple[int, int] | None]:
    def apply(place: tuple[int, ...]) -> tuple[int, int] | None:
        if len(place) != 2:
            return None
        a, b = (place[1], place[0]) if swap else (place[0], place[1])
        return sx * a, sy * b

    return apply


def _row(row: CrafterRow) -> dict[str, Any]:
    return {
        "agent": row.agent,
        "score": row.score,
        "rates": [row.rates[name] for name in ACHIEVEMENTS],
        "length": row.length,
        "per_round": row.per_round,
        "curve": list(row.curve),
        "ms": row.ms_per_step,
    }


def build(out: Path, measured: Path | None = None) -> None:
    """Schreibt die Seite."""
    found = rows(load_careers(measured)) if measured else run_crafter()
    data = {
        "achievements": list(ACHIEVEMENTS),
        "rows": [_row(row) for row in found],
        "replay": record(),
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    if DATA_MARKER not in page:
        raise ValueError("Die Vorlage hat keine Stelle für die Daten.")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    out.write_text(page.replace(DATA_MARKER, payload), encoding="utf-8")


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
