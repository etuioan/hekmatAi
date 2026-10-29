"""Startet alle Experimente und gibt die Ergebnisse auf Deutsch aus.

Aufruf: `PYTHONPATH=src python -m hekmatki`
"""

from collections.abc import Mapping, Sequence
from statistics import mean
from typing import Protocol

from hekmatki.experiments import (
    CombinedRow,
    DiscoveryResult,
    ExplorationResult,
    GameResult,
    H11Result,
    H12Result,
    MetaRow,
    MultiSchemaRow,
    RecognitionRow,
    StressRow,
    TransferResult,
    TransferRow,
    WakeSleepRow,
    run_combined,
    run_discovery,
    run_exploration,
    run_h11,
    run_h11_stress,
    run_h12,
    run_meta_schema,
    run_multi_schema,
    run_recognition,
    run_rule_transfer,
    run_traffic_light_game,
    run_wake_sleep,
)
from hekmatki.experiments.cross_world import HANDLINGS, CrossRow, compare_worlds
from hekmatki.experiments.exploration import HorizonResult, TrustRow, total_wins
from hekmatki.experiments.general_worlds import run_general_worlds
from hekmatki.experiments.grid_foreign import LEARNERS as FOREIGN_LEARNERS
from hekmatki.experiments.grid_foreign import ForeignRow, run_foreign
from hekmatki.experiments.grid_mechanics import LEARNERS as MECHANICS_LEARNERS
from hekmatki.experiments.grid_mechanics import (
    ClassicRow,
    MechanicsRow,
    run_classic_check,
    run_mechanics,
)
from hekmatki.experiments.grid_roles import LEARNERS as ROLE_LEARNERS
from hekmatki.experiments.grid_roles import RoleRow, run_roles
from hekmatki.experiments.grid_transfer import LEARNERS, GridRow, run_grid_transfer
from hekmatki.experiments.library_transfer import run_library_transfer
from hekmatki.experiments.new_world import run_new_world
from hekmatki.experiments.rule_transfer import KNOWLEDGE, Knowledge
from hekmatki.general_report import report_general_worlds, report_library, report_new_world


class _LevelRow(Protocol):
    @property
    def level(self) -> str: ...

    @property
    def size(self) -> int: ...


VALUE_EXPLANATION = (
    "Werte: typische Wahrscheinlichkeit (geometrisches Mittel) für das tatsächlich folgende Symbol."
)


def _report_h11(result: H11Result) -> None:
    print("Experiment H11: Lernt der Agent eine neue Wartesituation schneller mit Schema?")
    print("Neue Situation: Warten am Flughafen-Gate. Schema aus Arzt + U-Bahn.\n")
    print(f"{'Beobachtungen':>13} | {'ohne Schema':>11} | {'mit Schema':>10} | {'Optimum':>7}")
    print("-" * 52)
    for row in result.rows:
        values = f"{row.flat:>11.3f} | {row.schema:>10.3f} | {row.optimum:>7.3f}"
        print(f"{row.observations:>13} | {values}")
    print(f"\n{VALUE_EXPLANATION}")
    print(f"Strukturabstand Arzt ↔ U-Bahn:  {result.waiting_distance:.3f} (verschmolzen)")
    merged_text = (
        "verschmolzen, FEHLER" if result.small_talk_merged else "nicht verschmolzen, richtig"
    )
    print(f"Strukturabstand Arzt ↔ Plaudern: {result.small_talk_distance:.3f} ({merged_text})\n")


def _report_stress(rows: list[StressRow]) -> None:
    print("Härtetest H11: Gate-Situationen, die vom Schema abweichen oder gestört sind.")
    print("ohne    = kein Schema, nur eigene Beobachtungen")
    print("starr   = Schema wird unverändert übernommen")
    print("lernend = Schema ist Vorwissen und wird durch Beobachtungen korrigiert")
    print("geprüft = wie lernend, aber der Agent prüft, ob das Schema überhaupt passt\n")
    columns = ("Variante", "Beob.", "ohne", "starr", "lernend", "geprüft", "Opt.")
    header = " | ".join(f"{c:>8}" for c in columns)
    print(header)
    print("-" * len(header))
    for r in rows:
        values = (r.flat, r.fixed_schema, r.adaptive_schema, r.checked_schema, r.optimum)
        cells = [f"{r.variant:>8}", f"{r.observations:>8}", *(f"{v:>8.3f}" for v in values)]
        print(" | ".join(cells))
    print()


