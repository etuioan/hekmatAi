"""Rollen-Weltmodell: das Weltmodell eines Spiels ohne seine Farben (ab 0.14).

Das Weltmodell (`model.py`) spricht über Farben: „braun ist schiebbar, gelb verdeckt öffnet
pink“. In einem neuen Spiel haben alle Dinge neue Farben, und dieses Wissen hilft nicht mehr.
Das Rollen-Weltmodell setzt deshalb für jede Farbe ihre **Rolle** ein: „schiebbar“,
„auslöser“, „verschlossen“ … Die Regeln hängen dann an Rollen, nicht an Farben. Das ist die
Trennung von Struktur und Inhalt aus dem Tolman-Eichenbaum-Modell, angewandt auf Spielregeln
wie in Schema Networks (Kansky 2017) und OPINE-World (Courtis 2026).

Zu jeder Rolle merkt sich der Agent, wie ihre Farbe im ersten Bild eines Levels aussah (ein
Feld oder viele, am Rand oder innen). In einem neuen Spiel ordnet eine **Bindung** jeder
Farbe eine Rolle mit passendem Aussehen zu. Der Agent übernimmt nur, worin alle besten
Bindungen übereinstimmen. Wo sie sich widersprechen, bleibt die Farbe offen, und der Agent
probiert sie aus: Neugier genau dort, wo das Vorwissen mehrdeutig ist. Jede Beobachtung
streicht Bindungen, die ihr widersprechen (die Lehre aus Ergebnis 12). Rollen, deren Farbe
noch nie zu sehen war (das offene Tor), bekommen eine noch unbenutzte Farbe als Platzhalter,
bis eine Fernwirkung die echte zeigt.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from hekmatki.grid.effects import Change
from hekmatki.grid.model import Event, Rule, WorldModel
from hekmatki.grid.perception import Shape, shapes
from hekmatki.grid.world import PALETTE, Color, Grid

Role = str
Binding = Mapping[Color, Role]
"""Farbe → Rolle. Farben ohne Eintrag erklärt die Bindung nicht."""

SELF: Final = "ich"
TRIGGER: Final = "auslöser"
LOCKED: Final = "verschlossen"
OPENED: Final = "geöffnet"


def role_names(model: WorldModel) -> dict[Color, Role]:
    """Benennt jede Farbe, über die das Modell etwas weiß, nach ihrer Rolle.

    Die Figur ist „ich“. Eine Farbe, deren Verdecken anderswo Farben wechseln lässt, ist ein
    „auslöser“. Was beim Verdecken wechselt (oder beim Aufdecken zurück), ist vorher
    „verschlossen“ und danach „geöffnet“, solange die Regeln nicht dagegen sprechen. Sonst
    heißt die Farbe wie ihre Regel. Teilen sich zwei Farben einen Namen, bekommt die zweite
    eine Nummer („frei 2“).
    """
    triggers = {event.color for event, changes in model.consequences.items() if changes}
    opens = _openings(model)
    locked = {old for old, _ in opens}
    opened = {new for _, new in opens}
    colors = sorted({*model.rules, *triggers, *locked, *opened} - {model.player})
    names: dict[Color, Role] = {} if model.player is None else {model.player: SELF}
    for color in colors:
        rule = model.rules.get(color)
        if color in triggers and rule in (Rule.PASS, None):
            role: Role | None = TRIGGER
        elif color in locked and rule in (Rule.BLOCK, None):
            role = LOCKED
        elif color in opened and rule in (Rule.PASS, None):
            role = OPENED
        else:
            role = None if rule is None else str(rule)
        if role is not None:
            names[color] = _unique(role, set(names.values()))
    return names


def _openings(model: WorldModel, sure: bool = False) -> set[Change]:
    """Welche Farbe beim Verdecken zu welcher wird: (verschlossen, geöffnet).

    Beim Aufdecken geht der Wechsel in die Gegenrichtung. `sure`: nur sichere Wechsel.
    """
    found: set[Change] = set()
    for event, changes in model.consequences.items():
        unsure = model.unsure.get(event, frozenset()) if sure else frozenset()
        found |= {pair if event.covered else pair[::-1] for pair in changes - unsure}
    return found


def _unique(role: Role, taken: set[Role]) -> Role:
    if role not in taken:
        return role
    number = 2
    while f"{role} {number}" in taken:
        number += 1
    return f"{role} {number}"


@dataclass(frozen=True)
class RoleWorld:
    """Regeln über Rollen und wie jede Rolle in einem ersten Bild aussah."""

    model: WorldModel
    looks: Mapping[Role, frozenset[Shape]]

    @classmethod
    def from_level(cls, model: WorldModel, first: Grid) -> "RoleWorld":
        """Das Rollen-Weltmodell eines gespielten Levels aus seinem Modell und ersten Bild."""
        names = role_names(model)
        seen = shapes(first)
        looks = {role: frozenset({seen[color]}) for color, role in names.items() if color in seen}
        return cls(model.renamed(names), looks)

    @property
    def roles(self) -> frozenset[Role]:
        """Alle Rollen, über die dieses Modell etwas weiß."""
        return frozenset(role_names(self.model).values()) | frozenset(self.looks)

    def merged(self, newer: "RoleWorld") -> "RoleWorld":
        """Verbindet zwei Rollen-Weltmodelle: neueres Wissen zuerst, jedes gesehene Aussehen."""
        roles = sorted(set(self.looks) | set(newer.looks))
        looks = {r: self.looks.get(r, frozenset()) | newer.looks.get(r, frozenset()) for r in roles}
        return RoleWorld(newer.model.over(self.model), looks)


def fits(color: Color, role: Role, world: WorldModel, evidence: WorldModel) -> bool:
    """Passt die Rolle zu dem, was über die Farbe bekannt ist (`evidence`)?

    Die Figur ist genau die Rolle „ich“. Hat die Farbe schon eine Regel, muss die Rolle
    dieselbe haben, falls sie eine hat. Eine Farbe, die bisher nur blockierte, darf auch
    schiebbar sein: Eine Kiste vor der Wand sieht aus wie eine Wand. Eine Farbe ist genau
    dann ein Auslöser, wenn ihr Verdecken oder Aufdecken sicher anderswo Farben wechseln
    ließ, soweit beide Seiten das schon wissen. Und eine Farbe, die dabei sicher wechselte
    oder entstand, braucht eine Rolle, die das auch tut (verschlossen, geöffnet).
    """
    if evidence.player is not None and (color == evidence.player) != (role == SELF):
        return False
    for covered in (True, False):
        seen = evidence.consequences.get(Event(color, covered))
        expected = world.consequences.get(Event(role, covered))
        if seen is None:
            continue
        sure = seen - evidence.unsure.get(Event(color, covered), frozenset())
        if (sure and not expected) or (not seen and expected):
            return False
    for side in (0, 1):
        changed = {pair[side] for pair in _openings(evidence, sure=True)}
        if color in changed and role not in {pair[side] for pair in _openings(world)}:
            return False
    known, expected_rule = evidence.rules.get(color), world.rules.get(role)
    if known is None or expected_rule is None or known is expected_rule:
        return True
    return known is Rule.BLOCK and expected_rule is Rule.PUSH


class RoleBinder:
    """Vorwissen aus einem Rollen-Weltmodell für ein Spiel mit unbekannten Farben."""

    def __init__(self, world: RoleWorld, first: Grid) -> None:
        self.world = world
        looks = shapes(first)
        self._options = {
            color: sorted(r for r, seen in world.looks.items() if looks[color] in seen)
            for color in sorted(looks)
        }
        self._free = [color for color in PALETTE if color not in looks]
        """Farben, die im ersten Bild fehlen: Platzhalter für Rollen ohne sichtbare Farbe."""
        self.binding: dict[Color, Role] = {}
        self._evidence: WorldModel | None = None
        self._prior = WorldModel()

    def prior(self, evidence: WorldModel) -> WorldModel:
        """Das Vorwissen über Farben laut verfolgter Bindung, passend zu `evidence`."""
        if evidence == self._evidence:
            return self._prior
        candidates = {
            color: [r for r in roles if fits(color, r, self.world.model, evidence)]
            for color, roles in self._options.items()
        }
        self.binding = dict(self._shared(candidates, _observed(evidence)))
        complete = self._complete(self.binding, evidence)
        names = {role: color for color, role in complete.items()}
        self._evidence, self._prior = evidence, self.world.model.renamed(names)
        return self._prior

    def role_of(self, color: Color) -> Role | None:
        """Die Rolle, die die verfolgte Bindung dieser Farbe gibt."""
        return self.binding.get(color)

    def _shared(self, candidates: Mapping[Color, list[Role]], observed: set[Color]) -> Binding:
        """Was alle besten Deutungen gemeinsam sagen.

        Die besten Deutungen geben möglichst vielen Farben eine Rolle (jede Rolle höchstens
        einmal), zuerst denen, über die Beobachtungen schon etwas sagen (`observed`). Solche
        mit einem Ziel gehen vor, denn ein Level ohne Ziel gibt es nicht. Wo sie sich
        widersprechen, bleibt die Farbe offen: Dort probiert der Agent aus.
        """
        goals = {role for role, rule in self.world.model.rules.items() if rule is Rule.WIN}
        found = _best(candidates, observed)
        with_goal = [b for b in found if goals & set(b.values())]
        options = with_goal or found
        if not options:
            return {}
        first, rest = options[0], options[1:]
        return {c: r for c, r in first.items() if all(other.get(c) == r for other in rest)}

    def _complete(self, binding: Mapping[Color, Role], evidence: WorldModel) -> dict[Color, Role]:
        """Ergänzt Rollen, deren Farbe im ersten Bild fehlte.

        Hat der Agent schon gesehen, wozu ein Ereignis eine Farbe wechselt, gilt die neue
        Farbe als die erwartete Rolle. Sonst steht eine unbenutzte Farbe als Platzhalter da.
        """
        complete = dict(binding)
        colors = {role: color for color, role in binding.items()}
        for event, changes in self.world.model.consequences.items():
            trigger = colors.get(event.color)
            for old, new in sorted(changes):
                if new in complete.values() or old not in colors:
                    continue
                seen = (
                    frozenset()
                    if trigger is None
                    else evidence.consequences.get(Event(trigger, event.covered), frozenset())
                )
                shown = [after for before, after in seen if before == colors[old]]
                free = [c for c in self._free if c not in complete and c not in evidence.rules]
                color = shown[0] if shown else (free[0] if free else None)
                if color is not None and color not in complete:
                    complete[color] = new
                    colors[new] = color
        return complete


def _observed(evidence: WorldModel) -> set[Color]:
    """Farben, über die Beobachtungen schon etwas sagen."""
    player = set() if evidence.player is None else {evidence.player}
    events = {event.color for event, changes in evidence.consequences.items() if changes}
    changed = {color for pair in _openings(evidence, sure=True) for color in pair}
    return player | set(evidence.rules) | events | changed


def _best(candidates: Mapping[Color, list[Role]], observed: set[Color]) -> list[Binding]:
    """Alle besten Bindungen (Rollen verschieden).

    Am besten ist, wer die meisten Farben aus `observed` erklärt und dann die meisten Farben
    überhaupt. Die Suche lässt Zweige aus, die das nicht mehr erreichen können.
    """
    colors = sorted(candidates, key=lambda c: (c not in observed, len(candidates[c]), c))
    best: list[Binding] = []
    top = (-1, -1)

    def score(current: Binding) -> tuple[int, int]:
        return len(observed & set(current)), len(current)

    def extend(index: int, current: dict[Color, Role]) -> None:
        nonlocal best, top
        rest = colors[index:]
        bound = score(current)
        if (bound[0] + len(observed & set(rest)), bound[1] + len(rest)) < top:
            return
        if not rest:
            if bound > top:
                best, top = [], bound
            best.append(dict(current))
            return
        color = rest[0]
        for role in candidates[color]:
            if role not in current.values():
                current[color] = role
                extend(index + 1, current)
                del current[color]
        extend(index + 1, current)

    extend(0, {})
    return best
