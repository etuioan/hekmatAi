"""Die simulierte Welt: Alltagssituationen, die Beobachtungsfolgen erzeugen.

Jede Situation besteht aus einer Struktur (Übergänge zwischen Rollen) und einem Inhalt
(welches konkrete Symbol zu jeder Rolle gehört). Ähnliche Situationen teilen die Struktur.
"""

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass

RoleTransitions = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class Situation:
    """Eine Alltagssituation mit bekannter, wahrer Dynamik."""

    name: str
    transitions: RoleTransitions
    symbols: Mapping[str, str]
    action_role: str | None = None
    """Die Rolle, in der eigenes Handeln gelingt (`None`: nirgends). Weiß nur die Welt."""

    def __post_init__(self) -> None:
        roles = set(self.transitions)
        if roles != set(self.symbols):
            raise ValueError(
                f"{self.name}: Rollen in Übergängen und Symbolen stimmen nicht überein."
            )
        if self.action_role is not None and self.action_role not in roles:
            raise ValueError(f"{self.name}: Unbekannte Handlungsrolle {self.action_role!r}.")
        if len(set(self.symbols.values())) != len(self.symbols):
            raise ValueError(f"{self.name}: Jede Rolle braucht ein eigenes Symbol.")
        for role, row in self.transitions.items():
            unknown = set(row) - roles
            if unknown:
                raise ValueError(
                    f"{self.name}: Rolle {role!r} führt zu unbekannten Rollen {unknown}."
                )
            if any(p < 0.0 for p in row.values()):
                raise ValueError(f"{self.name}: Negative Wahrscheinlichkeit in Rolle {role!r}.")
            if not math.isclose(sum(row.values()), 1.0):
                raise ValueError(f"{self.name}: Übergänge aus {role!r} ergeben nicht 1.")

    @property
    def alphabet(self) -> tuple[str, ...]:
        """Alle Symbole dieser Situation, sortiert."""
        return tuple(sorted(self.symbols.values()))

    @property
    def action_symbols(self) -> tuple[str, ...]:
        """Die Symbole, in denen eigenes Handeln gelingt (leer, wenn nirgends)."""
        return () if self.action_role is None else (self.symbols[self.action_role],)

    def probability(self, previous: str, following: str) -> float:
        """Wahre Übergangswahrscheinlichkeit zwischen zwei Symbolen."""
        role_of = {symbol: role for role, symbol in self.symbols.items()}
        if previous not in role_of or following not in role_of:
            raise ValueError(f"{self.name}: unbekanntes Symbol in ({previous!r}, {following!r}).")
        return self.transitions[role_of[previous]].get(role_of[following], 0.0)

    def sample(self, length: int, rng: random.Random, start: str | None = None) -> list[str]:
        """Erzeugt eine Beobachtungsfolge der Länge `length`.

        Ohne `start` beginnt sie in einer zufälligen Rolle, sonst mit dem Symbol `start`.
        """
        if length < 1:
            raise ValueError(f"Die Länge muss mindestens 1 sein, war {length}.")
        role_of = {symbol: role for role, symbol in self.symbols.items()}
        if start is not None and start not in role_of:
            raise ValueError(f"{self.name}: Startsymbol {start!r} gehört nicht zur Situation.")
        role = rng.choice(sorted(self.transitions)) if start is None else role_of[start]
        sequence = [self.symbols[role]]
        for _ in range(length - 1):
            targets = sorted(self.transitions[role])
            weights = [self.transitions[role][t] for t in targets]
            role = rng.choices(targets, weights=weights)[0]
            sequence.append(self.symbols[role])
        return sequence


def _waiting_structure(stay: float) -> dict[str, dict[str, float]]:
    """Gemeinsame Struktur jeder Wartesituation. `stay` = wie lange man sich beschäftigt."""
    return {
        "beschäftigen": {"beschäftigen": stay, "hinweis": 1.0 - stay},
        "hinweis": {"hinweis": 0.2, "ereignis": 0.8},
        "ereignis": {"weitergehen": 1.0},
        "weitergehen": {"beschäftigen": 1.0},
    }


WAITING_ACTION_ROLE = "ereignis"
"""In jeder Wartesituation gelingt eigenes Handeln (weitergehen) genau beim Ereignis,
etwa einsteigen, wenn die Bahn einfährt. Das weiß nur die Welt, nicht der Agent."""


GATE_SYMBOLS = {
    "beschäftigen": "kaffee trinken",
    "hinweis": "boarding-durchsage",
    "ereignis": "bordkarte scannen",
    "weitergehen": "ins flugzeug",
}


