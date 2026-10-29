"""Das Weltmodell aus Beobachtungen ableiten und umlernen, wenn eine Beobachtung widerspricht.

Pro Tastendruck sieht der Agent zwei Raster. Daraus liest er ab:
1. **Figur und Tasten**: Die Farbe, die sich als einzige um ein Feld bewegt, ist die Figur;
   ihre Verschiebung ist die Richtung der Taste.
2. **Versuch**: Welche Farbe die Figur betreten wollte und was geschah: betreten,
   geschoben, blockiert, zurück zum Start oder Sieg.
3. **Ereignisse**: Welche Farben verdeckt oder aufgedeckt wurden und welche Farben sich
   sonst noch geändert haben.

Die Regel einer Farbe ist die einfachste, die zu allen Versuchen mit ihr passt. Passt keine
mehr, gilt der neueste Versuch, und das ältere Wissen über diese Farbe wird verworfen
(umlernen statt abbrechen). Die Fernwirkungen eines Ereignisses sind die Farbwechsel, die bei
*jedem* Auftreten zu sehen waren (Schnittmenge). So fallen zufällige Begleitumstände heraus.
Geschehen zwei neue Ereignisse zugleich (die Figur verlässt die Druckplatte und betritt den
Boden), bekommen beide den Wechsel, aber als unsicher. Das klärt erst ein Schritt, in dem nur
eines von beiden ihn erklären kann.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from hekmatki.grid.effects import Change
from hekmatki.grid.model import Event, Rule, WorldModel
from hekmatki.grid.perception import cells_of, changed_cells, color_at, movements
from hekmatki.grid.world import Cell, Color, Direction, Grid, neighbor


class Outcome(StrEnum):
    """Was bei einem Versuch geschah, ein Feld zu betreten."""

    ENTERED = "betreten"
    PUSHED = "geschoben"
    BLOCKED = "blockiert"
    RESET = "zurück"
    WIN = "ziel"


_RULE_OF = {
    Outcome.ENTERED: Rule.PASS,
    Outcome.PUSHED: Rule.PUSH,
    Outcome.BLOCKED: Rule.BLOCK,
    Outcome.RESET: Rule.RESET,
    Outcome.WIN: Rule.WIN,
}


@dataclass(frozen=True)
class Attempt:
    """Die Figur wollte ein Feld der Farbe `color` betreten."""

    color: Color
    outcome: Outcome
    behind: Color | None = None
    """Die Farbe hinter diesem Feld (wichtig, wenn geschoben wurde oder es nicht ging)."""


@dataclass(frozen=True)
class Observation:
    """Ein Tastendruck: Raster davor, Taste, Raster danach, und ob das Spiel einen Sieg meldete."""

    before: Grid
    button: str
    after: Grid
    won: bool


def rule_of(attempts: Sequence[Attempt]) -> Rule | None:
    """Die einfachste Regel, die zu allen Versuchen passt. `None`: Keine passt (Widerspruch).

    Schiebbares darf auch mal blockieren (wenn hinter ihm kein Platz ist).
    """
    if not attempts:
        raise ValueError("Ohne Versuche gibt es keine Regel.")
    outcomes = {attempt.outcome for attempt in attempts}
    if outcomes == {Outcome.PUSHED, Outcome.BLOCKED}:
        return Rule.PUSH
    if len(outcomes) == 1:
        return _RULE_OF[outcomes.pop()]
    return None


class Induction:
    """Sammelt die Beobachtungen eines Levels und leitet daraus das Weltmodell ab."""

    def __init__(self, prior: WorldModel | None = None, restart: str | None = None) -> None:
        """`prior`: Figur und Tasten aus früheren Leveln, bis eine Beobachtung widerspricht.
        `restart`: die Neustart-Taste; sie ist keine Richtung."""
        self.restart = restart
        self.observations: list[Observation] = []
        self.player: Color | None = None if prior is None else prior.player
        self.controls: dict[str, Direction] = {} if prior is None else dict(prior.controls)
        self._control_notes: list[str] = []
        self._clear()

    def _clear(self) -> None:
        """Vergisst alles, was aus den Beobachtungen abgeleitet wurde (nicht Figur und Tasten)."""
        self._attempts: dict[Color, list[Attempt]] = {}
        self._leaves: dict[Color, Color] = {}
        self._consequences: dict[Event, frozenset[Change]] = {}
        self._unsure: dict[Event, frozenset[Change]] = {}
        self._entered: dict[Cell, Color] = {}
        """Für jedes Feld unter Figur oder Kiste: welche Farbe es beim Betreten hatte."""
        self._rule_notes: list[str] = []

    @property
    def model(self) -> WorldModel:
        """Das Weltmodell nach allen bisherigen Beobachtungen."""
        rules = {color: rule_of(history) for color, history in self._attempts.items()}
        return WorldModel(
            player=self.player,
            controls=dict(self.controls),
            rules={color: rule for color, rule in rules.items() if rule is not None},
            box_enters=self._box_enters(),
            leaves=dict(self._leaves),
            consequences=dict(self._consequences),
            unsure={event: changes for event, changes in self._unsure.items() if changes},
            blocked_with={
                color: frozenset(a.behind for a in history if a.behind is not None)
                for color, history in self._attempts.items()
                if rule_of(history) is Rule.BLOCK
            },
        )

    @property
    def revisions(self) -> list[str]:
        """Was der Agent umlernen musste, als kurze Sätze."""
        return self._control_notes + self._rule_notes

    def entered_as(self, cell: Cell) -> Color | None:
        """Welche Farbe das Feld unter Figur oder Kiste beim Betreten hatte. `None`: unbekannt."""
        return self._entered.get(cell)

    def add(self, observation: Observation) -> None:
        """Lernt aus einem Tastendruck. Ändern sich Figur oder Tasten, wird alles neu gedeutet."""
        self.observations.append(observation)
        if self._learn_controls(observation):
            self._clear()
            for earlier in self.observations:
                self._analyse(earlier)
        else:
            self._analyse(observation)

    def _learn_controls(self, observation: Observation) -> bool:
        """Figur und Tastenrichtung aus einer Bewegung. True, wenn sich daran etwas ändert.

        Bewegt sich allein eine andere Farbe als die vermutete Figur, ist sie die Figur: Das
        Vorwissen über die Figur war falsch (etwa aus einem Spiel mit anderen Farben).
        """
        if observation.won or observation.button == self.restart:
            return False
        moved = movements(observation.before, observation.after)
        found_player = len(moved) == 1 and moved[0].color != self.player
        if found_player:
            if self.player is not None:
                self._control_notes.append(f"Die Figur ist {moved[0].color}, nicht {self.player}")
            self.player = moved[0].color
        mine = [m for m in moved if m.color == self.player]
        if len(mine) != 1:
            return found_player
        origin, destination = mine[0].origin, mine[0].destination
        shift = (destination[0] - origin[0], destination[1] - origin[1])
        known = self.controls.get(observation.button)
        if abs(shift[0]) + abs(shift[1]) != 1 or known == shift:
            return found_player
        if known is not None:
            self._control_notes.append(f"{observation.button} bewegt anders als gedacht")
        self.controls[observation.button] = shift
        return True

    def _analyse(self, observation: Observation) -> None:
        """Liest Versuch und Ereignisse aus einem Tastendruck ab (Figur und Taste bekannt)."""
        before, after = observation.before, observation.after
        origin = self._player_cell(before)
        if observation.button == self.restart:
            destination = self._player_cell(after)
            if origin is None or destination is None:
                self._entered.clear()
            elif before != after:
                self._observe(observation, *self._returns(observation, origin, destination))
            return
        direction = self.controls.get(observation.button)
        if origin is None or direction is None:
            if before != after:
                self._entered.clear()
            return
        target = neighbor(origin, direction)
        color = color_at(before, target)
        if observation.won:
            self._attempt(Attempt(color, Outcome.WIN))
            self._entered.clear()
            return
        destination = self._player_cell(after)
        if destination == origin and after == before:
            self._attempt(Attempt(color, Outcome.BLOCKED, _behind(before, target, direction)))
        elif destination == target:
            self._entered_target(observation, origin, target, direction)
        elif destination is not None and destination != origin:
            self._attempt(Attempt(color, Outcome.RESET))
            self._observe(observation, *self._returns(observation, origin, destination))
        else:
            self._entered.clear()

    def _entered_target(
        self, observation: Observation, origin: Cell, target: Cell, direction: Direction
    ) -> None:
        """Die Figur steht jetzt auf `target`: betreten, oder dabei etwas weitergeschoben."""
        before, after = observation.before, observation.after
        color = color_at(before, target)
        behind = _behind(before, target, direction)
        further = neighbor(target, direction)
        pushed = behind not in (None, color) and color_at(after, further) == color
        if pushed:
            self._attempt(Attempt(color, Outcome.PUSHED, behind))
            self._observe(observation, {origin, target}, {target, further})
        else:
            self._attempt(Attempt(color, Outcome.ENTERED, behind))
            self._observe(observation, {origin}, {target})

    def _returns(
        self, observation: Observation, origin: Cell, destination: Cell
    ) -> tuple[set[Cell], set[Cell]]:
        """Felder, die Figur und Schiebbares beim Zurücksetzen verlassen und betreten haben."""
        left, entered = {origin}, {destination}
        for color, history in self._attempts.items():
            if rule_of(history) is Rule.PUSH:
                old = set(cells_of(observation.before, color))
                new = set(cells_of(observation.after, color))
                left |= old - new
                entered |= new - old
        return left, entered

    def _observe(self, observation: Observation, left: set[Cell], entered: set[Cell]) -> None:
        """Ereignisse, Hinterlassenes und Fernwirkungen eines Tastendrucks.

        `left`: Felder, die Figur oder Kisten verlassen haben; `entered`: die sie betreten haben.
        Ein Feld in beiden (die Figur rückt auf den Platz der Kiste) bleibt verdeckt.
        Was unter Figur oder Kisten die Farbe wechselt, ist unsichtbar. Dafür nimmt der Agent
        die Fernwirkungen an, die er schon kennt, und streicht keine, die er nicht sehen konnte.
        """
        before, after = observation.before, observation.after
        revealed, covered = sorted(left - entered), sorted(entered - left)
        hidden = {cell: self._entered.pop(cell, None) for cell in revealed}
        events = {Event(self._uncovered(hidden[cell], after, cell), False) for cell in revealed}
        events |= {Event(color_at(before, cell), covered=True) for cell in covered}
        moved = left | entered
        leftover = frozenset(
            (color_at(before, cell), color_at(after, cell))
            for cell in changed_cells(before, after)
            if cell not in moved
        )
        expected = {change for e in events for change in self._consequences.get(e, frozenset())}
        recolor = dict(sorted(expected)) | dict(leftover)
        for cell, under in hidden.items():
            shown = color_at(after, cell)
            if under is not None and (shown == under or shown not in recolor.values()):
                self._learn_leaves(under, shown)
        self._entered = {cell: recolor.get(c, c) for cell, c in self._entered.items()}
        for cell in covered:
            self._entered[cell] = color_at(before, cell)
        visible = {
            color
            for r, row in enumerate(before)
            for c, color in enumerate(row)
            if (r, c) not in moved
        }
        self._attribute(events, leftover, visible)

    def _attribute(
        self, events: set[Event], leftover: frozenset[Change], visible: set[Color]
    ) -> None:
        """Ordnet die Farbwechsel `leftover` eines Schritts seinen Ereignissen zu.

        Ein neues Ereignis bekommt die Wechsel, die kein anderes schon sicher erklärt. Ein
        bekanntes behält, was wieder geschah oder diesmal nicht zu sehen war. Erklären mehrere
        Ereignisse denselben Wechsel, bleibt unsicher, welches ihn auslöste.
        """
        claims: dict[Event, frozenset[Change]] = {}
        for event in events:
            known = self._consequences.get(event)
            if known is None:
                explained = {c for other in events - {event} for c in self._sure(other)}
                claims[event] = leftover - explained
            else:
                unseen = frozenset(change for change in known if change[0] not in visible)
                claims[event] = (known & leftover) | unseen
        for event, changes in claims.items():
            others = {c for other, theirs in claims.items() if other != event for c in theirs}
            seen = changes & leftover
            shared = seen & others
            if event in self._consequences:
                earlier = self._unsure.get(event, frozenset())
                self._unsure[event] = (earlier & changes) - (seen - shared)
            else:
                self._unsure[event] = shared
            self._consequences[event] = changes

    def _sure(self, event: Event) -> frozenset[Change]:
        """Die Fernwirkungen eines Ereignisses, die sicher ihm gehören."""
        changes = self._consequences.get(event, frozenset())
        return changes - self._unsure.get(event, frozenset())

    def _uncovered(self, under: Color | None, after: Grid, cell: Cell) -> Color:
        """Welche Farbe aufgedeckt wurde: was beim Betreten dort war (wie es hinterlassen
        wird), sonst was jetzt zu sehen ist."""
        if under is None:
            return color_at(after, cell)
        return self._leaves.get(under, under)

    def _attempt(self, attempt: Attempt) -> None:
        """Merkt sich einen Versuch. Bei Widerspruch zählt nur noch der neueste."""
        history = self._attempts.setdefault(attempt.color, [])
        old = rule_of(history) if history else None
        history.append(attempt)
        if rule_of(history) is None:
            self._attempts[attempt.color] = [attempt]
            new = rule_of([attempt])
            self._rule_notes.append(f"{attempt.color}: erst „{old}“, jetzt „{new}“")

    def _learn_leaves(self, under: Color, revealed: Color) -> None:
        known = self._leaves.get(under)
        if known is not None and known != revealed:
            self._rule_notes.append(f"{under} hinterließ erst {known}, jetzt {revealed}")
        self._leaves[under] = revealed

    def _box_enters(self) -> dict[Color, bool]:
        """Worauf sich Schiebbares schieben ließ (der neueste Versuch zählt)."""
        enters: dict[Color, bool] = {}
        for history in self._attempts.values():
            if rule_of(history) is Rule.PUSH:
                for attempt in history:
                    if attempt.behind is not None:
                        enters[attempt.behind] = attempt.outcome is Outcome.PUSHED
        return enters

    def _player_cell(self, grid: Grid) -> Cell | None:
        """Das Feld der Figur, wenn sie genau eines hat."""
        if self.player is None:
            return None
        cells = cells_of(grid, self.player)
        return cells[0] if len(cells) == 1 else None


def _behind(grid: Grid, cell: Cell, direction: Direction) -> Color | None:
    """Die Farbe hinter `cell` in Richtung `direction`. `None`: außerhalb des Rasters."""
    row, column = neighbor(cell, direction)
    if 0 <= row < len(grid) and 0 <= column < len(grid[0]):
        return grid[row][column]
    return None
