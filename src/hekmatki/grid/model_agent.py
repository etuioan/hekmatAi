"""Der Modell-Agent: leitet ein Weltmodell aus Beobachtungen ab und plant darin.

Pro Schritt entscheidet er in dieser Reihenfolge:
1. Kennt er die Richtung einer Taste nicht und hat sie hier noch nicht gedrückt, probiert er
   sie aus.
2. Hat er einen Plan und kam bisher alles wie erwartet, geht er ihn weiter.
3. Sonst sucht er im Modell (samt Vorwissen) den kürzesten Weg zum Sieg, und wenn es keinen
   gibt, den kürzesten Weg zu einer offenen Frage, die er dann ausprobiert (Neugier).
4. Findet er nichts, zweifelt er Schritt für Schritt mehr (jede Stufe behält die vorigen):
   a. am Vorwissen: Farben, die laut Vorwissen blockieren oder zurückschicken, gelten als
      unbekannt, bis er sie in diesem Level selbst gesehen hat. Vorwissen kann falsch sein.
      Was nur aus Rollen anderer Spiele stammt, ist eine Deutung; daran zweifelt er ganz.
   b. an Wänden: Blockiert eine Farbe auch, wenn etwas anderes dahinter liegt? (Eine Kiste
      vor der Wand sieht aus wie eine Wand.)
   c. an seinem Weg: Er erlaubt sich Fallen und die Neustart-Taste (falls es eine gibt) als
      Neustart, etwa wenn eine Kiste festsitzt.
   d. nur mit Teilprüfung (ab 0.15): am ganzen Vorwissen. Er sucht nur noch mit dem, was er
      in diesem Level selbst gesehen hat; alles andere wird wieder zur offenen Frage.
5. Sonst drückt er eine zufällige Taste.

Kommt etwas anders als erwartet, verwirft er den Plan und plant mit dem neuen Modell neu.

Vorwissen gibt es in zwei Formen: ein Weltmodell aus früheren Leveln desselben Spiels
(gleiche Farben) und, ab 0.14, ein Rollen-Weltmodell aus anderen Spielen (`role_model.py`).
Das Rollen-Wissen setzt er über eine Bindung Farbe → Rolle ein; Wissen über die Farben
selbst geht vor. Ab 0.15 gibt es zwei Gegenmittel gegen falsches Vorwissen:
- Prüfung (`trust.py`, H17): Vorwissen erst nutzen, wenn es sich bewährt hat, und gar nicht
  mehr, sobald es einmal widerlegt ist.
- Teilprüfung (Stufe 4d, H16/H17): Jeder Teil des Vorwissens bleibt eine Vermutung, bis er
  selbst beobachtet ist; steckt der Agent fest, testet er die ungeprüften Teile.
"""

import random
from collections.abc import Iterator, Sequence
from enum import StrEnum

from hekmatki.grid.induction import Induction, Observation
from hekmatki.grid.model import Rule, WorldModel
from hekmatki.grid.perception import cells_of
from hekmatki.grid.role_model import RoleBinder, RoleWorld
from hekmatki.grid.search import SEARCH_LIMIT, Goal, Plan, search
from hekmatki.grid.simulation import Simulator, read_layout, read_scene
from hekmatki.grid.trust import Trust, verdict
from hekmatki.grid.world import Color, Grid


class Intent(StrEnum):
    """Warum der Agent eine Taste gewählt hat."""

    TRY = "probiert eine Taste aus"
    PLAN = "geht seinen Plan zum Ziel"
    RESTART = "nutzt eine Falle als Neustart"
    RESTART_BUTTON = "drückt die Neustart-Taste"
    EXPLORE = "testet"
    WANDER = "drückt eine zufällige Taste"