def waiting_situations() -> dict[str, Situation]:
    """Drei Wartesituationen mit gleicher Struktur und verschiedenen Symbolen."""
    return {
        "arzt": Situation(
            name="Warten beim Arzt",
            transitions=_waiting_structure(stay=0.85),
            symbols={
                "beschäftigen": "zeitschrift lesen",
                "hinweis": "name aufgerufen",
                "ereignis": "ins behandlungszimmer",
                "weitergehen": "rezept abholen",
            },
            action_role=WAITING_ACTION_ROLE,
        ),
        "ubahn": Situation(
            name="Warten auf die U-Bahn",
            transitions=_waiting_structure(stay=0.6),
            symbols={
                "beschäftigen": "aufs handy schauen",
                "hinweis": "anzeige 1 min",
                "ereignis": "bahn fährt ein",
                "weitergehen": "einsteigen",
            },
            action_role=WAITING_ACTION_ROLE,
        ),
        "gate": Situation(
            name="Warten am Flughafen-Gate",
            transitions=_waiting_structure(stay=0.75),
            symbols=GATE_SYMBOLS,
            action_role=WAITING_ACTION_ROLE,
        ),
    }


def gate_stress_variants() -> dict[str, Situation]:
    """Gate-Situationen, die vom gelernten Schema „Warten“ unterschiedlich stark abweichen."""
    return {
        "normal": Situation("Gate: normal", _waiting_structure(stay=0.75), GATE_SYMBOLS),
        "sehr lang": Situation("Gate: Verspätung", _waiting_structure(stay=0.97), GATE_SYMBOLS),
        "sehr kurz": Situation("Gate: sofort Boarding", _waiting_structure(stay=0.3), GATE_SYMBOLS),
        "gestört": Situation(
            "Gate: mit Störungen",
            with_disturbances(_waiting_structure(stay=0.75), share=0.2),
            GATE_SYMBOLS,
        ),
    }


def with_disturbances(transitions: RoleTransitions, share: float) -> dict[str, dict[str, float]]:
    """Mischt jedem Übergang einen Anteil `share` zufälliger Sprünge bei.

    So entstehen unerwartete Ereignisse, etwa eine Durchsage, die gar nicht zum Boarding führt.
    """
    if not 0.0 <= share <= 1.0:
        raise ValueError(f"Der Störanteil muss zwischen 0 und 1 liegen, war {share}.")
    roles = sorted(transitions)
    uniform = share / len(roles)
    return {
        role: {t: (1.0 - share) * transitions[role].get(t, 0.0) + uniform for t in roles}
        for role in roles
    }


def _conversation_structure() -> dict[str, dict[str, float]]:
    """Gemeinsame Struktur jedes Gesprächs: Frage, Antwort, Zustimmung, neues Thema."""
    return {
        "frage": {"antwort": 0.9, "frage": 0.1},
        "antwort": {"zustimmung": 0.8, "frage": 0.2},
        "zustimmung": {"frage": 0.7, "neues thema": 0.3},
        "neues thema": {"frage": 1.0},
    }


def conversation_situations() -> dict[str, Situation]:
    """Zwei Gespräche mit gleicher Struktur und verschiedenen Symbolen."""
    return {
        "nachbar": Situation(
            name="Gespräch mit dem Nachbarn",
            transitions=_conversation_structure(),
            symbols={
                "frage": "wie gehts",
                "antwort": "gut danke",
                "zustimmung": "ja genau",
                "neues thema": "übrigens",
            },
        ),
        "kollege": Situation(
            name="Gespräch mit der Kollegin",
            transitions=_conversation_structure(),
            symbols={
                "frage": "hast du kurz zeit",
                "antwort": "klar",
                "zustimmung": "stimmt",
                "neues thema": "noch was anderes",
            },
        ),
    }


def _queue_structure() -> dict[str, dict[str, float]]:
    """Gemeinsame Struktur jedes Anstehens: anstellen, vorrücken, dran sein, bezahlen.

    Ähnlich wie Warten (man wartet, bis man dran ist), aber mit anderen Zeiten: Das
    Vorrücken dauert, und nach dem Dransein bleibt man noch eine Weile beim Bezahlen.
    """
    return {
        "anstellen": {"anstellen": 0.3, "vorrücken": 0.7},
        "vorrücken": {"vorrücken": 0.6, "dran sein": 0.4},
        "dran sein": {"bezahlen": 1.0},
        "bezahlen": {"bezahlen": 0.5, "anstellen": 0.5},
    }


