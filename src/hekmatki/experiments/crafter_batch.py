"""Crafter-Messung in Teilen: jede Karte einzeln messen, danach alles zusammenführen.

So lässt sich eine Messung auf viele Rechner verteilen (GitHub Actions, später eigene PCs):
Jeder Rechner misst mit `play` einen Startwert und schreibt eine Teil-Datei, `merge` liest alle
Teile, prüft sie und druckt dieselbe Tabelle wie `crafter_run`, dazu die Streuung zwischen den
Karten. Die Teil-Dateien haben dasselbe Format wie `crafter_run.save_careers`.

Aufruf:
`python -m hekmatki.experiments.crafter_batch play 7 teil-7.json`
`python -m hekmatki.experiments.crafter_batch merge messung.json teil-*.json`
"""

import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from statistics import mean, stdev

from hekmatki.experiments.crafter_run import (
    AGENTS,
    EPISODES,
    WARMUP,
    Agent,
    Career,
    load_careers,
    play,
    report_crafter,
    rows,
    save_careers,
)


def play_seed(seed: int, episodes: int = EPISODES) -> list[Career]:
    """Alle Agenten auf einer Karte, jeder Agent in einem eigenen Prozess."""
    with ProcessPoolExecutor(min(len(AGENTS), os.cpu_count() or 1)) as pool:
        return list(pool.map(play, AGENTS, [seed] * len(AGENTS), [episodes] * len(AGENTS)))


def merge_parts(parts: list[Path]) -> list[Career]:
    """Liest alle Teil-Dateien; derselbe Agent mit demselben Startwert darf nur einmal kommen."""
    found = [career for part in parts for career in load_careers(part)]
    seen: set[tuple[Agent, int]] = set()
    for career in found:
        key = (career.agent, career.seed)
        if key in seen:
            raise ValueError(f"Doppelt gemessen: {career.agent} mit Startwert {career.seed}")
        seen.add(key)
    return found


def seed_spread(found: list[Career], warmup: int = WARMUP) -> dict[Agent, tuple[float, float]]:
    """Je Agent Mittelwert und Standardabweichung der Wertung über die einzelnen Karten."""
    spread = {}
    for agent in dict.fromkeys(c.agent for c in found):
        scores = [rows([c], warmup)[0].score for c in found if c.agent == agent]
        spread[agent] = (mean(scores), stdev(scores) if len(scores) > 1 else 0.0)
    return spread


def report_spread(found: list[Career]) -> None:
    """Druckt die Streuung zwischen den Karten: Nur wenn die Abstände größer sind, zählen sie."""
    seeds = sorted({c.seed for c in found})
    print(f"Wertung je Karte ({len(seeds)} Startwerte: {seeds[0]} bis {seeds[-1]}):\n")
    for agent, (average, deviation) in seed_spread(found).items():
        print(f"{agent:<12} | {average:>5.2f} ± {deviation:.2f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("play", help="alle Agenten auf einer Karte messen")
    one.add_argument("seed", type=int)
    one.add_argument("output", type=Path)
    one.add_argument("--episodes", type=int, default=EPISODES)
    merge = commands.add_parser("merge", help="Teil-Dateien zusammenführen und auswerten")
    merge.add_argument("output", type=Path)
    merge.add_argument("parts", type=Path, nargs="+")
    args = parser.parse_args()

    if args.command == "play":
        save_careers(play_seed(args.seed, args.episodes), args.output)
        return
    found = merge_parts(args.parts)
    save_careers(found, args.output)
    report_crafter(rows(found))
    report_spread(found)


if __name__ == "__main__":
    main()
