"""Vorwissen erst trauen, wenn es sich bewährt hat (H17, ab 0.15).

Vorwissen aus einem anderen Spiel ist eine Behauptung über dieses Spiel. Die Prüfung
vergleicht, was es über Farben behauptet, mit dem, was der Agent selbst beobachtet hat:
- **bestätigt**: Regel oder Fernwirkung einer Farbe stimmt mit der eigenen Beobachtung überein
- **widerlegt**: sie widerspricht ihr

Erst nach `CONFIRMATIONS_NEEDED` Bestätigungen gilt das Vorwissen. Ein einziger Widerspruch
nimmt es ganz aus dem Spiel; aufbewahrt bleibt es trotzdem, es wird nur nicht mehr benutzt.
Das ist die Lehre aus der ARC-Prize-Auswertung 2026 (falsche Analogien), dem Kepler-Agenten
(Vorhersagen prüfen) und Gershman 2017 (nicht das alte Wissen überschreiben).

Figur und Tasten zählen nicht: Die Regel-Ableitung übernimmt sie aus dem Vorwissen und
korrigiert sie selbst, eine „Bestätigung“ wäre dort nur ein Echo.
"""

from enum import StrEnum
from typing import Final

from hekmatki.grid.model import Rule, WorldModel

CONFIRMATIONS_NEEDED: Final = 2
"""Von Hand gewählt (ohne Grundlage): zwei Bestätigungen, etwa Boden und Wand."""


class Trust(StrEnum):
    """Wie weit der Agent seinem Vorwissen traut."""

    WAITING = "wartet auf Bestätigung"
    TRUSTED = "bestätigt"
    REFUTED = "widerlegt"


def check(prior: WorldModel, own: WorldModel) -> tuple[int, int]:
    """Zählt (bestätigt, widerlegt) für alles, was Vorwissen und Beobachtung beide sagen."""
    confirmed = refuted = 0
    for color in prior.rules.keys() & own.rules.keys():
        claimed_rule, seen_rule = prior.rules[color], own.rules[color]
        if claimed_rule is seen_rule:
            confirmed += 1
        elif not (seen_rule is Rule.BLOCK and claimed_rule is Rule.PUSH):
            refuted += 1  # Eine Kiste vor der Wand blockiert auch: kein Widerspruch.
    for event in prior.consequences.keys() & own.consequences.keys():
        claimed, seen = prior.consequences[event], own.consequences[event]
        sure = seen - own.unsure.get(event, frozenset())
        if seen == claimed:
            confirmed += 1
        elif not sure <= claimed or (not seen and claimed):
            refuted += 1
    return confirmed, refuted


def verdict(prior: WorldModel, own: WorldModel) -> Trust:
    """Gilt das Vorwissen schon, noch nicht oder nicht mehr?"""
    confirmed, refuted = check(prior, own)
    if refuted:
        return Trust.REFUTED
    return Trust.TRUSTED if confirmed >= CONFIRMATIONS_NEEDED else Trust.WAITING
