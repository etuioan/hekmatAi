# Paper-Zuordnung: Welches Modul stützt sich auf welche Forschung?

Stand: Prototyp 0.17, Dossier Runde 7 (29. Oktober 2026, 221 Paper).
Dossier: https://claude.ai/artifact/Sghxz5AxhcHgCKY9dtGSM5, Abschnitt „Paper ↔ Prototyp“.

**Regel:** Jede neue Version aktualisiert diese Datei. Ideen, die zuerst im Code entstehen,
bekommen den Vermerk **ohne Grundlage**. Sie sind der Suchauftrag für die nächste Paper-Runde.
P1–P8 sind die Prinzipien, H1–H24 die Hypothesen des Dossiers.

## Module und ihre Grundlagen

| Modul | Baustein der Architektur v0.3 | Paper | Prinzip / Hypothese |
|---|---|---|---|
| `situations.py`, `markov.py` | Welt, Situationsmodell (Ebene 1) | Behrens 2018, Whittington 2020 (Struktur und Inhalt getrennt) | P2 |
| `structure.py` | Schema-Stapel: Verschmelzen | Gentner 1983 (Strukturabbildung) | P3 |
| `schema.py` | Schema-Stapel: Schema, Bindung | Whittington 2020 (TEM), Tse 2007, Bhattarai 2026 | P3, H11 |
| `overlap.py`, `player.py` | Schema-Stapel: Schnittmenge, Analogie | Gentner 1983, Webb 2023 | P3, H11 |
| `stack.py` | Schema-Stapel: Ebenen mit einer Routine | Baram 2026, Smith 2020, Botvinick 2008, AXIOM 2025 | P6, H10, H13 |
| `context.py` | Kontext-Inferenz | Gershman 2010, COIN (Heald 2021), Collins & Frank 2013 | P7, H12 |
| `wake_sleep.py` | Gedächtnis, Schlafphase | Kumaran 2016 (komplementäre Lernsysteme), DreamCoder 2021 | P6, H12, H13 |
| `action.py` | Handlungswissen im Schema | Sutton 1999 (Optionen), Tse 2007 | P3 |
| `game.py` | Ampelspiel (Welt) | – (Testwelt) | H11 |
| `puzzle.py`, `game_schema.py` | Spiel-Schemata, Deutungen streichen | ARC-AGI-3 (2026), Collins & Frank 2013 | P4, H11 |
| `explorer.py`, `advisor.py` | Planer, Vorwissen | EMPA (Tsividis 2021); „einer Deutung folgen“ war **ohne Grundlage**, jetzt Tycho 2026 | P4, P5 |
| `rules.py` | Regel-Schemata | Chollet 2019 (Kernwissen), Schema Networks 2017 | P3, H11 |
| `curiosity.py` | Planer: epistemischer Wert | Friston 2017; feste Chancen 10 %/5 % waren **ohne Grundlage**, jetzt OPINE-World 2026 | P5, H3, H15 |
| `grid/world.py`, `grid/mazes.py` | Welt wie ARC-AGI-3, ab 0.14 mit Neustart-Taste, ab 0.15 mit fremder Mechanik | ARC-AGI-3 (2026, RESET), Grinsztajn 2021 (Sokoban); fremde Mechanik als Gegenprobe: Runde 5 (Mitchell 2021, Raji 2021); welche Mechaniken (Platte schließt, Eis) ist **ohne Grundlage** | G4 |
| `grid/perception.py`, `grid/effects.py` | Wahrnehmung (fest eingebaut) | Rudakov 2025 (einfarbige Flächen); fünf feste Wirkungen: Chollet 2019 | H5 (nicht geprüft) |
| `grid/knowledge.py`, `grid/agent.py`, `grid/planner.py` | Objekt-Agent | AXIOM 2025 (objektzentriert) | P2, P7 |
| `grid/roles.py` | Rollen-Schema | Schema Networks 2017; „Aussehen“ war **ohne Grundlage**, jetzt Silver 2023 | P3, H11, H14 |
| `grid/model.py`, `grid/induction.py` | Programmatisches Weltmodell | PoE-World 2025, WorldCoder 2024, OneLife 2025, AutumnSynth 2023 | P1, P2, P4, P7, H4 |
| `grid/role_model.py` | Rollen-Weltmodell: Regeln über Rollen, Bindung neuer Farben | Whittington 2020 (TEM, Struktur und Inhalt), Schema Networks 2017, OPINE-World 2026; „nur übernehmen, worin alle besten Bindungen übereinstimmen“ ist **ohne Grundlage** | P2, P3, H14, H15 |
| `grid/simulation.py`, `grid/search.py` | Planer im Weltmodell | MuZero 2020, EMPA 2021; „Kiste nicht in die Ecke“ war **ohne Grundlage**, jetzt Grinsztajn 2021, Go-Explore 2021 | P2, P5 |
| `grid/model_agent.py` | Modell-Agent, ab 0.15 mit Teilprüfung | Tycho 2026, Kepler 2026; Zweifel-Stufen waren **ohne Grundlage**, jetzt OPINE-World 2026; Teilprüfung: Franklin & Frank 2018/2020, Bilalić 2008 | P2, P4, P5, H16 |
| `grid/trust.py` | Vorwissen erst nach Bestätigung nutzen | ARC-Prize-Auswertung 2026, Kepler 2026, Gershman 2017; Schwelle von zwei Bestätigungen ist **ohne Grundlage** | H17 |
| `grid/baseline.py` | Vergleich | Rudakov 2025 (Graph-Entdecker) | – |
| `general/env.py`, `general/worlds.py` | Schnittstelle für jede Welt: nur Zahlen und Tasten, gemischt; Raum, Würfel, Suchbaum, ab 0.17 Eis, Drehscheiben, Tauschen und `Padded` (eine Schnittstelle für alle) | Runde 6: Philipona 2003 (Raum aus Sensomotorik), Kemp & Tenenbaum 2008; Gegenprobe gegen „Welt und Agent aus einer Hand“: Runde 5 G4; Eis ohne Fallen zu erzeugen ist **ohne Grundlage** | H18–H23 |
| `general/programs.py`, `general/synthesis.py` | Regeln als Programme, kürzeste Beschreibung; ab 0.17 Übernehmen, Ring, Schleife „bis Schalter“, aus den Daten vorgeschlagen | Schema 2026, Rule 2020 und 2024, Evans 2021 (Apperception), MDL nach Rissanen 1978; Runde 7: Sutton 1999 und Bacon 2017 (Optionen mit Abbruch), Ellis 2018, Cropper 2020 (Schleifen), Gulwani 2017 (Warnung: Schleifen sprengen die Suche); Bit-Preise sind **ohne Grundlage** | P1, P4, H19, H22 |
| `general/library.py` | Hekmat-Bibliothek mit Wiederverwendungs-Zähler, ab 0.17 mit Vorprüfung | DreamCoder 2021, Stitch 2023 (Anti-Unifikation), Berlot-Attwell 2026 (Zähler, gleiche Rechenzeit), TheoryCoder-2 2026; Runde 7: DeepCoder (Balog 2017), LAPS (Wong 2021), AbstractBeam (Zenkner 2024) | P6, H20, H24 |
| `general/form.py`, `general/planner.py` | Form der Welt als Grammatik (Kette, Ring, Rutschbahn, Ordnung), Karte mit Bezugssystem; ohne Form Suche im gelernten Modell | Kemp & Tenenbaum 2008, Duvenaud 2013, Grosse 2012, Constantinescu 2016, Bellmund 2018, Aronov 2017; Runde 7: Mahadevan & Maggioni 2007, Stachenfeld 2017, Mark 2020 | P2, H19, H21 |
| `general/knowledge.py` | Regelbuch und Ziel je Karte | Collins & Frank 2013 (Kontext-Karten), Gershman 2010 | P7 |
| `general/detector.py`, `general/agent.py` | Neue Umgebung erkennen: erwartete gegen unerwartete Unsicherheit, ab 0.17 per Bayes-Faktor | Yu & Dayan 2002, Sanders 2020, Heald 2021 (COIN), Stahl & Feigenson 2015; Runde 7: Adams & MacKay 2007, Liakoni 2021, Wald 1945 (sequentieller Test), Kass & Raftery 1995 (Schwelle), Dawid 1984 (prequentielle Wertung); Fenster 20 und Wechselrate 1/1000 sind **ohne Grundlage** | P7, H18, H23 |
| `experiments/` | Messung, ab 0.15 auch Schaden durch Vorwissen | Tastendrücke bis zum ersten Sieg; ARC-AGI-3 misst RHAE; negative Übertragung: Wang 2019; Vergleich Spielwelt–Alltagswelt: Runde 5 G4 | H11–H17 |

