# Paper-Zuordnung: Welches Modul stützt sich auf welche Forschung?

Stand: Prototyp 0.22, Dossier Runde 7 (29. Oktober 2026, 221 Paper) plus Paper zu 0.18 bis 0.22 (siehe unten).
Dossier: https://claude.ai/artifact/Sghxz5AxhcHgCKY9dtGSM5, Abschnitt „Paper ↔ Prototyp“.

**Regel:** Jede neue Version aktualisiert diese Datei. Ideen, die zuerst im Code entstehen,
bekommen den Vermerk **ohne Grundlage**. Sie sind der Suchauftrag für die nächste Paper-Runde.
P1–P8 sind die Prinzipien, H1–H24 die Hypothesen des Dossiers, H25–H28 neu mit 0.18, H29–H31 mit 0.19, H32–H34 mit 0.20, H35 mit 0.21, H36 mit 0.22 (siehe unten).

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
| `general/causes.py` | Ursachen: unter welcher Bedingung eine Taste etwas bewirkt (ab 0.18) | Regeln lernen durch schrittweises Abdecken (Michalski 1969, CN2: Clark & Niblett 1989), Literal-Wahl nach gewichteter relativer Genauigkeit (Lavrač, Flach & Zupan 1999), Schema Networks 2017 (Bedingung → Wirkung); höchstens 3 Literale, 4 Ursachen, 2 Treffer, Genauigkeit 0,34 sind **ohne Grundlage** | P1, P4, H25 |
| `general/subgoals.py` | Teilziele und Vorstellen mit Lücken (ab 0.18) | Mittel-Ziel-Analyse (Newell & Simon 1961), STRIPS (Fikes & Nilsson 1971), Optionen (Sutton, Precup, Singh 1999), Raum aus Sensomotorik (Philipona 2003, Laflaquière 2019); Tiefe 3, 200 vorgestellte Zustände und „seltene Ursache ab 5 %“ sind **ohne Grundlage** | P2, P5, H25, H26 |
| `general/space.py` | Raum aus eigener Bewegung: welches Sichtfeld neben welchem liegt, eigene Stelle als Lücke, Gruppen nach Abstand (ab 0.19) | Philipona, O'Regan & Nadal 2003 (Raum aus Sensomotorik), Pierce & Kuipers 1997 (Karten aus uninterpretierten Sinnen und Tasten), Laflaquière & Garcia Ortiz 2019, Kruskal 1956 (stärkste Kanten zuerst), deiktische Darstellung (Agre & Chapman 1987); ab 0.20 Hindernisse aus eigener Bewegung und Fühler („vorne“): sensomotorische Kontingenzen (O'Regan & Noë 2001); Gegenstimme Finney, Gardiol, Kaelbling & Oates 2002; alle Schwellen (90 %, 80 %, 95 %, 20 Schritte, 6 Werte, 90 % Kasten, 3 Ringe, ab 0.20 5 Stöße und 80 % für ein Hindernis) sind **ohne Grundlage** | P2, H29, H34 |
| `general/cues.py` | Gefahren als Hinweisreize: Schadensquote je Aussage mit Unsicherheit (ab 0.21) | Beta-Binomial-Angstlernen (Tzovara, Korn & Bach 2018); gelernter Schutz vor Katastrophen-Aktionen (Shperberg, Liu & Stone 2022); Gegenstimmen: Übergeneralisieren der Angst (Lissek u. a. 2005), Reize konkurrieren um die Vorhersage (Rescorla & Wagner 1972, hier nicht abgebildet); 95 % Sicherheit ist **ohne Grundlage** | P5, H35 |
| `general/drives.py` | Eigene Ziele: Bedürfnisse, Rekorde, Versuche, Erkunden, Abwehr (ab 0.18) | Homöostase (Keramati & Gutkin 2014), intrinsisch motivierte Zielprozesse (Forestier, Portelas, Mollard, Oudeyer 2022; Oudeyer & Kaplan 2007), Zählen als Neugier (Strehl & Littman 2008, Bellemare 2016), Go-Explore (Ecoffet 2021), Vermeiden lernen (Mowrer 1947; ab 0.19 „gut ist, was die Gefahr beendet“, Gegenstimme Herrnstein 1969), Neugier auf Neues zum Anfassen (ab 0.19: Piaget 1952, Stahl & Feigenson 2015), Abwehr als Option (ab 0.20: Sutton, Precup & Singh 1999, Dabney, Ostrovski & Barreto 2021; wenige Antworten: Bolles 1970), neuer Besitz, neuer Versuch (ab 0.20: Gibson 1979, Şahin u. a. 2007), modellfrei neben modellbasiert (Daw, Niv & Dayan 2005), Schrumpfen zum Mittel (Efron & Morris 1975), Zahl und Ort als Kernsysteme (Spelke 2022, Dehaene 2011); ab 0.22 keine Versuche mehr, wo nichts zu lernen ist (Lernfortschritt: Oudeyer & Kaplan 2007; rauschender Fernseher: Burda u. a. 2019); Gegenstimmen siehe unten; fast alle Schwellen sind **ohne Grundlage** | P5, H27, H28, H30 bis H33, H36 |
| `adapters/crafter.py`, `experiments/crafter_run.py`, `experiments/crafter_replay.py` | Prüfstein Crafter, Adapter getrennt vom Agenten (ab 0.18) | Crafter (Hafner 2021), Wertung wie dort; MineRL/MineDojo erst später (Prüfung vom 29.10.2026) | G4 |
| `adapters/minecraft.py`, `adapters/minecraft_bridge/`, `experiments/minecraft_run.py` | Prüfstein echtes Minecraft, Adapter getrennt vom Agenten wie bei Crafter (nach 0.20) | Mineflayer (PrismarineJS) als Spieler-Client; Ziel-Signal sind Minecrafts eigene Fortschritte. Vergleich: MineRL (Guss 2019), MineDojo (Fan 2022), Voyager (Wang 2023) nutzen Pixel oder Sprachmodelle mit Spielwissen, hier bewusst keins. Wertung wie Crafter (Hafner 2021) | G4 |
| `experiments/` | Messung, ab 0.15 auch Schaden durch Vorwissen | Tastendrücke bis zum ersten Sieg; ARC-AGI-3 misst RHAE; negative Übertragung: Wang 2019; Vergleich Spielwelt–Alltagswelt: Runde 5 G4 | H11–H17 |