def _report_h12(result: H12Result) -> None:
    print("Experiment H12: Vergisst der Agent weniger mit Kontextwechsel?")
    print("Strom: Pendeln Hinweg und Rückweg im Wechsel, gleiche Symbole, andere Abläufe.\n")
    print(f"Ein gemeinsames Modell:    {result.single_model:.3f}")
    print(f"Mit Kontextinferenz:       {result.with_contexts:.3f}")
    print(f"Optimum:                   {result.optimum:.3f}")
    print(f"Gefundene Kontexte (Mittel): {result.contexts_found:.1f} (richtig wären 2)")
    print("\nWerte: erste 30 Schritte nach jeder Rückkehr in eine bekannte Situation.\n")


def _report_combined(rows: list[CombinedRow]) -> None:
    print("Kontextwechsel + Scheiben: Baut der Agent eine neue Situation aus dem Schema?")
    print("Drei Wartesituationen zeigen dieselben vier Lampen mit anderer Bedeutung.")
    print("Wach: Arzt und U-Bahn im Wechsel. Schlaf: eigene Kontexte zum Schema verschmelzen.")
    print("Wach: Gate (neu), Arzt, U-Bahn, Gate.\n")
    columns = ("Agent", "neue Situation", "bekannte", "Kontexte")
    print(f"{columns[0]:<18} | {columns[1]:>14} | {columns[2]:>8} | {columns[3]:>8}")
    print("-" * 57)
    for r in rows:
        found = "-" if r.contexts_found is None else f"{r.contexts_found:.2f}"
        values = f"{r.new_situation:>14.3f} | {r.known_situations:>8.3f} | {found:>8}"
        print(f"{r.agent:<18} | {values}")
    print("\nWerte: erste 30 Schritte jedes Blocks; „neue Situation“ = erstes Gate.")
    print("Richtig wären 3 Kontexte (Arzt, U-Bahn, Gate).\n")


def _report_wake_sleep(rows: list[WakeSleepRow]) -> None:
    print("Wach-Schlaf: Entscheidet der Agent selbst, wann er schläft?")
    print("Strom: Arzt, U-Bahn, Arzt, U-Bahn, Gate (neu), Arzt, Gate, Kasse (neu), U-Bahn, Kasse.")
    print("fester Schlaf  = schläft einmal nach den ersten vier Blöcken (wie Version 0.3)")
    print("eigener Schlaf = schläft, sobald ein Kontext 100 Übergänge erlebt hat\n")
    columns = ("Agent", "Gate neu", "Kasse neu", "bekannte", "Schlaf", "im Schema")
    print(f"{columns[0]:<15} | " + " | ".join(f"{c:>9}" for c in columns[1:]))
    print("-" * 77)
    for r in rows:
        scores = (r.new_gate, r.new_checkout, r.known_situations)
        counts = (r.sleeps, r.contexts_in_schema)
        cells = [
            *(f"{v:>9.3f}" for v in scores),
            *("        -" if c is None else f"{c:>9.2f}" for c in counts),
        ]
        print(f"{r.agent:<15} | " + " | ".join(cells))
    print(
        "\nWerte: erste 30 Schritte jedes Blocks. „im Schema“ = Kontexte, die ins Schema flossen.\n"
    )


def _report_multi_schema(rows: list[MultiSchemaRow]) -> None:
    print("Mehrere Schemata: Bildet der Agent für Warten und Gespräche je ein eigenes Schema?")
    print("Strom: Wartesituationen und Gespräche im Wechsel, alle mit denselben vier Lampen.")
    print("Neu im Strom: Gate (Warten) und Gespräch mit dem Freund.\n")
    columns = ("Agent", "Gate neu", "Freund neu", "bekannte", "Schemata")
    print(f"{columns[0]:<17} | " + " | ".join(f"{c:>10}" for c in columns[1:]))
    print("-" * 71)
    for r in rows:
        scores = (r.new_gate, r.new_friend, r.known_situations)
        count = "-" if r.schemas is None else f"{r.schemas:.2f}"
        cells = [*(f"{v:>10.3f}" for v in scores), f"{count:>10}"]
        print(f"{r.agent:<17} | " + " | ".join(cells))
    print("\nWerte: erste 30 Schritte jedes Blocks. Richtig wären 2 Schemata.\n")