## Was aus der Architektur v0.3 noch fehlt

| Baustein | Stand | Paper |
|---|---|---|
| Hekmat-Bibliothek (wachsend, Wiederverwendung gezählt) | erster Anfang in 0.16 (`general/library.py`), nur Muster aus einer Regel, ab 0.17 mit Vorprüfung; noch keine Bibliothek über Pläne oder Formen, die Vorprüfung ist fest und nicht gelernt | DreamCoder, LILO, Stitch, SAGE; Runde 6: Rule 2020 und 2024, Piantadosi 2012, Ullman 2012, Schema 2026, TheoryCoder-2 2026; Warnung: Berlot-Attwell 2026 (Bibliotheken oft nicht wiederverwendet) |
| Neuronales Weltmodell | bewusst weggelassen (nur Standardbibliothek) | Causal-JEPA, DreamerV3 |
| Sprachorgan (LLM) | bewusst weggelassen | LILO; Tycho und Kepler zeigen, dass LLMs Weltmodelle als Code schreiben |
| Lehrplan-Generator | fehlt | Absolute Zero, Oudeyer 2007, POET |
| Kontext-Inferenz und Schlaf in der 2D-Welt | Kontext-Inferenz ab 0.16 im allgemeinen Agenten (`general/detector.py`), Schlaf fehlt | COIN, Bhattarai 2026; Runde 6: Sanders, Wilson, Gershman 2020, Yu & Dayan 2002 |

