"""Raum aus eigener Bewegung: welches Sichtfeld neben welchem liegt (ab 0.19, H29).

Der Agent weiß nicht, dass 63 seiner Größen ein Bild sind. Er sieht nur: Nach Taste a hat
Größe i oft den Wert, den eben noch Größe j hatte. Dann liegt j in Richtung a neben i, denn
was er sieht, wandert bei eigener Bewegung mit. Aus diesen Verschiebungen baut er sich ein
Gitter (Philipona, O'Regan & Nadal 2003; Pierce & Kuipers 1997: Karten aus uninterpretierten
Sinnen und Tasten; Laflaquière & Garcia Ortiz 2019).

Gezählt wird nur, wenn sich Größe i wirklich änderte. In Crafter ist fast alles Gras: Dort
ist „bleibt gleich“ meist richtig, und die Regeln in `knowledge` wählen darum oft `Keep`
statt `Copy`. Zählt man nur die Änderungen, fällt die Verschiebung trotzdem auf.

Eine Stelle im Gitter hat kein Feld: Dort ist er selbst. Alles wandert an ihm vorbei, nur
sein eigenes Feld nicht (der Körper als das, was bei eigener Bewegung gleich bleibt:
Philipona 2003). Von dieser Stelle aus misst er Abstände. So wird „ein Gegner direkt neben
mir“ eine Lage, egal auf welcher Seite (deiktische Darstellung, Agre & Chapman 1987).
"""

from collections import Counter, deque
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Final

from hekmatki.general.env import Observation, Transition

type Partial = tuple[int | None, ...]

type Point = tuple[int, ...]

FLOW_SHARE: Final = 0.9
"""So oft muss ein Feld nach einem Schritt den Wert seines Nachbarn haben (ohne Grundlage)."""
GAP: Final = 0.01
"""So viel öfter als jedes andere Feld muss der Nachbar passen (ohne Grundlage)."""
MIN_FLOW: Final = 4
CHANGE_SHARE: Final = 0.8
"""Hat sich ein Feld bei echten Schritten mindestens `MIN_FLOW`-mal geändert, muss der
Nachbar auch bei diesen Änderungen so oft passen. Im Gras passt fast alles; erst eine
Änderung zeigt, woher der Wert kam (ohne Grundlage)."""
STEADY: Final = 0.95
WALKS: Final = 0.2
"""Der Ort ändert sich bei einer Taste in mindestens `STEADY` der Fälle um denselben Schritt,
und nach mindestens `WALKS` der Tasten (sonst ist es nicht der Ort; ohne Grundlage)."""
WIDE: Final = 6
"""So viele verschiedene Werte braucht eine Größe, um ein Ort zu sein (ohne Grundlage)."""
MIN_WALKS: Final = 20
"""Erst nach so vielen echten Schritten in eine Richtung (beide Richtungen zusammen) urteilt
er, welches Feld neben welchem liegt."""
MIN_EDGES: Final = 4
"""Eine Taste verschiebt den Blick, wenn er mit ihr geht (sie hat einen Ort, siehe
`Space._find_walkers`) und sie mindestens so viele Felder verschiebt. Sonst wandert nur ein
Tier durchs Bild."""
RINGS: Final = 3
"""Bis zu diesem Abstand bildet er Gruppen „irgendwo im Abstand ≤ d“ (ohne Grundlage)."""
FILLED: Final = 0.9
"""So viel des Gitters muss er kennen, bevor er seine eigene Stelle sucht (ohne Grundlage).
Ab 0.22 auch: So groß wie das größte Stück muss ein anderes Stück fast sein, damit er seine
Stelle dort sucht, wenn das größte keine hat."""
MAX_BOX: Final = 10_000
"""Größer darf das Gitter nicht sein, damit die Suche nach der Lücke schnell bleibt."""
SETTLE: Final = 3
"""So oft rückt er Felder nach der Mehrheit ihrer Verschiebungen zurecht (ohne Grundlage)."""
MIN_BLOCKED: Final = 5
BLOCKING: Final = 0.8
"""Ein Wert ist ein Hindernis, wenn er vor so einem Feld in mindestens `BLOCKING` der Fälle
stehen blieb, ab `MIN_BLOCKED` Fällen (ab 0.20, ohne Grundlage)."""
REFRESH: Final = 100
"""So oft (in Schritten) baut er das Gitter neu."""


