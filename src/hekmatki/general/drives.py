"""Eigene Ziele: was der Agent will, wenn ihm niemand ein Ziel zeigt (ab 0.18, H25 und H27).

Bisher hatte der Agent nur ein Ziel: das, woran die Welt „erreicht“ meldet. Weiß er dafür
keinen Weg, drückte er bloß die Taste, die er am seltensten probiert hatte. Jetzt setzt er
sich selbst Ziele, alle über Größen, ohne zu wissen, was sie bedeuten:

- **Bedürfnisse:** Eine Größe, die von selbst sinkt, egal welche Taste er drückt, und die er
  heben kann, hält er oben (homöostatisches Lernen, Keramati & Gutkin 2014). Sinkt sie auf
  die Hälfte ihres höchsten Werts, will er sie heben; ist nichts anderes zu tun, schon unter
  90 % („Pflege“).
- **Rekorde:** Eine Größe, die er schon über ihren Anfangswert hinaus steigen ließ, will er
  höher bringen als je zuvor an diesem Ort („Zahl steigt“). Er wählt das Ziel, das er am seltensten
  erreicht oder aufgegeben hat: Neugier als Zählen (Strehl & Littman 2008, Bellemare 2016),
  Ziele selbst wählen wie bei den intrinsisch motivierten Zielprozessen (Forestier, Portelas,
  Mollard, Oudeyer 2022).
- **Versuche:** Eine Taste, die noch nie etwas Eigenes bewirkt hat, probiert er, sobald etwas
  Seltenes zu sehen ist, das er mit ihr noch nie gesehen hat. Eine Taste, die schon etwas
  bewirkt hat, probiert er, wenn dort, woran sie wirkt (die Größen in den Bedingungen ihrer
  Ursachen), ein Wert steht, den er mit ihr noch nie sah. Kinder testen gezielt, wenn ihre
  Erwartung verletzt ist (Stahl & Feigenson 2015); hier ist es das Unbekannte.
- **Erinnern:** Weiß er für ein Ziel hier keinen Weg, geht er dorthin zurück, wo die Größe
  an diesem Ort zuletzt stieg, auf der Karte seiner Form (die Achsen aus `form`, der Weg aus
  `planner.plan_space`). Ein Ort, an dem etwas gelang, ist eine Erinnerung mit Koordinaten
  (Ortszellen und episodisches Gedächtnis: O'Keefe & Nadel 1978, Tulving 1983).
- **Erkunden:** Bleibt nichts, geht er auf der Karte seiner Form dorthin, wo er an diesem
  Ort am seltensten war, und probiert ab und zu die Taste, die er an diesem Punkt am
  seltensten gedrückt hat (Go-Explore, Ecoffet 2021, als Zählen ohne Archiv).

Sank eine Menge wie Gesundheit oft nach einer bestimmten Lage, ist die Lage gefährlich. Dann
nimmt er die Taste, nach der in solchen Lagen bisher am wenigsten verloren ging (`_defend`).

Ein Ziel verfolgt er, bis er es erreicht oder `PATIENCE` Schritte lang nicht; dann gibt er
es auf und zählt das (ein aufgegebenes Ziel wird seltener gewählt). Der Weg zum Ziel kommt
aus `subgoals`.

Bedürfnisse und Rekorde gibt es nur für Mengen (siehe `owned`): Größen, die sich wie beim
Zählen um 1 ändern und keine Regel „übernimmt Gx“ oder „wird v“ haben. Größen mit solchen
Regeln wandern mit dem Blick oder werden von einer Taste gesetzt (eine Blickrichtung); sie
sind Wahrnehmung, kein Besitz. Das liest der Agent aus seinen Regeln und Schritten ab, nicht
aus der Welt (H26). Schalter (Größen mit zwei Werten) sind weder Bedürfnis noch Rekord.
Rekorde gibt es außerdem erst, wenn er die Form seiner Welt kennt, und nur für Größen, die
nach einer Taste stiegen, die nicht zum Gehen dient: Was sich beim Gehen ändert, ist Ort oder
Blick; Besitz ändert sich beim Handeln.
"""

import random
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final
from weakref import WeakKeyDictionary

from hekmatki.general.causes import Change, Event, Groups, Kind, Literal, Partial
from hekmatki.general.cues import Cues
from hekmatki.general.env import Observation, Transition
from hekmatki.general.form import STEPPED, Axis, Form
from hekmatki.general.knowledge import Knowledge
from hekmatki.general.planner import plan_space
from hekmatki.general.programs import Becomes, Copy, leaves
from hekmatki.general.space import Layout, Point
from hekmatki.general.subgoals import Model, achieve, imagine, model

