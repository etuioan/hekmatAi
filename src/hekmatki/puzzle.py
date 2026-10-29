"""Die Spielefamilie „Schlüssel und Tür“: gleiche Mechanik, anderes Aussehen, andere Tasten.

Ein Gang aus wenigen Feldern. Irgendwo liegt ein Schlüssel, irgendwo eine Tür. Wer mit dem
Schlüssel an der Tür „benutzen“ drückt, gewinnt und beginnt von vorn. Der Agent sieht nur
ein Symbol pro Zustand (etwa „rot kreis“) und drei Tasten mit beliebigen Namen. Was die
Symbole bedeuten und welche Taste was tut, muss er selbst herausfinden, wie bei ARC-AGI-3.
"""

import random
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import product

WIN = "gewonnen"
"""Was der Agent sieht, wenn er gewinnt. Danach steht er wieder am Start."""


class Move(StrEnum):
    """Was eine Taste in Wahrheit tut. Das weiß nur das Spiel, nicht der Agent."""

    LEFT = "links"
    RIGHT = "rechts"
    USE = "benutzen"


HiddenState = tuple[int, bool]
"""Position im Gang und ob der Agent den Schlüssel hat."""


@dataclass(frozen=True)
class Layout:
    """Der Bauplan eines Spiels: Länge des Gangs, Start, Schlüssel und Tür."""

    length: int = 4
    start: int = 1
    key: int = 0
    door: int = 3
    needs_key: bool = True
    """False: Die Tür geht auch ohne Schlüssel auf."""

    def __post_init__(self) -> None:
        if self.length < 2:
            raise ValueError(f"Der Gang braucht mindestens 2 Felder, hatte {self.length}.")
        for name, position in (("start", self.start), ("key", self.key), ("door", self.door)):
            if not 0 <= position < self.length:
                raise ValueError(
                    f"{name}={position} liegt außerhalb des Gangs (0 bis {self.length - 1})."
                )
        if self.key == self.door:
            raise ValueError("Schlüssel und Tür brauchen verschiedene Felder.")

    @property
    def hidden_states(self) -> list[HiddenState]:
        """Alle Zustände des Spiels."""
        return list(product(range(self.length), (False, True)))


STANDARD = Layout()
"""Schlüssel links vom Start, Tür am rechten Ende."""
MIRRORED = Layout(start=2, key=3, door=0)
"""Alles gespiegelt: Schlüssel rechts, Tür links."""
LONGER = Layout(length=5, door=4)
"""Ein Feld mehr im Gang."""
NO_KEY = Layout(needs_key=False)
"""Die Tür ist offen; der Schlüssel ist überflüssig."""

_COLORS = ("rot", "grün", "blau", "gelb", "lila", "weiß")
_SHAPES = ("kreis", "dreieck", "quadrat", "stern")
LOOKS = tuple(f"{color} {shape}" for color, shape in product(_COLORS, _SHAPES))
"""Mögliche Symbole für Zustände."""
BUTTONS = ("taste a", "taste b", "taste c", "taste x", "taste y", "taste z")
"""Mögliche Namen für Tasten."""


@dataclass(frozen=True)
class KeyDoorGame:
    """Ein Spiel der Familie: Bauplan plus Aussehen plus Tastenbelegung."""

    name: str
    layout: Layout
    looks: Mapping[HiddenState, str]
    controls: Mapping[str, Move]

    def __post_init__(self) -> None:
        if set(self.looks) != set(self.layout.hidden_states):
            raise ValueError(f"{self.name}: Jeder Zustand braucht genau ein Symbol.")
        symbols = list(self.looks.values())
        if len(set(symbols)) != len(symbols) or WIN in symbols:
            raise ValueError(f"{self.name}: Symbole müssen eindeutig sein und ≠ {WIN!r}.")
        if sorted(self.controls.values()) != sorted(Move):
            raise ValueError(f"{self.name}: Jede Bewegung braucht genau eine Taste.")

    @property
    def buttons(self) -> tuple[str, ...]:
        """Die Tasten, sortiert."""
        return tuple(sorted(self.controls))

    @property
    def start_symbol(self) -> str:
        """Was der Agent zu Beginn jeder Runde sieht."""
        return self.looks[(self.layout.start, False)]

    def step(self, symbol: str, button: str) -> str:
        """Führt einen Tastendruck aus und gibt das nächste Symbol zurück (oder `WIN`)."""
        if button not in self.controls:
            raise ValueError(f"{self.name}: Unbekannte Taste {button!r}.")
        position, has_key = self._hidden_state(symbol)
        last_field = self.layout.length - 1
        match self.controls[button]:
            case Move.LEFT:
                return self.looks[(max(0, position - 1), has_key)]
            case Move.RIGHT:
                return self.looks[(min(last_field, position + 1), has_key)]
            case Move.USE:
                return self._use(position, has_key)

    def _use(self, position: int, has_key: bool) -> str:
        """An der Tür (mit Schlüssel, falls nötig) gewinnt man; am Schlüssel nimmt man ihn."""
        layout = self.layout
        if position == layout.door and (has_key or not layout.needs_key):
            return WIN
        if position == layout.key:
            has_key = True
        return self.looks[(position, has_key)]

    def _hidden_state(self, symbol: str) -> HiddenState:
        for state, look in self.looks.items():
            if look == symbol:
                return state
        raise ValueError(f"{self.name}: Unbekanntes Symbol {symbol!r}.")


def make_game(name: str, layout: Layout, rng: random.Random) -> KeyDoorGame:
    """Ein Spiel mit zufälligem Aussehen und zufälliger Tastenbelegung."""
    states = layout.hidden_states
    looks = dict(zip(states, rng.sample(LOOKS, len(states)), strict=True))
    controls = dict(zip(rng.sample(BUTTONS, len(Move)), Move, strict=True))
    return KeyDoorGame(name, layout, looks, controls)
