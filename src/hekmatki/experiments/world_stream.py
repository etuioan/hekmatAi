"""Ein Strom ganz verschiedener Welten (ab 0.17, H23): Erkennt der Agent jeden Wechsel?

In 0.16 wurde das Erkennen einer neuen Welt nur mit vertauschten Tasten geprüft: Raum A,
derselbe Raum B mit anderen Tasten, wieder A. Hier erlebt ein Agent ohne Ankündigung Welten,
die nichts miteinander zu tun haben, hinter derselben Schnittstelle (`Padded`: 8 Größen,
6 Tasten):

1. „Raum“: rutschiger Raum 7×7 wie in `new_world` (jeder 10. Schritt geht nicht)
2. „Suchbaum“: sortierter Datenbestand mit 63 Schlüsseln
3. „Drehscheiben“: drei Scheiben mit je 8 Stellungen
4. „Raum wieder“: derselbe Raum wie am Anfang

Gemessen: Schritte je Runde in jeder Phase, wie oft ein Wechsel in den ersten 30 Schritten
erkannt wird, überzählige Wechsel (mehr als einer je Phase, in der ersten Phase jeder), und
ob der Agent im letzten Abschnitt zu seiner ersten Karte zurückkehrt.

Verglichen werden dieselben Umgänge mit Überraschung wie in `new_world`, dazu der
Bayes-Faktor (H23).
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Final

from hekmatki.experiments.new_world import EPISODE_LIMIT, EPISODES, HANDLINGS, NO_DETECTOR, SLIP
from hekmatki.general.agent import GeneralAgent, MapEvent
from hekmatki.general.detector import Detector, Strategy
from hekmatki.general.env import Environment, Padded, Wiring
from hekmatki.general.run import play_episode
from hekmatki.general.worlds import Dials, SortedSearch, random_lattice

WIDTH: Final = 8
ACTIONS: Final = 6
PHASES: Final = ("Raum", "Suchbaum", "Drehscheiben", "Raum wieder")
WITHIN: Final = 30
"""Ein Wechsel gilt als erkannt, wenn die Karte in so vielen Schritten wechselt."""


@dataclass(frozen=True)
class StreamLife:
    """Ein Lauf durch alle Phasen."""

    steps: dict[str, list[int]]
    starts: dict[str, int]
    events: list[MapEvent]
    maps: int


@dataclass(frozen=True)
class StreamRow:
    """Ein Umgang mit Überraschung, gemittelt über alle Läufe."""

    handling: str
    steps: dict[str, float]
    """Mittlere Schritte je Runde in jeder Phase."""
    detected: dict[str, float]
    """Je Phase ab der zweiten: Anteil der Läufe, in denen der Wechsel erkannt wurde."""
    extra: float
    """Überzählige Kartenwechsel je Lauf."""
    returned: float
    """Anteil der Läufe, in denen der Agent im letzten Abschnitt zur ersten Karte zurückkehrt."""
    maps: float


def worlds(seed: int) -> list[Environment]:
    """Die Welten des Stroms, in der Reihenfolge der Phasen."""
    rng = random.Random(seed)
    room = random_lattice(2, 7, Wiring.shuffled(8, 4, rng), rng, slip=SLIP)
    search = SortedSearch(6, Wiring.shuffled(4, 3, rng), rng.randrange(1_000_000))
    dials = Dials(3, 8, Wiring.shuffled(6, 6, rng))
    return [Padded(env, WIDTH, ACTIONS) for env in (room, search, dials, room)]


def live(handling: str, seed: int) -> StreamLife:
    """Ein Agent lebt durch alle Phasen."""
    detector = None if handling == NO_DETECTOR else Detector(Strategy(handling))
    agent = GeneralAgent(ACTIONS, detector=detector)
    rng = random.Random(seed * 7919 + 5)
    steps: dict[str, list[int]] = {}
    starts: dict[str, int] = {}
    for phase, env in zip(PHASES, worlds(seed), strict=True):
        starts[phase] = agent.steps
        steps[phase] = [play_episode(env, agent, rng, EPISODE_LIMIT).steps for _ in range(EPISODES)]
    return StreamLife(steps, starts, agent.events, len(agent.maps))


def run_world_stream(seeds: int = 10) -> list[StreamRow]:
    """Alle Umgänge mit Überraschung."""
    return [_row(handling, [live(handling, s) for s in range(seeds)]) for handling in HANDLINGS]


def _row(handling: str, lives: Sequence[StreamLife]) -> StreamRow:
    return StreamRow(
        handling,
        {p: mean(s for life in lives for s in life.steps[p]) for p in PHASES},
        {p: mean(_detected(life, p) for life in lives) for p in PHASES[1:]},
        mean(_extra(life) for life in lives),
        mean(_returned(life) for life in lives),
        mean(life.maps for life in lives),
    )


def _in_phase(life: StreamLife, phase: str) -> list[MapEvent]:
    """Kartenwechsel in einer Phase (Verfeinern einer Regel zählt nicht)."""
    index = PHASES.index(phase)
    start = life.starts[phase]
    end = life.starts[PHASES[index + 1]] if index + 1 < len(PHASES) else 10**9
    return [e for e in life.events if start < e.step <= end and e.kind != "verfeinern"]


def _detected(life: StreamLife, phase: str) -> bool:
    start = life.starts[phase]
    return any(e.step <= start + WITHIN for e in _in_phase(life, phase))


def _extra(life: StreamLife) -> int:
    first, *later = PHASES
    return len(_in_phase(life, first)) + sum(max(len(_in_phase(life, p)) - 1, 0) for p in later)


def _returned(life: StreamLife) -> bool:
    events = _in_phase(life, PHASES[-1])
    return bool(events) and events[0].kind == "zurück" and events[0].target == 0