@dataclass(frozen=True)
class Layout:
    """Das gelernte Gitter: wo jedes Sichtfeld liegt und wie Tasten den Blick verschieben."""

    flows: dict[int, dict[int, int]] = field(default_factory=dict)
    """Taste → {Feld j: Feld i}: Nach der Taste steht in i, was vorher in j stand."""
    places: dict[int, Point] = field(default_factory=dict)
    """Feld → seine Stelle im Gitter, vom eigenen Ort aus gemessen."""
    vectors: dict[int, Point] = field(default_factory=dict)
    """Taste → in welche Richtung er sich mit ihr bewegt."""
    axes: tuple[int, ...] = ()
    """Die Ortsgrößen, eine je Richtung des Gitters: Ein Schritt um +1 in Richtung k ändert
    `axes[k]` um +1."""
    centred: bool = False
    """Ob er seinen eigenen Ort im Gitter gefunden hat (sonst gibt es keine Abstände)."""
    obstacles: frozenset[int] = frozenset()
    """Werte, in die er nicht hineingehen kann: Ging er auf so ein Feld zu, blieb er stehen."""
    mirrors: dict[int, frozenset[Point]] = field(default_factory=dict)
    """Größe → die Nachbarstellen, deren Wert sie zeigt, je nachdem, wohin er zuletzt ging
    (ein Fühler wie „vorne“): Sie bekommt beim Gehen den Wert eines Nachbarn, ist aber kein
    Feld des Gitters."""

    def distance(self, component: int) -> int | None:
        """Wie weit ein Feld von ihm weg ist (in Schritten), None: kein Feld oder unbekannt."""
        place = self.places.get(component)
        if place is None or not self.centred:
            return None
        return sum(abs(x) for x in place)

    def groups(self) -> tuple[tuple[int, ...], ...]:
        """Die Felder im Abstand ≤ 1, ≤ 2, … ≤ `RINGS`: „irgendwo nah bei mir“."""
        if not self.centred:
            return ()
        found: list[tuple[int, ...]] = []
        for radius in range(1, RINGS + 1):
            near = tuple(sorted(c for c in self.places if (self.distance(c) or 0) <= radius))
            if near and (not found or near != found[-1]):
                found.append(near)
        return tuple(found)

    def route(self, sources: Iterable[int], targets: Iterable[int]) -> int | None:
        """Die erste Taste, die etwas aus einem der Felder `sources` in eins der Felder
        `targets` holt (Breitensuche über die Verschiebungen); None: kein Weg."""
        wanted = set(targets)
        first: dict[int, int | None] = {}
        frontier: deque[int] = deque()
        for source in sources:
            if source not in first:
                first[source] = None
                frontier.append(source)
        while frontier:
            here = frontier.popleft()
            if here in wanted:
                return first[here]
            for action, flow in sorted(self.flows.items()):
                there = flow.get(here)
                if there is None or there in first:
                    continue
                start = first[here]
                first[there] = action if start is None else start
                frontier.append(there)
        return None

    def fetch(self, observation: Partial, value: int, targets: Iterable[int]) -> int | None:
        """Die erste Taste, die etwas mit dem Wert `value`, das er gerade sieht, in eins der
        Felder `targets` holt: hingehen, wo man es sieht. Kennt er seine eigene Stelle, geht er
        um Hindernisse herum (`walk`); ein Fühler wie „vorne“ zeigt `value`, wenn er neben
        dem Ding steht und darauf zugeht."""
        targets = list(targets)
        if not self.centred:
            wanted = [c for c in targets if c in self.places]
            sources = [c for c in self.places if observation[c] == value and c not in wanted]
            return self.route(sources, wanted) if wanted and sources else None
        seen = [p for c, p in self.places.items() if observation[c] == value]
        spots: set[Point] = set()
        for target in targets:
            if target in self.places:
                spots |= {_minus(point, self.places[target]) for point in seen}
            for near in self.mirrors.get(target, ()):
                if near in seen:
                    return self._toward(near)  # Daneben: hindrehen.
                spots |= {_minus(point, near) for point in seen}
        return self.walk(observation, spots)

    def head(self, observation: Partial, where: Partial) -> int | None:
        """Die erste Taste zu einem Ort (Werte der Ortsgrößen), auch wenn er ihn nicht sieht:
        zu dem Feld, das er erreichen kann und das dem Ort am nächsten liegt, um Hindernisse
        herum. None: Er ist schon da, kommt nicht näher oder kennt sein Gitter nicht."""
        if not self.centred or not self.axes:
            return None
        goal: list[int] = []
        for axis in self.axes:
            now, then = observation[axis], where[axis]
            if now is None or then is None:
                return None
            goal.append(then - now)
        target = tuple(goal)
        reach = self._reachable(observation)
        best = min(
            reach, key=lambda p: (sum(abs(a - b) for a, b in zip(p, target, strict=True)), p)
        )
        return reach[best]

    def walk(self, observation: Partial, spots: set[Point]) -> int | None:
        """Die erste Taste auf dem kürzesten Weg zu einer der Stellen `spots`, nur über
        Felder, die er sieht und die kein Hindernis sind (Breitensuche); None: kein Weg."""
        if not spots or not self.axes:
            return None
        reach = self._reachable(observation)
        found = [p for p in spots if reach.get(p) is not None]
        if not found:
            return None
        return reach[min(found, key=lambda p: (sum(abs(x) for x in p), p))]

    def _reachable(self, observation: Partial) -> dict[Point, int | None]:
        """Jede Stelle, die er über freie Felder im Blick erreicht, mit der ersten Taste
        dorthin (None für die eigene Stelle)."""
        origin = tuple(0 for _ in self.axes)
        free = {point for c, point in self.places.items() if observation[c] not in self.obstacles}
        first: dict[Point, int | None] = {origin: None}
        frontier: deque[Point] = deque([origin])
        while frontier:
            here = frontier.popleft()
            for action, vector in sorted(self.vectors.items()):
                there = _plus(here, vector)
                if there in first or there not in free:
                    continue
                first[there] = action if first[here] is None else first[here]
                frontier.append(there)
        return first

    def _toward(self, point: Point) -> int | None:
        return next((a for a, v in sorted(self.vectors.items()) if v == point), None)

    def relation(self, action: int, place: Point) -> str | None:
        """Bringt die Taste ihn näher zu `place` („hin“), weiter weg („weg“) oder keins von
        beiden („quer“)? None: Die Taste bewegt ihn nicht."""
        vector = self.vectors.get(action)
        if vector is None:
            return None
        dot = sum(a * b for a, b in zip(vector, place, strict=True))
        return "hin" if dot > 0 else "weg" if dot < 0 else "quer"


