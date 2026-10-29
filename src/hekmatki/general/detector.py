"""Eine neue Umgebung erkennen (ab 0.16, H18).

Der Agent hat für jede Umgebung, die er kennt, eine eigene Karte (`Knowledge`). Nach jedem
Schritt fragt er: Passt das noch zu meiner jetzigen Karte? Drei Antworten werden verglichen:

- **jede Überraschung**: Liegt eine verlässliche Regel daneben, ist das eine andere Umgebung.
  Er wechselt zu einer Karte, die den Schritt erklärt, oder legt eine neue an.
- **nie neue Karte**: Es gibt nur eine Karte. Bei unerwarteter Überraschung lernt er sie neu
  (umlernen), die alte ist dann weg.
- **erwartet / unerwartet** (H18): Jede Regel weiß, wie oft sie danebenliegt (erwartete
  Unsicherheit). Unerwartet ist, wenn eine Regel in den letzten `WINDOW` Schritten so oft
  danebenlag, dass das bei ihrer gewohnten Fehlerquote fast unmöglich ist (Wahrscheinlichkeit
  unter `TAIL_LIMIT`). Dann prüft er seine anderen Karten und nimmt die, die die letzten
  Schritte am besten erklärt, oder legt eine neue an, falls keine passt.

- **Bayes-Faktor** (ab 0.17, H23): Ausgelöst wird wie bei „erwartet / unerwartet“. Ab da
  sammelt er alle Schritte, bis eine Erklärung klar gewinnt (sequentieller Test wie bei
  Wald 1945). Verglichen wird, wie gut jede Erklärung diese Schritte vorausgesagt hätte, in
  Bits: dieselbe Karte, eine der alten Karten oder eine neue, die ihre neuen Regeln erst
  bezahlen muss. Ein Wechsel kostet vorab `CHANGE_BITS`, weil Welten selten wechseln
  (Wechselrate `HAZARD`, Adams & MacKay 2007, Liakoni 2021). Entschieden wird erst bei einem
  Unterschied von `BF_BITS` (Bayes-Faktor 150, „sehr stark“ nach Kass & Raftery 1995).
  Gewinnt die jetzige Karte, verfeinert er die auffälligen Regeln, falls das geht.

Geprüft wird jede Regel einzeln, nicht die Summe: Viele unsichere Regeln würden sonst den
Fehler einer einzigen sicheren Regel verdecken (Lehre aus H16: Teile statt Ganzes).
Bevor der Agent auf eine andere Welt schließt, fragt er außerdem: War die Regel nur
unvollständig oder falsch? Gibt es eine verfeinerte Regel, die alte und neue Schritte erklärt
(etwa „-1, außer an einer Wand“ statt „-1“), verfeinert er sie und bleibt (Teile
korrigieren). Erklärt gar keine Regel die neuen Schritte, lässt er die Regel fallen. Nur wenn
eine *andere* Regel die neuen Schritte gut erklärt, spricht das für eine andere Welt.

Grundlage: Yu & Dayan 2005 (erwartete gegen unerwartete Unsicherheit), Sanders, Wilson und
Gershman 2020 (Remapping als Schluss auf einen verborgenen Zustand), Gershman 2017
(neue Karte statt Überschreiben), Ergebnis 3 und 12 dieses Prototyps.
"""

import math
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Literal

from hekmatki.general.env import Transition
from hekmatki.general.knowledge import Knowledge, Slot
from hekmatki.general.programs import Program, fits
from hekmatki.general.synthesis import Example, Found, description_bits

WINDOW: Final = 20
"""So viele letzte Schritte zählen für den Test (von Hand gewählt, ohne Grundlage)."""
TAIL_LIMIT: Final = 1e-5
"""Unwahrscheinlicher als das ist unerwartet (von Hand gewählt, ohne Grundlage)."""
DOUBT: Final = 0.85
"""Lag eine Regel daneben, die mindestens so oft stimmt, lernt die Karte vorerst nicht daraus."""
RELIABLE: Final = 0.75
"""Ab dieser Trefferquote gilt eine Regel als verlässlich (für „jede Überraschung“)."""
HAZARD: Final = 1 / 1000
"""Vorab erwartete Häufigkeit eines Weltwechsels je Schritt (Wechselrate wie bei Adams &
MacKay 2007; der Wert ist von Hand gewählt, ohne Grundlage). Ein Wechsel kostet daher
vorab log2((1 − h) / h) ≈ 10 Bit."""
CHANGE_BITS: Final = math.log2((1 - HAZARD) / HAZARD)
BF_BITS: Final = 5.0 / math.log(2.0)
"""So viele Bits kürzer muss eine Erklärung sein, damit sie gilt: 2·ln B ≥ 10, „sehr stark“
nach Kass & Raftery 1995 (B ≈ 148, also etwa 7,2 Bits)."""