QUEUE_ACTION_ROLE = "dran sein"
"""Beim Anstehen gelingt eigenes Handeln (bestellen) genau, wenn man dran ist."""


def queue_situations() -> dict[str, Situation]:
    """Drei Situationen zum Anstehen mit gleicher Struktur und verschiedenen Symbolen."""

    def queue(name: str, join: str, advance: str, turn: str, pay: str) -> Situation:
        return Situation(
            name=name,
            transitions=_queue_structure(),
            symbols={"anstellen": join, "vorrücken": advance, "dran sein": turn, "bezahlen": pay},
            action_role=QUEUE_ACTION_ROLE,
        )

    return {
        "bäcker": queue(
            "Anstehen beim Bäcker", "nummer ziehen", "brote anschauen", "bestellen", "brot zahlen"
        ),
        "post": queue(
            "Anstehen bei der Post",
            "in die schlange",
            "paket halten",
            "schalter frei",
            "porto zahlen",
        ),
        "kantine": queue(
            "Anstehen in der Kantine",
            "tablett nehmen",
            "vorrutschen",
            "essen wählen",
            "an der kasse",
        ),
    }


def small_talk() -> Situation:
    """Eine Situation ohne Wartestruktur: jedes Thema folgt gleich wahrscheinlich auf jedes."""
    topics = ("wetter", "urlaub", "arbeit", "familie")
    return Situation(
        name="Plaudern",
        transitions={t: dict.fromkeys(topics, 0.25) for t in topics},
        symbols={t: t for t in topics},
    )


def commuting_situations() -> dict[str, Situation]:
    """Hin- und Rückweg: gleiche Symbole, aber widersprüchliche Übergänge."""
    symbols = {s: s for s in ("zuhause", "haltestelle", "bahn", "arbeit")}
    return {
        "hinweg": Situation(
            name="Pendeln: Hinweg",
            transitions={
                "zuhause": {"haltestelle": 1.0},
                "haltestelle": {"haltestelle": 0.5, "bahn": 0.5},
                "bahn": {"bahn": 0.3, "arbeit": 0.7},
                "arbeit": {"zuhause": 1.0},
            },
            symbols=symbols,
        ),
        "rueckweg": Situation(
            name="Pendeln: Rückweg",
            transitions={
                "arbeit": {"haltestelle": 1.0},
                "haltestelle": {"haltestelle": 0.5, "bahn": 0.5},
                "bahn": {"bahn": 0.3, "zuhause": 0.7},
                "zuhause": {"arbeit": 1.0},
            },
            symbols=symbols,
        ),
    }


def lamp_situations() -> dict[str, Situation]:
    """Vier Wartesituationen, die dieselben vier Lampen zeigen, aber mit anderer Bedeutung.

    Der Agent sieht nur Farben. Was eine Farbe bedeutet (z. B. „Hinweis“ oder „Ereignis“),
    hängt vom Ort ab. Er muss also am Ablauf erkennen, wo er ist.
    """

    def lamps(busy: str, hint: str, event: str, leave: str) -> dict[str, str]:
        return {"beschäftigen": busy, "hinweis": hint, "ereignis": event, "weitergehen": leave}

    return {
        "arzt": Situation(
            "Lampen: Arzt", _waiting_structure(stay=0.85), lamps("rot", "grün", "blau", "gelb")
        ),
        "ubahn": Situation(
            "Lampen: U-Bahn", _waiting_structure(stay=0.6), lamps("blau", "rot", "gelb", "grün")
        ),
        "gate": Situation(
            "Lampen: Gate", _waiting_structure(stay=0.75), lamps("gelb", "blau", "grün", "rot")
        ),
        "kasse": Situation(
            "Lampen: Kasse", _waiting_structure(stay=0.7), lamps("grün", "gelb", "rot", "blau")
        ),
    }


def lamp_conversations() -> dict[str, Situation]:
    """Drei Gespräche mit denselben vier Lampen wie `lamp_situations`, aber Gesprächsstruktur.

    Sie passen nicht zum Schema „Warten“ und brauchen deshalb ein eigenes Schema.
    """

    def lamps(question: str, answer: str, agree: str, topic: str) -> dict[str, str]:
        return {"frage": question, "antwort": answer, "zustimmung": agree, "neues thema": topic}

    structure = _conversation_structure()
    return {
        "nachbar": Situation("Lampen: Nachbar", structure, lamps("rot", "grün", "gelb", "blau")),
        "kollege": Situation("Lampen: Kollegin", structure, lamps("gelb", "blau", "rot", "grün")),
        "freund": Situation("Lampen: Freund", structure, lamps("grün", "rot", "blau", "gelb")),
    }
