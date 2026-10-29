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

REPLAY_SEED: Final = 0
TRAINING: Final = 25
"""So viele Runden spielt der Agent, bevor die Aufzeichnung beginnt."""
CANDIDATES: Final = 5
"""So viele Runden werden danach aufgezeichnet; gezeigt wird die mit den meisten Erfolgen."""
SHOWN_STEPS: Final = 600
"""Höchstens so viele Schritte zeigt die Seite (eine Runde dauert meist viel kürzer)."""
TEMPLATE: Final = Path(__file__).with_name("crafter_replay_template.html")
DATA_MARKER: Final = "/*CRAFTER_DATA*/null"


def record(seed: int = REPLAY_SEED, training: int = TRAINING) -> dict[str, Any]:
    """Spielt `training` Runden, zeichnet die nächsten `CANDIDATES` auf und zeigt die mit den
    meisten Erfolgen. Dazu, was er danach gelernt hat."""
    world = CrafterWorld(seed)
    rng = random.Random(seed)
    agent = GeneralAgent(ACTIONS, own_goals=True)
    for _ in range(training):
        _play(world, agent, rng, None)
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
    form = drives.steady(agent.form())
    own = drives.owned(knowledge, form)
    body = drives.body(knowledge, form)
    harmed = drives.harmed(knowledge, form)
    causes = []
    for component in sorted(own, key=lambda c: components[c]):
        for cause in knowledge.causes.causes(Event(component, Change.RISES))[:2]:
            causes.append(
                {
                    "effect": f"{components[component]} steigt",
                    "action": actions[cause.action],
                    "when": [_say(literal, components) for literal in cause.literals],
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
            [_say(literal, components) for literal in danger]
            for danger in drives.dangers(knowledge, body, harmed)
        ],
        "causes": causes,
    }


def _say(literal: Literal, components: list[str]) -> str:
    """Ein Literal in Crafters Namen, etwa „vorne = tree“ oder „wood ≥ 1“."""
    name = components[literal.component]
    if name.startswith("Sicht") or name == "vorne":
        value = MATERIALS[literal.value] if 0 <= literal.value < len(MATERIALS) else literal.value
    else:
        value = literal.value
    sign = "=" if literal.kind is Kind.EQUAL else "≥"
    return f"{name} {sign} {value}"


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