## Umgesetzt in 0.17 (Test von H21 bis H24 nach Runde 7)

| Vorschlag aus Runde 7 | Stand |
|---|---|
| H21: Form als Grammatik, Suche im Modell als Rückfall | **gestützt** (Ergebnis 20): „Ring × Ring × Ring“ bei den Drehscheiben und „Rutschbahn mit 2 Dimensionen“ auf Eis in 10 von 10 Läufen; 0.16 hielt beides für einen Raum oder eine Ordnung. Drehscheiben 9,6 statt 13,9 Schritte (bestenfalls 9,6). Tauschen hat keine Form: Mit Suche im Modell 7,7 Schritte (bestenfalls 7,5), ohne 762. Die Laplace-Koordinaten von Mahadevan 2007 wurden nicht gebaut, die Grammatik reichte |
| H22: ein Schleifenbaustein „Schritt, bis Schalter“ | **gestützt** (Ergebnis 20): Eis 11,9 statt 98 Schritte (bestenfalls 5,0, Tabelle 86). Das ist noch mehr als das Doppelte des kürzesten Wegs: Wo er noch nicht war, weiß er nicht, wo das Rutschen endet |
| H23: neue Welt per Bayes-Faktor | **teilweise** (Ergebnis 19 und 21): Ganz verschiedene Welten im selben Strom (Raum → Suchbaum → Drehscheiben → Raum) erkennt schon der Binomial-Test aus 0.16 meist (80 / 80 / 100 %). Der Bayes-Faktor erkennt öfter (80 / 100 / 100 %), legt weniger überzählige Karten an (1,2 statt 1,4) und findet öfter die erste Karte wieder (80 statt 60 %), braucht aber mehr Schritte (Suchbaum 92 statt 44, Drehscheiben 108 statt 73). Bei vertauschten Tasten ist der Binomial-Test besser (zurück zur alten Karte 100 statt 90 %, 17 statt 40 Schritte). Schwelle nach Kass & Raftery, Wechselrate ohne Grundlage |
| H24: Bibliothek mit Vorprüfung spart insgesamt | **teilweise** (Ergebnis 18): Über alle Suchen 8 bzw. 1 % weniger Programme als ohne Bibliothek; ohne Vorprüfung 6 % weniger bzw. 5 % mehr. Die Vorprüfung macht die Bibliothek also in beiden Reihenfolgen sparsam, aber nur knapp. Bei knappem Budget erreicht er das Ziel im 3D-Raum mit Bibliothek seltener (96 statt 100 %). Die Vorprüfung ist von Hand gebaut, nicht gelernt wie bei DeepCoder |
| Gegenstimme Gulwani 2017: Schleifen sprengen die Suche | beachtet: genau eine Schleifenform, nur vorgeschlagen, wenn lange Sprünge vorkommen; Ergebnis 17 bleibt genau wie in 0.16 |
| Ziel in eine neue Karte übernehmen (0.16) | **zurückgenommen**: Im Strom verschiedener Welten führte das alte Ziel in die Irre (Suchbaum 194 statt 93 Schritte). Neue Ursache, neues Wissen (Gershman 2017) |
| Übernehmen nur mit Beleg | Ein „übernimmt G6“ aus wenigen Zufallstreffern machte den 3D-Würfel langsamer (13,7 statt 10,8 Schritte). Jetzt braucht Übernehmen jeden Wechsel als Beleg, mindestens zwei verschiedene neue Werte und eine Quelle, die alle Werte der Größe gezeigt hat. Danach ist Ergebnis 17 wieder genau wie in 0.16 |