class Strategy(StrEnum):
    """Wie der Agent auf Überraschung reagiert."""

    EVERY = "jede Überraschung"
    NEVER = "nie neue Karte"
    EXPECTED = "erwartet / unerwartet"
    BAYES = "Bayes-Faktor"


type Kind = Literal["neu", "zurück", "umlernen", "verfeinern"]


@dataclass(frozen=True)
class Decision:
    """Was der Agent mit seinen Karten tut."""

    kind: Kind
    target: int
    """Index der Karte, die danach gilt (bei „neu“: die nächste freie Stelle)."""
    refined: dict[Slot, Found] = field(default_factory=dict)
    """Bei „verfeinern“: die verbesserten Regeln."""


def binomial_tail(misses: int, uses: int, miss_rate: float) -> float:
    """Wahrscheinlichkeit, mindestens `misses` Fehler in `uses` Versuchen zu sehen."""
    return sum(
        math.comb(uses, k) * miss_rate**k * (1.0 - miss_rate) ** (uses - k)
        for k in range(misses, uses + 1)
    )


def tails(knowledge: Knowledge, transitions: Sequence[Transition]) -> dict[Slot, float]:
    """Je Regel mit Fehlern: wie unwahrscheinlich so viele Fehler bei ihrer Quote sind."""
    misses: defaultdict[Slot, int] = defaultdict(int)
    uses: defaultdict[Slot, int] = defaultdict(int)
    reliability: dict[Slot, float] = {}
    for transition in transitions:
        for check in knowledge.checks(transition):
            uses[check.slot] += 1
            misses[check.slot] += not check.hit
            reliability[check.slot] = check.reliability
    return {
        slot: binomial_tail(misses[slot], uses[slot], 1.0 - reliability[slot])
        for slot in uses
        if misses[slot]
    }


def smallest_tail(knowledge: Knowledge, transitions: Sequence[Transition]) -> float:
    """Wie unwahrscheinlich die Fehler der auffälligsten Regel sind (1: alles wie erwartet)."""
    return min(tails(knowledge, transitions).values(), default=1.0)


def log_likelihood(knowledge: Knowledge, transitions: Sequence[Transition]) -> float:
    """Wie gut die Karte die Schritte erklärt (natürlicher Logarithmus)."""
    return sum(
        math.log(check.reliability if check.hit else 1.0 - check.reliability)
        for transition in transitions
        for check in knowledge.checks(transition)
    )


def _since_change(
    knowledge: Knowledge, slots: Sequence[Slot], window: Sequence[Transition]
) -> list[Transition]:
    """Die Schritte ab dem ersten Fehler einer auffälligen Regel: vermutlich schon die neue
    Welt. Nur an ihnen werden die anderen Karten geprüft."""
    for index, transition in enumerate(window):
        if any(not c.hit and c.slot in slots for c in knowledge.checks(transition)):
            return list(window[index:])
    return list(window)


