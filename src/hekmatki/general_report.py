"""Ausgabe der Experimente zum allgemeinen Agenten (ab 0.16), auf Deutsch.

Eigenes Modul, damit `__main__` nicht weiter wächst. Aufgerufen von `__main__.main`.
"""

from collections.abc import Sequence

from hekmatki.experiments.general_worlds import AGENTS, TEST_LIMIT, WorldRow
from hekmatki.experiments.library_transfer import (
    BUDGET,
    BUDGETED,
    CONDITIONS,
    EntryRow,
    LibraryRow,
)
from hekmatki.experiments.new_world import HANDLINGS, PHASES, NewWorldRow


def print_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    """Eine Tabelle: erste Spalte links-, alle anderen rechtsbündig."""
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]

    def line(cells: Sequence[str]) -> str:
        first = f"{cells[0]:<{widths[0]}}"
        rest = [f"{c:>{w}}" for c, w in zip(cells[1:], widths[1:], strict=True)]
        return " | ".join([first, *rest])

    print(line(headers))
    print("-" * len(line(headers)))
    for row in rows:
        print(line(row))
    print()


def report_general_worlds(rows: Sequence[WorldRow]) -> None:
    """Ergebnis 17: ein Agent, drei Welten."""
    print("\nEin Agent, drei Welten (H19). Derselbe Code, nur Zahlen und Tasten, gemischt.")
    print("Lehrplan: kleine Räume / Suchbäume, dann Prüfung in der großen Welt (5 Runden).")
    print(f"Schritte bis zum Ziel in der Prüfung, nicht erreicht zählt als {TEST_LIMIT}.\n")
    headers = ["Welt", "Größe", *AGENTS, "bestenfalls"]
    print_table(
        headers,
        [[r.world, r.size, *(f"{r.steps[a]:.1f}" for a in AGENTS), f"{r.best:.1f}"] for r in rows],
    )
    print("Ziel erreicht (% der Prüfrunden):\n")
    print_table(
        ["Welt", *AGENTS],
        [[r.world, *(f"{100 * r.reached[a]:.0f}" for a in AGENTS)] for r in rows],
    )
    print("Form, die der Agent selbst gefunden hat:\n")
    print_table(
        ["Welt", "richtige Form gefunden", "Formen (je Lauf)"],
        [[r.world, f"{100 * r.form_found:.0f} %", _counted(r.forms)] for r in rows],
    )


def report_library(rows: Sequence[LibraryRow], entries: Sequence[EntryRow]) -> None:
    """Ergebnis 18: die Bibliothek über Welten hinweg."""
    print("Bibliothek über Welten (H20). Geprüfte Programme: erst nur die Suchen mit Erfolg")
    print("(Größen mit einer Regel ohne Ausnahme; in Klammern: davon Regeln aus der")
    print("Bibliothek), dann alle Suchen, auch die vergeblichen nach unvorhersagbaren Größen.")
    print("Zufallsbibliothek = zwei Zufallsmuster gleicher Länge, die nie entfernt werden.\n")
    print("Suchen mit Erfolg:\n")
    print_table(
        ["Reihenfolge", "Welt", *CONDITIONS],
        [
            [
                r.order,
                r.world,
                *(f"{r.tested_found[c]:.0f} ({r.borrowed[c]:.1f})" for c in CONDITIONS),
            ]
            for r in rows
        ],
    )
    print("Alle Suchen:\n")
    print_table(
        ["Reihenfolge", "Welt", *CONDITIONS],
        [[r.order, r.world, *(f"{r.tested[c]:.0f}" for c in CONDITIONS)] for r in rows],
    )
    print(f"Gleiches Budget: höchstens {BUDGET} Programme je Regelsuche. Ziel erreicht (%):\n")
    print_table(
        ["Reihenfolge", "Welt", *BUDGETED],
        [[r.order, r.world, *(f"{100 * r.budget_reached[c]:.0f}" for c in BUDGETED)] for r in rows],
    )
    print("Einträge am Ende (erster Lauf jeder Reihenfolge):\n")
    print_table(
        ["Reihenfolge", "Eintrag", "Muster", "aus", "genutzt in", "Stand"],
        [
            [
                e.order,
                e.name,
                e.pattern,
                e.origin,
                ", ".join(f"{w}: {n}" for w, n in e.reuses.items()) or "nirgends",
                "entfernt" if e.removed else "behalten",
            ]
            for e in entries
        ],
    )


def report_new_world(rows: Sequence[NewWorldRow]) -> None:
    """Ergebnis 19: eine neue Umgebung erkennen."""
    print("Neue Umgebung erkennen (H18). Rutschiger Raum A (jeder 10. Schritt geht nicht),")
    print("dann B (Tasten vertauscht), dann wieder A. 15 Runden je Phase.\n")
    print("Mittlere Schritte je Runde (in Klammern: die ersten drei Runden der Phase):\n")
    print_table(
        ["Umgang", *PHASES],
        [
            [r.handling, *(f"{r.steps[p]:.1f} ({r.first_steps[p]:.0f})" for p in PHASES)]
            for r in rows
        ],
    )
    print_table(
        ["Umgang", "Karten", "Fehlalarme in A", "B erkannt", "alte Karte wieder"],
        [
            [
                r.handling,
                f"{r.maps:.1f}",
                f"{r.false_alarms:.1f}",
                f"{100 * r.detected_b:.0f} %",
                f"{100 * r.returned:.0f} %",
            ]
            for r in rows
        ],
    )
    print("B erkannt = Kartenwechsel in den ersten 30 Schritten von B. Alte Karte wieder =")
    print(
        f"der erste Wechsel in „A wieder“ führt zur ersten Karte zurück. ({len(HANDLINGS)} Umgänge)"
    )


def _counted(forms: Sequence[str]) -> str:
    counts: dict[str, int] = {}
    for form in forms:
        counts[form] = counts.get(form, 0) + 1
    return ", ".join(f"{form} ×{n}" for form, n in counts.items())
