"""Das Weltmodell: Regeln, die der Agent aus seinen Beobachtungen ableitet.

Es beschreibt in Farben, was passiert, wenn die Figur einen Schritt versucht:
- **Regel** jeder Farbe: blockiert, frei, schiebbar, zurück (zum Start) oder Ziel
- **Kisten**: auf welche Farben sich etwas Schiebbares schieben lässt
- **Hinterlassen**: welche Farbe bleibt, wenn die Figur ein Feld wieder verlässt
  (ein Schlüssel ist danach weg, eine Druckplatte bleibt)
- **Fernwirkungen**: Wird eine Farbe verdeckt oder aufgedeckt, wechseln anderswo Farben
  (verdeckte Druckplatte: das Tor wird offen; aufgedeckte: es schließt sich wieder).
  Geschahen zwei Ereignisse zugleich, ist unsicher, welches den Wechsel auslöste.

Ein Modell ist unveränderlich. Wer lernt, baut ein neues. Vorwissen aus früheren Leveln ist
ebenfalls ein Modell; `over` legt das eigene Wissen darüber.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum

from hekmatki.grid.effects import Change
from hekmatki.grid.world import Color, Direction


class Rule(StrEnum):
    """Was passiert, wenn die Figur ein Feld dieser Farbe betreten will."""

    BLOCK = "blockiert"
    PASS = "frei"
    PUSH = "schiebbar"
    RESET = "zurück"
    WIN = "ziel"


@dataclass(frozen=True, order=True)
class Event:
    """Eine Farbe wird verdeckt (von Figur oder Kiste) oder wieder aufgedeckt."""

    color: Color
    covered: bool

    def __str__(self) -> str:
        return f"{self.color} {'verdeckt' if self.covered else 'aufgedeckt'}"


@dataclass(frozen=True)
class WorldModel:
    """Was der Agent über die Regeln eines Spiels glaubt."""

    player: Color | None = None
    controls: Mapping[str, Direction] = field(default_factory=dict)
    rules: Mapping[Color, Rule] = field(default_factory=dict)
    box_enters: Mapping[Color, bool] = field(default_factory=dict)
    """Ob sich Schiebbares auf diese Farbe schieben lässt."""
    leaves: Mapping[Color, Color] = field(default_factory=dict)
    """Welche Farbe zum Vorschein kommt, wenn die Figur ein Feld dieser Farbe verlässt."""
    consequences: Mapping[Event, frozenset[Change]] = field(default_factory=dict)
    """Welche Farben überall wechseln, wenn das Ereignis eintritt."""
    unsure: Mapping[Event, frozenset[Change]] = field(default_factory=dict)
    """Der Teil der Fernwirkungen, der bisher nur zusammen mit anderen Ereignissen auftrat."""
    blocked_with: Mapping[Color, frozenset[Color]] = field(default_factory=dict)
    """Für blockierende Farben: welche Farben dahinter lagen, als sie blockierten."""

    def over(self, prior: "WorldModel") -> "WorldModel":
        """Dieses Wissen, wo vorhanden; sonst das Vorwissen `prior`."""
        return WorldModel(
            player=self.player if self.player is not None else prior.player,
            controls={**prior.controls, **self.controls},
            rules={**prior.rules, **self.rules},
            box_enters={**prior.box_enters, **self.box_enters},
            leaves={**prior.leaves, **self.leaves},
            consequences={**prior.consequences, **self.consequences},
            unsure={
                **{e: c for e, c in prior.unsure.items() if e not in self.consequences},
                **self.unsure,
            },
            blocked_with={**prior.blocked_with, **self.blocked_with},
        )

    def renamed(self, names: Mapping[Color, Color]) -> "WorldModel":
        """Dasselbe Wissen mit anderen Namen für die Farben, ohne Tasten.

        Was eine Farbe ohne neuen Namen betrifft, fällt weg. So wird aus einem Modell über
        Farben eines über Rollen und umgekehrt (`role_model.py`).
        """

        def changes(found: frozenset[Change]) -> frozenset[Change]:
            return frozenset(
                (names[old], names[new]) for old, new in found if old in names and new in names
            )

        def events(found: Mapping[Event, frozenset[Change]]) -> dict[Event, frozenset[Change]]:
            return {
                Event(names[event.color], event.covered): changes(effects)
                for event, effects in found.items()
                if event.color in names
            }

        return WorldModel(
            player=None if self.player is None else names.get(self.player),
            rules={names[c]: rule for c, rule in self.rules.items() if c in names},
            box_enters={names[c]: ok for c, ok in self.box_enters.items() if c in names},
            leaves={
                names[c]: names[rest]
                for c, rest in self.leaves.items()
                if c in names and rest in names
            },
            consequences=events(self.consequences),
            unsure={e: c for e, c in events(self.unsure).items() if c},
            blocked_with={
                names[c]: frozenset(names[b] for b in behind if b in names)
                for c, behind in self.blocked_with.items()
                if c in names
            },
        )

    def without(self, colors: Iterable[Color]) -> "WorldModel":
        """Dasselbe Modell, aber ohne Regeln für diese Farben."""
        dropped = set(colors)
        rules = {color: rule for color, rule in self.rules.items() if color not in dropped}
        return replace(self, rules=rules)

    def describe(self, color: Color) -> str | None:
        """Was das Modell über eine Farbe sagt, als kurzer Text. `None`: nichts."""
        if color == self.player:
            return "ich"
        rule = self.rules.get(color)
        if rule is None:
            return None
        parts = [str(rule)]
        if self.leaves.get(color, color) != color:
            parts.append(f"wird zu {self.leaves[color]}")
        for covered in (True, False):
            event = Event(color, covered)
            changes = self.consequences.get(event, frozenset())
            unsure = self.unsure.get(event, frozenset())
            if changes:
                text = ", ".join(
                    f"{old}→{new}{'?' if (old, new) in unsure else ''}"
                    for old, new in sorted(changes)
                )
                parts.append(f"{'verdeckt' if covered else 'aufgedeckt'}: {text}")
        return "; ".join(parts)