**Ohne Grundlage (neu in 0.17), Suchauftrag für Runde 8:**
- Synthese: Anteil 90 % für die Vorprüfung (`COVERAGE`), Ring ab 3 Werten (`MIN_RING`), höchstens 4 Quellen für Übernehmen (`MAX_SOURCES`), Länge 2 für Ring und Schleife (`LOOP_COST`).
- Planer: Suche im Modell nur mit Regeln aus mindestens 3 Beispielen (`MODEL_SUPPORT`), höchstens 5000 vorgestellte Zustände (`MODEL_LIMIT`); beim Rutschen im Kopf an der ersten unbekannten Stelle anhalten.
- Erkennen: Wechselrate 1/1000 je Schritt (`HAZARD`), zweifache Kreuzprüfung für den Verlust neuer Regeln (statt voller prequentieller Wertung nach Dawid 1984).
- Welt: Eis-Räume ohne Fallen, nur Hindernisse, die das Spielgebiet nicht verkleinern.

## Umgesetzt in 0.16 (Test von H18 bis H20 nach Runde 6)

| Vorschlag aus Runde 6 | Stand |
|---|---|
| H19: erst die Form, dann die Regeln | **gestützt** in drei Welten (`general/form.py`, Ergebnis 17): Form in 30 von 30 Läufen selbst gefunden; mit Form 23,2 / 10,8 / 18,0 Schritte (bestenfalls 17,8 / 9,1 / 18,0), ohne Form 52,4 / 19,0 / nie am Ziel. Der Vergleich „fest eingebautes Raster“ ist entfallen, weil das Raster aus 0.15 in diesen Welten gar nicht läuft. Formen kommen aus einer festen Liste |
| H20: Bausteine plus Bibliothek mit Zähler, gleiche Rechenzeit | **teilweise**: Das Muster aus dem 2D-Raum wird im 3D-Raum 6× genutzt und halbiert die erfolgreichen Suchen (762 → 364), die Zufallsbibliothek schadet (1279). Über alle Suchen −8 % bis +8 %, bei knappem Budget kein Gewinn (Berlot-Attwells Warnung trifft teilweise zu). Eis nicht geprüft: kein Baustein „wiederholen“ |
| H18: neue Umgebung an unerwarteter Unsicherheit erkennen | **gestützt** für vertauschte Tasten (Ergebnis 19): 0,1 Fehlalarme bei 10 % Rauschen (gegen 416 bei „jede Überraschung“), B in 80 % erkannt, in 90 % zurück zur alten Karte, erste Runden danach 18 statt 50 Schritte (Umlernen) und 150 (ohne Erkennung). Wechsel zwischen ganz verschiedenen Welten offen |
| Kernwissen: wenige allgemeine Systeme (Spelke 2022) | teilweise: Orte und Bezugssysteme (Raumachsen), Größenordnung (Ordnung). Objekte, Zahl, Handelnde fehlen |
| Dieselbe Routine für jede Umgebung (Aronov 2017, Thousand Brains) | umgesetzt für Raum, Würfel und Suchbaum: ein Code, nur die Welt wechselt |

