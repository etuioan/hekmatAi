"""Rollen-Schema: Farbwirkungen auf ein Spiel mit neuen Farben übertragen.

Nach einem Spiel benennt der Agent jede Farbe nach ihrer Wirkung, zum Beispiel „blockiert“
oder „auslöser“. Eine Farbe, die ein Auslöser umfärbt, heißt „verschlossen“; der Agent
nimmt an, dass sie bis dahin blockiert, auch wenn er nie dagegen gelaufen ist. Diese
Rollen merkt er sich zusammen damit, wie die Farbe aussah (ein Feld oder viele, am Rand
oder innen), und welche Rolle ein Auslöser in welche verwandelt.

In einem neuen Spiel kennt er die Farben nicht. Eine Deutung ordnet jeder Farbe eine Rolle
mit passendem Aussehen zu (oder keine). Was der Agent beobachtet, streicht Deutungen. Er
folgt einer Deutung, die möglichst viele Farben erklärt, bis sie widerlegt ist.
"""

import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import product

from hekmatki.grid.effects import Effect, Kind
from hekmatki.grid.knowledge import Knowledge
from hekmatki.grid.perception import Shape, shapes
from hekmatki.grid.world import Color, Grid

SELF = "ich"
LOCKED = "verschlossen"
ROLE_KINDS: dict[str, Kind] = {
    str(Kind.BLOCK): Kind.BLOCK,
    LOCKED: Kind.BLOCK,
    str(Kind.PASS): Kind.PASS,
    str(Kind.TRIGGER): Kind.TRIGGER,
    str(Kind.RESET): Kind.RESET,
    str(Kind.WIN): Kind.WIN,
}
"""Jede Rolle außer „ich“ und die Wirkung, nach der sie benannt ist."""
ALL_ROLES = frozenset({SELF, *ROLE_KINDS})
GUESSED = "vermutet: "
"""Kennzeichen für Farben, die der Agent noch nie gesehen hat, aber erwartet."""


def role_of(color: Color, knowledge: Knowledge) -> str | None:
    """Die Rolle einer Farbe nach dem, was der Agent gelernt hat. `None`: noch unklar."""
    if color == knowledge.player:
        return SELF
    effect = knowledge.effects.get(color)
    if _is_unlocked_by_trigger(color, knowledge) and (effect is None or effect.kind is Kind.BLOCK):
        return LOCKED
    return None if effect is None else str(effect.kind)


def possible_roles(color: Color, knowledge: Knowledge) -> frozenset[str]:
    """Alle Rollen, die nach dem Gelernten für diese Farbe noch in Frage kommen."""
    effect = knowledge.effects.get(color)
    if effect is not None and effect.kind is Kind.BLOCK and not knowledge.triggers:
        return frozenset({str(Kind.BLOCK), LOCKED})
    role = role_of(color, knowledge)
    if role is not None:
        return frozenset({role})
    return ALL_ROLES - {SELF} if knowledge.player is not None else ALL_ROLES


def _is_unlocked_by_trigger(color: Color, knowledge: Knowledge) -> bool:
    return any(old == color for trigger in knowledge.triggers for old, _ in trigger.changes)


@dataclass(frozen=True)
class RoleSchema:
    """Rollen mit ihrem Aussehen und welche Rolle ein Auslöser in welche verwandelt."""

    shapes: Mapping[str, frozenset[Shape]]
    opens: Mapping[str, str]

    def __post_init__(self) -> None:
        unknown = (set(self.shapes) | set(self.opens) | set(self.opens.values())) - ALL_ROLES
        if unknown:
            raise ValueError(f"Unbekannte Rollen im Schema: {sorted(unknown)}.")


def schema_from_knowledge(knowledge: Knowledge) -> RoleSchema:
    """Das Rollen-Schema eines gespielten Spiels."""
    found: dict[str, set[Shape]] = {}
    for color, shape in knowledge.shapes.items():
        role = role_of(color, knowledge)
        if role is not None:
            found.setdefault(role, set()).add(shape)
    opens: dict[str, str] = {}
    for trigger in knowledge.triggers:
        for old, new in trigger.changes:
            before, after = role_of(old, knowledge), role_of(new, knowledge)
            if before is not None and after is not None:
                opens[before] = after
    return RoleSchema({role: frozenset(s) for role, s in found.items()}, opens)


def revised(old: RoleSchema, new: RoleSchema) -> RoleSchema:
    """Verbindet zwei Rollen-Schemata: alle Rollen, jedes gesehene Aussehen."""
    roles = sorted(set(old.shapes) | set(new.shapes))
    merged = {r: old.shapes.get(r, frozenset()) | new.shapes.get(r, frozenset()) for r in roles}
    return RoleSchema(merged, {**old.opens, **new.opens})