## Was aus der Architektur v0.3 noch fehlt

| Baustein | Stand | Paper |
|---|---|---|
| Hekmat-Bibliothek (wachsend, Wiederverwendung gezählt) | erster Anfang in 0.16 (`general/library.py`), nur Muster aus einer Regel, ab 0.17 mit Vorprüfung; noch keine Bibliothek über Pläne oder Formen, die Vorprüfung ist fest und nicht gelernt | DreamCoder, LILO, Stitch, SAGE; Runde 6: Rule 2020 und 2024, Piantadosi 2012, Ullman 2012, Schema 2026, TheoryCoder-2 2026; Warnung: Berlot-Attwell 2026 (Bibliotheken oft nicht wiederverwendet) |
| Neuronales Weltmodell | bewusst weggelassen (nur Standardbibliothek) | Causal-JEPA, DreamerV3 |
| Sprachorgan (LLM) | bewusst weggelassen | LILO; Tycho und Kepler zeigen, dass LLMs Weltmodelle als Code schreiben |
| Lehrplan-Generator | fehlt | Absolute Zero, Oudeyer 2007, POET |
| Kontext-Inferenz und Schlaf in der 2D-Welt | Kontext-Inferenz ab 0.16 im allgemeinen Agenten (`general/detector.py`), Schlaf fehlt | COIN, Bhattarai 2026; Runde 6: Sanders, Wilson, Gershman 2020, Yu & Dayan 2002 |

## Umgesetzt in 0.22 (Tasten ohne Wirkung, H36)