@dataclass(frozen=True, order=True)
class Edge:
    """Eine Verschiebung: Nach Taste `action` steht in `target`, was in `source` stand."""

    strength: float
    """Wie sicher sie ist (`Space._strength`): Die sicheren baut er zuerst ins Gitter."""
    action: int
    source: int
    target: int


class Space:
    """Zählt, welche Größe nach welcher Taste den Wert welcher anderen übernimmt."""

    def __init__(self) -> None:
        self._pressed: Counter[int] = Counter()
        self._changed: Counter[tuple[int, int]] = Counter()
        """(Taste, Größe i) → wie oft sich i nach der Taste änderte."""
        self._units: Counter[tuple[int, int, int]] = Counter()
        """(Taste, Größe, ±1) → wie oft die Größe nach der Taste um genau so viel wechselte."""
        self._values: dict[int, set[int]] = {}
        """Größe → die Werte, die sie schon hatte (höchstens `WIDE` gezählt)."""
        self._mobile: set[int] = set()
        """Größen, die sich schon einmal geändert haben: Nur sie können ein Sichtfeld sein."""
        self._walkers: dict[int, tuple[int, int]] = {}
        """Taste → (Größe, Schritt): eine Größe, die sich bei ihr fast immer um denselben
        Schritt ±1 ändert, der Ort. Ändert sie sich, ist er wirklich gegangen."""
        self._walked: Counter[int] = Counter()
        self._shifted: Counter[tuple[int, int]] = Counter()
        """(Taste, i) → wie oft sich i bei einem echten Schritt änderte."""
        self._matched: Counter[tuple[int, int, int]] = Counter()
        """(Taste, i, j) → wie oft i dabei den alten Wert von j bekam."""
        self._agreed: Counter[tuple[int, int, int]] = Counter()
        """(Taste, i, j) → wie oft nach einem echten Schritt i den alten Wert von j hatte, auch
        wenn i gleich blieb: Ist er gegangen, ist das ganze Bild verschoben."""
        self._blocked: Counter[int] = Counter()
        self._passed: Counter[int] = Counter()
        """Wert → wie oft er auf ein Feld mit diesem Wert zuging und stehen blieb, oder ging."""
        self._steps = 0
        self._layout = Layout()

    def observe(self, transition: Transition) -> None:
        """Merkt sich, welche Größen sich änderten und wessen alten Wert sie bekamen."""
        self._steps += 1
        before, after, action = transition.before, transition.after, transition.action
        self._pressed[action] += 1
        holders: dict[int, list[int]] = {}
        for component, value in enumerate(before):
            holders.setdefault(value, []).append(component)
        for component, (old, new) in enumerate(zip(before, after, strict=True)):
            if new == old:
                continue
            self._mobile.add(component)
            values = self._values.setdefault(component, {old})
            if len(values) < WIDE:
                values.add(new)
            self._changed[action, component] += 1
            if abs(new - old) == 1:
                self._units[action, component, new - old] += 1
        walker = self._walkers.get(action)
        if walker is not None:
            moved = before[walker[0]] != after[walker[0]]
            if moved:
                self._walk(action, before, after, holders)
            self._bump(action, before, moved)
        if self._steps % REFRESH == 0:
            self._walkers = self._find_walkers()
            edges, oneway = self._edges()
            layout = build(edges, self._walkers, oneway)
            if layout.centred or not self._layout.centred:
                self._layout = layout  # Ein Gitter mit Mitte gibt er nur für ein besseres her.
            self._layout = replace(self._layout, obstacles=self._obstacles())

    def _bump(self, action: int, before: Observation, moved: bool) -> None:
        """Merkt sich, was auf dem Feld stand, auf das er zuging, und ob er hinkam."""
        layout = self._layout
        vector = layout.vectors.get(action)
        if not layout.centred or vector is None:
            return
        ahead = next((c for c, place in layout.places.items() if place == vector), None)
        if ahead is not None:
            (self._passed if moved else self._blocked)[before[ahead]] += 1

    def _obstacles(self) -> frozenset[int]:
        """Werte, vor denen er fast immer stehen blieb (`BLOCKING`, ab `MIN_BLOCKED` Fällen):
        Hindernisse lernt er wie alles andere aus seiner Bewegung."""
        return frozenset(
            value
            for value, blocked in self._blocked.items()
            if blocked >= MIN_BLOCKED and blocked >= BLOCKING * (blocked + self._passed[value])
        )

    def _walk(
        self,
        action: int,
        before: Observation,
        after: Observation,
        holders: dict[int, list[int]],
    ) -> None:
        """Ein echter Schritt: Für jede Größe zählt er, wessen alten Wert sie jetzt hat."""
        self._walked[action] += 1
        for component, new in enumerate(after):
            changed = new != before[component]
            self._shifted[action, component] += changed
            for source in holders.get(new, ()):
                self._agreed[action, component, source] += 1
                self._matched[action, component, source] += changed

    @property
    def walking(self) -> set[int]:
        """Die Tasten, mit denen er geht: Bei ihnen ändert sich sein Ort."""
        return set(self._walkers)

    @property
    def whereabouts(self) -> set[int]:
        """Die Größen, die sein Ort sind: Sie ändern sich, wenn er geht."""
        return {component for component, _ in self._walkers.values()}

    @property
    def layout(self) -> Layout:
        """Das Gitter, wie er es zuletzt gebaut hat."""
        return self._layout

    def _find_walkers(self) -> dict[int, tuple[int, int]]:
        """Für jede Taste die Größe, die sich bei ihr am öftesten um immer denselben Schritt
        ±1 ändert (in mindestens `STEADY` der Fälle, nach mindestens `WALKS` der Tasten) und
        schon viele Werte hatte: Ein Ort hat viele Werte, eine Blickrichtung wenige. Und es
        gibt eine Taste, die sie um den Schritt zurück ändert: Ein Ort ist, wohin man hin und
        zurück gehen kann (ab 0.20). Ein Vorrat, der beim Schöpfen steigt und von selbst sinkt,
        ist kein Ort."""
        best: dict[int, tuple[int, int, int]] = {}
        for (action, component, step), count in self._units.items():
            changed = self._changed[action, component]
            if count < STEADY * changed or changed < WALKS * self._pressed[action]:
                continue
            if len(self._values.get(component, ())) < WIDE:
                continue
            if action not in best or count > best[action][0]:
                best[action] = (count, component, step)
        found = {action: (component, step) for action, (_, component, step) in best.items()}
        return {
            action: (component, step)
            for action, (component, step) in found.items()
            if (component, -step) in found.values()
        }

    def _edges(self) -> tuple[list[Edge], list[Edge]]:
        """Für jede Taste, mit der er geht, und jedes Feld i das Feld j, dessen Wert i nach
        einem echten Schritt fast immer hat (`FLOW_SHARE`), deutlich öfter als jedes andere
        (`GAP`). Die Gegenrichtung zählt mit: Holt „links“ j nach i, holt „rechts“ i nach j.
        Dazu die Verschiebungen, die nur in eine Richtung passen (Abbilder wie „vorne“).

        Gehen mehrere Tasten in die Gegenrichtung (in Minecraft „vor“ und „springen“), zählt
        die, mit der es am besten passt (ab 0.22): Ein Sprung bergauf verschiebt das Bild
        auch nach unten und darf das saubere „vor“ nicht verdecken."""
        backs: dict[int, list[int]] = {}
        for action, (component, step) in self._walkers.items():
            for reverse, (component2, step2) in self._walkers.items():
                if component2 == component and step2 == -step:
                    backs.setdefault(action, []).append(reverse)
        scores: dict[tuple[int, int], dict[int, int]] = {}
        for (action, target, source), count in self._agreed.items():
            if source != target and target in self._mobile:
                scores.setdefault((action, target), {})[source] = count
        edges: list[Edge] = []
        oneway: list[Edge] = []
        for (action, target), found in scores.items():
            candidates: list[int | None] = [*backs.get(action, [])] or [None]
            ranked = [self._ranked(action, target, found, other) for other in candidates]
            best = max((r for r in ranked if r is not None), key=lambda r: r[0], default=None)
            if best is None:
                continue
            share, second, source, other = best
            if share < FLOW_SHARE or share - second < GAP:
                continue
            if not self._fits_changes(action, target, source):
                continue  # Wo sich i änderte, passte j zu selten.
            edge = Edge(self._strength(action, target, source, other), action, source, target)
            if other is not None and not self._fits_changes(other, source, target):
                oneway.append(edge)  # In der Gegenrichtung passt es nicht: nur ein Abbild.
                continue
            edges.append(edge)
        moving = Counter(edge.action for edge in edges)
        return [edge for edge in edges if moving[edge.action] >= MIN_EDGES], oneway

    def _ranked(
        self, action: int, target: int, found: dict[int, int], other: int | None
    ) -> tuple[float, float, int, int | None] | None:
        """Das Feld, dessen Wert ein Feld nach einem Schritt am öftesten hat, mit seinem Anteil
        und dem des zweitbesten, zusammen mit der Gegenrichtung `other`. None, solange er
        mit beiden zusammen weniger als `MIN_WALKS` echte Schritte gemacht hat."""
        walked = self._walked[action] + (self._walked[other] if other is not None else 0)
        if walked < MIN_WALKS:
            return None
        ranked = sorted(
            (
                (count + (self._agreed[other, source, target] if other is not None else 0))
                / walked,
                source,
            )
            for source, count in found.items()
        )
        share, source = ranked[-1]
        second = ranked[-2][0] if len(ranked) > 1 else 0.0
        return share, second, source, other

    def _strength(self, action: int, target: int, source: int, other: int | None) -> float:
        """Wie sicher die Verschiebung ist: wie oft bei echten Schritten, nach denen sich
        `target` änderte, der Wert von `source` kam (mit der Gegenrichtung, geglättet nach
        Laplace). Im Gras passt fast alles; erst Änderungen trennen den Nachbarn vom Feld
        auf der anderen Seite von ihm."""
        changed = self._shifted[action, target]
        matched = self._matched[action, target, source]
        if other is not None:
            changed += self._shifted[other, source]
            matched += self._matched[other, source, target]
        return (matched + 1) / (changed + 2)

    def _fits_changes(self, action: int, target: int, source: int) -> bool:
        """Hat sich `target` bei echten Schritten mit der Taste oft genug geändert, bekam es
        dabei meist den alten Wert von `source` (`CHANGE_SHARE`). Ein Feld wie „vorne“ bekommt
        beim Gehen nach unten den Wert von weiter unten, beim Gehen nach oben aber nicht den
        von „vorne“ zurück: Es ist kein Nachbar, sondern ein Abbild des Felds, auf das er
        schaut."""
        changed = self._shifted[action, target]
        return changed < MIN_FLOW or self._matched[action, target, source] >= CHANGE_SHARE * changed


