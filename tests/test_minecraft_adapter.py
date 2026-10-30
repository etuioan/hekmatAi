"""Tests für den Minecraft-Adapter und die Messung (nach 0.20), ohne Server und ohne Node.

Eine gespielte Verbindung (`FakeConnection`) ersetzt die Brücke. Ob die Brücke selbst mit einem
Server spielt, prüft der Workflow `minecraft.yml`.
"""

import json
import random
from pathlib import Path
from typing import Any

import pytest

from hekmatki.adapters.minecraft import MinecraftWorld
from hekmatki.adapters.minecraft_server import offline_uuid, prepare
from hekmatki.experiments.minecraft_run import (
    ADVANCEMENTS,
    Career,
    Round,
    load_careers,
    play,
    rows,
    save_careers,
    score,
)

LAYOUT = ("Block vorne", "Leben", "Ort x")
ACTIONS = ("nichts", "vor", "angreifen", "benutzen")


class FakeConnection:
    """Eine Brücke zum Mitschreiben: Taste 1 läuft, Taste 2 bringt einen Fortschritt."""

    layout = LAYOUT
    action_names = ACTIONS

    def __init__(self, dies_at: int | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self.dies_at = dies_at
        self.x = 0
        self.steps = 0

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(message)
        advancements: list[str] = []
        if message["op"] == "reset":
            self.x, self.steps = 0, 0
        elif message["action"] == 1:
            self.x += 1
        elif message["action"] == 2:
            advancements = [ADVANCEMENTS[1]]
        self.steps += message["op"] == "step"
        dead = self.dies_at is not None and self.steps >= self.dies_at
        answer = {"inner": [5, 20, self.x], "advancements": advancements, "dead": dead}
        if message.get("record"):
            answer["scene"] = {"action": ACTIONS[message.get("action", 0)], "position": [self.x]}
        return answer

    def close(self) -> None:
        pass


def inner_key(world: MinecraftWorld, name: str) -> int:
    """Welche Taste des Agenten die innere Handlung `name` auslöst."""
    return world.wiring.actions.index(ACTIONS.index(name))


def test_observation_is_mixed_numbers_and_names_match() -> None:
    world = MinecraftWorld(3, FakeConnection())
    observation = world.reset(random.Random(0))
    components, actions = world.names()
    assert dict(zip(components, observation, strict=True)) == {
        "Block vorne": 5,
        "Leben": 20,
        "Ort x": 0,
    }
    assert sorted(actions) == sorted(ACTIONS)
    assert world.actions == len(ACTIONS)


def test_keys_are_mixed_before_they_reach_the_bridge() -> None:
    connection = FakeConnection()
    world = MinecraftWorld(5, connection)
    world.reset(random.Random(0))
    world.step(inner_key(world, "vor"), random.Random(0))
    assert connection.requests[-1] == {
        "op": "step",
        "action": ACTIONS.index("vor"),
        "record": False,
    }


def test_goal_reached_only_for_a_new_advancement() -> None:
    world = MinecraftWorld(1, FakeConnection())
    world.reset(random.Random(0))
    attack = inner_key(world, "angreifen")
    assert world.step(attack, random.Random(0)).reached
    assert not world.step(attack, random.Random(0)).reached
    assert world.unlocked == [(1, ADVANCEMENTS[1])]


def test_round_ends_at_death_or_length() -> None:
    world = MinecraftWorld(1, FakeConnection(dies_at=3), length=10)
    world.reset(random.Random(0))
    for _ in range(3):
        world.step(0, random.Random(0))
    assert world.finished
    with pytest.raises(RuntimeError):
        world.step(0, random.Random(0))
    short = MinecraftWorld(1, FakeConnection(), length=2)
    short.reset(random.Random(0))
    short.step(0, random.Random(0))
    short.step(0, random.Random(0))
    assert short.finished


def test_each_round_asks_for_a_new_place() -> None:
    connection = FakeConnection()
    world = MinecraftWorld(2, connection)
    world.reset(random.Random(0))
    world.reset(random.Random(0))
    seeds = [m["seed"] for m in connection.requests if m["op"] == "reset"]
    assert len(set(seeds)) == 2


def test_play_and_save_and_merge(tmp_path: Path) -> None:
    world = MinecraftWorld(4, FakeConnection(), length=20)
    career = play("Zufall", world, episodes=6)
    assert len(career.rounds) == 6
    assert all(r.steps == 20 for r in career.rounds)
    part = tmp_path / "teil.json"
    save_careers([career], part)
    loaded = load_careers([part])
    assert loaded[0].rounds == career.rounds
    with pytest.raises(ValueError, match="doppelt"):
        load_careers([part, part])


def test_rows_count_only_rounds_after_warmup() -> None:
    hit = Round(10, ((3, ADVANCEMENTS[0]), (5, "minecraft:story/lava_bucket")))
    career = Career("Zufall", 0, [Round(10, ())] * 4 + [hit, Round(10, ())])
    row = rows([career], warmup=4)[0]
    assert row.rates[ADVANCEMENTS[0]] == 0.5
    assert row.others == {"minecraft:story/lava_bucket": 0.5}
    assert row.per_round == 1.0
    assert score({name: 0.0 for name in ADVANCEMENTS}) == pytest.approx(0.0)


def test_offline_uuid_matches_minecraft() -> None:
    assert str(offline_uuid("Notch")) == "b50ad385-829d-3141-a216-7e7d7539ba7f"


def test_server_files_accept_eula_only_when_asked(tmp_path: Path) -> None:
    prepare(tmp_path, 7, eula_accepted=False)
    assert (tmp_path / "eula.txt").read_text() == "eula=false\n"
    assert "level-seed=7" in (tmp_path / "server.properties").read_text()
    assert json.loads((tmp_path / "ops.json").read_text())[0]["name"] == "hekmat"
    prepare(tmp_path, 7, eula_accepted=True)
    assert (tmp_path / "eula.txt").read_text() == "eula=true\n"


def test_replay_records_only_the_last_round(tmp_path: Path) -> None:
    world = MinecraftWorld(4, FakeConnection(), length=5)
    path = tmp_path / "wiedergabe.json"
    play("Zufall", world, episodes=3, replay=path)
    data = json.loads(path.read_text())
    assert data["episode"] == 3
    assert len(data["scenes"]) == 6  # Start und fünf Schritte
    assert all("advancements" in scene for scene in data["scenes"])


class SightConnection(FakeConnection):
    """Wie `FakeConnection`, aber mit Fadenkreuz und einem Fach: Taste 1 schaut auf einen
    Block (Nummer 7, sonst −1) und legt Ding 3, dann Ding 4 ins Fach."""

    layout = ("Block im Blick", "Fach 1 Ding", "Fach 1 Anzahl")

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        answer = super().request(message)
        looks = message["op"] == "step" and message["action"] == 1
        answer["inner"] = [7 if looks else -1, 2 + self.x if self.x else 0, min(self.x, 1)]
        return answer


def test_round_counts_sight_and_things_for_the_report() -> None:
    world = MinecraftWorld(0, SightConnection(), length=5)
    world.reset(random.Random(0))
    walk, idle = inner_key(world, "vor"), inner_key(world, "nichts")
    for action in (walk, idle, walk):
        world.step(action, random.Random(0))
    assert world.looking == 2
    assert world.items == {3, 4}
    world.reset(random.Random(0))
    assert (world.looking, world.items) == (0, set())