Abgeleitet aus der Frage, warum er Minecraft nicht spielt. Eine Aufzeichnung der Gründe auf
dem Testserver: bis zu 90 % der Schritte waren Versuche mit Tasten ohne Wirkung (meist
Rezepte ohne Holz), weil in einer großen Welt immer etwas selten ist. Das ist das Problem
des „rauschenden Fernsehers“: Neuheit, die nie verschwindet, zieht die Neugier für immer an
(Burda, Edwards, Pathak u. a. 2019; Pathak u. a. 2017). Die Antwort aus dem Dossier ist
Lernfortschritt statt Neuheit (Oudeyer & Kaplan 2007, Gottlieb & Oudeyer 2018): Wo sich die
Vorhersage nicht mehr verbessert, ist nichts zu lernen.

| Hypothese | Stand |
|---|---|
| H36: Eine Taste, die mit demselben Besitz oft genug nichts Eigenes bewirkt hat, verdient keinen Versuch mehr, bis sich der Besitz ändert (eine einfache Form von Lernfortschritt) | **teilweise gestützt** (Ergebnis 26): Der Mechanismus wirkt (Testwelt: 47 statt 1314 Versuche in 2000 Schritten; Testserver: Versuche ab Runde 2 bei 2 bis 50 % statt bis zu 90 %). Crafter wird nicht schlechter (3,0 statt 2,8 %, innerhalb der Streuung). In Minecraft aber kein messbarer Gewinn: gleiche Wertung (0,4 %), „Block im Blick“ +6,6 ± 4,6 Punkte, weiter unter dem Zufall. An die Stelle der Versuche treten Rekorde bei Position und Blickwinkel; der eigentliche Engpass ist der fehlende Raum |

**Gegenstimmen und Warnungen zu 0.22:**
- Maier & Seligman 2016 (erlernte Hilflosigkeit, neu gelesen): Wer lernt, dass Handeln
  nichts bewirkt, gibt auch dort auf, wo es später wirken würde. Hier hängt das Aufgeben nur
  am Besitz; hängt die Wirkung am Ort (Wasser vor ihm, Werkbank daneben), gibt er zu früh
  auf. Gegenprobe in Crafter: Trinken und Werkbank werden nicht seltener (44 statt 43 %,
  17 statt 9 %).
- Schmidhuber 1991 und Oudeyer & Kaplan 2007 messen Lernfortschritt als Verbesserung der
  Vorhersage, nicht als Zählung. Die feste Zahl 20 ist ein grober Ersatz.
- Burda u. a. 2019: Auch Neugier mit gelernten Merkmalen bleibt an echtem Rauschen hängen.
  Dasselbe passiert jetzt bei den Rekorden (Position, Blickwinkel); H36 behebt das nicht.

**Ohne Grundlage (neu in 0.22):** 20 Versuche ohne Wirkung je Besitz (`FUTILE`); „Besitz“
als einziger Zusammenhang, in dem neu gezählt wird.

## Umgesetzt in 0.21 (Gefahren mit Unsicherheit, H35)

Abgeleitet aus Ergebnis 24 und einem Vorschlag aus der Auswertung des Active-Inference-Agenten:
Die Quote war schon ein Beta-Mittel ((Treffer + 1) / (Fälle + 2)), aber die feste Schwelle von
5 Treffern und das Abdecken über viele Literale verwarfen die Unsicherheit. Eine Prüfung auf 8
Karten: Vor 255 Zombie-Treffern war er 113-mal in Abwehr, 109-mal galt eine falsche gelernte
Lage (oft Gras), 33-mal kannte er keine.

