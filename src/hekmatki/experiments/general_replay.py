"""Seite „Ein Agent, drei Welten“ (ab 0.16): der allgemeine Agent zum Anschauen.

Für jede der drei Welten (`general_worlds`) werden die Prüfrunden nach dem Lehrplan
aufgezeichnet und die längste gezeigt (die kürzeste wäre oft nur ein, zwei Schritte).
Die Seite zeigt nebeneinander, was der Agent sieht (nur gemischte Zahlen), was in Wahrheit
passiert (Raum, Würfel, Suchbaum) und was er selbst herausgefunden hat: die Form und seine
Regeln, in seinen Worten und übersetzt. Dazu die Mittelwerte aller Läufe, die Bibliothek
(Ergebnis 18) und das Erkennen einer neuen Umgebung (Ergebnis 19).

Aufruf: `PYTHONPATH=src python -m hekmatki.experiments.general_replay docs/welten.html`
"""

import json
import math
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from hekmatki.experiments import general_worlds as worlds
from hekmatki.experiments import library_transfer as library
from hekmatki.experiments import new_world
from hekmatki.general.agent import GeneralAgent
from hekmatki.general.detector import TAIL_LIMIT, Strategy
from hekmatki.general.env import Observation, Wiring
from hekmatki.general.form import Form
from hekmatki.general.programs import Keep, core, describe
from hekmatki.general.run import play_episode
from hekmatki.general.worlds import Lattice, SortedSearch

REPLAY_SEED: Final = 0
TEMPLATE: Final = Path(__file__).with_name("general_replay_template.html")
DATA_MARKER: Final = "/*WORLDS_DATA*/null"
SHOWN_LIMIT: Final = 12.0
"""Unerwartetheit wird bis 10^-12 gezeichnet, kleinere Wahrscheinlichkeiten am Rand."""


def world_replay(spec: worlds.WorldSpec, seed: int = REPLAY_SEED) -> dict[str, Any]:
    """Lehrplan, dann die längste Prüfrunde Schritt für Schritt, mit allem, was der Agent weiß."""
    setting = worlds.prepare(spec, seed)
    agent = GeneralAgent(spec.actions)
    worlds.teach(agent, setting)
    episodes = [
        play_episode(setting.test, agent, setting.rng, worlds.TEST_LIMIT, record=True)
        for _ in range(worlds.TEST_EPISODES)
    ]
    round_number, episode = max(enumerate(episodes, 1), key=lambda pair: pair[1].steps)
    env = setting.test
    if not isinstance(env, Lattice | SortedSearch):
        raise TypeError(f"Unbekannte Welt: {type(env).__name__}")
    component_names, action_names = env.names()
    seen_names = [component_names[i] for i in setting.wiring.components]
    seen_actions = [action_names[i] for i in setting.wiring.actions]
    data: dict[str, Any] = {
        "name": spec.name,
        "size": spec.size_text(spec.test),
        "round": round_number,
        "rounds": len(episodes),
        "steps": episode.steps,
        "least": episode.least,
        "reached": episode.reached,
        "observations": [list(o) for o in episode.trace],
        "pressed": list(episode.pressed),
        "componentNames": seen_names,
        "actionNames": seen_actions,
        "form": _form_data(agent.form(), seen_names, seen_actions),
        "goal": _goal_data(agent, seen_names),
        "rules": _rules_data(agent, seen_names, seen_actions),
    }
    inner = [_inner(setting.wiring, o) for o in episode.trace]
    if isinstance(env, Lattice):
        data |= {
            "kind": "lattice",
            "dims": env.dims,
            "edge": env.size,
            "blocked": sorted(list(cell) for cell in env.blocked),
            "positions": [o[: env.dims] for o in inner],
            "target": inner[0][3 * env.dims :],
        }
    else:
        target = inner[0][1] // 1000
        data |= {
            "kind": "search",
            "count": env.count,
            "targetIndex": target,
            "targetKey": inner[0][1],
            "frames": [_search_frame(env, o) for o in inner],
        }
    return data