class Detector:
    """Entscheidet nach jedem Schritt, ob die jetzige Karte noch gilt."""

    def __init__(self, strategy: Strategy, window: int = WINDOW, limit: float = TAIL_LIMIT) -> None:
        self.strategy, self.limit, self.window = strategy, limit, window
        self.recent: deque[Transition] = deque(maxlen=window)
        self.history: list[float] = []
        """Kleinste Wahrscheinlichkeit der jeweils geltenden Karte nach jedem Schritt."""
        self.evidence: list[Transition] = []
        """Nur beim Bayes-Faktor: alle Schritte seit der Änderung, bis entschieden ist."""
        self.suspects: set[Slot] = set()
        """Nur beim Bayes-Faktor: die Regeln, die seither unerwartet danebenlagen."""

    def judge(
        self, maps: Sequence[Knowledge], current: int, transition: Transition
    ) -> Decision | None:
        """None heißt: Die Karte gilt weiter."""
        self.recent.append(transition)
        decision = self._decide(maps, current, transition)
        if decision is not None:
            self.recent.clear()
        return decision

    @property
    def deciding(self) -> bool:
        """Sammelt er gerade Belege, ob sich die Welt geändert hat? Solange lernt die Karte
        nicht aus den Schritten, an denen sie zweifelt."""
        return bool(self.evidence)

    def doubts(self, knowledge: Knowledge, transition: Transition) -> bool:
        """Lag eine sonst sichere Regel daneben? Dann lernt die Karte vorerst nicht daraus.

        Sonst würde die alte Karte von der neuen Umgebung verdorben, bevor der Wechsel erkannt
        ist. Gelernt wird später: von der neuen Karte, oder von der alten, wenn es doch nur
        Rauschen war (Zuordnung zu einer verborgenen Ursache, Gershman 2017).
        """
        if self.strategy is Strategy.EVERY:
            return False
        return any(not c.hit and c.reliability >= DOUBT for c in knowledge.checks(transition))

    def _decide(
        self, maps: Sequence[Knowledge], current: int, transition: Transition
    ) -> Decision | None:
        if self.strategy is Strategy.EVERY:
            return self._every(maps, current, transition)
        window = list(self.recent)
        by_slot = tails(maps[current], window)
        self.history.append(min(by_slot.values(), default=1.0))
        unexpected = [slot for slot, tail in by_slot.items() if tail < self.limit]
        if self.strategy is Strategy.BAYES:
            return self._bayes(maps, current, unexpected, window)
        if not unexpected:
            return None
        refined = self._refine(maps[current], unexpected, window)
        if refined is not None:
            return Decision("verfeinern", current, refined)
        if self.strategy is Strategy.NEVER:
            return Decision("umlernen", current)
        since = _since_change(maps[current], unexpected, window)
        fitting = [
            (log_likelihood(knowledge, since), index)
            for index, knowledge in enumerate(maps)
            if index != current
            and knowledge.rules.found
            and smallest_tail(knowledge, since) >= self.limit
        ]
        if fitting:
            return Decision("zurück", max(fitting)[1])
        return Decision("neu", len(maps))

    def _bayes(
        self,
        maps: Sequence[Knowledge],
        current: int,
        unexpected: Sequence[Slot],
        window: Sequence[Transition],
    ) -> Decision | None:
        """Dieselbe Welt, eine alte Karte oder eine neue: Welche sagt die Schritte seit der
        Änderung am besten voraus? Gewechselt wird, wenn eine andere Karte um mindestens
        `BF_BITS` besser ist als die jetzige.

        Gemessen wird in Bits Vorhersage-Verlust: Jede Regel sagt mit ihrer bisherigen
        Trefferquote voraus; ein Treffer einer sicheren Regel kostet fast nichts, ein Fehler
        viel. Ein Wechsel kostet vorab `CHANGE_BITS`, weil Welten selten wechseln. Wie bei
        Walds sequentiellem Test sammelt er ab der ersten unerwarteten
        Überraschung alle Schritte, bis eine Seite klar gewinnt, statt nur ein festes Fenster
        anzusehen. Gewinnt die jetzige Karte klar, verfeinert er die auffälligen Regeln, falls
        das geht (wie bei „erwartet / unerwartet“), oder hört auf zu sammeln, sobald die
        Überraschung vorbei ist.
        """
        here = maps[current]
        if self.evidence:
            self.evidence.append(window[-1])
        elif unexpected:
            self.evidence = _since_change(here, unexpected, window)
        else:
            return None
        self.suspects.update(unexpected)
        judged = _judged(here, self.evidence)
        stay = _map_bits(here, judged, self.evidence)
        options = [
            (CHANGE_BITS + _map_bits(knowledge, judged, self.evidence), Decision("zurück", index))
            for index, knowledge in enumerate(maps)
            if index != current and knowledge.rules.found
        ]
        new = CHANGE_BITS + _new_bits(here, judged, self.evidence)
        options.append((new, Decision("neu", len(maps))))
        elsewhere, decision = min(options, key=lambda option: option[0])
        if stay - elsewhere >= BF_BITS:
            return self._settle(decision)
        if elsewhere - stay < BF_BITS:
            return None  # Noch nicht klar: weiter sammeln.
        refined = self._refine(here, sorted(self.suspects), self.evidence)
        if refined is not None:
            return self._settle(Decision("verfeinern", current, refined))
        if not unexpected:
            return self._settle(None)  # Dieselbe Welt, die Überraschung ist vorbei: Rauschen.
        return None

    def _settle(self, decision: Decision | None) -> Decision | None:
        self.evidence, self.suspects = [], set()
        return decision

    def _refine(
        self, knowledge: Knowledge, slots: Sequence[Slot], window: Sequence[Transition]
    ) -> dict[Slot, Found] | None:
        """Erklären sich die auffälligen Regeln ohne neue Welt? Für jede Regel drei Fälle:

        1. Eine verfeinerte Regel erklärt alte und neue Schritte: verfeinern.
        2. Eine andere Regel erklärt allein die neuen Schritte gut: Hinweis auf eine andere
           Welt (None).
        3. Keine Regel erklärt die neuen Schritte: Die Größe ist hier nicht vorhersagbar, die
           Regel wird fallen gelassen. Das ist keine neue Welt, nur ein Irrtum über sie.
        """
        refined = {}
        for slot in slots:
            extra = [Example(t.before, t.after) for t in window if t.action == slot[0]]
            better = knowledge.rules.refine(slot, extra)
            if better is not None:
                refined[slot] = better
            elif knowledge.rules.fit_alone(slot, extra) is not None:
                return None
            else:
                refined[slot] = Found(None, 0, len(extra), 0)
        return refined

    def _every(
        self, maps: Sequence[Knowledge], current: int, transition: Transition
    ) -> Decision | None:
        def missed(knowledge: Knowledge) -> bool:
            checks = knowledge.checks(transition)
            return any(not c.hit and c.reliability >= RELIABLE for c in checks)

        if not missed(maps[current]):
            return None
        fitting = [
            i for i, k in enumerate(maps) if i != current and k.rules.found and not missed(k)
        ]
        return Decision("zurück", fitting[0]) if fitting else Decision("neu", len(maps))