| Hypothese | Stand |
|---|---|
| H35: Eine Gefahr ist eine einzelne Aussage, deren Schadensquote mit Sicherheit über einer Schwelle liegt (Beta-Verteilung), statt einer Bedingung aus dem Abdecken mit fester Trefferzahl | **teilweise gestützt** (Ergebnis 25): Er lebt etwa 10 Schritte länger (bekannte Karten +12,8 ± 3,7, neue Karten +7,7 ± 4,2, Karte für Karte gegen 0.20). Keine Treffer mehr ohne bekannte Gefahr (vorher 33 von 255). Wertung nur innerhalb der Streuung besser (3,0 statt 2,7 % auf bekannten Karten, auf neuen gleich). Die Hälfte der Treffer kommt weiter ohne Abwehr, weil die gelernte Gefahr gerade nicht galt (oft kein Gitter, also keine Gruppe „nah bei mir“) |

**Gegenstimmen und Warnungen zu 0.21:**
- Lissek u. a. 2005 (Metaanalyse zur Angstkonditionierung bei Angststörungen): Wer Gefahr zu
  leicht annimmt, verallgemeinert die Angst und meidet zu viel. Gegenprobe: Abwehr nimmt 7 %
  seiner Schritte ein (0.20: 6 %), und die Wertung sinkt nicht.
- Nesse 2005 (Rauchmelder-Prinzip): Ist die Abwehr billig und der Schaden teuer, sind viele
  Fehlalarme richtig. Das spricht für eine niedrige Schwelle; wie billig die Abwehr hier ist,
  misst er nicht, darum bleibt die Schwelle fest.
- Rescorla & Wagner 1972, Kamin 1969 (Blockieren): Reize teilen sich die Vorhersage; wer jeden
  Reiz einzeln zählt, hält auch Begleiter der Gefahr für gefährlich (vereinzelte
  Zufallstreffer wie „eine Werkbank fünf Felder entfernt“). Nicht abgebildet.

**Ohne Grundlage (neu in 0.21):** 95 % Sicherheit (`CONFIDENCE`); die Schwelle 15 %
(`DANGER`) gab es schon.

## Umgesetzt in 0.20 (Überleben und Wege, H32 bis H34)

Abgeleitet aus Ergebnis 23: Er starb so früh wie der Zufall, als beste Abwehr stand oft eine
Taste ohne Wirkung, und auf dem Weg zum Wasser lief er in 55 % der Schritte gegen etwas.

| Hypothese | Stand |
|---|---|
| H32: Abwehr als Option (bei einer Antwort bleiben, bis die Gefahr vorbei ist; als Ganzes abrechnen), mit wenigen Antworten | **teilweise gestützt** (Ergebnis 24): Er besiegt Zombies in 8 % der Runden statt 2 bis 3 % (0.19, zwei Messungen). Er lebt aber nicht länger (171 statt 175 Schritte): 7 von 10 Zombie-Treffern kommen ohne Abwehr in den drei Schritten davor, weil er die Gefahr nicht erkennt. Die Option hilft also, wo die Gefahr erkannt ist; das Erkennen ist die Lücke |
| H33: Neuer Besitz, neuer Versuch (Versuche zählen je nach dem, was er bei sich hat) | **offen**: Nur zusammen mit dem Ort-Fehler gemessen; zusammen stiegen die Erfolge je Runde von 2,4 auf 2,9. Werkbank und Werkzeug wurden dabei nicht häufiger |
| H34: Hindernisse aus eigener Bewegung, Wege um sie herum, „vorne“ als Fühler | **gestützt für die Wege**: Anteil der Schritte gegen ein Hindernis beim Trinken von 55 auf etwa 35 %, Trinken in 43 statt 32 bis 38 % der Runden. Gesamt (alle drei): Wertung 2,7 statt 2,5 %, je Startwert 2,24 ± 0,11 gegen 1,9 bis 2,0 %, 3,0 statt 2,4 bis 2,6 Erfolge je Runde. Werkbank seltener (9 statt 14 bis 21 %), Ursache offen |

**Gegenstimmen und Warnungen zu 0.20:**
- Bolles 1970 (artspezifische Abwehrreaktionen): Vermeiden lernen Tiere leicht nur, wenn die
  verlangte Antwort zu Flucht, Erstarren oder Kampf gehört; eine beliebige Antwort lernen sie
  kaum. Das spricht gegen „jede Taste ist eine Antwort“ (0.19) und für eine kleine Auswahl,
  aber auch dagegen, dass ein Agent ohne solche angeborenen Antworten sie schnell findet. Hier
  ist die Auswahl (hin, weg, quer, Taste daran) eine Annahme, keine gelernte.