def build(
    edges: list[Edge], walkers: dict[int, tuple[int, int]], oneway: Iterable[Edge] = ()
) -> Layout:
    """Das Gitter aus den Verschiebungen: Jede Ortsgröße ist eine Achse, jede Taste, mit der
    er geht, ein Schritt auf ihr; der eigene Ort ist die Lücke. Verschiebungen nur in eine
    Richtung (`oneway`) machen eine Größe zum Abbild ihrer Nachbarn (`Layout.mirrors`)."""
    actions = {edge.action for edge in edges}
    axes = sorted({component for action, (component, _) in walkers.items() if action in actions})
    vectors = {
        action: tuple(step * int(axis == component) for axis in axes)
        for action, (component, step) in walkers.items()
        if action in actions
    }
    pieces = _places([e for e in edges if e.action in vectors], vectors)
    if not pieces:
        return Layout()
    places, kept = _own_piece(pieces)
    centre = _gap(places)
    flows: dict[int, dict[int, int]] = {}
    for edge in kept:
        flows.setdefault(edge.action, {})[edge.source] = edge.target
    if centre is None:
        return Layout(flows, places, vectors, tuple(axes), centred=False)
    shifted = {c: tuple(x - m for x, m in zip(p, centre, strict=True)) for c, p in places.items()}
    mirrors = _mirrors(oneway, shifted, vectors)
    return Layout(flows, shifted, vectors, tuple(axes), centred=True, mirrors=mirrors)


