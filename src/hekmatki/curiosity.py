"""Neugier mit Augenmaß: Lohnt sich ein Abstecher ins Unbekannte?

Kennt der Agent schon einen Weg zum Sieg, kostet jeder Abstecher Zeit. Er kann sich aber
lohnen, wenn eine nie probierte Taste eine Abkürzung sein könnte. Dann gewinnt der Agent
für den Rest des Spiels öfter. Der Wert eines Abstechers ist deshalb:

    Überraschungschance × zusätzliche Siege, falls Abkürzung − Siege, die der Umweg kostet

Das ist eine einfache Form des epistemischen Werts aus der aktiven Inferenz: Wissen ist
umso mehr wert, je länger man es noch nutzen kann. Kurz vor Schluss lohnt sich Neugier
kaum, am Anfang eines langen Spiels sehr.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Curiosity:
    """Wie viel der Agent einer nie probierten Taste zutraut."""

    surprise: float = 0.1
    """Chance, dass eine nie probierte Taste eine Abkürzung zum Sieg ist."""
    schema_surprise: float = 0.05
    """Dieselbe Chance, wenn das Schema für diese Taste etwas anderes vorhersagt."""

    def __post_init__(self) -> None:
        for name, value in (("surprise", self.surprise), ("schema_surprise", self.schema_surprise)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} muss zwischen 0 und 1 liegen, war {value}.")


@dataclass(frozen=True)
class Detour:
    """Ein möglicher Abstecher: zu einem Zustand gehen und dort eine unerprobte Taste drücken.

    Alle Angaben sind Tastendrücke auf bekannten Wegen.
    """

    steps_there: int
    """Vom aktuellen Zustand bis zum Ziel des Abstechers."""
    steps_from_start: int
    """Vom Start bis zum Ziel des Abstechers. Wäre die Taste dort eine Abkürzung, dauerte
    eine Runde künftig `steps_from_start + 1`."""
    steps_on_to_win: int
    """Vom Ziel des Abstechers weiter zum Sieg, falls die Taste nichts bewirkt."""
    steps_by_plan: int
    """Vom aktuellen Zustand direkt zum Sieg, ohne Abstecher."""
    round_trip: int
    """Bekannte Rundenlänge vom Start bis zum Sieg."""

    def __post_init__(self) -> None:
        if self.round_trip < 1:
            raise ValueError(f"Eine Runde dauert mindestens einen Schritt, war {self.round_trip}.")

    def value(self, surprise: float, steps_left: int) -> float:
        """Erwartete zusätzliche Siege minus erwartete verlorene Siege."""
        shortcut = self.steps_from_start + 1
        time_after = steps_left - self.steps_there - 1
        extra_wins = max(0.0, time_after * (1 / shortcut - 1 / self.round_trip))
        extra_steps = self.steps_there + 1 + self.steps_on_to_win - self.steps_by_plan
        lost_wins = extra_steps / self.round_trip
        return surprise * extra_wins - lost_wins