- Harb, Bacon, Klissarov & Precup 2018 (Abwägungskosten bei Optionen): Zu lange Optionen
  verlieren Reaktionsfähigkeit, zu kurze bringen nichts. Darum bricht die Option ab, sobald
  die Gefahr nicht mehr gilt, und dauert höchstens 8 Schritte (ohne Grundlage).
- Eigener Gegenversuch: Gesundheit sinkt auch bei leerem Bedürfnis. Solche Fälle aus dem
  Lernen der Gefahren herauszunehmen, ließ zu wenige Fälle übrig, und die gelernten Gefahren
  wurden schlechter. Nicht übernommen.

**Ohne Grundlage (neu in 0.20), Suchauftrag für Runde 8:**
- Abwehr: Option und Schadensfenster 8 Schritte (`HARM_WINDOW`).
- Hindernis: ab 5 gescheiterten Schritten (`MIN_BLOCKED`) und 80 % gescheitert (`BLOCKING`).
- Neuer Besitz: nur „über 0 oder nicht“, nicht wie viel.

## Umgesetzt in 0.19 (Raum aus eigener Bewegung, H29 bis H31)

Abgeleitet aus Ergebnis 22: Gefahren und Ursachen hingen an einzelnen Feldern der Sicht.

| Hypothese | Stand |
|---|---|
| H29: Raum aus eigener Bewegung (welches Sichtfeld neben welchem liegt, die eigene Stelle als Lücke) macht Bedingungen unabhängig von der Seite | **gestützt für den Raum, teilweise für die Bedingungen** (Ergebnis 23): Nach 10 Runden hat er auf 10 bis 11 von 16 Karten ein Gitter mit eigener Stelle, fast immer alle 62 Felder richtig; in etwa jedem zehnten Fall ist ein Block um ein Feld verschoben. Gefahren als Gruppe („Zombie irgendwo im Abstand ≤ 3“) auf 2 von 8 geprüften Karten. Wertung 2,5 statt 2,0 % (0.18), je Startwert 1,92 ± 0,13 gegen 1,49 ± 0,16 %; Holz 59 statt 39 %, Werkbank 21 statt 8 % |
| H30: Abwehr mit Richtung (hin, weg, quer, Taste an der Gefahr), gut ist, was die Gefahr beendet | **nicht gestützt**: Er stirbt so früh wie vorher (175 Schritte). Als beste Antwort steht oft eine Taste ohne Wirkung; Zombies laufen nach. Beim Prüfen der Einzeländerungen verdreifachte „Taste an der Gefahr“ die besiegten Zombies (5 bis 6 statt 2 %), in der Endmessung waren es 2 % |
| H31: Neugier auf Sichtfelder (hingehen, um Neues anzufassen) | **offen**: Teil des Pakets, das Holz, Werkbank und Werkzeug häufiger macht; einzeln ohne messbaren Unterschied (innerhalb der Streuung) |

**Gegenstimmen und Warnungen zu 0.19:**
- Finney, Gardiol, Kaelbling & Oates 2002 („The thing that we tried didn't work very well:
  deictic representation in reinforcement learning“): Eine Sicht „vom Agenten aus“ macht
  Lagen ununterscheidbar, die verschieden behandelt werden müssen, und kann das Lernen
  verschlechtern. Darum ersetzen die Gruppen hier die einzelnen Felder nicht, sondern kommen
  als weitere Literale dazu; das Abdecken wählt.
- Herrnstein 1969: Vermeiden wird nicht (nur) dadurch belohnt, dass die Gefahr endet,
  sondern dadurch, dass weniger Schaden folgt. Darum zählt hier beides: Schaden und ob die
  Gefahr noch da ist.