def _own_piece(
    pieces: list[tuple[dict[int, Point], list[Edge]]],
) -> tuple[dict[int, Point], list[Edge]]:
    """Das Stück, in dem er steht: das größte, wenn es seine eigene Stelle zeigt (eine
    Lücke), sonst ein fast so großes mit Lücke (`FILLED`, ab 0.22). In Minecraft ist die
    Schicht unter den Füßen voll, nur in der Schicht der Füße fehlt seine Stelle."""
    largest = pieces[0]
    for piece in pieces:
        if len(piece[0]) < FILLED * len(largest[0]):
            break
        if _gap(piece[0]) is not None:
            return piece
    return largest


def _mirrors(
    oneway: Iterable[Edge], places: dict[int, Point], vectors: dict[int, Point]
) -> dict[int, frozenset[Point]]:
    """Größen außerhalb des Gitters, die nach einem Schritt den Wert eines Felds direkt neben
    ihm zeigen: Sie liegen dort, wo die Verschiebung sie hinlegen würde, im Abstand 1."""
    found: dict[int, set[Point]] = {}
    for edge in oneway:
        if edge.target in places or edge.source not in places or edge.action not in vectors:
            continue
        near = _minus(places[edge.source], vectors[edge.action])
        if sum(abs(x) for x in near) == 1:
            found.setdefault(edge.target, set()).add(near)
    return {component: frozenset(points) for component, points in found.items()}