**Ohne Grundlage (neu in 0.16), Suchauftrag für Runde 7:**
- Preise der Beschreibungslänge: 4 Bit je Baustein (`NODE_BITS`), `log2(n+1)` je Ausnahme; Fehlergrenze 30 % für „unvorhersagbar“ (`MAX_ERROR_RATE`).
- Bibliothek: höchstens zwei neue Muster je Welt (`MAX_NEW`), Aufrufpreis ein Baustein (`CALL_COST`), Geduld zwei Welten (`PATIENCE`), Budget 20 Programme im Vergleich (`BUDGET`).
- Erkennen: Fenster 20 Schritte (`WINDOW`), Grenze 10⁻⁵ (`TAIL_LIMIT`), Zweifel ab 0,85 Zuverlässigkeit (`DOUBT`), Binomial-Test je Regel statt einer Bayes-Inferenz über Karten wie bei Sanders 2020.
- Form: Toleranz `2 × Rauschpegel + 0,01` (`NOISE_MARGIN`), die feste Liste der Formen (Raum, Ordnung).
- Ziel nur als Paare „Größe i = Größe j“ (Grammatik des Ziels).
- Planer: nach drei gleichen Versuchen ausweichen (`STUCK`), Unbekanntes gilt als frei.

## Umgesetzt in 0.15 (Gegenprobe nach Runde 5)

| Vorschlag aus Runde 5 | Stand |
|---|---|
| Gegenprobe mit fremder Mechanik, Schaden messen (Wang 2019) | umgesetzt in `experiments/grid_foreign.py`. Ergebnis 16: Sieht ein Level aus wie Spiel A, hat aber eine umgekehrte Platte, kostet das Farbmodell aus A +146 Tastendrücke (+295 %), 40 % der Läufe ohne Sieg. Ursache: Das Vorwissen verhindert genau den Test, der es widerlegen würde (Einstellung-Effekt, Bilalić 2008) |
| H17: Vorwissen erst nach bestandener Vorhersage | als Ganzes (`trust.py`) **widerlegt**: Boden und Wand bestätigen sofort, der Widerspruch kommt zu spät oder nie (+149) |
| H16: Teile einzeln wiederverwenden und prüfen | **gestützt**: Teilprüfung senkt den Schaden auf +5 (+10 %), kein Lauf ohne Sieg, ohne Kosten, wo das Vorwissen passt. Damit gilt auch H17 in der Form des Dossiers („jedes Teil erst nach einer Vorhersage“), nicht als Ganzes |
| Übertragung zwischen Spielwelt und Alltagswelt | teilweise, `experiments/cross_world.py`: Teile korrigieren hilft in beiden Welten; als Ganzes prüfen nur in der Alltagswelt, wo Beobachtungen unabhängig vom Handeln kommen. Verschiedener Code, gemeinsamer Mechanismus offen |
| G4: Gegenprobe außerhalb des Eingebauten | Eis schafft kein Agent (etwa 130 statt 8 Tastendrücke): Neue Regelarten kann er nicht bilden |
| H14 nur nahe Übertragung | bestätigt: Rollen aus A schaden auch bei fremder Mechanik nicht, helfen aber nur wenig (−5 bis −8) |

**Ohne Grundlage (neu in 0.15), Suchauftrag für Runde 6:**
- Zwei Bestätigungen als Schwelle der Prüfung (`CONFIRMATIONS_NEEDED`).
- Teilprüfung erst bei Stillstand auszulösen (statt etwa, wenn ein Plan länger dauert als erwartet).
- Die Wahl der fremden Mechaniken (Platte schließt, Eis) und die Mindestlänge der Eis-Level (6).
- Der Befund, dass passives Prüfen nur ohne eigenes Handeln reicht, braucht Paper zum aktiven Lernen (etwa Gureckis & Markant 2012, Einstellung-Effekt) und einen gemeinsamen Mechanismus für beide Welten.

## Umgesetzt in 0.14