PATIENCE: Final = 60
"""So viele Schritte verfolgt der Agent ein Ziel, bevor er es aufgibt (ohne Grundlage)."""
DECAY_PRESSES: Final = 40
DECAY_SHARE: Final = 0.75
"""Eine Größe sinkt von selbst, wenn sie nach so einem Anteil der Tasten, die schon
`DECAY_PRESSES`-mal gedrückt wurden, mindestens einmal gesunken ist (ohne Grundlage)."""
RARE: Final = 30
"""So selten muss etwas zu sehen gewesen sein, damit es einen Versuch lohnt (ohne Grundlage)."""
OWN_EFFECT: Final = 3.0
"""Eine Taste bewirkt ein Ereignis selbst, wenn es nach ihr so viel öfter passiert als im
Mittel (von Hand gewählt, ohne Grundlage)."""
REVIEW: Final = 50
"""So oft (in Schritten) prüft der Agent, welche Tasten schon etwas Eigenes bewirken."""
GOALS_PER_STEP: Final = 4
"""So viele neue Ziele probiert er je Schritt, ob er einen Weg weiß (Rechenzeit)."""
COUNTING: Final = 0.8
"""Eine Menge ändert sich in mindestens diesem Anteil der Fälle um genau 1 (ohne Grundlage)."""
HARM_WINDOW: Final = 8
"""So lange bleibt er bei einer Antwort auf eine Gefahr, und so viele Schritte zählt danach
der Schaden. Manches wirkt erst nach mehreren Schritten (ein Gegner fällt erst nach mehreren
Schlägen); ab 0.20, vorher 5 Schritte ohne Dabeibleiben (ohne Grundlage)."""
HURT: Final = 0.5
"""Sinkt eine Größe nach so einem Anteil der oft gedrückten Tasten, achtet er darauf, wann
(ohne Grundlage)."""
SHRINK: Final = 3
"""So viele gedachte Fälle zieht das gemeinsame Mittel beim Schaden (ohne Grundlage)."""
SMALL: Final = 2
"""Größen wie Gesundheit ändern sich meist um höchstens so viel (ohne Grundlage)."""
LINGER: Final = 1
"""Ist die Gefahr nach `HARM_WINDOW` Schritten noch da, zählt das wie so viel Schaden: Gut
ist, was die Gefahr beendet (Mowrer 1947); von Hand gewählt, ohne Grundlage."""
RISK: Final = 0.5
"""Eine Taste meidet er, wo danach mindestens so oft Gesundheit sank (ohne Grundlage)."""
URGENT: Final = 0.5
"""Ein Bedürfnis ist dringend, wenn es auf diesen Anteil gesunken ist (ohne Grundlage)."""
TOP_UP: Final = 0.9
"""Ist nichts anderes zu tun, hebt er Bedürfnisse schon unter diesem Anteil (ohne Grundlage)."""
DANGER: Final = 0.15
"""Eine Lage ist gefährlich, wenn danach Gesundheit mit Sicherheit öfter als so oft sank
(ab 0.21 mit Unsicherheit, `cues`; ohne Grundlage)."""
STRETCH: Final = (4, 12)
"""Beim Erkunden geht er so viele Schritte geradeaus (von Hand gewählt, ohne Grundlage)."""
STUCK: Final = 3
"""Drückt er so oft hintereinander in derselben Lage dieselbe Taste, ohne dass sich etwas
ändert, versucht er eine andere (von Hand gewählt, ohne Grundlage)."""
CURIOUS: Final = 0.15
"""Beim Erkunden drückt er so oft die Taste, die er an diesem Punkt am seltensten probiert hat,
statt weiterzugehen (von Hand gewählt, ohne Grundlage)."""
TRIES: Final = 5
"""So oft probiert er eine Taste mit Wirkung an einem Wert aus, bevor er aufgibt: Manches
wirkt erst nach mehreren Schlägen (von Hand gewählt, ohne Grundlage)."""
RETRY: Final = 10
"""Weiß er für ein Ziel keinen Weg, fragt er erst nach so vielen Schritten wieder."""


@dataclass
class Guard:
    """Eine Antwort auf eine Gefahr, bei der er bleibt, bis die Gefahr vorbei ist oder
    `HARM_WINDOW` Schritte um sind: eine Option mit Abbruchbedingung (Sutton, Precup & Singh
    1999), abgerechnet als Ganzes (H32)."""

    danger: tuple[Literal, ...]
    answer: str
    until: int


@dataclass
class Pursuit:
    """Ein Ziel, das der Agent gerade verfolgt."""

    goal: Literal
    since: int
    reason: str