def _places(
    edges: list[Edge], vectors: dict[int, Point]
) -> list[tuple[dict[int, Point], list[Edge]]]:
    """Stellen im Gitter: Bewegt er sich mit Taste a um v und wandert dabei j nach i, liegt j
    um v weiter als i. Die sichersten Verschiebungen zuerst; eine, die zu dem schon Gebauten
    nicht passt oder zwei Felder auf eine Stelle legen würde, fällt weg (wie beim Bauen
    eines Baums aus den stärksten Kanten, Kruskal 1956). Das Feld links von ihm bekommt
    beim Gehen, worauf er stand, und das sieht oft aus wie das Feld rechts von ihm: Solche
    Verschiebungen sind schwächer und passen nicht. Am Ende bleiben nur Felder, die mit
    mindestens zwei Verschiebungen im Gitter stehen (das Feld „vorne“ fällt so heraus).

    Ab 0.22 kommen alle Stücke zurück, das größte zuerst, jedes mit seinen Verschiebungen.
    Sieht er mehrere Schichten (in Minecraft unter den Füßen, Füße, Kopf), ist jede ein
    eigenes Stück, denn keine Taste bewegt ihn nach oben oder unten."""
    piece_of: dict[int, int] = {}
    pieces: dict[int, dict[int, Point]] = {}
    for edge in sorted(edges, reverse=True):
        _join(pieces, piece_of, edge.source, edge.target, vectors[edge.action])
    result = []
    for piece in sorted(pieces.values(), key=len, reverse=True):
        places = _settle(piece, edges, vectors)
        kept = [e for e in edges if _fits_edge(e, places, vectors)]
        support = Counter(c for e in kept for c in (e.source, e.target))
        places = {c: p for c, p in places.items() if support[c] >= 2}
        if places:
            result.append((places, [e for e in kept if e.source in places and e.target in places]))
    return sorted(result, key=lambda found: len(found[0]), reverse=True)