def _report_game(result: GameResult) -> None:
    print("Ampelspiel: Findet der Agent „Warten“ als Schnittmenge, ohne zu verschmelzen?")
    print("Warten ist sicher, Laufen gewinnt nur bei Grün, sonst gibt es einen Unfall.")
    print("Der Agent kennt die Schemata „Warten“ und „Gespräch“ aus dem Alltag, samt dem")
    print("Handlungswissen, das er dort selbst durch Ausprobieren gelernt hat.\n")
    columns = ("Spieler", "Siege 1-10", "Siege 11-30", "Unfälle", "1. Sieg")
    print(f"{columns[0]:<15} | " + " | ".join(f"{c:>11}" for c in columns[1:]))
    print("-" * 70)
    for r in result.rows:
        rates = (f"{v:>11.0%}" for v in (r.early_win_rate, r.late_win_rate))
        cells = [*rates, f"{r.accidents:>11.1f}", f"{r.first_win:>11.1f}"]
        print(f"{r.player:<15} | " + " | ".join(cells))
    print("\nUnfälle pro Spiel mit 30 Runden; 1. Sieg = Runde des ersten Siegs.")
    print(
        f"Schnittmenge im Spiel gefunden: {result.found_during_game:.0%} der Läufe, "
        f"im Mittel nach Runde {result.found_in_round:.1f}"
    )
    print(f"Ohne Vorwissen, nach dem Spiel gefunden: {result.found_after_game:.0%} der Läufe")
    correct = f"{result.core_correct:.0%}"
    print(f"Davon richtig (Autos, Gelb, Grün = Beschäftigen, Hinweis, Ereignis): {correct}")
    print(f"„drüben“ als Weitergehen erkannt: {result.goal_as_continuation:.0%}")
    print("Spielmodell und Schemata bleiben getrennt; gespeichert wird nur die Zuordnung.")
    learned = ", ".join(f"{role} {p:.2f}" for role, p in result.learned_action.items())
    print(f"Gelernt im Alltag, Erfolg beim Handeln pro Rolle von „Warten“: {learned}")


def _report_meta_schema(rows: list[MetaRow]) -> None:
    print("\nDritte Ebene: Verdichtet der Agent Schemata zu einem Meta-Schema?")
    print("Erlebt: Warten (Arzt, U-Bahn), Anstehen (Bäcker, Post), Gespräch (Nachbar, Kollegin).")
    print("Schlaf: dieselbe Routine zweimal, Ebene 2 mit Schwellenwert 0,1, Ebene 3 mit 0,2.")
    print("Erwartet: drei Schemata, dann ein Meta-Schema aus Warten + Anstehen.\n")
    full = rows[-1]
    print(f"Nach {full.experience} Schritten pro Situation:\n")
    columns = ("Ebene", "Scheiben", "Gate", "Kantine")
    print(f"{columns[0]:<21} | " + " | ".join(f"{c:>8}" for c in columns[1:]))
    print("-" * 54)
    for layer, decisions in full.right_decisions.items():
        cells = [f"{full.slices[layer]:>8.1f}", *(f"{v:>8.0%}" for v in decisions.values())]
        print(f"{layer:<21} | " + " | ".join(cells))
    print("\nGate, Kantine = Anteil der Läufe, in denen der Agent in der neuen Situation genau")
    print("im richtigen Moment handeln würde (geliehenes Handlungswissen, 30 Schritte gesehen).")
    print(f"Ebene 3 wie erwartet: {full.meta_as_expected:.0%} der Läufe.")
    unchecked = f"{full.unchecked_all_in_one:.0%}"
    print(
        f"Ohne Prüfung des Handlungswissens fällt alles in eine Scheibe: {unchecked} der Läufe.\n"
    )
    print("H13: Verschmelzen nach wenig Erfahrung (sofort) oder nach viel (verzögert)?\n")
    h13_columns = ("Schritte", "Schemata ok", "vermischt", "Meta ok", "Entscheidung")
    print(" | ".join(f"{c:>12}" for c in h13_columns))
    print("-" * 74)
    for r in rows:
        decision = mean(r.right_decisions["Ebene 3"].values())
        shares = (r.schemas_as_expected, r.families_mixed, r.meta_as_expected, decision)
        print(f"{r.experience:>12} | " + " | ".join(f"{v:>12.0%}" for v in shares))
    print("\nSchritte = erlebte Schritte pro Situation vor dem Schlaf.")
    print("vermischt = ein Schema enthält Situationen aus verschiedenen Familien.")
    print("Entscheidung = mit Ebene 3 richtig gehandelt, Mittel aus Gate und Kantine.")