Hypothesis = Mapping[Color, str]
"""Eine Deutung: Farbe → Rolle. Farben ohne Eintrag erklärt sie nicht."""


class RoleAdvisor:
    """Vorwissen aus einem Rollen-Schema für ein Spiel mit unbekannten Farben."""

    def __init__(self, schema: RoleSchema, first_grid: Grid) -> None:
        self.schema = schema
        seen = shapes(first_grid)
        options = {
            color: sorted(role for role, looks in schema.shapes.items() if shape in looks)
            for color, shape in seen.items()
        }
        self.hypotheses: list[Hypothesis] = list(_injective(options))
        self.followed: Hypothesis | None = None

    def pick(self, rng: random.Random) -> None:
        """Folgt weiter der bisherigen Deutung; ist sie widerlegt, wählt er eine neue.

        Neue Deutungen kommen aus denen, die die meisten Farben erklären.
        """
        if self.followed in self.hypotheses:
            return
        if not self.hypotheses:
            self.followed = None
            return
        most = max(len(h) for h in self.hypotheses)
        self.followed = rng.choice([h for h in self.hypotheses if len(h) == most])

    def effect(self, color: Color, knowledge: Knowledge) -> Effect | None:
        """Die Wirkung, die die verfolgte Deutung für diese Farbe erwartet."""
        if self.followed is None:
            return None
        role = self._role(color, knowledge, self.followed)
        if role is None or role == SELF:
            return None
        kind = ROLE_KINDS[role]
        if kind is not Kind.TRIGGER:
            return Effect(kind)
        changes = frozenset(self._expected_changes(self.followed))
        return Effect(Kind.TRIGGER, changes) if changes else Effect(Kind.PASS)

    def learn(self, knowledge: Knowledge) -> None:
        """Streicht Deutungen, die dem Gelernten widersprechen."""
        self.hypotheses = [h for h in self.hypotheses if _consistent(h, knowledge)]

    def fits(self) -> bool:
        """True, solange noch eine Deutung möglich ist."""
        return bool(self.hypotheses)

    def guesses(self, knowledge: Knowledge) -> dict[Color, str]:
        """Die Rollen, die die verfolgte Deutung den noch unklaren Farben gibt."""
        if self.followed is None:
            return {}
        return {
            color: role
            for color, role in self.followed.items()
            if color not in knowledge.effects and color != knowledge.player
        }

    def _role(self, color: Color, knowledge: Knowledge, hypothesis: Hypothesis) -> str | None:
        """Rolle laut Deutung; neu aufgetauchte Farben erben sie vom Auslöser."""
        if color.startswith(GUESSED):
            return color.removeprefix(GUESSED)
        if color in hypothesis:
            return hypothesis[color]
        for trigger in knowledge.triggers:
            for old, new in trigger.changes:
                source = hypothesis.get(old) or role_of(old, knowledge)
                if new == color and source is not None and source in self.schema.opens:
                    return self.schema.opens[source]
        return None

    def _expected_changes(self, hypothesis: Hypothesis) -> Iterable[tuple[Color, Color]]:
        """Welche Farben ein Auslöser laut Deutung umfärbt (unbekannte Ziele: vermutet)."""
        by_role = {role: color for color, role in hypothesis.items()}
        for source, target in self.schema.opens.items():
            if source in by_role:
                yield by_role[source], by_role.get(target, GUESSED + target)


def _injective(options: Mapping[Color, list[str]]) -> Iterable[Hypothesis]:
    """Alle Deutungen, die jede Rolle höchstens einer Farbe geben."""
    colors = sorted(options)
    for roles in product(*([*options[c], None] for c in colors)):
        assigned = [r for r in roles if r is not None]
        if len(assigned) == len(set(assigned)):
            yield {c: r for c, r in zip(colors, roles, strict=True) if r is not None}


def _consistent(hypothesis: Hypothesis, knowledge: Knowledge) -> bool:
    """Jede Rolle passt zum Gelernten, und keine Rolle geht an eine zweite Farbe."""
    if not all(role in possible_roles(c, knowledge) for c, role in hypothesis.items()):
        return False
    candidates = {color: possible_roles(color, knowledge) for color in knowledge.shapes}
    settled = {color: roles for color, roles in candidates.items() if len(roles) == 1}
    return all(
        hypothesis.get(other) not in roles
        for color, roles in settled.items()
        for other in hypothesis
        if other != color
    )