def _examples(slot: Slot, transitions: Sequence[Transition]) -> list[Example]:
    return [Example(t.before, t.after) for t in transitions if t.action == slot[0]]


def _judged(knowledge: Knowledge, since: Sequence[Transition]) -> list[Slot]:
    """Alle Regeln der Karte, die zu den Schritten seit der Änderung etwas voraussagen."""
    actions = {t.action for t in since}
    return [
        slot
        for slot, found in sorted(knowledge.rules.found.items())
        if slot[0] in actions and found.program is not None
    ]


def _map_bits(knowledge: Knowledge, slots: Sequence[Slot], since: Sequence[Transition]) -> float:
    """Vorhersage-Verlust einer Karte in Bits: je Regel und Schritt −log2 der Wahrscheinlichkeit,
    die sie dem Gesehenen gab. Fehlt der Karte eine Regel, zählt jeder Schritt ein Bit."""
    total = 0.0
    for slot in slots:
        examples = _examples(slot, since)
        found = knowledge.rules.found.get(slot)
        if found is None or found.program is None:
            total += len(examples)
            continue
        total += _loss(found.program, found.reliability, slot, examples)
    return total


def _loss(program: Program, reliability: float, slot: Slot, examples: Sequence[Example]) -> float:
    hits = sum(fits(program, e.before, e.after, slot[1]) for e in examples)
    misses = len(examples) - hits
    return -hits * math.log2(reliability) - misses * math.log2(1.0 - reliability)


def _new_bits(knowledge: Knowledge, slots: Sequence[Slot], since: Sequence[Transition]) -> float:
    """Vorhersage-Verlust einer neuen Karte in Bits.

    Die neue Karte wird als Abwandlung der jetzigen beschrieben: welche k Regeln neu sind
    (log2 der Zahl solcher Auswahlen, plus k selbst), die neuen Regeln (4 Bit je Baustein)
    und ihr Verlust an Schritten, aus denen sie nicht gelernt wurden (`_unseen_loss`).
    Gewählt wird das k mit dem kleinsten Verlust."""
    kept_total = 0.0
    savings = []
    for slot in slots:
        examples = _examples(slot, since)
        found = knowledge.rules.found.get(slot)
        kept = (
            float(len(examples))
            if found is None or found.program is None
            else _loss(found.program, found.reliability, slot, examples)
        )
        rule = knowledge.rules.search(examples, slot[1]).program
        fresh = description_bits(rule, 0, len(examples)) + _unseen_loss(knowledge, slot, examples)
        kept_total += kept
        savings.append(kept - fresh)
    savings.sort(reverse=True)
    count = len(savings)
    best, saved = kept_total + math.log2(count + 1), 0.0
    for changed in range(1, count + 1):
        saved += savings[changed - 1]
        which = math.log2(count + 1) + math.log2(math.comb(count, changed))
        best = min(best, kept_total - saved + which)
    return best


def _unseen_loss(knowledge: Knowledge, slot: Slot, examples: Sequence[Example]) -> float:
    """Verlust einer neuen Regel an Schritten, die sie nicht kannte: aus jedem zweiten Schritt
    lernen, an den anderen vorhersagen, und umgekehrt. Das ist eine billige Form der
    prequentiellen Wertung (Dawid 1984): Eine Regel aus wenigen Schritten ist unsicher, und
    eine, die nur deren Rauschen nachbildet, sagt die übrigen schlecht voraus."""
    halves = (examples[0::2], examples[1::2])
    total = 0.0
    for learn, check in (halves, halves[::-1]):
        found = knowledge.rules.search(learn, slot[1]) if learn else None
        if found is None or found.program is None:
            total += len(check)
        else:
            total += _loss(found.program, found.reliability, slot, check)
    return total