class Drives:
    """Bedürfnisse, Rekorde, Versuche und Erkunden: woher die eigenen Ziele kommen."""

    def __init__(self, actions: int) -> None:
        self.actions = actions
        self.steps = 0
        self.first: dict[int, int] = {}
        """Der erste Wert jeder Größe, den der Agent gesehen hat."""
        self.highest: dict[int, int] = {}
        """Der höchste Wert jeder Größe, den er je sah."""
        self.highest_here: dict[int, int] = {}
        """Der höchste Wert an diesem Ort: Rekorde zählen je Ort, wie in jedem neuen Spiel."""
        self.reached: Counter[int] = Counter()
        """Wie oft jede Größe einen neuen Höchstwert erreicht hat."""
        self.given_up: Counter[int] = Counter()
        self.pursuit: Pursuit | None = None
        self.reason = ""
        """Warum er die letzte Taste gewählt hat (zum Nachvollziehen)."""
        self.log: list[tuple[int, str, Literal]] = []
        """(Schritt, Grund, Ziel) jedes neu gewählten Ziels, zum Nachvollziehen."""
        self._falls: Counter[tuple[int, int]] = Counter()
        self._all_changes: Counter[int] = Counter()
        self._unit_changes: Counter[int] = Counter()
        self._small_changes: Counter[int] = Counter()
        """Wie oft sich jede Größe änderte, und wie oft davon um genau 1."""
        self._seen: Counter[tuple[int, int]] = Counter()
        self._visits: Counter[Partial] = Counter()
        """Wie oft er an jedem Punkt seiner Karte war, an diesem Ort (für das Erkunden)."""
        self._at: Counter[tuple[Partial, int]] = Counter()
        """Wie oft er an jedem Punkt jede Taste gedrückt hat, an diesem Ort."""
        self._with: Counter[tuple[int, int, int, tuple[int, ...]]] = Counter()
        """(Taste, Größe, Wert, was er besitzt) → wie oft er die Taste dort probiert hat."""
        self._kit: frozenset[int] = frozenset()
        """Mengen, die er besitzt und die keine Bedürfnisse sind (Holz, eine Spitzhacke): Mit
        etwas Neuem in der Hand wirkt eine Taste vielleicht anders (ab 0.20, H33)."""
        self._pressed: Counter[int] = Counter()
        self._rises: Counter[tuple[int, int]] = Counter()
        """(Taste, Größe) → wie oft die Größe nach der Taste stieg."""
        self._all_rises: Counter[int] = Counter()
        self._unknown: set[int] = set(range(actions))
        self._retry: dict[int, int] = {}
        self._retry_goal: dict[Literal, int] = {}
        self._operands: dict[int, set[int]] = {}
        self._operands_due = 0
        """Taste → die Größen, an denen sie wirkt (aus ihren Ursachen, ab und zu neu gelernt)."""
        self._forms: WeakKeyDictionary[Knowledge, Form] = WeakKeyDictionary()
        """Die stetige Form je Karte: Wechselt der Agent die Karte, gilt deren Form."""
        self._last: Observation | None = None
        self._heading: tuple[int, int] = (-1, 0)
        """Erkunden: in welche Richtung er geht und wie viele Schritte noch."""
        self._last_point: Partial = ()
        self._repeats = 0
        self._last_choice: tuple[Observation, int] | None = None
        self._harm: Counter[tuple[tuple[Literal, ...], str]] = Counter()
        """(Lage, Antwort) → Schaden danach, samt `LINGER` für eine Gefahr, die blieb."""
        self._tried_in: Counter[tuple[tuple[Literal, ...], str]] = Counter()
        self._harm_any: Counter[str] = Counter()
        self._tried_any: Counter[str] = Counter()
        self._pending: deque[tuple[int, tuple[Literal, ...], str, int]] = deque()
        """Abwehr, deren Folgen noch nicht abgerechnet sind: Schritt, Lage, Antwort, Gesundheit.
        Die Antwort ist eine Taste oder, ab 0.19, eine Richtung zur Gefahr („hin“, „weg“)."""
        self._guard: Guard | None = None
        """Die Antwort, bei der er gerade bleibt (ab 0.20)."""
        self._hurt_cache: list[int] = []
        self._cues = Cues()
        self._groups: Groups = ()
        """Die Gruppen „nah bei mir“ beim letzten Wählen; mit ihnen zählt er Hinweisreize."""
        self._where: dict[int, Observation] = {}
        """Größe → die Beobachtung, nach der sie an diesem Ort zuletzt stieg."""

    @property
    def unknown(self) -> set[int]:
        """Tasten, die noch nie selbst etwas steigen ließen."""
        return set(self._unknown)

    def new_place(self) -> None:
        """Ein neuer Ort: Was hier selten war, zählt neu; das Ziel von eben gilt nicht mehr."""
        if self._last is not None:
            self._settle(self._last, everything=True)  # Die Runde ist vorbei: jetzt abrechnen.
        self.highest_here.clear()
        self._visits.clear()
        self._at.clear()
        self._heading = (-1, 0)
        self._where.clear()
        self.pursuit = None
        self._guard = None

    def observe(self, transition: Transition) -> None:
        """Lernt aus einem Schritt: Rekorde, was von selbst sinkt, was er schon gesehen hat."""
        self.steps += 1
        before, after, action = transition.before, transition.after, transition.action
        self._pressed[action] += 1
        for component, (old, new) in enumerate(zip(before, after, strict=True)):
            self.first.setdefault(component, old)
            self._seen[component, old] += 1
            self._with[action, component, old, self._carried(before)] += 1
            if new != old:
                self._all_changes[component] += 1
                self._unit_changes[component] += abs(new - old) == 1
                self._small_changes[component] += abs(new - old) <= SMALL
            if new < old:
                self._falls[component, action] += 1
            elif new > old:
                self._rises[action, component] += 1
                self._all_rises[component] += 1
                self._where[component] = before
            highest = max(self.highest.get(component, old), old)
            if new > highest:
                self.reached[component] += 1
            self.highest[component] = max(highest, new)
            self.highest_here[component] = max(self.highest_here.get(component, old), old, new)
        if self.pursuit is not None and self.pursuit.goal.holds(after):
            self.pursuit = None
        self._cues.observe(before, after, self._groups)
        self._last = after
        self._settle(after)
        if self.steps % REVIEW == 0:
            self._review()

    def _settle(self, observation: Observation, everything: bool = False) -> None:
        """Rechnet ab, wie viel nach einer Abwehr in `HARM_WINDOW` Schritten verloren ging, und
        ob die Gefahr dann noch da ist (ab 0.19)."""
        while self._pending and (everything or self._pending[0][0] <= self.steps - HARM_WINDOW):
            _, danger, answer, health = self._pending.popleft()
            now = sum(observation[c] for c in self._hurt_cache)
            lingers = all(literal.holds(observation) for literal in danger)
            cost = max(0, health - now) + LINGER * int(lingers)
            self._harm[danger, answer] += cost
            self._tried_in[danger, answer] += 1
            self._harm_any[answer] += cost
            self._tried_any[answer] += 1

    def choose(
        self, knowledge: Knowledge, form: Form, observation: Observation, rng: random.Random
    ) -> int | None:
        """Die nächste Taste für ein eigenes Ziel, oder zum Erkunden (None: gar kein Modell)."""
        world = model(knowledge, self.actions)
        if not world:
            return None
        form = self.steady(knowledge, form)
        body = self.body(knowledge, form)
        own = self.owned(knowledge, form)
        if self.steps >= self._operands_due:
            self._operands = {a: knowledge.causes.operands(a, own) for a in range(self.actions)}
            self._operands_due = self.steps + REVIEW
        plan = _Plan(knowledge, world, form, self._where)
        self._groups = knowledge.space.layout.groups()
        choices: tuple[tuple[str, Callable[[], int | None]], ...]
        needs = set(self.needs(knowledge, own))
        self._kit = frozenset(own - needs)
        harmed = self._hurt(knowledge, body, needs)
        risky = self.risky(knowledge, observation, harmed)
        defence = self._defend(knowledge, world, observation, body, harmed, risky, rng)
        if defence is not None:
            self.reason = "Abwehr"
            return defence
        choices = (
            ("Bedürfnis", lambda: self._need(plan, observation, own)),
            ("Ziel", lambda: self._continue(plan, observation, own)),
            ("Versuch", lambda: self._trial(knowledge, observation, body, own, rng)),
            ("Neugier", lambda: self._curious(plan, observation, body)),
            ("Rekord", lambda: self._record(plan, observation, own)),
            ("Pflege", lambda: self._need(plan, observation, own, TOP_UP)),
            ("Erkunden", lambda: self._explore(form, world, observation, rng)),
        )
        point = _point(form.of_kind(*STEPPED), observation)
        self._visits[point] += 1
        for reason, choice in choices:
            step = choice()
            if step is not None:
                self.reason = reason
                step = self._unstick(world, observation, step, rng)
                if step in risky:
                    self.reason += ", Vorsicht"
                    step = rng.choice([a for a in world if a not in risky] or [step])
                self._at[point, step] += 1
                return step
        self.reason = ""
        return None

    def _unstick(
        self, world: Model, observation: Observation, step: int, rng: random.Random
    ) -> int:
        """Ändert die Taste nichts (er läuft gegen einen Baum), nach `STUCK` Mal eine andere."""
        if self._last_choice == (observation, step):
            self._repeats += 1
        else:
            self._repeats = 0
        self._last_choice = (observation, step)
        if self._repeats < STUCK:
            return step
        self._repeats = 0
        self.reason += ", festgefahren"
        return rng.choice([action for action in world if action != step] or [step])

    def dangers(
        self, knowledge: Knowledge, body: set[int], harmed: list[int]
    ) -> list[tuple[Literal, ...]]:
        """Lagen, nach denen eine Menge, die nach vielen Tasten sinken kann (etwa Gesundheit),
        mit Sicherheit oft sank, egal nach welcher Taste. Nur Aussagen über das, was er sieht;
        Bedingungen über seine Mengen (Durst ist 0) stillt er als Bedürfnis, nicht durch Abwehr.
        Ab 0.19 auch über Gruppen von Feldern („ein Gegner irgendwo direkt neben mir“, aus
        `space`). Ab 0.21 je eine einzelne Aussage mit ihrer Unsicherheit (`cues`), statt
        Bedingungen aus dem Abdecken mit mindestens 5 Treffern."""
        seen = frozenset(range(knowledge.rules.width)) - body - set(self._axes(knowledge))
        groups = knowledge.space.layout.groups()
        return [
            (literal,)
            for component in harmed
            for literal in self._cues.alarms(component, DANGER, seen, groups)
        ]

    def _axes(self, knowledge: Knowledge) -> list[int]:
        form = self._forms.get(knowledge)
        return [] if form is None else [axis.component for axis in form.axes]

    def risky(self, knowledge: Knowledge, observation: Observation, harmed: list[int]) -> set[int]:
        """Tasten, nach denen hier meist Gesundheit sank: Ihre Ursache für „sinkt“ gilt gerade
        (ein Schritt in die Lava). Er lernt das wie jede andere Wirkung einer Taste."""
        return {
            cause.action
            for component in harmed
            for cause in knowledge.causes.causes(Event(component, Change.FALLS), RISK)
            if cause.ready(observation)
        }

    def _defend(
        self,
        knowledge: Knowledge,
        world: Model,
        observation: Observation,
        body: set[int],
        harmed: list[int],
        risky: set[int],
        rng: random.Random,
    ) -> int | None:
        """In einer gefährlichen Lage die Antwort, nach der bisher am wenigsten Schaden folgte;
        bei Gleichstand die, nach der er sich außer Gefahr denkt.

        Gefährlich ist eine Lage, nach der eine Menge wie Gesundheit oft sank (`dangers`). Was
        dagegen hilft, kann sein Modell nicht vorhersagen (ein Gegner läuft hinterher). Darum
        lernt er es aus Erfahrung: Für jede gefährliche Lage und Antwort zählt er, wie viel in
        den nächsten `HARM_WINDOW` Schritten verloren ging und ob die Gefahr dann noch da war.
        Was er dort noch nie probiert hat, gilt als harmlos, damit er es probiert
        (modellfreies neben modellbasiertem Lernen: Daw, Niv & Dayan 2005; Vermeiden lernen:
        Mowrer 1947, Herrnstein 1969).

        Ab 0.19 ist eine Antwort, wo er die Gefahr im Blick hat, keine Taste mehr, sondern eine
        Richtung: „hin“, „weg“ oder „quer“ (aus `space`). Was gegen einen Gegner links hilft,
        hilft dann auch gegen einen rechts. Tasten, die hier selbst schaden (`risky`), nimmt
        er nicht.
        """
        dangers = self.dangers(knowledge, body, harmed)
        layout = knowledge.space.layout
        safe = [a for a in world if a not in risky] or list(world)
        held = self._hold(layout, safe, observation)
        if held is not None:
            return held
        for danger in dangers:
            if all(literal.holds(observation) for literal in danger):
                options = self._options(layout, safe, danger, observation)
                cost = {
                    answer: (
                        self._expected_harm(danger, answer),
                        _holding(dangers, imagine(world, observation, step)),
                    )
                    for answer, step in options.items()
                }
                least = min(cost.values())
                answer = rng.choice([a for a in options if cost[a] == least])
                self._hurt_cache = harmed
                health = sum(observation[c] for c in harmed)
                self._pending.append((self.steps, danger, answer, health))
                self._guard = Guard(danger, answer, self.steps + HARM_WINDOW)
                return options[answer]
        return None

    def _options(
        self,
        layout: Layout,
        safe: list[int],
        danger: tuple[Literal, ...],
        observation: Observation,
    ) -> dict[str, int]:
        """Die Antworten, die er auf diese Gefahr geben kann, je mit ihrer ersten Taste.

        Weiß er, wo die Gefahr ist, sind das wenige (ab 0.20): hin, weg, quer, und jede Taste
        mit Wirkung, die an der Gefahr wirken kann („Taste a daran“: Woran sie wirkt, hat den
        Wert der Gefahr schon einmal gezeigt). Tiere lernen Abwehr leicht nur aus wenigen
        angeborenen Antworten, Flucht, Erstarren, Kampf (Bolles 1970); eine beliebige Taste
        als Antwort zu finden dauert zu lange. Weiß er nicht, wo sie ist, ist jede Taste eine
        Antwort."""
        place = _nearest(layout, danger, observation)
        anything = {self._answer(layout, a, place, danger, observation): a for a in safe}
        if place is None:
            return anything
        values = _values(danger)
        toward = [a for a in safe if layout.relation(a, place) == "hin"]
        options: dict[str, int] = {}
        for action in safe:
            relation = layout.relation(action, place)
            operands = self._operands.get(action, set())
            if relation is not None:
                options.setdefault(relation, action)
            elif any(self._seen[c, v] for c in operands for v in values):
                at = any(observation[c] in values for c in operands)
                if at or toward:
                    options[f"Taste {action} daran"] = action if at else toward[0]
        return options or anything

    def _hold(self, layout: Layout, safe: list[int], observation: Observation) -> int | None:
        """Bleibt bei der Antwort von eben, solange ihre Gefahr gilt und die Zeit nicht um ist
        (H32): Ein Gegner fällt erst nach mehreren Schlägen, und wer nach jedem Schlag etwas
        anderes probiert, lernt nie, dass Schlagen hilft. Die Taste dafür sucht er in der Lage
        von jetzt: „hin“ ist nach einem Schritt eine andere Taste, wenn der Gegner mitläuft;
        „Taste a daran“ heißt erst hingehen, bis die Gefahr dort ist, woran a wirkt."""
        guard = self._guard
        if guard is None:
            return None
        if self.steps >= guard.until or not all(lit.holds(observation) for lit in guard.danger):
            self._guard = None
            return None
        place = _nearest(layout, guard.danger, observation)
        step = self._realize(layout, safe, place, guard, observation)
        if step is None:
            self._guard = None
        return step

    def _realize(
        self,
        layout: Layout,
        safe: list[int],
        place: Point | None,
        guard: Guard,
        observation: Observation,
    ) -> int | None:
        """Eine Taste, die jetzt die Antwort `guard.answer` gibt (None: keine)."""
        toward = [a for a in safe if place is not None and layout.relation(a, place) == "hin"]
        for action in safe:
            answer = self._answer(layout, action, place, guard.danger, observation)
            if answer == guard.answer:
                return action
            if guard.answer == f"Taste {action} daran" and toward:
                return toward[0]  # Erst hin, bis die Gefahr dort ist, woran die Taste wirkt.
        return None

    def _answer(
        self,
        layout: Layout,
        action: int,
        place: Point | None,
        danger: tuple[Literal, ...],
        observation: Observation,
    ) -> str:
        """Die Antwort auf eine Gefahr: eine Richtung zu ihr hin oder von ihr weg, wenn die
        Taste ihn bewegt und er weiß, wo die Gefahr ist. Sonst die Taste selbst, und ob sie
        gerade an der Gefahr wirkt: Steht dort, woran sie wirkt (`operands`, etwa das Feld vor
        ihm), der Wert der Gefahr, ist „Taste daran“ etwas anderes als „Taste“ (H30)."""
        relation = None if place is None else layout.relation(action, place)
        if relation is not None:
            return relation
        values = _values(danger)
        at = any(observation[c] in values for c in self._operands.get(action, ()))
        return f"Taste {action} daran" if at else f"Taste {action}"

    @property
    def tried(self) -> dict[tuple[tuple[Literal, ...], str], int]:
        """(Lage, Antwort) → wie oft er sie in dieser gefährlichen Lage gegeben hat."""
        return dict(self._tried_in)

    def cost(self, danger: tuple[Literal, ...], answer: str) -> float:
        """Was danach im Mittel geschah: Schaden, und `LINGER`, wenn die Gefahr blieb."""
        return self._harm[danger, answer] / max(self._tried_in[danger, answer], 1)

    def _expected_harm(self, danger: tuple[Literal, ...], answer: str) -> float:
        """Mittlerer Schaden nach dieser Antwort in dieser Lage, zum Mittel über alle
        gefährlichen Lagen hin gezogen (`SHRINK` gedachte Fälle): Was gegen einen Gegner hilft,
        hilft oft auch gegen einen anderen (Schrumpfen zum gemeinsamen Mittel, Efron & Morris
        1975). Nie probiert heißt Schaden 0, damit er es probiert."""
        pooled = self._harm_any[answer] / (self._tried_any[answer] + 1)
        return (self._harm[danger, answer] + SHRINK * pooled) / (
            self._tried_in[danger, answer] + SHRINK
        )

    def harmed(self, knowledge: Knowledge, form: Form) -> list[int]:
        """Größen wie Gesundheit, auf die er achtet: Was ihnen schadet, ist Gefahr (`_hurt`)."""
        form = self.steady(knowledge, form)
        own = self.owned(knowledge, form)
        return self._hurt(knowledge, self.body(knowledge, form), set(self.needs(knowledge, own)))

    def _hurt(self, knowledge: Knowledge, body: set[int], needs: set[int]) -> list[int]:
        """Größen des Körpers, die sich in kleinen Schritten ändern und nach mindestens der
        Hälfte der oft gedrückten Tasten schon sanken (Gesundheit, nicht Holz): Was ihnen
        schadet, kommt von außen. Bedürfnisse (Durst) sinken von selbst, nicht durch eine Lage;
        sie stillt er, statt sie abzuwehren."""
        frequent = [a for a, n in self._pressed.items() if n >= DECAY_PRESSES]
        switches = set(knowledge.rules.sensors())
        return sorted(
            c
            for c in body - switches - needs
            if self._small_changes[c] >= COUNTING * self._all_changes[c]
            and frequent
            and sum(self._falls[c, a] > 0 for a in frequent) >= HURT * len(frequent)
        )

    def steady(self, knowledge: Knowledge, form: Form) -> Form:
        """Die Form mit den meisten Achsen, die er bisher gefunden hat. Eine Karte verschwindet
        nicht, nur weil eine Regel gerade ein paar Ausnahmen mehr hat."""
        known = self._forms.get(knowledge)
        if known is None or len(form.of_kind(*STEPPED)) > len(known.of_kind(*STEPPED)):
            self._forms[knowledge] = known = form
        return known

    def body(self, knowledge: Knowledge, form: Form) -> set[int]:
        """Größen, die weder Ort (eine Achse, ab 0.19 auch was sich beim Gehen um 1 ändert, aus
        `space`) noch Blick sind: keine Regel „übernimmt“ oder „wird“. Ohne Form weiß er noch
        nicht, was Ort ist (leere Menge)."""
        if not form.axes:
            return set()
        place = {axis.component for axis in form.axes} | knowledge.space.whereabouts
        body = set(range(knowledge.rules.width)) - place
        for (_, component), found in knowledge.rules.found.items():
            if found.program is not None and any(
                isinstance(leaf, Copy | Becomes) for leaf in leaves(found.program)
            ):
                body.discard(component)
        return body

    def owned(self, knowledge: Knowledge, form: Form) -> set[int]:
        """Mengen: Größen des Körpers (`body`), die sich fast immer um genau 1 ändern, wie beim
        Zählen. So unterscheidet der Agent Besitz und Zustand (Holz, Durst) vom Blick, in dem
        Nummern für Dinge springen. Zahl und Ort als getrennte Kernsysteme: Spelke 2022,
        Dehaene 2011 (Zahlensinn)."""
        return {
            c
            for c in self.body(knowledge, form)
            if self._unit_changes[c] >= COUNTING * self._all_changes[c] and self._all_changes[c]
        }

    def needs(self, knowledge: Knowledge, own: set[int]) -> list[int]:
        """Größen, die von selbst sinken: nach fast jeder oft gedrückten Taste. Keine Schalter."""
        frequent = [a for a, n in self._pressed.items() if n >= DECAY_PRESSES]
        if len(frequent) < 2:
            return []
        switches = knowledge.rules.sensors()
        return sorted(
            c
            for c in own
            if c not in switches
            and sum(self._falls[c, a] > 0 for a in frequent) >= DECAY_SHARE * len(frequent)
        )

    def records(self, knowledge: Knowledge, form: Form, own: set[int]) -> list[int]:
        """Größen, die schon über ihren Anfangswert stiegen, nach einer Taste, die nicht zum
        Gehen dient; die seltensten Rekorde zuerst. Ohne Form noch keine."""
        walking = {action for axis in form.axes for action in (axis.up, axis.down)}
        if not walking:
            return []
        excluded = set(self.needs(knowledge, own)) | set(knowledge.rules.sensors())
        risen = {
            c
            for (action, c) in self._rises
            if action not in walking
            and c in own
            and c not in excluded
            and self.highest[c] > self.first[c]
        }
        return sorted(risen, key=lambda c: (self.reached[c] + self.given_up[c], c))

    def _low(
        self, knowledge: Knowledge, observation: Observation, own: set[int], share: float
    ) -> list[int]:
        """Bedürfnisse, die auf diesen Anteil ihres höchsten Werts gesunken sind, das
        dringendste zuerst."""
        low = [
            (observation[c] / self.highest[c], c)
            for c in self.needs(knowledge, own)
            if self.highest[c] > 0 and observation[c] <= share * self.highest[c]
        ]
        return [c for _, c in sorted(low)]

    def _need(
        self, plan: "_Plan", observation: Observation, own: set[int], share: float = URGENT
    ) -> int | None:
        """Ein Schritt, um ein Bedürfnis zu heben, das auf `share` gesunken ist. Dringend ab
        der Hälfte; sonst, wenn nichts anderes zu tun ist, schon knapp unter dem höchsten Wert
        (je weiter weg vom Sollwert, desto stärker der Antrieb: Keramati & Gutkin 2014)."""
        for component in self._low(plan.knowledge, observation, own, share):
            goal = Literal(component, observation[component] + 1, Kind.AT_LEAST)
            step = plan.toward(observation, goal)
            if step is not None:
                self._pursue(goal, "Bedürfnis")
                return step
        return None

    def _continue(self, plan: "_Plan", observation: Observation, own: set[int]) -> int | None:
        """Weiter am Ziel von eben, solange es Sinn hat und die Geduld reicht."""
        pursuit = self.pursuit
        if pursuit is None:
            return None
        if pursuit.goal.component not in own and pursuit.reason != "Neugier":
            self.pursuit = None  # Doch nur Blick: kein Ziel.
            return None
        if self.steps - pursuit.since > PATIENCE:
            self.given_up[pursuit.goal.component] += 1
            self.pursuit = None
            return None
        step = plan.toward(observation, pursuit.goal)
        if step is None:
            self.pursuit = None
        return step

    def _record(self, plan: "_Plan", observation: Observation, own: set[int]) -> int | None:
        asked = 0
        for component in self.records(plan.knowledge, plan.form, own):
            if self._retry.get(component, 0) > self.steps:
                continue
            if asked == GOALS_PER_STEP:
                break
            asked += 1
            here = self.highest_here.get(component, observation[component])
            goal = Literal(component, here + 1, Kind.AT_LEAST)
            step = plan.toward(observation, goal)
            if step is not None:
                self._pursue(goal, "Rekord")
                return step
            self._retry[component] = self.steps + RETRY  # Kein Weg bekannt: später wieder.
        return None

    def _trial(
        self,
        knowledge: Knowledge,
        observation: Observation,
        body: set[int],
        own: set[int],
        rng: random.Random,
    ) -> int | None:
        """Eine Taste ohne eigene Wirkung bei etwas Seltenem, das sie noch nie sah, oder eine
        mit Wirkung bei einem Wert dort, woran sie wirkt. Ist das etwas, das er sieht (nicht
        sein Körper), probiert er es bis zu `TRIES`-mal: Manches wirkt erst beim dritten
        Schlag (H31)."""
        rare = [c for c, value in enumerate(observation) if self._seen[c, value] <= RARE]
        carried = self._carried(observation)
        fresh = [
            action
            for action in range(self.actions)
            if any(
                self._with[action, c, observation[c], carried] < self._tries(action, c, body)
                for c in (rare if action in self._unknown else self._operands.get(action, ()))
            )
        ]
        return rng.choice(fresh) if fresh else None

    def _carried(self, observation: Partial) -> tuple[int, ...]:
        """Welche seiner Mengen er gerade hat (mehr als 0): Ein Versuch, der ohne Spitzhacke
        nichts brachte, zählt mit Spitzhacke neu. Was etwas einem anbietet, hängt vom
        Handelnden ab (Affordanz: Gibson 1979; Şahin u. a. 2007)."""
        return tuple(c for c in sorted(self._kit) if (observation[c] or 0) > 0)

    def _tries(self, action: int, component: int, body: set[int]) -> int:
        """Wie oft er eine Taste an einem Wert probiert: mehrmals an dem, was er sieht."""
        return 1 if action in self._unknown or component in body else TRIES

    def _curious(self, plan: "_Plan", observation: Observation, body: set[int]) -> int | None:
        """Hingehen, um etwas auszuprobieren: Sieht er im Blick einen Wert, den eine Taste mit
        Wirkung dort, woran sie wirkt (etwa am Feld vor ihm), noch nie hatte, macht er das zum
        Ziel (H31). Kinder greifen nach Neuem, um zu sehen, was es tut (Piaget 1952: Zirkuläre
        Reaktionen; Stahl & Feigenson 2015)."""
        layout = plan.knowledge.space.layout
        if not layout.centred:
            return None  # Erst wenn er das Gitter kennt, weiß er, was „vor ihm“ und was Blick ist.
        visible = sorted(
            {observation[c] for c in layout.places},
            key=lambda v: min(
                layout.distance(c) or 0 for c in layout.places if observation[c] == v
            ),
        )
        asked = 0
        carried = self._carried(observation)
        for action, operands in sorted(self._operands.items()):
            if action in self._unknown:
                continue
            looking = operands - set(layout.places) - body - set(self._axes(plan.knowledge))
            for component in sorted(looking):
                for value in visible:
                    tried = self._with[action, component, value, carried]
                    if tried >= TRIES or asked == GOALS_PER_STEP:
                        continue
                    goal = Literal(component, value)
                    if self._retry_goal.get(goal, 0) > self.steps:
                        continue
                    asked += 1
                    step = plan.toward(observation, goal)
                    if step is not None:
                        self._pursue(goal, "Neugier")
                        return step
                    self._retry_goal[goal] = self.steps + RETRY
        return None

    def _explore(
        self, form: Form, world: Model, observation: Observation, rng: random.Random
    ) -> int | None:
        """Erkunden auf der Karte seiner Form: ein Stück geradeaus in eine Richtung, dann eine
        neue, bevorzugt dorthin, wo er an diesem Ort seltener war (Lévy-artige Suche wie bei
        Tieren auf Futtersuche, Viswanathan 1999). Ab und zu die Taste, die er an diesem Punkt
        am seltensten gedrückt hat. Ohne Form weiß er nicht, was ein Ort ist (None)."""
        axes = form.of_kind(*STEPPED)
        if not axes:
            return None
        point = _point(axes, observation)
        if rng.random() < CURIOUS:
            counts = [self._at[point, action] for action in range(self.actions)]
            return rng.choice([a for a, n in enumerate(counts) if n == min(counts)])
        heading, left = self._heading
        if left > 0 and heading in world and point != self._last_point:
            self._heading = (heading, left - 1)
            self._last_point = point
            return heading
        options = []
        for axis in axes:
            for action in (axis.up, axis.down):
                if action not in world or action == heading:
                    continue
                target = _point(axes, imagine(world, observation, action))
                if target != point and None not in target:
                    options.append((self._visits[target], action))
        if not options:
            return None
        fewest = min(n for n, _ in options)
        step = rng.choice([action for n, action in options if n == fewest])
        self._heading = (step, rng.randint(*STRETCH))
        self._last_point = point
        return step

    def _pursue(self, goal: Literal, reason: str) -> None:
        if self.pursuit is None or self.pursuit.goal != goal:
            self.pursuit = Pursuit(goal, self.steps, reason)
            self.log.append((self.steps, reason, goal))

    def _review(self) -> None:
        """Welche Tasten bewirken schon selbst, dass etwas steigt (öfter als im Mittel)?"""
        total = sum(self._pressed.values())
        for (action, component), count in self._rises.items():
            mean_rate = self._all_rises[component] / total
            if count >= 2 and count / self._pressed[action] > OWN_EFFECT * mean_rate:
                self._unknown.discard(action)