def _report_discovery(result: DiscoveryResult) -> None:
    print("\nSpielefamilie „Schlüssel und Tür“: Entdeckt der Agent die Regeln selbst?")
    print("Gleiche Mechanik, aber jedes Spiel hat andere Symbole und eine andere Tastenbelegung.")
    print("Nach jedem der Spiele 1 bis 3 bildet oder ergänzt der Agent sein Schema.")
    print("Härtetest mit dem Schema aus Spiel 1 bis 3: gespiegelt, länger, ohne Schlüssel.\n")
    columns = ("Spiel", "1. Sieg ohne", "mit Schema", "Optimum", "Siege ohne", "mit Schema", "max")
    print(f"{columns[0]:<14} | " + " | ".join(f"{c:>12}" for c in columns[1:]))
    print("-" * 104)
    for r in result.rows:
        cells = [
            f"{r.fresh_first_win:>12.1f}",
            f"{r.schema_first_win:>12.1f}",
            f"{r.optimal_first_win:>12}",
            f"{r.fresh_wins:>12.1f}",
            f"{r.schema_wins:>12.1f}",
            f"{r.optimal_wins:>12}",
        ]
        print(f"{r.game:<14} | " + " | ".join(cells))
    print("\n1. Sieg = Tastendrücke bis zum ersten Sieg; Siege = in 60 Tastendrücken.")
    fits = ", ".join(f"{r.game} {r.schema_fits:.0%}" for r in result.rows[1:])
    print(f"Schema passt am Ende noch (eine Deutung übrig): {fits}")
    sizes = ", ".join(f"nach {name} {size:.1f}" for name, size in result.schema_size.items())
    print(f"Bekannte Übergänge im Schema (von 24): {sizes}")


def _report_exploration(result: ExplorationResult) -> None:
    print("\nNeugier: Lohnt sich ein Abstecher ins Unbekannte, wenn man schon gewinnen kann?")
    print("Gleiche Spiele wie oben. „+ Neugier“ = wägt Abstecher gegen sichere Siege ab.")
    for horizon in result.horizons:
        _print_horizon(horizon)
    long_run = result.horizons[-1]
    plain_size = long_run.plain.schema_size["Spiel 3"]
    curious_size = long_run.curious.schema_size["Spiel 3"]
    print(f"\nBekannte Übergänge im Schema nach Spiel 3 (von 24): {plain_size:.1f} ohne,")
    print(f"{curious_size:.1f} mit Neugier ({long_run.steps} Tastendrücke).")
    _print_trust(result.trust, long_run.steps)


def _print_horizon(horizon: HorizonResult) -> None:
    print(f"\nSiege in {horizon.steps} Tastendrücken:\n")
    columns = ("Spiel", "ohne Schema", "+ Neugier", "mit Schema", "+ Neugier", "max")
    print(f"{columns[0]:<16} | " + " | ".join(f"{c:>11}" for c in columns[1:]))
    print("-" * 86)
    for plain, curious in zip(horizon.plain.rows, horizon.curious.rows, strict=True):
        wins = (plain.fresh_wins, curious.fresh_wins, plain.schema_wins, curious.schema_wins)
        cells = [*(f"{w:>11.1f}" for w in wins), f"{plain.optimal_wins:>11}"]
        print(f"{plain.game:<16} | " + " | ".join(cells))
    totals = [
        total_wins(run, agent)
        for agent in ("ohne Schema", "mit Schema")
        for run in (horizon.plain, horizon.curious)
    ]
    print(f"{'Summe ab Spiel 2':<16} | " + " | ".join(f"{w:>11.1f}" for w in totals))


