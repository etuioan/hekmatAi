import random

import pytest

from hekmatki.experiments.general_replay import DATA_MARKER, TEMPLATE, world_replay
from hekmatki.experiments.general_worlds import (
    AGENTS,
    WORLD_BY_NAME,
    WORLDS,
    make_agent,
    run_general_worlds,
    run_world,
    same_tasks,
)
from hekmatki.experiments.library_transfer import (
    CONDITIONS,
    ORDERS,
    random_library,
    run_library_transfer,
)
from hekmatki.experiments.new_world import HANDLINGS, PHASES, live, run_new_world, swapped
from hekmatki.general.agent import GeneralAgent
from hekmatki.general.env import Wiring
from hekmatki.general_report import print_table


def test_one_agent_three_worlds() -> None:
    rows = run_general_worlds(seeds=1)
    assert [row.world for row in rows] == [spec.name for spec in WORLDS]
    for row in rows:
        assert set(row.steps) == set(AGENTS)
        assert row.form_found == 1.0
        assert row.reached["Form + Regeln"] == 1.0
    search = rows[-1]
    assert search.size == "1.048.575 Schlüssel"
    assert search.steps["Form + Regeln"] == search.best
    assert search.reached["Zufall"] == 0.0


def test_world_runs_are_repeatable() -> None:
    spec = WORLD_BY_NAME["2D-Raum"]
    first = run_world(spec, make_agent("Form + Regeln", spec), seed=3)
    second = run_world(spec, make_agent("Form + Regeln", spec), seed=3)
    assert first.test_steps == second.test_steps
    assert isinstance(first.agent, GeneralAgent)


def test_library_transfer_reports_both_orders() -> None:
    rows, entries = run_library_transfer(seeds=1)
    assert [(r.order, r.world) for r in rows] == [
        (" → ".join(order), world) for order in ORDERS for world in order
    ]
    for row in rows:
        assert set(row.tested) == set(CONDITIONS)
    three_d = next(r for r in rows if r.world == "3D-Raum")
    assert three_d.borrowed["mit Bibliothek"] > 0
    assert three_d.tested_found["mit Bibliothek"] < three_d.tested_found["ohne Bibliothek"]
    assert three_d.tested["ohne Bibliothek"] >= three_d.tested_found["ohne Bibliothek"]
    assert any(e.origin == "2D-Raum" and e.reuses for e in entries)


def test_random_library_has_no_blocking_pattern() -> None:
    library = random_library(random.Random(0))
    assert len(library.entries) == 2
    assert all("bleibt" not in str(entry.pattern) for entry in library.entries)


def test_new_world_detection() -> None:
    rows = run_new_world(seeds=1)
    assert [row.handling for row in rows] == list(HANDLINGS)
    by_name = {row.handling: row for row in rows}
    assert by_name["ohne Erkennung"].maps == 1
    assert by_name["jede Überraschung"].false_alarms > 10
    assert set(by_name["erwartet / unerwartet"].steps) == set(PHASES)


def test_swapped_wiring_changes_every_action() -> None:
    wiring = Wiring.shuffled(8, 4, random.Random(1))
    other = swapped(wiring, random.Random(2))
    assert other.components == wiring.components
    assert all(a != b for a, b in zip(other.actions, wiring.actions, strict=True))
    life = live("erwartet / unerwartet", 0)
    assert list(life.steps) == list(PHASES)


def test_print_table(capsys: object) -> None:
    print_table(["Welt", "Wert"], [["A", "1.0"], ["Raum", "12.5"]])
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Raum | 12.5" in out


def test_world_replay_records_longest_round() -> None:
    for spec in WORLDS:
        replay = world_replay(spec)
        assert replay["steps"] == len(replay["pressed"]) == len(replay["observations"]) - 1
        assert 1 <= replay["round"] <= replay["rounds"]
        assert replay["form"]["axes"], spec.name
    search = world_replay(WORLD_BY_NAME["Suche"])
    assert search["kind"] == "search"
    assert search["form"]["name"] == "Ordnung"
    assert search["frames"][-1]["index"] == search["targetIndex"]


def test_replay_template_has_one_data_marker() -> None:
    assert TEMPLATE.read_text(encoding="utf-8").count(DATA_MARKER) == 1


def test_every_agent_gets_the_same_test_tasks() -> None:
    spec = WORLD_BY_NAME["2D-Raum"]
    least = {agent: run_world(spec, make_agent(agent, spec), seed=0).test_least for agent in AGENTS}
    assert same_tasks(least) == least["Zufall"]


def test_different_tasks_are_not_compared() -> None:
    with pytest.raises(ValueError, match="andere Prüfaufgaben"):
        same_tasks({"Zufall": [30, 6], "Form + Regeln": [18, 28]})