def _settle(
    places: dict[int, Point], edges: list[Edge], vectors: dict[int, Point]
) -> dict[int, Point]:
    """Rückt Felder an die Stelle, für die die meisten ihrer Verschiebungen sprechen, wenn
    dort noch nichts liegt. Eine falsche Verschiebung über ihn hinweg, früh eingebaut, legt
    sonst ein Feld neben ihm auf seine eigene Stelle."""
    places = dict(places)
    for _ in range(SETTLE):
        moved = False
        for component, votes in _votes(places, edges, vectors).items():
            (best, count), *_ = votes.most_common(1)
            here = places[component]
            if best != here and count > votes[here] and best not in places.values():
                places[component] = best
                moved = True
        if not moved:
            break
    return places


def _votes(
    places: dict[int, Point], edges: list[Edge], vectors: dict[int, Point]
) -> dict[int, Counter[Point]]:
    """Für jedes Feld: Welche Stelle ergibt sich aus jeder seiner Verschiebungen?"""
    votes: dict[int, Counter[Point]] = {}
    for edge in edges:
        if edge.source not in places or edge.target not in places:
            continue
        vector = vectors[edge.action]
        votes.setdefault(edge.source, Counter())[_plus(places[edge.target], vector)] += 1
        votes.setdefault(edge.target, Counter())[_minus(places[edge.source], vector)] += 1
    return votes