def write_page(output: Path, template: Path = TEMPLATE, seeds: int = 10) -> None:
    """Schreibt die Seite: Vorlage plus Aufzeichnungen plus Mittelwerte aller Läufe."""
    page = template.read_text(encoding="utf-8")
    if page.count(DATA_MARKER) != 1:
        raise ValueError(f"Die Vorlage braucht genau einmal {DATA_MARKER!r}.")
    rows = {row.world: row for row in worlds.run_general_worlds(seeds)}
    shown = []
    for spec in worlds.WORLDS:
        replay = world_replay(spec)
        row = rows[spec.name]
        replay["summary"] = {
            "steps": row.steps,
            "reached": row.reached,
            "best": row.best,
            "formFound": row.form_found,
        }
        shown.append(replay)
    library_rows, entries = library.run_library_transfer(seeds)
    data = {
        "seeds": seeds,
        "agents": list(worlds.AGENTS),
        "testLimit": worlds.TEST_LIMIT,
        "worlds": shown,
        "library": {
            "conditions": list(library.CONDITIONS),
            "budget": library.BUDGET,
            "rows": [_plain(r) for r in library_rows],
            "entries": [_plain(e) for e in entries],
        },
        "newWorld": _new_world_data(new_world.run_new_world(seeds)),
    }
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    output.write_text(page.replace(DATA_MARKER, text.replace("</", "<\\/")), encoding="utf-8")


def _inner(wiring: Wiring, observation: Observation) -> list[int]:
    """Die Beobachtung zurück in die innere Reihenfolge (nur für die Zeichnung)."""
    inner = [0] * len(observation)
    for position, index in enumerate(wiring.components):
        inner[index] = observation[position]
    return inner


def _search_frame(env: SortedSearch, inner: Sequence[int]) -> dict[str, int]:
    index = inner[0] // 1000
    low, high = env.interval(index)
    return {"index": index, "key": inner[0], "low": low, "high": high}


def _named(text: str, names: Sequence[str]) -> str:
    return re.sub(r"G(\d+)", lambda m: names[int(m.group(1))], text)


def _form_data(form: Form, names: Sequence[str], actions: Sequence[str]) -> dict[str, Any]:
    return {
        "name": form.name,
        "axes": [
            {
                "component": axis.component,
                "name": names[axis.component],
                "kind": axis.kind.value,
                "up": axis.up,
                "upName": actions[axis.up],
                "down": axis.down,
                "downName": actions[axis.down],
            }
            for axis in form.axes
        ],
        "fixed": [{"component": c, "name": names[c]} for c in form.fixed],
    }


def _goal_data(agent: GeneralAgent, names: Sequence[str]) -> list[dict[str, Any]]:
    pairs = agent.knowledge.goal.pairs or ()
    return [{"pair": [i, j], "names": [names[i], names[j]]} for i, j in pairs]


def _rules_data(
    agent: GeneralAgent, names: Sequence[str], actions: Sequence[str]
) -> dict[str, Any]:
    """Die Regeln ohne Ausnahme, die etwas bewegen; „bleibt“ und unsichere nur gezählt."""
    found = agent.knowledge.rules.found
    moving = []
    kept = unpredictable = 0
    for (action, component), rule in sorted(found.items()):
        if rule.program is None or not rule.exact:
            unpredictable += 1
        elif isinstance(core(rule.program), Keep):
            kept += 1
        else:
            text = describe(rule.program)
            moving.append(
                {
                    "action": action,
                    "component": component,
                    "agent": f"Taste {action}: G{component} {text}",
                    "ours": f"{actions[action]}: {names[component]} {_named(text, names)}",
                }
            )
    return {"moving": moving, "kept": kept, "unpredictable": unpredictable}


def _new_world_data(rows: Sequence[new_world.NewWorldRow]) -> dict[str, Any]:
    life = new_world.live(Strategy.EXPECTED.value, REPLAY_SEED)
    surprise = [min(-math.log10(max(p, 1e-300)), SHOWN_LIMIT) for p in life.history]
    return {
        "phases": list(new_world.PHASES),
        "episodes": new_world.EPISODES,
        "rows": [_plain(r) for r in rows],
        "life": {
            "surprise": [round(s, 2) for s in surprise],
            "limit": -math.log10(TAIL_LIMIT),
            "starts": life.starts,
            "events": [{"step": e.step, "kind": e.kind, "target": e.target} for e in life.events],
            "steps": life.steps,
        },
    }


def _plain(row: object) -> dict[str, Any]:
    """Ein Ergebnis-Datensatz als JSON-taugliches Wörterbuch."""
    fields: dict[str, Any] = vars(row)
    return {re.sub(r"_(\w)", lambda m: m.group(1).upper(), k): v for k, v in fields.items()}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Aufruf: python -m hekmatki.experiments.general_replay ZIELDATEI.html")
    write_page(Path(sys.argv[1]))