- Eigene Beobachtung: Im Gras passt beim Zählen „hat i den Wert von j“ fast alles. Die
  Arbeiten zum Raum aus Sensomotorik (Philipona 2003, Laflaquière 2019) nutzen reiche,
  veränderliche Eindrücke; erst das Zählen nur bei Änderungen trennt hier Nachbarn von
  Zufallstreffern.

**Ohne Grundlage (neu in 0.19), Suchauftrag für Runde 8:**
- Raum: Nachbar ab 90 % (`FLOW_SHARE`), bei Änderungen 80 % (`CHANGE_SHARE`, ab 4
  Änderungen), Abstand 0,01 zum Zweitbesten, Ort bei 95 % gleichem Schritt nach 20 % der
  Drücke und 6 Werten, 20 echte Schritte, 4 Verschiebungen je Taste, 90 % des Kastens,
  dreimal zurechtrücken, Gruppen bis Abstand 3, Neubau alle 100 Schritte.
- Abwehr: Die Gefahr, die nach 5 Schritten noch da ist, kostet so viel wie 1 Schaden.
- Neugier: 5 Versuche je Taste und Wert.

## Umgesetzt in 0.18 (eigene Ziele und Crafter, H25 bis H28)

Neue Hypothesen, abgeleitet aus der Crafter-Prüfung vom 29. Oktober 2026 (dort hieß der
Vorschlag „Nacht als Kontext“ noch H27; er ist verschoben):

| Hypothese | Stand |
|---|---|
| H25: Ziele und Teilziele aus gelernten Ursachen (Mittel-Ziel-Analyse über Bedingungen, die der Agent selbst findet) | **gestützt in der Testwelt, teilweise in Crafter** (Ergebnis 22): Er lernt etwa „Holz steigt nach Taste X, wenn vorne ein Baum ist“ (32 von 32 auf der Seite) und „Holzspitzhacke steigt, wenn vorne eine Werkbank ist und Holz ≥ 1“, und sammelt Holz öfter (39 statt 25 %), Werkbank und Werkzeug nur wenig öfter (8 statt 5 %, je 2 statt 1 %). Viele Ursachen bleiben übergenau (zufällige Nebenfelder als Literal); längere Ketten (Stein-, Eisenwerkzeug) schafft er nicht |
| H26: Ein mitwanderndes Sichtfeld als „übernimmt den Nachbarn“, Planen mit Lücken | **teilweise**: Mit Rauschen (Tiere) braucht Übernehmen eine Toleranz; die strenge Fassung lässt viele Sichtfelder ohne Regel. Raum (welches Feld neben welchem) folgt daraus noch nicht |
| H27: Eigene Ziele (Bedürfnisse, Rekorde, Versuche) bringen ohne äußere Belohnung voran | **teilweise** (Ergebnis 22, 16 Startwerte): Was er sich vornimmt, schafft er öfter (Trinken 27 statt 8 %, Holz 39 statt 28 % gegen 0.17), in der Wertung aber nur 2,0 statt 1,6 %, je Startwert innerhalb der Streuung, weil er leichte Zufallserfolge verliert. In der Testwelt „Quelle“ hebt er einen Vorrat, den ihm niemand als Ziel nennt (Test). Gegenstimme bestätigt: Neugier allein bleibt in Crafter bei etwa 2 % (Hafner 2021, Plan2Explore, RND) |
| H28: Gefahren lernen und meiden | **nicht gestützt**: Er stirbt so früh wie Zufall (etwa 170 Schritte). Gefahren hängen an einzelnen Feldern; Flucht hilft nicht, weil Zombies hinterherlaufen |

**Gegenstimmen und Warnungen zu 0.18:**
- Burda u. a. 2019 (Neugier im großen Maßstab): Neugier allein scheitert an Zufall im Bild
  („rauschender Fernseher“). Unsere Neugier ist Zählen, nicht Vorhersagefehler; bei Tieren im
  Bild bleibt das Risiko.