class ModelAgent:
    """Ein Agent, der sich die Regeln des Spiels selbst erschließt und vorausdenkt."""

    def __init__(
        self,
        buttons: Sequence[str],
        prior: WorldModel | None = None,
        limit: int = SEARCH_LIMIT,
        roles: RoleWorld | None = None,
        restart: str | None = None,
        checked: bool = False,
        doubts_parts: bool = False,
    ) -> None:
        """`prior`: Modell aus früheren Leveln desselben Spiels; `roles`: aus anderen Spielen;
        `restart`: die Neustart-Taste des Spiels, falls es eine hat; `checked`: Vorwissen
        erst nutzen, wenn es sich bewährt hat (`trust.py`); `doubts_parts`: Teilprüfung,
        bei Stillstand am ganzen ungeprüften Vorwissen zweifeln (Stufe 4d)."""
        if not buttons:
            raise ValueError("Der Agent braucht mindestens eine Taste.")
        if restart is not None and restart in buttons:
            raise ValueError("Die Neustart-Taste gehört nicht zu den Richtungstasten.")
        self.buttons = tuple(sorted(buttons))
        self.restart = restart
        self.checked = checked
        self.doubts_parts = doubts_parts
        self.trust = Trust.WAITING if checked else Trust.TRUSTED
        """Wie weit er dem Vorwissen traut. Ohne Prüfung traut er ihm von Anfang an."""
        self.roles = roles
        self.limit = limit
        self._same_game = prior
        self._binder: RoleBinder | None = None
        self.induction = Induction(prior, restart)
        self.surprises = 0
        """Wie oft etwas anders kam, als sein Modell vorhergesagt hatte."""
        self._reason = str(Intent.TRY)
        self._tried: set[tuple[Grid, str]] = set()
        self._first: Grid | None = None
        self._plan: Plan | None = None
        self._done = 0
        """Wie viele Tasten des Plans schon gedrückt sind."""
        self._view = WorldModel()
        """Das Modell, mit dem der Plan gefunden wurde."""
        self._version = WorldModel()
        """Das ganze Modell (mit Vorwissen) zur Zeit der Planung."""
        self._stuck: WorldModel | None = None
        """Unter diesem Modell fand keine vollständige Suche etwas."""

    @property
    def reason(self) -> str:
        """Warum der Agent zuletzt seine Taste gewählt hat."""
        return self._reason

    @property
    def prior(self) -> WorldModel | None:
        """Das Vorwissen, das er gerade nutzt: alles Angebotene, sobald er ihm traut."""
        return self._offered if self.trust is Trust.TRUSTED else None

    @property
    def _offered(self) -> WorldModel | None:
        """Das ganze Vorwissen: aus demselben Spiel, ergänzt um die Rollen anderer Spiele."""
        if self._binder is None:
            return self._same_game
        own = self.induction.model
        known = own if self._same_game is None else own.over(self._same_game)
        guessed = self._binder.prior(known)
        return guessed if self._same_game is None else self._same_game.over(guessed)

    def knowledge(self) -> WorldModel:
        """Was er über die Farben dieses Spiels weiß: eigenes Wissen und Vorwissen aus
        demselben Spiel, ohne Deutungen aus Rollen. Das gibt er an das nächste Level weiter."""
        own = self.induction.model
        return own if self._same_game is None else own.over(self._same_game)

    def world_model(self) -> WorldModel:
        """Eigenes Wissen aus diesem Level, ergänzt um das Vorwissen."""
        own = self.induction.model
        prior = self.prior
        return own if prior is None else own.over(prior)

    def choose(self, grid: Grid, rng: random.Random, steps_left: int) -> str:
        """Wählt die nächste Taste. `steps_left` braucht dieser Agent nicht."""
        if self._first is None:
            self._first = grid
            if self.roles is not None:
                self._binder = RoleBinder(self.roles, grid)
        model = self.world_model()
        untried = [
            b for b in self.buttons if b not in model.controls and (grid, b) not in self._tried
        ]
        if untried:
            return self._decide(Intent.TRY, rng.choice(untried))
        if model.player is None or not _single(model.player, grid, self._first):
            return self._decide(Intent.WANDER, rng.choice(self.buttons))
        button = self._follow(grid, model) or self._new_plan(grid, model)
        return button or self._decide(Intent.WANDER, rng.choice(self.buttons))

    def learn(self, before: Grid, button: str, after: Grid, won: bool) -> None:
        """Lernt aus einem Tastendruck."""
        if button not in self.buttons and button != self.restart:
            raise ValueError(f"Unbekannte Taste {button!r}.")
        if button not in self.world_model().controls:
            self._tried.add((before, button))
        self.induction.add(Observation(before, button, after, won))
        self._check_prior()
        if self._plan is not None:
            self._done += 1

    def beliefs(self) -> dict[Color, str]:
        """Was der Agent über jede Farbe weiß oder vermutet, als kurzer Text."""
        own = self.induction.model
        prior = self.prior or WorldModel()
        found = {}
        for color in sorted({*own.rules, *prior.rules, *_players(own, prior)}):
            known, guessed = own.describe(color), prior.describe(color)
            role = None if self._binder is None else self._binder.role_of(color)
            if known is None and guessed is not None:
                found[color] = f"vermutlich {guessed}"
                if role is not None and color not in (self._same_game or WorldModel()).rules:
                    found[color] += f" (Rolle „{role}“)"
            elif known is not None:
                old = prior.rules.get(color)
                contradicted = old is not None and color in own.rules and old != own.rules[color]
                found[color] = f"{known} (Vorwissen: {old})" if contradicted else known
        return found

    def _check_prior(self) -> None:
        """Prüft das Vorwissen gegen die eigenen Beobachtungen. Widerlegt bleibt widerlegt."""
        offered = self._offered
        if not self.checked or self.trust is Trust.REFUTED or offered is None:
            return
        self.trust = verdict(offered, self.induction.model)

    def _decide(self, intent: Intent, button: str, question: str | None = None) -> str:
        if intent in (Intent.TRY, Intent.WANDER):
            self._plan = None
        self._reason = str(intent) if question is None else f"{intent}: {question}"
        return button

    def _follow(self, grid: Grid, model: WorldModel) -> str | None:
        """Die nächste Taste des Plans, wenn er noch gilt. Sonst wird er verworfen."""
        plan = self._plan
        if plan is None:
            return None
        if self._done > 0:
            expected = plan.expected[self._done - 1]
            seen = read_scene(grid, self._view, self.induction.entered_as)
            if expected is not None and seen != expected:
                self.surprises += 1
                self._plan = None
                return None
        if self._done >= len(plan.buttons) or model != self._version:
            self._plan = None
            return None
        return plan.buttons[self._done]

    def _new_plan(self, grid: Grid, model: WorldModel) -> str | None:
        """Sucht einen neuen Plan, eine Stufe nach der anderen (siehe `_stages`)."""
        if model == self._stuck or self._first is None:
            return None
        complete = True
        for view, doubt, allow_reset in self._stages(model):
            scene = read_scene(grid, view, self.induction.entered_as)
            simulator = Simulator(view, read_layout(self._first, view), doubt, self.restart)
            known = [button for button in self.buttons if button in view.controls]
            if self.restart is not None:
                known.append(self.restart)
            result = search(simulator, scene, known, allow_reset, self.limit)
            complete = complete and result.complete
            if result.plan is not None:
                return self._adopt(result.plan, view, model)
        if complete:
            self._stuck = model
        return None

    def _stages(self, model: WorldModel) -> Iterator[tuple[WorldModel, bool, bool]]:
        """Die Suchen nacheinander: mit welchem Wissen, ob mit Zweifel, ob mit Neustart."""
        yield model, False, False
        prior = self.prior
        if prior is not None:
            own = self.induction.model
            same_game = self._same_game or WorldModel()
            hindering = [
                color
                for color, rule in prior.rules.items()
                if color not in own.rules
                and (rule in (Rule.BLOCK, Rule.RESET) or color not in same_game.rules)
            ]
            model = own.over(prior.without(hindering))
            yield model, False, False
        yield model, True, False
        yield model, True, True
        if self.doubts_parts and prior is not None:
            own = self.induction.model
            yield own, True, False
            yield own, True, True

    def _adopt(self, plan: Plan, view: WorldModel, model: WorldModel) -> str:
        self._plan, self._done, self._view, self._version = plan, 0, view, model
        if plan.goal is Goal.LEARN:
            return self._decide(Intent.EXPLORE, plan.buttons[0], plan.question)
        button = plan.buttons[0]
        if button == self.restart:
            return self._decide(Intent.RESTART_BUTTON, button)
        return self._decide(Intent.RESTART if plan.restarts else Intent.PLAN, button)


def _single(color: Color, *grids: Grid) -> bool:
    """Hat die Farbe in jedem Raster genau ein Feld (wie eine Figur)?"""
    return all(len(cells_of(grid, color)) == 1 for grid in grids)


def _players(*models: WorldModel) -> set[Color]:
    return {model.player for model in models if model.player is not None}