| Vorschlag aus Runde 4 | Stand |
|---|---|
| Regeln an Rollen statt Farben (H14) | umgesetzt in `grid/role_model.py`. Ergebnis 15: **teilweise bestätigt**, in fünf von sechs Leveln 8 bis 20 % schneller als ohne Vorwissen und seltener in Fallen; Farbwissen aus einem anderen Spiel schadet dagegen stark. Zum Bestwert fehlt viel (Tasten, gleiches Aussehen) |
| Neustart-Taste | umgesetzt; gelernte Umkehrbarkeit (wann lohnt sie sich?) fehlt noch |
| Neugier nach Widerspruch (H15) | teilweise: Mehrdeutige Rollen bleiben offen und werden gezielt getestet. Die festen Chancen in `curiosity.py` sind unverändert |
| Schlaf in der 2D-Welt, RHAE | offen |

**Ohne Grundlage (neu in 0.14), Suchauftrag für Runde 5:**
- Nur übernehmen, worin alle besten Bindungen übereinstimmen (statt einer zufälligen Deutung zu folgen). Verwandt mit Versionsräumen (Mitchell 1982) und Konsens über Hypothesen, aber nicht aus einem Paper übernommen.
- Rang der Bindungen: erst Farben mit Beobachtungen, dann alle Farben, dann „hat ein Ziel“.
- Aussehen nur als „ein Feld oder viele, Rand oder innen“: Die meisten Spielelemente sehen gleich aus (Silver 2023, Prädikat-Erfindung, wäre der nächste Schritt).

## Gegenprüfung Runde 5 (kritische Paper)