def _print_trust(rows: list[TrustRow], steps: int) -> None:
    print(f"\nVertrauen ins Schema (mit Schema und Neugier, {steps} Tastendrücke):\n")
    columns = ("Überraschung", "Siege normal", "ohne Schlüssel")
    print(" | ".join(f"{c:>14}" for c in columns))
    print("-" * 48)
    for row in rows:
        values = (
            f"{row.schema_surprise:.4f}",
            f"{row.ordinary_wins:.1f}",
            f"{row.surprising_wins:.1f}",
        )
        print(" | ".join(f"{v:>14}" for v in values))
    print("\nÜberraschung = Chance, die der Agent einer Taste zutraut, wenn das Schema etwas")
    print("anderes vorhersagt. Siege normal = Mittel aus Spiel 2, Spiel 3 und gespiegelt.")


def _report_rule_transfer(result: TransferResult) -> None:
    print("\nRegeln statt Zustände: Überträgt der Agent das Spiel auf andere Größen?")
    print("Spiel 1 bis 3 werden länger (4, 5, 6 Felder). Drei Agenten spielen dieselben Spiele.")
    print("Härtetest mit dem Vorwissen aus Spiel 1 bis 3: gespiegelt, viel länger, ohne Schlüssel.")
    first_wins = [(r, r.first_win, r.optimal_first_win) for r in result.rows]
    _print_transfer_table("1. Sieg", "Optimum", first_wins)
    _print_transfer_table("Siege", "max", [(r, r.wins, r.optimal_wins) for r in result.rows])
    fits = ", ".join(f"{r.game} {r.rules_fit:.0%}" for r in result.rows[1:])
    print(f"\nRegel-Schema passt am Ende noch (eine Deutung übrig): {fits}")
    print("Ortsbeschreibungen im Regel-Schema nach Spiel 3 (Läufe):")
    for number, counter in enumerate(result.descriptions, start=1):
        found = ", ".join(f"{text} ({count})" for text, count in counter.most_common())
        print(f"  Ereignis {number}: {found}")


def _print_transfer_table(
    measure: str, best: str, lines: Sequence[tuple[TransferRow, Mapping[Knowledge, float], int]]
) -> None:
    columns = ("Spiel", "Länge", *KNOWLEDGE, best)
    header = f"{columns[0]:<14} | " + " | ".join(f"{c:>15}" for c in columns[1:])
    print(f"\n{measure}:\n")
    print(header)
    print("-" * len(header))
    for row, values, optimum in lines:
        cells = [f"{row.length:>15}", *(f"{values[k]:>15.1f}" for k in KNOWLEDGE), f"{optimum:>15}"]
        print(f"{row.game:<14} | " + " | ".join(cells))


def _report_grid_transfer(rows: list[GridRow]) -> None:
    print("\n2D-Welt wie ARC-AGI-3: Labyrinthe als Farbraster, jedes Level mit neuen Farben.")
    print("Bilder = jedes Raster ein Zustand; Objekte = lernt Figur, Tasten, Farbwirkungen;")
    print("+ Schema = bringt Rollen aus Level 1 bis 3 mit. 200 Tastendrücke pro Level.")
    best = [row.optimal_first_win for row in rows]
    _print_level_table("1. Sieg", rows, LEARNERS, [row.first_win for row in rows], best)
    wins, traps = [row.wins for row in rows], [row.traps for row in rows]
    _print_level_table("Siege", rows, LEARNERS, wins, [row.optimal_wins for row in rows])
    _print_level_table("Schritte in eine Falle", rows, LEARNERS, traps)
    fits = ", ".join(f"{r.level} {r.schema_fits:.0%}" for r in rows[1:])
    print(f"\nRollen-Schema passt am Ende noch (eine Deutung übrig): {fits}")


