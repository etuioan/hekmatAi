"""Tests für die verteilte Crafter-Messung; ohne `crafter` übersprungen."""

from pathlib import Path

import pytest

pytest.importorskip("crafter")

from hekmatki.experiments.crafter_batch import merge_parts, seed_spread
from hekmatki.experiments.crafter_run import Career, Round, save_careers


def career(seed: int, wood_rounds: int) -> Career:
    rounds = [Round(100, ((5, "collect_wood"),)) for _ in range(wood_rounds)]
    rounds += [Round(100, ()) for _ in range(4 - wood_rounds)]
    return Career("Zufall", seed, rounds)


def test_merge_keeps_all_parts(tmp_path: Path) -> None:
    save_careers([career(0, 1)], tmp_path / "a.json")
    save_careers([career(1, 2)], tmp_path / "b.json")
    merged = merge_parts([tmp_path / "a.json", tmp_path / "b.json"])
    assert [c.seed for c in merged] == [0, 1]


def test_merge_refuses_the_same_seed_twice(tmp_path: Path) -> None:
    save_careers([career(0, 1)], tmp_path / "a.json")
    with pytest.raises(ValueError, match="Doppelt"):
        merge_parts([tmp_path / "a.json", tmp_path / "a.json"])


def test_spread_is_over_single_maps() -> None:
    always_wood = 101 ** (1 / 22) - 1  # Wertung, wenn nur Holz immer gelingt
    average, deviation = seed_spread([career(0, 0), career(1, 4)], warmup=0)["Zufall"]
    assert average == pytest.approx(always_wood / 2)
    assert deviation == pytest.approx(always_wood / 2**0.5)
