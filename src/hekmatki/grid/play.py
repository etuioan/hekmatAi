"""Ein Spiel der 2D-Welt durchspielen und auf Wunsch jeden Schritt aufzeichnen.

Ein Agent, dessen Wissen einer Beobachtung widerspricht und der darauf nur mit einem Fehler
(`ContradictionError`) antworten kann, scheidet aus: Das Spiel endet für ihn an dieser Stelle.
"""

import random
from dataclasses import dataclass
from typing import Protocol

from hekmatki.grid.effects import ContradictionError
from hekmatki.grid.world import Color, Grid, GridGame


class GridAgent(Protocol):
    """Was ein Agent in der 2D-Welt können muss."""

    @property
    def reason(self) -> str:
        """Warum er zuletzt seine Taste gewählt hat."""
        ...

    def choose(self, grid: Grid, rng: random.Random, steps_left: int) -> str:
        """Wählt die nächste Taste."""
        ...

    def learn(self, before: Grid, button: str, after: Grid, won: bool) -> None:
        """Lernt aus einem Tastendruck."""
        ...

    def beliefs(self) -> dict[Color, str]:
        """Was er über jede Farbe weiß oder vermutet."""
        ...


@dataclass(frozen=True)
class Frame:
    """Ein aufgezeichneter Moment: was der Agent sah, was er drückte und warum."""

    grid: Grid
    button: str | None
    """`None` im letzten Bild nach dem letzten Tastendruck."""
    reason: str
    beliefs: dict[Color, str]
    won: bool = False
    trapped: bool = False


@dataclass(frozen=True)
class GridPlay:
    """Wie ein Spiel lief."""

    first_win: int | None
    """Nach wie vielen Tastendrücken der erste Sieg kam (`None`: nie)."""
    wins: int
    traps: int
    """Wie oft der Agent in eine Falle trat."""
    frames: tuple[Frame, ...] = ()
    stopped: str | None = None
    """Warum der Agent ausgeschieden ist (`None`: er hat bis zum Ende gespielt)."""
    stopped_at: int | None = None
    """Bei welchem Tastendruck er ausgeschieden ist."""
    restarts: int = 0
    """Wie oft er die Neustart-Taste gedrückt hat."""


def play_grid(
    game: GridGame, agent: GridAgent, steps: int, rng: random.Random, record: bool = False
) -> GridPlay:
    """Lässt den Agenten `steps` Tasten drücken. Mit `record` wird jeder Schritt aufgezeichnet."""
    state = game.start
    first_win: int | None = None
    wins = traps = restarts = 0
    frames: list[Frame] = []
    stopped: str | None = None
    stopped_at: int | None = None
    for step_number in range(1, steps + 1):
        before = game.render(state)
        button = agent.choose(before, rng, steps_left=steps - step_number + 1)
        beliefs = agent.beliefs() if record else {}
        step = game.step(state, button)
        wins += step.won
        traps += step.trapped
        restarts += step.restarted
        if step.won and first_win is None:
            first_win = step_number
        state = step.state
        try:
            agent.learn(before, button, game.render(state), step.won)
        except ContradictionError as error:
            stopped, stopped_at = str(error), step_number
        if record:
            reason = agent.reason if stopped is None else f"bricht ab: {stopped}"
            frames.append(Frame(before, button, reason, beliefs, step.won, step.trapped))
        if stopped is not None:
            break
    if record:
        frames.append(Frame(game.render(state), None, "", agent.beliefs()))
    return GridPlay(first_win, wins, traps, tuple(frames), stopped, stopped_at, restarts)