def _report_mechanics(rows: list[MechanicsRow], classic: list[ClassicRow]) -> None:
    print("\nWeltmodell: ein Spiel mit sechs Leveln in denselben Farben, wie bei ARC-AGI-3.")
    print("Neue Regeln ab Level „Kiste“: Kisten schieben, Druckplatte, Tor (offen, solange")
    print("etwas auf der Platte steht). Im Level „Tausch“ haben Ausgang und Fallen die Farben")
    print("getauscht. Objekte 0.12 = Objekt-Agent aus Ergebnis 13; Weltmodell = leitet Regeln")
    print("ab und plant darin; + Vorwissen = bringt sein Modell aus den vorigen Leveln mit.")
    print("300 Tastendrücke pro Level, nie gewonnen zählt als 301.")
    learners = MECHANICS_LEARNERS
    best = [row.optimal_first_win for row in rows]
    _print_level_table("1. Sieg", rows, learners, [row.first_win for row in rows], best)
    _print_level_table("Siege", rows, learners, [row.wins for row in rows])
    _print_level_table("Schritte in eine Falle", rows, learners, [row.traps for row in rows])
    stopped = ", ".join(f"{r.level} {r.stopped['Objekte 0.12']:.0%}" for r in rows)
    print(f"\nObjekte 0.12 bricht ab (Widerspruch zu seinem Wissen): {stopped}")
    print("\nGegenprobe auf den Labyrinthen aus Ergebnis 13 (1. Sieg, 200 Tastendrücke):\n")
    header = f"{'Level':<14} | {'Objekte':>10} | {'Weltmodell':>10}"
    print(header)
    print("-" * len(header))
    for row in classic:
        print(f"{row.level:<14} | {row.objects:>10.1f} | {row.model:>10.1f}")


def _report_roles(rows: list[RoleRow]) -> None:
    print("\nRollen-Weltmodell (H14): Nach einem ganzen Spiel A bekommt der Agent neue Level in")
    print("den Farben und mit den Tasten eines neuen Spiels B. Was in A braun war, ist in B")
    print("vielleicht gelb. Farben aus A = bringt sein Modell über Farben mit; Rollen aus A =")
    print("bringt Regeln über Rollen mit (schiebbar, auslöser, …); gleiches Spiel = dasselbe")
    print("Level in den Farben von A, der Bestwert. Alle kennen die Neustart-Taste.")
    print("300 Tastendrücke pro Level, nie gewonnen zählt als 301.")
    best = [row.optimal_first_win for row in rows]
    first = [row.first_win for row in rows]
    _print_level_table("1. Sieg", rows, ROLE_LEARNERS, first, best)
    _print_level_table("Neustart-Taste gedrückt", rows, ROLE_LEARNERS, [r.restarts for r in rows])
    _print_level_table("Schritte in eine Falle", rows, ROLE_LEARNERS, [r.traps for r in rows])
    for learner in ROLE_LEARNERS:
        no_win = ", ".join(f"{r.level} {r.no_win[learner]:.0%}" for r in rows if r.no_win[learner])
        print(f"\nOhne Sieg ({learner}): {no_win or 'keine'}", end="")
    print()


def _report_foreign(rows: list[ForeignRow]) -> None:
    print("\nGegenprobe: fremde Mechanik. Nach Spiel A kommen Level von Spiel B. „gewohnt“ hat")
    print("die Regeln von A; bei „Tor umgekehrt“ schließt die Druckplatte das Tor, und die Kiste")
    print("steht zu Beginn darauf; bei „Eis“ rutscht die Figur, bis etwas sie aufhält.")
    print("Aussehen A = dasselbe Level in Farben und Tasten von A. Modell aus A = bringt sein")
    print("Modell über die Farben von A mit: Das Level sieht aus wie A, ist es aber nicht immer.")
    print("+ Prüfung = Vorwissen erst nach zwei Bestätigungen nutzen, nach einem Widerspruch nie")
    print("mehr (H17). + Teilprüfung = Vorwissen sofort nutzen, aber bei Stillstand jeden Teil")
    print("testen, der nicht selbst gesehen ist (H16).")
    print("300 Tastendrücke pro Level, nie gewonnen zählt als 301.")
    best = [row.optimal_first_win for row in rows]
    _print_level_table("1. Sieg", rows, FOREIGN_LEARNERS, [r.first_win for r in rows], best)
    harm = [row.harm for row in rows]
    title = "Schaden (1. Sieg minus ohne Vorwissen im selben Aussehen)"
    _print_level_table(title, rows, FOREIGN_LEARNERS, harm)
    no_win = [{k: 100 * v for k, v in row.no_win.items()} for row in rows]
    _print_level_table("Ohne Sieg (% der Läufe)", rows, FOREIGN_LEARNERS, no_win)
    refuted = [{k: 100 * v for k, v in row.refuted.items()} for row in rows]
    _print_level_table("Vorwissen am Ende widerlegt (% der Läufe)", rows, FOREIGN_LEARNERS, refuted)


