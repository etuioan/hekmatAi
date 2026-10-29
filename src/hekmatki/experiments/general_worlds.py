"""Ein Agent, drei Welten (ab 0.16, H19): Versteht derselbe Agent ganz verschiedene Umgebungen?

Tenshiras Frage nach Runde 5: Was, wenn die neue Umgebung gar kein ähnliches Spiel ist,
sondern plötzlich dreidimensional, oder eine Datenmenge, in der man unter Millionen Einträgen
etwas finden muss? Drei Welten, ein Agent, derselbe Code:
- „2D-Raum“: Raster mit Hindernissen
- „3D-Raum“: Würfel mit Hindernissen
- „Suche“: ein sortierter Datenbestand, als Suchbaum begehbar

Der Agent sieht nur Zahlen, gemischt in einer Reihenfolge, die jede Welt selbst festlegt.
Er lernt nach einem kleinen Lehrplan: erst kleine Umgebungen (Raster 4×4 bis 6×6, Würfel
3×3×3 und 4×4×4, Suchbäume mit 7, 15 und 31 Schlüsseln), dann die Prüfung in einer großen
(Raster 25×25, Würfel 10×10×10, 1.048.575 Schlüssel). Zum Vergleich:
- „Zufall“: zufällige Tasten
- „Tabelle“: Q-Lernen ohne Regeln, kann nicht auf Neues übertragen
- „Regeln ohne Form“: dieselben Regeln, aber nur einen Schritt vorausgedacht (H19-Gegenprobe)
- „Form + Regeln“: der allgemeine Agent

Grundlage: Lehrplan vom Kleinen zum Großen (Elman 1993, Oudeyer 2007; im Dossier als
Lehrplan-Generator), Form vor Regeln (Kemp & Tenenbaum 2008, Philipona 2003).
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from statistics import mean
from typing import Final, Literal

from hekmatki.general.agent import GeneralAgent, Planning
from hekmatki.general.env import Environment, Wiring
from hekmatki.general.library import Library
from hekmatki.general.run import Learner, RandomAgent, TableAgent, play_episode
from hekmatki.general.worlds import SortedSearch, random_lattice

LESSON_EPISODES: Final = 6
LESSON_LIMIT: Final = 300
TEST_EPISODES: Final = 5
TEST_LIMIT: Final = 2000

Agent = Literal["Zufall", "Tabelle", "Regeln ohne Form", "Form + Regeln"]
AGENTS: tuple[Agent, ...] = ("Zufall", "Tabelle", "Regeln ohne Form", "Form + Regeln")


@dataclass(frozen=True)
class WorldSpec:
    """Eine Art von Welt: Lehrplan, Prüfung und wie man sie baut."""

    name: str
    components: int
    actions: int
    lessons: tuple[int, ...]
    test: int
    expected_form: str
    build: Callable[[int, Wiring, random.Random], Environment]
    size_text: Callable[[int], str]


def _lattice(dims: int) -> Callable[[int, Wiring, random.Random], Environment]:
    def build(size: int, wiring: Wiring, rng: random.Random) -> Environment:
        return random_lattice(dims, size, wiring, rng)

    return build


def _search(height: int, wiring: Wiring, rng: random.Random) -> Environment:
    return SortedSearch(height, wiring, rng.randrange(1_000_000))


WORLDS: Final = (
    WorldSpec(
        "2D-Raum", 8, 4, (4, 5, 6), 25, "Raum mit 2 Dimensionen", _lattice(2), lambda s: f"{s}×{s}"
    ),
    WorldSpec(
        "3D-Raum",
        12,
        6,
        (3, 4),
        10,
        "Raum mit 3 Dimensionen",
        _lattice(3),
        lambda s: f"{s}×{s}×{s}",
    ),
    WorldSpec(
        "Suche",
        4,
        3,
        (3, 4, 5),
        20,
        "Ordnung",
        _search,
        lambda h: f"{2**h - 1:,} Schlüssel".replace(",", "."),
    ),
)
WORLD_BY_NAME: Final = {spec.name: spec for spec in WORLDS}


@dataclass(frozen=True)
class WorldRun:
    """Ein Lauf eines Agenten durch Lehrplan und Prüfung einer Welt."""

    test_steps: list[int]
    test_reached: list[bool]
    test_least: list[int]
    agent: Learner


def make_agent(agent: Agent, spec: WorldSpec, library: Library | None = None) -> Learner:
    """Baut einen Agenten für diese Welt."""
    match agent:
        case "Zufall":
            return RandomAgent(spec.actions)
        case "Tabelle":
            return TableAgent(spec.actions)
        case "Regeln ohne Form":
            return GeneralAgent(spec.actions, Planning.GREEDY, library)
        case "Form + Regeln":
            return GeneralAgent(spec.actions, Planning.FORM, library)


@dataclass(frozen=True)
class Setting:
    """Eine Welt für einen Lauf: Mischung, Lehrplan, Prüfung und der Zufall für die Runden."""

    wiring: Wiring
    lessons: list[Environment]
    test: Environment
    rng: random.Random


def prepare(spec: WorldSpec, seed: int) -> Setting:
    """Baut Lehrplan und Prüfung; mit gleichem `seed` für jeden Agenten dieselben."""
    worlds = random.Random(seed)
    wiring = Wiring.shuffled(spec.components, spec.actions, worlds)
    lessons = [spec.build(size, wiring, worlds) for size in spec.lessons]
    test = spec.build(spec.test, wiring, worlds)
    return Setting(wiring, lessons, test, random.Random(seed * 7919 + 1))


def teach(learner: Learner, setting: Setting) -> None:
    """Der Lehrplan: einige Runden in jeder kleinen Umgebung, danach die große als neuer Ort."""
    for env in setting.lessons:
        learner.new_place()
        for _ in range(LESSON_EPISODES):
            play_episode(env, learner, setting.rng, LESSON_LIMIT)
    learner.new_place()


def run_world(spec: WorldSpec, learner: Learner, seed: int) -> WorldRun:
    """Lehrplan, dann Prüfung."""
    setting = prepare(spec, seed)
    teach(learner, setting)
    episodes = [
        play_episode(setting.test, learner, setting.rng, TEST_LIMIT) for _ in range(TEST_EPISODES)
    ]
    return WorldRun(
        [e.steps for e in episodes],
        [e.reached for e in episodes],
        [e.least for e in episodes],
        learner,
    )


@dataclass(frozen=True)
class WorldRow:
    """Ergebnis einer Welt über alle Läufe."""

    world: str
    size: str
    steps: dict[Agent, float]
    """Mittlere Schritte bis zum Ziel in der Prüfung (nicht erreicht zählt als TEST_LIMIT)."""
    reached: dict[Agent, float]
    """Anteil der Prüfrunden, in denen das Ziel erreicht wurde."""
    best: float
    """Mittlerer kürzester Weg."""
    form_found: float
    """Anteil der Läufe, in denen „Form + Regeln“ die richtige Form gefunden hat."""
    forms: tuple[str, ...]
    """Die gefundenen Formen, je Lauf."""


def run_general_worlds(seeds: int = 10) -> list[WorldRow]:
    """Alle drei Welten, alle Agenten."""
    return [_world_row(spec, seeds) for spec in WORLDS]


def _world_row(spec: WorldSpec, seeds: int) -> WorldRow:
    steps: dict[Agent, float] = {}
    reached: dict[Agent, float] = {}
    best: list[int] = []
    forms: list[str] = []
    for agent in AGENTS:
        runs = [run_world(spec, make_agent(agent, spec), seed) for seed in range(seeds)]
        steps[agent] = mean(s for run in runs for s in run.test_steps)
        reached[agent] = mean(r for run in runs for r in run.test_reached)
        if agent == "Form + Regeln":
            best = [least for run in runs for least in run.test_least]
            forms = [_form_name(run.agent) for run in runs]
    found = mean(form == spec.expected_form for form in forms)
    return WorldRow(
        spec.name, spec.size_text(spec.test), steps, reached, mean(best), found, tuple(forms)
    )


def _form_name(learner: Learner) -> str:
    if not isinstance(learner, GeneralAgent):
        raise TypeError("Nur der allgemeine Agent hat eine Form.")
    return learner.form().name