@dataclass(frozen=True)
class _Plan:
    """Alles, was der Agent braucht, um den Weg zu einem Ziel zu finden."""

    knowledge: Knowledge
    world: Model
    form: Form
    where: dict[int, Observation]
    memo: dict[tuple[Literal, int], int | None] = field(default_factory=dict)

    def toward(self, observation: Observation, goal: Literal) -> int | None:
        """Erst hier mit Teilzielen; sonst zurück zu dem Ort, an dem die Größe zuletzt stieg."""
        step = achieve(self.knowledge, self.world, observation, goal, memo=self.memo)
        if step is not None:
            return step
        remembered = self.where.get(goal.component)
        if remembered is None:
            return None
        layout = self.knowledge.space.layout
        if layout.centred and layout.axes:
            return layout.head(observation, remembered)  # Um Hindernisse herum (ab 0.20).
        axes = self.form.of_kind(*STEPPED)
        if not axes:
            return None
        wanted = {axis.component: remembered[axis.component] for axis in axes}
        return plan_space(axes, wanted, self.knowledge, observation)


def _nearest(layout: Layout, danger: tuple[Literal, ...], observation: Observation) -> Point | None:
    """Wo im Blick die Gefahr am nächsten ist; None, wenn sie nicht im Gitter liegt."""
    places = [
        layout.places[c]
        for literal in danger
        for c in literal.where(observation)
        if c in layout.places and layout.centred
    ]
    if not places:
        return None
    return min(places, key=lambda p: sum(abs(x) for x in p))


def _values(danger: tuple[Literal, ...]) -> set[int]:
    """Die Werte, an denen man die Gefahr erkennt (ein Gegner hat die Nummer 15)."""
    return {literal.value for literal in danger if literal.kind is not Kind.AT_LEAST}


def _holding(situations: list[tuple[Literal, ...]], observation: Partial) -> int:
    """Wie viele der Lagen in der (vorgestellten) Beobachtung gelten."""
    return sum(all(literal.holds(observation) for literal in s) for s in situations)


def _point(axes: tuple[Axis, ...], observation: Partial) -> Partial:
    """Der Punkt auf der Karte: die Werte der Achsen."""
    return tuple(observation[axis.component] for axis in axes)