def _report_cross_world(rows: list[CrossRow]) -> None:
    print("\nSpielwelt gegen Alltagswelt: Schaden durch Vorwissen in Prozent (negativ = hilft).")
    print("Alltag = Härtetest H11 von oben (Vorhersage, gemittelt über 10, 40, 160 Beob.),")
    print("Spiel = Gegenprobe (Tastendrücke bis zum 1. Sieg, Aussehen A).")
    print("übernehmen = starr / Modell aus A; als Ganzes prüfen = geprüft / Modell + Prüfung;")
    print("Teile korrigieren = lernend / Modell + Teilprüfung. Gleiches Prinzip, anderer Code.\n")
    header = f"{'Welt':<6} | {'Lage':<15} | " + " | ".join(f"{h:>17}" for h in HANDLINGS)
    print(header)
    print("-" * len(header))
    for row in rows:
        cells = " | ".join(f"{row.harm[h]:>+16.1f}%" for h in HANDLINGS)
        print(f"{row.world:<6} | {row.situation:<15} | {cells}")
    print()


def _print_level_table[Name: str](
    measure: str,
    rows: Sequence[_LevelRow],
    learners: Sequence[Name],
    values: Sequence[Mapping[Name, float]],
    best: Sequence[float] | None = None,
) -> None:
    """Eine Tabelle: pro Level eine Zeile, pro Agent eine Spalte (breit genug für den Namen)."""
    columns = ["Größe", *map(str, learners)] + (["bestenfalls"] if best else [])
    widths = [max(16, len(column)) for column in columns]
    cells = [f"{column:>{width}}" for column, width in zip(columns, widths, strict=True)]
    header = f"{'Level':<14} | " + " | ".join(cells)
    print(f"\n{measure}:\n")
    print(header)
    print("-" * len(header))
    for index, row in enumerate(rows):
        numbers = [values[index][learner] for learner in learners]
        numbers += [best[index]] if best else []
        cells = [f"{f'{row.size}×{row.size}':>{widths[0]}}"]
        cells += [f"{n:>{w}.1f}" for n, w in zip(numbers, widths[1:], strict=True)]
        print(f"{row.level:<14} | " + " | ".join(cells))


def _report_recognition(rows: list[RecognitionRow]) -> None:
    print("Kontexterkennung: Ordnet der Agent jeden Übergang der richtigen Situation zu?\n")
    columns = ("Welt", "Situationen", "Kontexte", "richtig")
    print(f"{columns[0]:<27} | " + " | ".join(f"{c:>11}" for c in columns[1:]))
    print("-" * 70)
    for r in rows:
        cells = (f"{r.situations:>11}", f"{r.contexts_found:>11.2f}", f"{r.correct_share:>11.1%}")
        print(f"{r.world:<27} | " + " | ".join(cells))
    print("\nrichtig = Anteil der Übergänge im Kontext, der ihrer Situation zugeordnet ist.\n")


def main() -> None:
    """Führt alle Experimente mit Standardeinstellungen aus."""
    _report_h11(run_h11())
    stress = run_h11_stress()
    _report_stress(stress)
    _report_h12(run_h12())
    _report_recognition(run_recognition())
    _report_combined(run_combined())
    _report_wake_sleep(run_wake_sleep())
    _report_multi_schema(run_multi_schema())
    _report_game(run_traffic_light_game())
    _report_meta_schema(run_meta_schema())
    _report_discovery(run_discovery())
    _report_exploration(run_exploration())
    _report_rule_transfer(run_rule_transfer())
    _report_grid_transfer(run_grid_transfer())
    _report_mechanics(run_mechanics(), run_classic_check())
    _report_roles(run_roles())
    foreign = run_foreign()
    _report_foreign(foreign)
    _report_cross_world(compare_worlds(stress, foreign))
    report_general_worlds(run_general_worlds())
    report_library(*run_library_transfer())
    report_new_world(run_new_world())


if __name__ == "__main__":
    main()