def _join(
    pieces: dict[int, dict[int, Point]],
    piece_of: dict[int, int],
    source: int,
    target: int,
    vector: Point,
) -> None:
    """Fügt die Verschiebung „`source` liegt um `vector` weiter als `target`“ ein, wenn sie
    zu dem schon Gebauten passt."""
    a, b = piece_of.get(source), piece_of.get(target)
    if a is None and b is None:
        key = max(pieces, default=-1) + 1
        pieces[key] = {target: (0,) * len(vector), source: vector}
        piece_of[source] = piece_of[target] = key
    elif a is None and b is not None:
        _attach(pieces, piece_of, b, source, _plus(pieces[b][target], vector))
    elif b is None and a is not None:
        _attach(pieces, piece_of, a, target, _minus(pieces[a][source], vector))
    elif a is not None and b is not None and a != b:
        offset = _minus(_plus(pieces[b][target], vector), pieces[a][source])
        moved = {c: _plus(p, offset) for c, p in pieces[a].items()}
        if set(moved.values()) & set(pieces[b].values()):
            return  # Die Stücke würden sich überlappen.
        pieces[b].update(moved)
        for component in moved:
            piece_of[component] = b
        del pieces[a]
    # Schon im selben Stück: Passt sie nicht, bleibt sie draußen.


def _attach(
    pieces: dict[int, dict[int, Point]],
    piece_of: dict[int, int],
    key: int,
    component: int,
    point: Point,
) -> None:
    if point not in pieces[key].values():
        pieces[key][component] = point
        piece_of[component] = key


def _fits_edge(edge: Edge, places: dict[int, Point], vectors: dict[int, Point]) -> bool:
    if edge.source not in places or edge.target not in places:
        return False
    return places[edge.source] == _plus(places[edge.target], vectors[edge.action])


def _gap(places: dict[int, Point]) -> Point | None:
    """Seine eigene Stelle: die einzige freie Stelle im Inneren des Gitters, und alle ihre
    Nachbarn sind Felder. Am Rand darf etwas fehlen (dort kommt Neues ins Bild und wird
    seltener gelernt), innen nicht: Fehlen innen zwei Stellen, weiß er nicht, welche er ist.
    None auch, solange er weniger als `FILLED` des Gitters kennt."""
    if not places:
        return None
    taken = set(places.values())
    dims = len(next(iter(taken)))
    low = [min(p[k] for p in taken) for k in range(dims)]
    high = [max(p[k] for p in taken) for k in range(dims)]
    size = 1
    for lo, hi in zip(low, high, strict=True):
        size *= hi - lo + 1
    if size > MAX_BOX or len(taken) < FILLED * (size - 1):
        return None
    inner = [
        point
        for point in _box(low, high)
        if point not in taken
        and all(lo < x < hi for x, lo, hi in zip(point, low, high, strict=True))
    ]
    if len(inner) != 1:
        return None
    units = [
        tuple(int(k == axis) * sign for k in range(dims))
        for axis in range(dims)
        for sign in (1, -1)
    ]
    point = inner[0]
    return point if all(_plus(point, unit) in taken for unit in units) else None


def _box(low: list[int], high: list[int]) -> list[Point]:
    points: list[Point] = [()]
    for lo, hi in zip(low, high, strict=True):
        points = [(*p, x) for p in points for x in range(lo, hi + 1)]
    return points


def _plus(a: Point, b: Point) -> Point:
    return tuple(x + y for x, y in zip(a, b, strict=True))


def _minus(a: Point, b: Point) -> Point:
    return tuple(x - y for x, y in zip(a, b, strict=True))