- Sutton 2019 („The Bitter Lesson“): Von Hand gebaute Antriebe skalieren schlechter als
  allgemeine Lernverfahren. Die Antriebe hier sind allgemein (keine Spielnamen), aber ihre
  Reihenfolge ist von Hand.
- Pyke 2015: Die Lévy-Hypothese bei Tieren ist umstritten. Wir nutzen nur gerade Strecken
  zufälliger Länge, ohne Anspruch auf Optimalität.
- Hafner 2021: Erfolge in Crafter hängen am Überleben; ohne Abwehr bleibt jede Wertung klein.

**Ohne Grundlage (neu in 0.18), Suchauftrag für Runde 8:**
- Ursachen: höchstens 3 Literale (`MAX_LITERALS`), 4 Ursachen (`MAX_CAUSES`), mindestens
  2 Treffer (`MIN_HITS`), Genauigkeit 0,34 (`MIN_PRECISION`), seltene Ursache ab 5 % (`WEAK`),
  Gedächtnis 400 Schritte je Taste, Neulernen alle 100 bzw. 250 Schritte.
- Teilziele: Tiefe 3, drei Ursachen je Teilziel, 200 vorgestellte Zustände.
- Eigene Ziele: dringend ab der Hälfte, Pflege ab 90 %, 60 Schritte Geduld, „sinkt nach 75 %
  der Tasten“ = Bedürfnis, „nach 50 %“ = Schaden, Mengen ändern sich in 80 % der Fälle um 1,
  Schaden in 5 Schritten, Gefahr ab 15 % und 5 Treffern, Taste meiden ab 50 %, 3 gedachte
  Fälle beim Schrumpfen, Strecken von 4 bis 12 Schritten, 15 % Neugier beim Erkunden.
- Synthese: Übernehmen trotz Rauschen ab 90 % von 10 Wechseln; Regeln mit Ausnahmen nach 200
  Schritten neu suchen.
- Die Reihenfolge der Antriebe (Abwehr, Bedürfnis, Ziel, Versuch, Rekord, Pflege, Erkunden).

## Umgesetzt in 0.17 (Test von H21 bis H24 nach Runde 7)

| Vorschlag aus Runde 7 | Stand |
|---|---|
| H21: Form als Grammatik, Suche im Modell als Rückfall | **gestützt** (Ergebnis 20): „Ring × Ring × Ring“ bei den Drehscheiben und „Rutschbahn mit 2 Dimensionen“ auf Eis in 10 von 10 Läufen; 0.16 hielt beides für einen Raum oder eine Ordnung. Drehscheiben 9,6 statt 13,9 Schritte (bestenfalls 9,6). Tauschen hat keine Form: Mit Suche im Modell 7,7 Schritte (bestenfalls 7,5), ohne 762. Die Laplace-Koordinaten von Mahadevan 2007 wurden nicht gebaut, die Grammatik reichte |
| H22: ein Schleifenbaustein „Schritt, bis Schalter“ | **gestützt** (Ergebnis 20): Eis 11,9 statt 98 Schritte (bestenfalls 5,0, Tabelle 86). Das ist noch mehr als das Doppelte des kürzesten Wegs: Wo er noch nicht war, weiß er nicht, wo das Rutschen endet |
| H23: neue Welt per Bayes-Faktor | **teilweise** (Ergebnis 19 und 21): Ganz verschiedene Welten im selben Strom (Raum → Suchbaum → Drehscheiben → Raum) erkennt schon der Binomial-Test aus 0.16 meist (80 / 100 / 100 %), der Bayes-Faktor gleich oft. Er legt weniger überzählige Karten an (1,3 statt 1,7) und findet doppelt so oft die erste Karte wieder (80 statt 40 %), braucht aber mehr Schritte (Suchbaum 78 statt 61, Drehscheiben 90 statt 67). Bei vertauschten Tasten ist der Binomial-Test schneller (zurück in A 11 statt 41 Schritte). Schwelle nach Kass & Raftery, Wechselrate ohne Grundlage |
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
