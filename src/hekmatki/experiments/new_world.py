"""Eine neue Umgebung erkennen (ab 0.16, H18): Rauschen oder andere Welt?

Der allgemeine Agent lebt in einem rutschigen Raum (2D, 7×7): Jeder zehnte Schritt geht
nicht, das ist erwartete Unsicherheit. Ohne Ankündigung werden dann die Tasten vertauscht
(eine andere Umgebung mit demselben Aussehen), später kommt der alte Raum zurück:

1. „A“: der rutschige Raum
2. „B“: derselbe Raum, Tasten vertauscht
3. „A wieder“: zurück in A

Vier Agenten, gleich bis auf den Umgang mit Überraschung (`general/detector.py`):
- „ohne Erkennung“: eine Karte, lernt einfach weiter
- „jede Überraschung“: wechselt bei jedem Fehler einer verlässlichen Regel
- „nie neue Karte“: lernt bei deutlicher Überraschung eine Karte neu
- „erwartet / unerwartet“: H18, wechselt nur bei unerwarteter Unsicherheit und kehrt zu
  alten Karten zurück

Gemessen: Schritte je Runde in jeder Phase, Zahl der Karten, Fehlalarme in A, wie schnell
der Wechsel erkannt wird und ob der Agent bei der Rückkehr seine alte Karte wiederfindet.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Final

from hekmatki.general.agent import GeneralAgent, MapEvent
from hekmatki.general.detector import Detector, Strategy
from hekmatki.general.env import Wiring
from hekmatki.general.run import Chance, play_episode
from hekmatki.general.worlds import Lattice, random_lattice

SIZE: Final = 7
SLIP: Final = 0.1
EPISODES: Final = 15
EPISODE_LIMIT: Final = 300
PHASES: Final = ("A", "B", "A wieder")
NO_DETECTOR: Final = "ohne Erkennung"
HANDLINGS: Final = (NO_DETECTOR, *(s.value for s in Strategy))


@dataclass(frozen=True)
class Life:
    """Ein Lauf durch alle drei Phasen."""

    steps: dict[str, list[int]]
    """Schritte je Runde, je Phase."""
    starts: dict[str, int]
    """Bei welchem Schritt (des ganzen Laufs) die Phase beginnt."""
    events: list[MapEvent]
    maps: int
    history: list[float]


@dataclass(frozen=True)
class NewWorldRow:
    """Ein Umgang mit Überraschung, gemittelt über alle Läufe."""

    handling: str
    steps: dict[str, float]
    """Mittlere Schritte je Runde in jeder Phase."""
    first_steps: dict[str, float]
    """Mittlere Schritte der ersten drei Runden jeder Phase (dort zählt die Erkennung)."""
    maps: float
    false_alarms: float
    """Kartenwechsel in Phase A, obwohl sich nichts geändert hat."""
    detected_b: float
    """Anteil der Läufe, in denen der Wechsel zu B in den ersten 30 Schritten erkannt wurde."""
    returned: float
    """Anteil der Läufe, in denen der Agent in „A wieder“ zu seiner ersten Karte zurückkehrt."""


def swapped(wiring: Wiring, rng: random.Random) -> Wiring:
    """Dieselben Größen, aber jede Taste tut etwas anderes als vorher."""
    while True:
        order = list(wiring.actions)
        rng.shuffle(order)
        if all(a != b for a, b in zip(order, wiring.actions, strict=True)):
            return Wiring(wiring.components, tuple(order))


def live(handling: str, seed: int) -> Life:
    """Ein Agent lebt durch A, B und wieder A."""
    worlds = random.Random(seed)
    wiring = Wiring.shuffled(8, 4, worlds)
    room_a = random_lattice(2, SIZE, wiring, worlds, slip=SLIP)
    room_b = Lattice(2, SIZE, room_a.blocked, swapped(wiring, worlds), SLIP)
    detector = None if handling == NO_DETECTOR else Detector(Strategy(handling))
    agent = GeneralAgent(4, detector=detector)
    chance = Chance.seeded(seed * 7919 + 3)
    steps: dict[str, list[int]] = {}
    starts: dict[str, int] = {}
    for phase, room in zip(PHASES, (room_a, room_b, room_a), strict=True):
        starts[phase] = agent.steps
        steps[phase] = [
            play_episode(room, agent, chance, EPISODE_LIMIT).steps for _ in range(EPISODES)
        ]
    history = [] if detector is None else detector.history
    return Life(steps, starts, agent.events, len(agent.maps), history)


def run_new_world(seeds: int = 10) -> list[NewWorldRow]:
    """Alle vier Umgänge mit Überraschung."""
    return [_row(handling, [live(handling, s) for s in range(seeds)]) for handling in HANDLINGS]


def _row(handling: str, lives: Sequence[Life]) -> NewWorldRow:
    return NewWorldRow(
        handling,
        {p: mean(s for life in lives for s in life.steps[p]) for p in PHASES},
        {p: mean(s for life in lives for s in life.steps[p][:3]) for p in PHASES},
        mean(life.maps for life in lives),
        mean(len(_in_phase(life, "A")) for life in lives),
        mean(_detected(life, "B", within=30) for life in lives),
        mean(_returned(life) for life in lives),
    )


def _in_phase(life: Life, phase: str) -> list[MapEvent]:
    """Kartenwechsel in einer Phase (Verfeinern einer Regel zählt nicht)."""
    index = PHASES.index(phase)
    start = life.starts[phase]
    end = life.starts[PHASES[index + 1]] if index + 1 < len(PHASES) else 10**9
    return [e for e in life.events if start < e.step <= end and e.kind != "verfeinern"]


def _detected(life: Life, phase: str, within: int) -> bool:
    start = life.starts[phase]
    return any(start < e.step <= start + within for e in _in_phase(life, phase))


def _returned(life: Life) -> bool:
    events = _in_phase(life, "A wieder")
    return bool(events) and events[0].kind == "zurück" and events[0].target == 0