Dossier-Abschnitt „Was gegen unsere Annahmen spricht“ (#runde5), 17 Arbeiten.

| Annahme | Stand nach Runde 5 | Wichtigste Gegenbelege |
|---|---|---|
| H14 Übertragung über Rollen | eingeschränkt: nahe Übertragung gestützt, andere Mechanik nicht belegt | Sala & Gobet 2017, Gick & Holyoak 1980, Ramakrishnan 2023 |
| Spielerkennung, ein Modell pro Spielfamilie | in dieser Form widerlegt | Franklin & Frank 2018/2020, Gershman 2017, ARC-Prize-Auswertung 2026, Gentner 1993, Bilalić 2008 |
| Schemata beschleunigen (H11–H13) | gestützt, aber mit Preis | Brewer & Treyens 1981, Bilalić 2008 |
| Spielwelten als Weg zur AGI | nicht belegt | Raji 2021, Mitchell 2021, Cobbe 2019, Sutton 2019, Botvinick 2017, Greff 2020 |

Neue Hypothesen: H16 (Teile statt Ganzes wiederverwenden), H17 (Vorwissen erst nach bestandener Vorhersage).
Größte Schwäche laut Runde 5: Welt und Agent stammen aus derselben Hand (fünf Regelarten = fünf Feldarten).

## Runde 7: Die Grenzen von 0.16 überwinden (29. Oktober 2026)

Dossier-Abschnitt #runde7, 19 Arbeiten, dazu nach dem Bau von 0.17 drei Grundlagen für den Bayes-Faktor
(Wald 1945, Kass & Raftery 1995, Dawid 1984).

| Grenze von 0.16 | Lösung | Grundlage | Hypothese |
|---|---|---|---|
| Formen aus einer festen Liste | Grammatik aus Kette, Ring, Ordnung (und Rutschbahn), Welten als Produkt; ohne Form Suche im Modell | Grosse 2012, Kemp & Tenenbaum 2008, Mahadevan & Maggioni 2007, Stachenfeld 2017, Mark 2020 | H21 |
| Kein Baustein „wiederholen“ (Eis) | eine Schleifenform „Schritt, bis Schalter“ | Sutton 1999, Bacon 2017, Ellis 2018, Cropper 2020; Warnung Gulwani 2017 | H22 |
| Neue Welt nur mit vertauschten Tasten geprüft | Karten gegen ein frisches Modell abwägen, Strom ganz verschiedener Welten | Adams & MacKay 2007, Liakoni 2021, Sanders 2020 | H23 |
| Bibliothek spart insgesamt nichts | billige Vorbedingung je Muster (Erkennungsmodell) | DeepCoder (Balog 2017), LAPS (Wong 2021), AbstractBeam (Zenkner 2024) | H24 |

Gegenstimmen: Schleifen sprengen die Suche (Gulwani 2017); vom Gehirn auf Algorithmen zu schließen bleibt riskant
(Schaeffer, Khona, Fiete 2022).

## Runde 6: Neue Umgebungen verstehen lernen (29. Oktober 2026)

Dossier-Abschnitt #runde6, 27 Arbeiten aus KI, Hirnforschung, Entwicklungspsychologie und Kritik.

| Baustein | heute (0.15) | nach Runde 6 | Grundlage |
|---|---|---|---|
| Neue Umgebung erkennen | Kontext-Inferenz nur in der Alltagswelt, Anteil 0,03 von Hand | für jede Welt: unerwartete gegen erwartete Unsicherheit, neue Karte statt Umlernen | Sanders 2020, Yu & Dayan 2002, Stahl & Feigenson 2015 |
| Form der Umgebung | festes 2D-Raster mit Farben | Strukturfinder: Dimension und Form aus den Folgen eigener Handlungen | Philipona 2003, Kemp & Tenenbaum 2008, Duvenaud 2013 |
| Regeln | fünf feste Regelarten | Programme aus einer kleinen Grammatik, gegen die Erfahrung geprüft | Schema 2026, Rule 2020 und 2024, Evans 2021 |
| Bibliothek | fehlt | nur aufnehmen, was nachweislich wiederverwendet wird, gemessen bei gleicher Rechenzeit | Berlot-Attwell 2026, TheoryCoder-2 2026 |
| Kernwissen | zufällig das, was die Spielwelt braucht | wenige allgemeine Kernsysteme: Objekte, Orte und Bezugssysteme, Zahl, Handelnde | Spelke 2022, Wolpert & Macready 1997 |
| Module | eigener Code pro Welt | dieselbe Routine für jede Umgebung: eine Karte mit Bezugssystem | Aronov 2017, Constantinescu 2016, Thousand Brains 2025 |

Neue Hypothesen: H18 (neue Umgebung an unerwarteter Unsicherheit erkennen), H19 (erst die Form, dann die Regeln),
H20 (Bausteine plus Bibliothek mit Wiederverwendungs-Zähler, gemessen bei gleicher Rechenzeit).
Gegenbelege: Ohne Vorwissen geht es nicht (No free lunch); ob neue Bausteine überhaupt lernbar sind, ist umstritten
(Fodor, Rey gegen Carey); Gitter-Signale im menschlichen MRT sind umstritten (Almog 2026); vom Gehirn auf
Algorithmen zu schließen ist riskant (Jonas & Kording 2017).
Damit haben „Anteil 0,03 für einen neuen Kontext“ (Sanders 2020) und „neue Regelarten bilden“ (Rule 2024, Schema 2026)
eine Grundlage. Weiter **ohne Grundlage**: die Schwelle von zwei Bestätigungen in `trust.py`.

## Nächste Schritte aus den Papern (Vorschlag 0.18, nach Ergebnis 21)

1. Die Vorprüfung der Bibliothek lernen statt von Hand bauen (DeepCoder, LAPS), Bibliothek auch über Formen und Pläne (H24).
2. Eis: Wo er noch nicht war, erkunden statt raten; Neugier auf das Ende einer Rutschpartie (H22, OPINE-World 2026).
3. Bayes-Faktor schneller entscheiden lassen, ohne mehr Fehlalarme (er sammelt oft zu lange); Wechselrate aus Erfahrung schätzen statt fest (Adams & MacKay 2007, Heald 2021) (H23).
4. Die 2D-Spielwelt an die allgemeine Schnittstelle anschließen (ein Agent für Spiel und Raum).
5. Kernwissen ergänzen: Objekte und Zahl (Spelke 2022); Tauschen zeigt, dass ohne Form nur rohe Suche bleibt.
6. Aus 0.15 offen: Teilprüfung in Alltagswelt und Spielwelt mit gemeinsamem Mechanismus (H16), reicheres Aussehen (Silver 2023).
