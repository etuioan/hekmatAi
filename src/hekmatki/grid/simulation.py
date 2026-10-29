"""Im Weltmodell vorausdenken: Was würde ein Tastendruck bewirken?

Eine **Szene** ist das Raster, wie der Agent es versteht: die Figur, das Schiebbare (Kisten)
und der Hintergrund, also die Farben der Felder darunter. Der Hintergrund ist eine
Zeichenkette mit einer Ziffer pro Feld (Platz der Farbe in der ARC-Palette), damit Szenen
schnell zu vergleichen sind.

Der Simulator wendet die Regeln des Modells an. Wo das Modell nichts weiß (eine Farbe ohne
Regel, ein Ereignis, das nie beobachtet wurde), sagt er nichts voraus, sondern nennt die
offene Frage. Genau dort lohnt sich Neugier. Ebenso, wenn ein Schritt eine unsichere
Fernwirkung eindeutig prüfen würde. Im Zweifel-Modus fragt er außerdem, ob eine
blockierende Farbe auch dann blockiert, wenn etwas anderes dahinter liegt als bisher: Eine
Kiste vor einer Wand sieht aus wie eine Wand.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace

from hekmatki.grid.model import Rule, WorldModel
from hekmatki.grid.perception import cells_of
from hekmatki.grid.world import PALETTE, Cell, Color, Grid

Objects = tuple[tuple[int, str], ...]
"""Schiebbares: (Feldnummer, Farbziffer), sortiert."""


def code(color: Color) -> str:
    """Die Ziffer einer Farbe."""
    if color not in PALETTE:
        raise ValueError(f"Die Farbe {color!r} gehört nicht zur Palette.")
    return str(PALETTE.index(color))


def name(digit: str) -> Color:
    """Die Farbe zu einer Ziffer."""
    return PALETTE[int(digit)]


@dataclass(frozen=True)
class Scene:
    """Figur, Schiebbares und Hintergrund. Feldnummer = Zeile × Breite + Spalte."""

    background: str
    player: int
    objects: Objects = ()


@dataclass(frozen=True)
class Layout:
    """Was in einem Level fest ist: Größe und wo Figur und Schiebbares beginnen."""

    height: int
    width: int
    start: int
    homes: Objects = ()


@dataclass(frozen=True)
class Prediction:
    """Was ein Tastendruck laut Modell bewirkt."""

    scene: Scene | None
    """Die Szene danach. `None` nach einem Sieg oder wenn das Modell es nicht weiß."""
    won: bool = False
    reset: bool = False
    """Die Figur landet wieder am Start."""
    question: str | None = None
    """Was das Modell nicht weiß, als Frage."""
    disturbs: bool = False
    """Der Druck verschiebt Kisten (oder würde es, falls die Frage mit Ja beantwortet wird)."""
    cornered: bool = False
    """Eine verschobene Kiste säße danach in einer Ecke fest (oder würde es)."""


def read_scene(grid: Grid, model: WorldModel, entered_as: Callable[[Cell], Color | None]) -> Scene:
    """Die Szene zu einem Raster. Unter Figur und Kisten liegt, was beim Betreten dort war.

    Ist das unbekannt (etwa am Start), vermutet der Agent die häufigste freie Farbe.
    """
    if model.player is None:
        raise ValueError("Ohne bekannte Figur gibt es keine Szene.")
    width = len(grid[0])
    pushable = {color for color, rule in model.rules.items() if rule is Rule.PUSH}
    floor = _floor_guess(grid, model)
    background = []
    for r, row in enumerate(grid):
        for c, color in enumerate(row):
            if color == model.player or color in pushable:
                under = entered_as((r, c))
                color = floor if under is None else model.leaves.get(under, under)
            background.append(code(color))
    player = cells_of(grid, model.player)
    if len(player) != 1:
        raise ValueError(f"Die Figur ({model.player}) muss genau ein Feld haben.")
    objects = sorted(
        (r * width + c, code(color))
        for r, row in enumerate(grid)
        for c, color in enumerate(row)
        if color in pushable
    )
    return Scene("".join(background), player[0][0] * width + player[0][1], tuple(objects))


def read_layout(first: Grid, model: WorldModel) -> Layout:
    """Die festen Größen eines Levels aus seinem ersten Raster."""
    scene = read_scene(first, model, lambda cell: None)
    return Layout(len(first), len(first[0]), scene.player, scene.objects)


class Simulator:
    """Sagt mit einem Weltmodell voraus, was Tastendrücke bewirken."""

    def __init__(
        self, model: WorldModel, layout: Layout, doubt: bool = False, restart: str | None = None
    ) -> None:
        """`restart`: die Neustart-Taste, falls das Spiel eine hat."""
        self.layout = layout
        self.doubt = doubt
        self.restart = restart
        self._moves = dict(model.controls)
        self._rules = {code(color): rule for color, rule in model.rules.items()}
        self._enters = {code(color): ok for color, ok in model.box_enters.items()}
        self._leaves = {code(color): code(rest) for color, rest in model.leaves.items()}
        self._effects = {
            (code(event.color), event.covered): {ord(code(old)): code(new) for old, new in changes}
            for event, changes in model.consequences.items()
        }
        self._unsure = {
            (code(event.color), event.covered): sorted(
                (code(old), code(new)) for old, new in changes
            )
            for event, changes in model.unsure.items()
        }
        self._blocked_with = {
            code(color): {code(behind) for behind in behinds}
            for color, behinds in model.blocked_with.items()
        }

    def predict(self, scene: Scene, button: str) -> Prediction:
        """Was der Tastendruck `button` in der Szene `scene` bewirkt. Blockiert: dieselbe Szene."""
        if button == self.restart:
            return self._moved(scene, self.layout.start, self.layout.homes, reset=True)
        move = self._moves.get(button)
        if move is None:
            return Prediction(None, question=f"Wohin führt {button}?")
        target = self._next(scene.player, move)
        if target is None:
            return Prediction(scene)
        objects = dict(scene.objects)
        if target in objects:
            return self._push(scene, objects, target, move)
        digit = scene.background[target]
        match self._rules.get(digit):
            case None:
                return Prediction(None, question=f"Was passiert auf {name(digit)}?")
            case Rule.PASS:
                return self._moved(scene, target, scene.objects)
            case Rule.WIN:
                return Prediction(None, won=True)
            case Rule.RESET:
                return self._moved(scene, self.layout.start, self.layout.homes, reset=True)
            case _:
                return self._blocked(scene, objects, target, move)

    def _blocked(
        self, scene: Scene, objects: dict[int, str], target: int, move: tuple[int, int]
    ) -> Prediction:
        """Die Farbe auf `target` blockiert. Im Zweifel: auch mit dem, was dahinter liegt?"""
        further = self._next(target, move)
        if not self.doubt or further is None or further in objects:
            return Prediction(scene)
        digit, behind = scene.background[target], scene.background[further]
        if behind in self._blocked_with.get(digit, set()):
            return Prediction(scene)
        question = f"Blockiert {name(digit)} auch mit {name(behind)} dahinter?"
        cornered = self._cornered(scene, further, target)
        return Prediction(None, question=question, disturbs=True, cornered=cornered)

    def _push(
        self, scene: Scene, objects: dict[int, str], target: int, move: tuple[int, int]
    ) -> Prediction:
        """Die Figur läuft gegen Schiebbares auf `target`."""
        further = self._next(target, move)
        if further is None or further in objects:
            return Prediction(scene)
        digit = scene.background[further]
        enters = self._box_enters(digit)
        cornered = self._cornered(scene, further, target)
        if enters is None:
            box = name(objects[target])
            question = f"Lässt sich {box} auf {name(digit)} schieben?"
            return Prediction(None, question=question, disturbs=True, cornered=cornered)
        if not enters:
            return Prediction(scene)
        objects[further] = objects.pop(target)
        following = self._moved(scene, target, tuple(sorted(objects.items())))
        return replace(following, cornered=cornered)

    def _moved(
        self, scene: Scene, player: int, objects: Objects, reset: bool = False
    ) -> Prediction:
        """Figur und Schiebbares stehen neu: Was wird verdeckt, aufgedeckt, und was folgt?"""
        old = {scene.player, *(cell for cell, _ in scene.objects)}
        new = {player, *(cell for cell, _ in objects)}
        background = scene.background
        events = [(background[cell], False) for cell in old - new]
        events += [(background[cell], True) for cell in new - old]
        disturbs = objects != scene.objects
        recolor: dict[int, str] = {}
        for event in events:
            effect = self._effects.get(event)
            if effect is None:
                question = f"Was folgt, wenn {_event_text(event)} wird?"
                return Prediction(None, reset=reset, question=question, disturbs=disturbs)
            recolor.update(effect)
        doubt = self._unsure_question(events, background, new)
        if doubt is not None:
            return Prediction(None, reset=reset, question=doubt, disturbs=disturbs)
        covered = [(cell, background[cell]) for cell in new - old]
        if any(self._leaves.get(digit, digit) != digit for _, digit in covered):
            cells = list(background)
            for cell, digit in covered:
                cells[cell] = self._leaves.get(digit, digit)
            background = "".join(cells)
        if recolor:
            background = background.translate(recolor)
        following = Scene(background, player, objects)
        return Prediction(following, reset=reset, disturbs=disturbs)

    def _unsure_question(
        self, events: list[tuple[str, bool]], background: str, occupied: set[int]
    ) -> str | None:
        """Eine unsichere Fernwirkung, die dieser Schritt klären würde, als Frage.

        Klären heißt: Die alte Farbe ist zu sehen (nicht unter Figur oder Kiste), und kein
        anderes Ereignis dieses Schritts sagt denselben Wechsel voraus.
        """
        doubts = [(event, change) for event in events for change in self._unsure.get(event, [])]
        if not doubts:
            return None
        shown = {digit for cell, digit in enumerate(background) if cell not in occupied}
        for event, (old, new) in doubts:
            claimed = any(
                self._effects[other].get(ord(old)) == new for other in events if other != event
            )
            if old in shown and not claimed:
                return f"Wechselt {name(old)} zu {name(new)}, wenn {_event_text(event)} wird?"
        return None

    def _cornered(self, scene: Scene, cell: int, origin: int) -> bool:
        """Säße eine Kiste, von `origin` nach `cell` geschoben, in einer Ecke fest?

        Fest heißt: oben oder unten blockiert es, und links oder rechts auch. Von dort lässt
        sie sich in keine Richtung mehr schieben.
        """

        def solid(move: tuple[int, int]) -> bool:
            near = self._next(cell, move)
            if near is None:
                return True
            return near != origin and self._rules.get(scene.background[near]) is Rule.BLOCK

        vertical = solid((-1, 0)) or solid((1, 0))
        return vertical and (solid((0, -1)) or solid((0, 1)))

    def _box_enters(self, digit: str) -> bool | None:
        """Lässt sich Schiebbares auf diese Farbe schieben? `None`: Das weiß niemand.

        Ungeprüft gilt die einfachste Annahme: dorthin, wo auch die Figur frei gehen kann.
        """
        known = self._enters.get(digit)
        rule = self._rules.get(digit)
        if known is not None or rule is None:
            return known
        return rule is Rule.PASS

    def _next(self, cell: int, move: tuple[int, int]) -> int | None:
        """Das Nachbarfeld in Richtung `move`. `None`: außerhalb."""
        row, column = divmod(cell, self.layout.width)
        row, column = row + move[0], column + move[1]
        if 0 <= row < self.layout.height and 0 <= column < self.layout.width:
            return row * self.layout.width + column
        return None


def _event_text(event: tuple[str, bool]) -> str:
    digit, covered = event
    return f"{name(digit)} {'verdeckt' if covered else 'aufgedeckt'}"


def _floor_guess(grid: Grid, model: WorldModel) -> Color:
    """Die freie Farbe mit den meisten Feldern; ohne Wissen die häufigste Farbe im Inneren."""
    counts = Counter(color for row in grid[1:-1] for color in row[1:-1])
    free = [color for color in counts if model.rules.get(color) is Rule.PASS]
    candidates = free or [color for color in counts if color != model.player]
    return max(candidates, key=lambda color: (counts[color], color))
