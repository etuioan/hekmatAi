# HekmatKI Prototyp 0.19: Schema-Stapel, Weltmodell und ein allgemeiner Agent für fremde Welten

Dieser Prototyp prüft zwei Hypothesen aus dem Forschungsdossier, mit möglichst wenig Code:

- **H11:** Wenn ähnliche Situationen zu einem gemeinsamen Schema verschmolzen werden, lernt der Agent eine neue, ähnliche Situation aus wenigen Beobachtungen.
- **H12:** Wenn der Agent erkennt, welche Situation gerade gilt, und nur deren Modell aktualisiert, vergisst er weniger als ein Agent mit einem einzigen gemeinsamen Modell.

Version 0.3 verbindet beide: Erkennt der Agent eine neue Situation, baut er ihr Modell sofort aus einem Schema, das er vorher aus seinen eigenen Kontexten gebildet hat. In Version 0.4 entscheidet der Agent selbst, wann er schläft, und neue Situationen wachsen ins Schema hinein. Version 0.5 erlaubt mehrere Schemata und prüft mit einem Ampelspiel, ob der Agent ein Schema als Schnittmenge in einem größeren Modell wiederfindet, ohne zu verschmelzen.

Bewusst nicht enthalten: Bilder, neuronale Netze, LLMs, Planung. Diese Module kommen erst dazu, wenn die Idee im Kleinen trägt.

## 1. Begriffe

| Begriff | Bedeutung im Code |
|---|---|
| Symbol | Eine Beobachtung, z. B. `"name aufgerufen"`. |
| Rolle | Ein abstrakter Zustand eines Schemas, z. B. `"hinweis"`. |
| Situation | Die „echte Welt“ der Simulation: eine Rollenstruktur plus eine Zuordnung Rolle → Symbol. Erzeugt Beobachtungsfolgen. |
| Situationsmodell (Ebene 1) | Was der Agent über eine Situation gelernt hat: ein Markov-Modell über Symbole. |
| Schema (Ebene 2) | Ein Markov-Modell über Rollen. Mehrere Situationsmodelle mit gleicher Struktur teilen sich ein Schema. |
| Meta-Schema (Ebene 3) | Ein Schema über Schemata: entsteht, wenn sich Schemata ähnlich genug sind und ihr Handlungswissen sich nicht widerspricht (seit 0.8). |
| Scheibe | Oberbegriff für jede Ebene des Stapels: erlebte Situation, Schema oder Meta-Schema. |
| Spielmodell | Was der Entdecker über ein Spiel weiß: wohin jede Taste in jedem Zustand geführt hat (seit 0.9). |
| Spiel-Schema | Ein Spielmodell mit neutralen Namen für Zustände und Tasten. |
| Deutung | Eine Hypothese, wie ein neues Spiel auf ein Spiel-Schema passt: Tastenbelegung plus Zuordnung der bisher gesehenen Symbole. |
| Ratgeber | Vorwissen, das dem Entdecker Tasten empfiehlt und widerlegte Deutungen streicht (`Advisor`, seit 0.11). |
| Regel-Schema | Pro Modus ein Ereignis (Wechsel oder Sieg) und die Orte, an denen Benutzen es auslöst. Unabhängig von der Länge des Gangs (seit 0.11). |
| Karte | Wo jedes Symbol unter einer Tastendeutung liegt: Position vom Start aus und Modus, dazu Wände und Wirkungen von Benutzen. |
| Farbraster | Was der Agent in der 2D-Welt sieht: eine Farbe pro Feld (seit 0.12). |
| Wirkung | Was das Betreten einer Farbe bewirkt: blockiert, frei, Auslöser (färbt andere Farben um), zurück (zum Start), Ziel. |
| Weltmodell | Was der Modell-Agent über die Regeln eines Spiels glaubt: Figur, Tasten, Regel pro Farbe, worauf sich Kisten schieben lassen, Fernwirkungen (seit 0.13). |
| Regel | Was passiert, wenn die Figur eine Farbe betreten will: blockiert, frei, schiebbar, zurück, Ziel. |
| Ereignis | Eine Farbe wird verdeckt (von Figur oder Kiste) oder wieder aufgedeckt. |
| Fernwirkung | Welche Farben anderswo wechseln, wenn ein Ereignis eintritt (Platte verdeckt: Tor offen). Unsicher, solange sie nur zusammen mit einem anderen Ereignis zu sehen war. |
| Szene | Das Raster, wie der Modell-Agent es versteht: Figur, Kisten und der Hintergrund darunter. Darin plant er. |
| Rolle (2D-Welt) | Eine Farbe, benannt nach ihrer Wirkung, mit ihrem Aussehen (ein Feld oder viele, Rand oder innen). |
| Ortsbeschreibung | „Wand“ in einer Richtung oder „n Schritte vom Start“ in einer Richtung (`Place`). |
| Bindung | Eine eindeutige Zuordnung Symbol → Rolle. Sie setzt den Inhalt einer Situation in ein Schema ein. |
| Kontext | Eine vom Agenten vermutete Situation, zu der ein eigenes Situationsmodell gehört. |
| Schnittmenge | Ein Teil eines größeren Modells, in dem die Struktur eines Schemas vollständig steckt. Wird als Zuordnung gespeichert, ohne Modell oder Schema zu verändern. |
| Handlungswissen | Pro Rolle eines Schemas: wie oft Handeln dort versucht wurde und wie oft es klappte. Selbst gelernt (seit 0.7). |

## 2. Datenstrukturen

**`MarkovModel`** zählt Übergänge `vorher → nachher` über einem festen Alphabet. Die Wahrscheinlichkeit wird mit einem Pseudozähler geglättet, damit nie eine Null entsteht. Es kann umbenannt werden (`relabeled`), womit ein Situationsmodell in Rollen übersetzt wird.

**`Situation`** beschreibt die Simulation: Übergangswahrscheinlichkeiten zwischen Rollen und eine Rollen-Symbol-Zuordnung. Ungültige Wahrscheinlichkeiten (Summe ≠ 1, unbekannte Rollen) führen sofort zu einem Fehler.

**`Schema`** besteht aus einem Namen, einem `MarkovModel` über seinen Rollen und dem Handlungswissen pro Rolle (`action_knowledge`, Abbildung Rolle → `ActionRecord`). Handlungswissen für unbekannte Rollen führt zu einem Fehler.

**`ActionRecord`** (`action.py`) zählt Versuche und Erfolge. Die Erfolgswahrscheinlichkeit ist `(Erfolge + 0,5) / (Versuche + 1)`, also 0,5 ohne jede Erfahrung.

Alle Modelle, die Vorhersagen machen, erfüllen dasselbe Protokoll `Predictor` mit der Methode `probability(previous, following)`. Dadurch gibt es genau eine Bewertungsfunktion für alle Modelle.

## 3. Verschmelzen zweier Situationsmodelle (Konvergenz)

Zwei Situationsmodelle A und B werden verglichen, indem alle Zuordnungen der Symbole von B auf die Symbole von A ausprobiert werden (Strukturabbildung nach Gentner). Für jede Zuordnung wird der mittlere absolute Unterschied der Übergangsmatrizen berechnet. Die beste Zuordnung gewinnt.

- Ist der Unterschied kleiner als ein Schwellenwert (Standard 0,1), entsteht ein Schema. Seine Zählungen sind die Summe beider Modelle, in Rollen übersetzt.
- Sonst entsteht kein Schema. Das wird ausdrücklich als `None` zurückgegeben und nicht verschwiegen.
- `merge` liefert ein `MergeResult` mit Schema, Abstand und den beiden Zuordnungen Symbol → Rolle. Darüber wird Wissen, das pro Symbol gesammelt wurde (Handlungswissen), auf die Rollen übertragen.
- Seit 0.8 steckt das in `merge_schemas`, das Scheiben jeder Ebene samt Handlungswissen verschmilzt; `merge` ist die Kurzform für Modelle ohne Handlungswissen. Mit `check_decisions` (Standard) sind Zuordnungen verboten, unter denen sich das Handlungswissen widerspricht: In einer Rolle, die beide Seiten ausprobiert haben, lohnt sich Handeln bei der einen und bei der anderen nicht (`action.decisions_conflict`). Gibt es keine erlaubte Zuordnung, ist der Abstand unendlich.

Die Suche steckt in `structure.best_match` und ist dieselbe wie bei der Schnittmenge (Abschnitt 7): Verschmelzen ist eine Schnittmenge, die alle Symbole umfasst. Bei vier Symbolen gibt es 24 Zuordnungen. Ausprobieren ist hier einfacher und verständlicher als jeder clevere Algorithmus. Für mehr als 8 Symbole bricht der Code mit einer klaren Fehlermeldung ab, statt still sehr langsam zu werden.

## 4. Neue Situation aus einem Schema lernen

Für eine neue Situation mit unbekannten Symbolen kennt der Agent nur wenige Beobachtungen. Er weiß nicht sicher, welches Symbol welche Rolle hat. Darum bildet er für jede mögliche Bindung ein Modell, bewertet es danach, wie gut es die Beobachtungen erklärt, und mittelt alle Modelle gewichtet (Bayessche Modellmittelung, Klasse `OnlineMixture`). Es gibt drei Varianten:

| Variante | Funktion | Verhalten |
|---|---|---|
| starr | `fixed_schema_predictor` | Die Situation wird genau wie das Schema vorhergesagt. Die Beobachtungen bestimmen nur die Bindung. |
| lernend | `adaptive_schema_predictor` | Das Schema ist Vorwissen im Umfang von 10 Beobachtungen pro Zustand (`instantiate`). Die Beobachtungen korrigieren es. |
| geprüft | `schema_or_flat_predictor` | Wie lernend, aber zusätzlich steht ein Modell ohne Vorwissen zur Wahl. Vorab gilt „Schema passt“ und „Schema passt nicht“ je zur Hälfte, dann entscheiden die Daten. |

Bewertet wird jedes Modell, indem es jede Beobachtung vorhersagt, bevor es sie lernt. So misst die Bewertung ehrlich die Vorhersagekraft.

Vergleich: ein „flacher“ Lerner, der dieselben Beobachtungen ohne Schema in ein neues `MarkovModel` zählt.

## 5. Kontextwechsel

Der `ContextInference`-Agent hält eine Liste von Kontexten, jeder mit eigenem `MarkovModel`. Für jede neue Beobachtung:

1. Für jeden bekannten Kontext wird berechnet, wie wahrscheinlich die Beobachtung in ihm war.
2. Diese Wahrscheinlichkeit wird mit einer „klebrigen“ Vorannahme verrechnet: Mit `stay_probability` (Standard 0,95) bleibt die Verteilung über die Kontexte, wie sie war. Der Rest ist ein möglicher Wechsel: Davon geht `new_context_share` (Standard 0,03) an „neuer Kontext“, der Rest gleichmäßig an die bekannten Kontexte.
3. Die Option „neuer Kontext“ wird wie ein Kontext behandelt: Ihre Wahrscheinlichkeit wird von Schritt zu Schritt weitergetragen, so sammeln sich Belege über mehrere Beobachtungen (seit 0.6; vorher musste ein einzelner Schritt reichen). Womit ein neuer Kontext startet, ist austauschbar (`new_context_model` bzw. `replace_new_context_model`): standardmäßig ein leeres `MarkovModel`, nach einer Schlafphase ein Modell aus dem Schema.
4. Der wahrscheinlichste Kontext wird aktiv. Nur sein Modell lernt die Beobachtung (Gating).

Das ist eine vereinfachte Form der Latent-Cause-Modelle (Gershman 2010) und von COIN (Heald 2021). Ein Sprung im Vorhersagefehler löst den Wechsel aus, wie bei Ereignisgrenzen (Zacks 2007).

Vergleich: ein Agent mit einem einzigen gemeinsamen `MarkovModel`.

## 6. Kontextwechsel und Scheiben verbunden

Ablauf in drei Phasen, wie ein Wach-Schlaf-Zyklus:

1. **Wach:** Der Agent erlebt Arzt und U-Bahn im Wechsel und findet die Kontexte selbst (Abschnitt 5). Er weiß nicht, welche Situation wirklich gilt.
2. **Schlaf:** Er vergleicht alle Paare seiner eigenen Kontexte und verschmilzt das ähnlichste Paar zum Schema „Warten“ (Abschnitt 3). Lässt sich kein Paar verschmelzen, bricht der Code mit einer klaren Fehlermeldung ab.
3. **Wach:** Ab jetzt startet jeder neue Kontext als „geprüftes“ Modell aus dem Schema (`schema_or_flat_model`, Abschnitt 4). Passt das Schema nicht, übernimmt das Modell ohne Vorwissen.

Die Testwelt dafür (`lamp_situations`): Arzt, U-Bahn und Gate zeigen dieselben vier Lampen (rot, grün, blau, gelb), aber jede Farbe bedeutet an jedem Ort etwas anderes. Der Agent muss also am Ablauf erkennen, wo er ist, und das Schema muss die Bedeutung der Farben neu zuordnen.

Die Option „neuer Kontext“ ist ein noch unbenutztes Startmodell. Erst wenn sie gewinnt, kommt sie in die Liste der Kontexte und lernt; bekannte Kontexte bleiben dabei unverändert (Gating).

### Selbst gesteuerter Schlaf (`WakeSleepAgent`, ab 0.4)

Der Agent führt neben jedem Kontext ein **Erfahrungsgedächtnis**: ein `MarkovModel`, das nur zählt, was in diesem Kontext tatsächlich erlebt wurde. Das Vorhersagemodell eines Kontexts kann Schema-Vorwissen enthalten; das Erfahrungsgedächtnis nie. Verschmolzen wird immer nur Erfahrung, damit das Schema sein eigenes Vorwissen nicht doppelt zählt.

- **Reife:** Ein Kontext ist gereift, wenn er mindestens `maturity` Übergänge erlebt hat (Standard 100).
- **Wann schlafen:** nach jedem Schritt, in dem die Zahl gereifter Kontexte gestiegen ist.
- **Was im Schlaf passiert:** Gibt es noch kein Schema, entsteht es aus dem ähnlichsten Paar gereifter Kontexte. Danach wird jeder gereifte Kontext, der noch nicht im Schema steckt, mit dem Schema verschmolzen, wenn sein Strukturabstand unter dem Schwellenwert liegt. Passt er nicht, bleibt er draußen und wird beim nächsten Schlaf erneut geprüft. Zum Schluss starten neue Kontexte aus dem aktualisierten Schema.
- Mit `maturity=None` schläft der Agent nur, wenn `sleep()` von außen aufgerufen wird. Dann gilt jeder Kontext als gereift. Das Experiment aus 0.3 nutzt diesen Modus.

### Mehrere Schemata (ab 0.5)

Im Schlaf tritt jeder gereifte Kontext, der noch in keinem Schema steckt, dem Schema bei, zu dem er strukturell am nächsten ist, sofern der Abstand unter dem Schwellenwert liegt. Danach gründet das ähnlichste Paar der übrigen gereiften Kontexte ein neues Schema. Beides wiederholt sich, bis sich nichts mehr ändert. `max_schemas` begrenzt die Zahl der Schemata (für den Vergleich mit 0.4).

Neue Kontexte starten aus allen Schemata zugleich (`schemas_or_flat_model`): Vorab gilt je die Hälfte für „ein Schema passt“ (gleich verteilt auf die Schemata, dann auf ihre Bindungen) und „kein Schema passt“.

## 7. Schnittmenge und Ampelspiel (ab 0.5)

**Ampelspiel** (`game.py`). Zustände: `autos fahren`, `ampel gelb`, `ampel grün`, `drüben`, `verpasst`, `unfall`. Aktionen: warten, laufen. Beim Warten läuft das Spiel wie eine Wartesituation ab (Autos bleiben mit 0,8, Gelb bleibt mit 0,2, sonst geht es weiter; nach Grün kommt `verpasst`). Laufen bei Grün führt zu `drüben`, Laufen sonst zu `unfall`. Nach `drüben`, `verpasst` oder `unfall` beginnt eine neue Runde.

**Schnittmenge** (`overlap.py`). Für jedes Schema werden alle Zuordnungen seiner Rollen zu gleich vielen Symbolen des Modells ausprobiert (bei 6 Symbolen und 4 Rollen: 15 Teilmengen × 24 Reihenfolgen). Verglichen werden nur die Übergänge zwischen den zugeordneten Symbolen, als mittlerer absoluter Unterschied. Die nächste Zuordnung über alle Schemata gewinnt, wenn sie unter dem Schwellenwert 0,1 liegt. Die Suche ist dieselbe wie beim Verschmelzen (`structure.best_match`); nur dürfen hier Symbole des Modells übrig bleiben. Gespeichert wird nur die Zuordnung (`Overlap`); Modell und Schema werden nicht verändert.

**Handlungswissen lernen** (seit 0.7, `action.py`). Während der Agent eine Alltagssituation erlebt, probiert er in jedem Schritt mit Wahrscheinlichkeit 0,1 zu handeln (`try_actions`). Er erfährt nur, ob es geklappt hat. Die Weltregel der Simulation: Handeln klappt genau beim Symbol der Rolle `ereignis`, im Gespräch nirgends. Seit 0.8 steht das bei jeder Situation selbst (`Situation.action_role`; beim Anstehen ist es `dran sein`). Das Ausprobieren verändert den Ablauf der Situation nicht. Beim Verschmelzen wird das Wissen beider Situationen über die Zuordnungen aus `MergeResult` auf Rollen übertragen (`by_role`) und addiert (`combined`).

**Spieler** (`player.py`). Er zählt alle Übergänge im Spiel (sein Spielmodell) und pro Zustand, wie oft Laufen versucht wurde und wie oft es zum Ziel führte. Er läuft, wenn die geschätzte Erfolgswahrscheinlichkeit über 0,5 liegt; in Zuständen mit weniger als 3 Versuchen probiert er Laufen mit Wahrscheinlichkeit 0,2 aus. Nach jeder Runde (ab 20 Beobachtungen) sucht er eine Schnittmenge. Findet er eine, leiht er sich für jeden Zustand der Schnittmenge, dessen Rolle Handlungswissen hat, Erfahrung im Umfang von 5 Versuchen: Erfolg mit der gelernten Erfolgswahrscheinlichkeit dieser Rolle.

### Schema-Stapel (`stack.py`, ab 0.8)

`experience` erlebt eine Situation: Übergänge zählen und mit Wahrscheinlichkeit 0,1 pro Schritt handeln. Das Ergebnis ist die unterste Scheibe (eine `Group` aus Schema und Namen der Situation). `consolidate` macht aus einer Ebene die nächste: Es sucht unter allen Paaren das mit dem kleinsten Abstand, das verschmelzen darf (`merge_schemas`), verschmilzt es und wiederholt das, bis kein Paar mehr passt. Was nirgends passt, bleibt als eigene Scheibe erhalten. Jede verdichtete Scheibe merkt sich, aus welchen Situationen sie entstanden ist. Ebene 2 entsteht mit Schwellenwert 0,1, Ebene 3 mit 0,2, beide mit derselben Funktion.

### Spielefamilie und Entdecker (ab 0.9)

**Spiele** (`puzzle.py`). Ein Gang mit `length` Feldern; Start, Schlüssel und Tür liegen auf festen Feldern (`Layout`). Verborgener Zustand: Position und ob der Schlüssel getragen wird. Tasten: links, rechts, benutzen; an den Enden bleibt man stehen. Benutzen am Schlüssel nimmt ihn, benutzen an der Tür mit Schlüssel (oder bei `needs_key=False` auch ohne) ergibt `WIN`, danach beginnt das Spiel am Start. `make_game` vergibt zufällige Symbole (Farbe + Form) und eine zufällige Tastenbelegung.

**Entdecker** (`explorer.py`). Er merkt sich jeden Übergang (`model`). Pro Schritt: (1) eigener kürzester Weg zum Sieg, falls bekannt; (2) sonst der Rat seines Vorwissens (`Advisor`). Beim Spiel-Schema empfiehlt jede noch mögliche Deutung die erste Taste ihres Wegs zum Sieg im Schema, es gewinnt die häufigste Empfehlung (Gleichstand per Zufall); (3) sonst Neugier: eine hier noch nie gedrückte Taste oder der kürzeste Weg zu einem Zustand mit einer solchen.

**Deutungen** (`game_schema.py`). Zu Beginn eines Spiels gibt es eine Deutung pro Tastenbelegung (bei 3 Tasten 6), jede mit Start → Start des Schemas. Bei jeder Beobachtung (Zustand, Taste, Ergebnis) prüft jede Deutung: Kennt sie den Zustand und kennt das Schema den Übergang, muss das Ergebnis zum vorhergesagten Schema-Zustand passen. Ein neues Symbol bekommt den vorhergesagten Zustand, sofern dieser noch frei ist. Sonst ist die Deutung widerlegt und fällt weg. Beobachtungen, die eine Deutung noch nicht prüfen konnte, werden später nicht nachgeprüft (Vereinfachung).

**Neugier** (`curiosity.py`, ab 0.10). Mit `Curiosity` prüft der Entdecker vor dem Gehen eines bekannten Wegs zum Sieg jeden Abstecher: zu einem bekannten Zustand gehen und dort eine nie gedrückte Taste probieren. Wert eines Abstechers (`Detour.value`): `Überraschung × zusätzliche Siege − verlorene Siege`. Zusätzliche Siege = verbleibende Tastendrücke nach dem Abstecher × (1/Abkürzungsrunde − 1/bekannte Runde), wobei die Abkürzungsrunde der Weg vom Start zu diesem Zustand plus 1 ist (die Taste gewinnt sofort). Verlorene Siege = Mehrschritte des Umwegs / bekannte Runde. Überraschung ist `surprise` (Standard 0,1) oder `schema_surprise` (0,05), wenn alle noch möglichen Deutungen dasselbe Ergebnis für diese Taste vorhersagen. Der Abstecher mit dem höchsten positiven Wert gewinnt, sonst geht der Agent seinen Weg.

**Schlaf nach einem Spiel.** Nach dem ersten Spiel wird das Spielmodell neutral umbenannt (`schema_from_model`). Nach jedem weiteren ergänzt die Deutung mit den meisten Zuordnungen das Schema um alle Übergänge, deren Zustände sie zuordnen kann (`merged_schema`).

### Regel-Schemata (`rules.py`, ab 0.11)

**Kernwissen.** Das Spiel ist ein Gang mit drei Tasten: vorwärts, rückwärts, benutzen. Eine Tastendeutung (`Controls`) legt fest, welche Taste welche ist; bei drei Tasten gibt es sechs.

**Karte** (`corridor_map`). Unter einer Deutung bekommt der Start (0, 0). Von bekannten Symbolen aus wird jeder Übergang eingetragen: Bewegung ändert die Position um ±1, Bewegung ohne Wirkung ist eine Wand, Benutzen mit neuem Symbol erhöht den Modus, Benutzen ohne Wirkung wird als „nichts“ vermerkt. Widerspruch (Symbol an zwei Orten, zwei Symbole an einem Ort, Sieg durch Bewegung, Symbol hinter einer Wand) ergibt `None`: die Deutung ist falsch.

**Ortsbeschreibungen** (`places_of`). Für eine Position: „n Schritte vom Start“ in ihrer Richtung, dazu „Wand“ in jeder Richtung, der die Karte nicht widerspricht. Eine nie angestoßene Wand bleibt möglich; nur ein bekanntes Feld dahinter schließt sie aus.

**Regeln ablesen** (`learn_rules`). Unter der ersten Deutung, deren Karte widerspruchsfrei ist, muss es pro Modus genau einen Ort geben, an dem Benutzen etwas bewirkt hat, und der letzte muss gewinnen. Sonst gibt es keine Regeln (etwa ohne Sieg).

**Regeln verbinden** (`revised`). Vorwärts und rückwärts sind nur Namen. Die neuen Regeln werden deshalb in der Richtung genommen (normal oder gespiegelt), in der sie mehr Beschreibungen mit den alten teilen. Pro Ereignis bleibt die Schnittmenge; ist sie leer, war das alte Wissen zu eng, und die neuen Beschreibungen gelten. Bei verschiedenem Ablauf gelten ganz die neuen Regeln.

**Ratgeber** (`RuleAdvisor`). Hypothesen = Tastendeutung × eine Beschreibung pro Ereignis. Nach jeder Beobachtung werden die Karten neu gezeichnet; eine Hypothese fällt weg, wenn ihre Karte widersprüchlich ist, ein Ort mit Schritten hinter einer bekannten Wand läge, Benutzen am beschriebenen Ort nichts bewirkte oder Benutzen anderswo etwas bewirkte. Der Ratgeber folgt einer zufällig gewählten Hypothese, bis sie wegfällt: am Ort benutzen, sonst einen Schritt dorthin. Er stimmt nicht ab, weil gespiegelte Hypothesen alles gleich gut erklären und immer entgegengesetzt stimmen würden. `predicts` ist immer False, Neugier nutzt also stets die volle Überraschung.

### 2D-Welt (`grid/`, ab 0.12)

**Welt** (`world.py`). Ein Labyrinth (`Maze`) mit Wandrand, Start, Tür, Schlüssel (oder keinem) und Fallen. Feldarten (`Tile`): Boden, Wand, Schlüssel, Tür, offene Tür, Falle, Spieler; jede bekommt pro Spiel eine eigene der zehn ARC-Farben, die vier Richtungen bekommen zufällige Tastennamen. Schritt in Wand oder geschlossene Tür: nichts passiert. Schlüssel: Figur steht dort, Schlüssel verschwindet, die Tür wird zur offenen Tür. Offene Tür: Sieg, Neustart. Falle: zurück zum Start (Schlüssel bleibt). `random_maze` gräbt ein Labyrinth per Tiefensuche, öffnet 15 % der trennenden Wände für Schleifen und verteilt Start, Schlüssel, Tür und Fallen so, dass das Spiel lösbar ist und Fallen mindestens drei Schritte vom Start liegen.

**Wahrnehmung** (`perception.py`). Die Farbe, die vor und nach einem Schritt genau ein Feld hat, aber ein anderes, ist die bewegte Farbe (`movement`). `shapes` beschreibt jede Farbe: ein Feld oder mehrere, am Rand oder nicht.

**Lernen** (`knowledge.py`). Die erste bewegte Farbe ist die Figur. Ein Schritt um genau ein Feld legt die Richtung der gedrückten Taste fest. Ist beides bekannt, ergibt jeder Schritt die Wirkung der Zielfarbe (`observed_effect`): Raster unverändert = blockiert; Figur am Ziel und sonst nichts verändert = frei; Figur am Ziel und andere Felder umgefärbt = Auslöser mit diesen Farbwechseln; Figur woanders = zurück; Sieg gemeldet = Ziel. Eine Farbe mit zwei verschiedenen Wirkungen löst einen `ValueError` aus.

**Entscheiden** (`agent.py`). (1) Unbekannte Taste, die in diesem Raster noch nicht gedrückt wurde: ausprobieren. (2) Kürzester Weg zum Ziel mit eigenem Wissen. (3) Mit Vorwissen: derselbe Plan mit den Vermutungen der verfolgten Deutung. (4) Kürzester Weg bis vor eine Farbe ohne bekannte (oder vermutete) Wirkung und hinein; mit Vorwissen danach auch ohne Vermutungen. (5) Zufällige Taste. Der Planer (`planner.py`) ist eine Breitensuche über (Feld, ausgelöste Farbwechsel); blockierende, zurückschickende und unbekannte Farben betritt er nicht.

**Rollen** (`roles.py`). Rolle einer Farbe = Name ihrer Wirkung; eine Farbe, die ein Auslöser umfärbt, heißt „verschlossen“ und gilt als blockierend. Das Rollen-Schema speichert pro Rolle die gesehenen Aussehen und welche Rolle ein Auslöser in welche verwandelt; `revised` vereinigt beides. Deutungen in einem neuen Spiel: jede Farbe des ersten Rasters bekommt eine Rolle mit passendem Aussehen oder keine, jede Rolle höchstens eine Farbe. Eine Deutung fällt weg, wenn eine Farbe eine Rolle bekommt, die ihrer beobachteten Wirkung widerspricht, oder wenn sie einer Farbe eine Rolle gibt, die eine andere Farbe nachweislich schon hat. Der Agent folgt einer zufällig gewählten Deutung unter denen, die die meisten Farben erklären, bis sie wegfällt. Farben, die erst durch einen Auslöser entstehen, bekommen die Rolle, in die das Schema die Ausgangsrolle verwandelt.

### Weltmodell (`grid/`, ab 0.13)

**Neue Spielelemente** (`world.py`, `mazes.py`). Kiste: lässt sich schieben, wenn dahinter Boden, Druckplatte oder offenes Tor liegt; sonst blockiert sie. Druckplatte und Tor gibt es nur zusammen: Das Tor ist offen, solange die Figur oder eine Kiste auf der Platte steht. Fallen setzen Figur und Kisten zurück. `puzzle_maze` baut Rätsel, die nur mit einer Kiste lösbar sind: Das Tor liegt in einem Engpass mindestens drei Schritte vom Start, die Platte auf der Startseite mindestens drei Felder vom Tor, die erste Kiste auf einer geraden Bahn zwei bis drei Felder vor der Platte. `shortest_win` ist eine Breitensuche über (Feld, Schlüssel, Kisten).

**Regeln ableiten** (`induction.py`). Wie in 0.12 werden Figur und Tasten aus der Bewegung gelesen; Vorwissen gibt beide vor, bis eine Beobachtung widerspricht (dann wird alles neu gedeutet). Jeder Schritt ist ein Versuch: betreten, geschoben, blockiert, zurück oder Ziel, dazu die Farbe dahinter. Die Regel einer Farbe ist die einfachste, die zu allen Versuchen passt („schiebbar“ erlaubt auch blockiert). Passt keine mehr, gilt nur noch der neueste Versuch, und der Wechsel wird notiert (`revisions`). Wo sich Kisten hinschieben lassen, gilt der neueste Versuch pro Farbe.

**Ereignisse und Fernwirkungen.** Felder, die Figur oder Kisten verlassen, werden aufgedeckt; Felder, die sie betreten, verdeckt. Was beim Betreten unter einem Feld lag, merkt sich der Agent (`entered_as`), damit er beim Aufdecken weiß, welche Farbe zum Vorschein kommt (`leaves`). Alle übrigen Farbwechsel des Schritts sind Fernwirkungen. Ein neues Ereignis bekommt die Wechsel, die kein anderes Ereignis schon sicher erklärt; ein bekanntes behält die Schnittmenge mit dem, was diesmal geschah, plus die Wechsel, deren Ausgangsfarbe nicht zu sehen war (sie können nicht widerlegt werden). Erklären zwei Ereignisse eines Schritts denselben Wechsel, ist er bei beiden **unsicher**, bis ein Schritt kommt, in dem nur eines von beiden ihn erklärt.

**Vorausdenken** (`simulation.py`, `search.py`). Eine Szene ist der Hintergrund (eine Ziffer pro Feld), das Feld der Figur und die Kisten. Der Simulator wendet die Regeln an: blockiert, frei, Ziel, zurück (Figur und Kisten an den Start), schiebbar (Kiste weiter, wenn sie das Ziel betreten kann; ungeprüft gilt: wohin die Figur frei gehen kann). Danach Ereignisse, Hinterlassenes und Fernwirkungen. Wo das Modell nichts weiß, sagt er nichts voraus, sondern nennt die offene Frage: unbekannte Farbe, unbekanntes Ereignis, unbekannter Kistenschritt, oder eine unsichere Fernwirkung, die dieser Schritt klären würde (ihre Ausgangsfarbe ist zu sehen, kein anderes Ereignis sagt dasselbe voraus). Im Zweifel-Modus fragt er zusätzlich, ob eine blockierende Farbe auch mit einer anderen Farbe dahinter blockiert. Die Suche (Dijkstra) hat die Kosten (Kisten in Ecken, verschobene Kisten, Schritte); eine Ecke heißt: oben oder unten und links oder rechts blockiert. Sie liefert den billigsten Sieg, sonst die billigste offene Frage, höchstens 30 000 Szenen. Schritte, die zum Start zurückschicken, nutzt sie nur, wenn erlaubt.

**Entscheiden** (`model_agent.py`). (1) Unbekannte Taste, hier noch nicht gedrückt: ausprobieren. (2) Einen Plan weitergehen, solange jede Szene wie erwartet ist und sich das Modell nicht geändert hat; sonst verwerfen (Überraschung). (3) Neu planen, Stufe für Stufe, jede behält die vorige: mit dem ganzen Modell; ohne Vorwissen über blockierende und zurückschickende Farben, die er hier noch nicht selbst gesehen hat; mit Zweifel an Wänden; mit Fallen als Neustart. Ein Frage-Plan heißt „testet“, sonst „geht seinen Plan“ oder „nutzt eine Falle als Neustart“. (4) Zufällige Taste. Fand keine vollständige Suche etwas, plant er erst wieder, wenn sich das Modell ändert. `beliefs` zeigt eigenes Wissen, „vermutlich …“ für reines Vorwissen und „(Vorwissen: …)“, wo beides sich widerspricht.

### Rollen-Weltmodell und Neustart-Taste (`grid/`, ab 0.14)

**Rollen statt Farben** (`role_model.py`). `role_names` benennt jede Farbe eines Weltmodells nach ihrer Rolle: Figur = „ich“; eine Farbe, deren Verdecken oder Aufdecken anderswo Farben wechseln lässt (Regel frei oder unbekannt) = „auslöser“; was beim Verdecken wechselt (beim Aufdecken in Gegenrichtung) = „verschlossen“ (Regel blockiert oder unbekannt), was dabei entsteht = „geöffnet“ (frei oder unbekannt); sonst der Name der Regel. Doppelte Namen bekommen eine Nummer. `WorldModel.renamed` überträgt Regeln, Kistenwissen, Hinterlassenes, Fernwirkungen und Unsicherheiten auf neue Namen (ohne Tasten) und lässt weg, was eine Farbe ohne neuen Namen betrifft. `RoleWorld` ist das umbenannte Modell plus das Aussehen jeder Rolle im ersten Bild eines Levels (`shapes`); `merged` legt neueres Wissen über älteres und vereinigt die Aussehen.

**Bindung** (`RoleBinder`). Jede Farbe des ersten Bilds eines neuen Spiels kann jede Rolle mit passendem Aussehen haben. `fits` streicht Rollen, die dem Beobachteten widersprechen: Figur genau „ich“; sichere Fernwirkung beobachtet, aber die Rolle hat keine, oder umgekehrt; Farbe wechselte sicher (oder entstand) bei einer Fernwirkung, aber die Rolle tut das nie; Regel bekannt und verschieden (bisher nur blockiert darf noch schiebbar sein). Unter allen Bindungen (jede Rolle höchstens einmal) zählen die besten: zuerst die meisten Farben, über die Beobachtungen etwas sagen, dann die meisten Farben überhaupt; solche mit einer Ziel-Rolle gehen vor. Übernommen wird nur, worin **alle** besten Bindungen übereinstimmen. Die übrigen Farben bleiben unbekannt, und der Agent testet sie (Neugier genau dort, wo das Vorwissen mehrdeutig ist). Rollen, deren Farbe im ersten Bild fehlt (offenes Tor), bekommen die beobachtete Farbe einer Fernwirkung oder eine unbenutzte Platzhalterfarbe. Das Ergebnis ist ein Vorwissen über Farben (`renamed` zurück).

**Im Modell-Agenten.** `ModelAgent(roles=…)` legt das gebundene Rollen-Wissen unter eigenes Wissen und unter Vorwissen aus demselben Spiel. In der ersten Zweifel-Stufe fällt alles weg, was nur aus Rollen stammt. `knowledge()` gibt eigenes Wissen plus Vorwissen aus demselben Spiel zurück, ohne Rollen-Vermutungen; nur das wird an das nächste Level weitergegeben. `beliefs` zeigt „(Rolle „…“)“ für Farben, deren Wissen aus der Bindung stammt.

**Neustart-Taste** (`world.py`, `simulation.py`, `induction.py`). `GridGame(restart=…)` hat eine zusätzliche Taste, die das Level auf den Anfang setzt (`Step.restarted`); sie darf keine Richtung haben. Der Agent kennt sie (wie RESET in ARC-AGI-3), der Simulator sagt sie voraus, und die Regel-Ableitung lernt aus ihr keine Richtung. Die Suche nutzt sie wie Fallen nur in der letzten Zweifel-Stufe. `GridPlay.restarts` zählt, wie oft sie gedrückt wurde.

### Fremde Mechanik und Vorwissen prüfen (`grid/`, ab 0.15)

**Fremde Mechanik** (`world.py`). `Maze(mechanics=Mechanics(…))` weicht von den üblichen Regeln ab: `plate_closes` dreht die Druckplatte um (das Tor ist offen, solange nichts auf ihr steht; `Maze.gate_open`), `ice` lässt die Figur nach jedem Schritt auf Boden weiterrutschen, bis das nächste Feld kein Boden ist oder eine Kiste dort steht. Ein Rutschschritt, der in eine Falle oder den Ausgang führt, endet dort. Eine Kiste darf ab 0.15 zu Beginn auf der Platte stehen. Der Agent kennt keine dieser Abweichungen.

**Prüfung** (`trust.py`, H17). `check(prior, own)` zählt Bestätigungen und Widersprüche zwischen Vorwissen und eigenem Modell: gleiche Regel einer Farbe bestätigt, andere Regel widerspricht (außer: selbst blockiert gesehen, laut Vorwissen schiebbar); gleiche Fernwirkung bestätigt, eine sichere eigene Änderung, die das Vorwissen nicht kennt, oder keine Änderung, wo es eine behauptet, widerspricht. Figur und Tasten zählen nicht. `verdict`: ein Widerspruch = widerlegt, sonst ab `CONFIRMATIONS_NEEDED` (2) Bestätigungen bestätigt, sonst wartend. `ModelAgent(checked=True)` nutzt Vorwissen nur im Zustand bestätigt und nach einem Widerspruch nie mehr.

**Teilprüfung** (`model_agent.py`, H16). `ModelAgent(doubts_parts=True)` hängt an die Zweifel-Stufen zwei weitere an: Suche nur mit dem eigenen Modell (mit Zweifel an Wänden), dann zusätzlich mit Neustart. Sie greifen erst, wenn keine Stufe mit Vorwissen einen Plan findet. Dann wird alles, was nur das Vorwissen behauptet, wieder zur offenen Frage und gezielt getestet.

## 8. Experimente und Messgrößen

**Messgröße.** Die typische Wahrscheinlichkeit, die der Agent dem tatsächlich folgenden Symbol gibt, berechnet als geometrisches Mittel (`typical_probability`). Sie ist eine ehrliche Bewertungsregel: Kein Modell kann im Durchschnitt besser abschneiden als das wahre Modell der Simulation, das als „Optimum“ mit ausgegeben wird. Version 0.1 nutzte das einfache Mittel; das belohnt übertriebene Sicherheit und wurde deshalb ersetzt.

**Experiment H11.** Der Agent lernt „Warten beim Arzt“ und „Warten auf die U-Bahn“ und verschmilzt beide zum Schema „Warten“. Dann sieht er N Beobachtungen aus „Warten am Flughafen-Gate“ (andere Symbole, gleiche Struktur) und wird auf 500 neuen Schritten geprüft. N läuft von 5 bis 160, gemittelt über 20 Zufallsstarts. Kontrolle: „Plaudern“ hat keine Wartestruktur und darf nicht verschmolzen werden.

**Härtetest H11.** Dieselbe Prüfung mit vier Gate-Varianten: normal, sehr lange Wartezeit (Verspätung), sehr kurze Wartezeit (sofort Boarding) und mit 20 % zufälligen Störungen. Verglichen werden ohne Schema, starr, lernend und geprüft.

**Experiment H12.** Ein Strom wechselt in Blöcken zwischen „Pendeln: Hinweg“ und „Pendeln: Rückweg“. Beide nutzen dieselben Symbole, aber widersprüchliche Übergänge. Jeder Block setzt am letzten Symbol des vorherigen an, damit an den Grenzen keine Übergänge entstehen, die in keiner Situation möglich sind. Gemessen wird in den ersten 30 Schritten nach jeder Rückkehr zu einer schon bekannten Situation, gemittelt über 20 Zufallsstarts.

**Experiment Kontextwechsel + Scheiben.** Wachphase mit den Blöcken Arzt, U-Bahn, Arzt, U-Bahn (je 150 Schritte), Schlafphase, dann Testblöcke Gate, Arzt, U-Bahn, Gate. Verglichen werden ein einziges Modell, Kontexte ohne Schema und Kontexte mit Schema; beide Kontext-Agenten sind bis zur Schlafphase identisch. Gemessen werden die ersten 30 Schritte jedes Testblocks, getrennt nach „neue Situation“ (erstes Gate) und „bekannte Situation“ (alle anderen Testblöcke), gemittelt über 20 Zufallsstarts.

**Experiment Wach-Schlaf.** Ein durchgehender Strom aus zehn Blöcken: Arzt, U-Bahn, Arzt, U-Bahn, Gate, Arzt, Gate, Kasse, U-Bahn, Kasse. Verglichen werden Kontexte ohne Schlaf, „fester Schlaf“ (einmal nach dem vierten Block) und „eigener Schlaf“ (`WakeSleepAgent` mit Reifeschwelle 100). Gemessen werden die ersten 30 Schritte beim ersten Auftauchen von Gate und Kasse sowie bei jeder Rückkehr; die ersten Blöcke von Arzt und U-Bahn werden nicht gemessen, weil dort noch kein Agent ein Schema haben kann.

**Experiment mehrere Schemata.** Lampenwelt mit Wartesituationen und drei Gesprächen (gleiche Struktur, andere Lampenbedeutung), Blöcke à 150 Schritte: Arzt, Nachbar, U-Bahn, Kollegin, Arzt, Nachbar, Gate, Freund, U-Bahn, Kollegin, Gate, Freund. Verglichen werden Kontexte ohne Schlaf, Wach-Schlaf mit höchstens einem Schema und mit beliebig vielen. Gemessen beim ersten Gate, beim ersten Freund und bei jeder Rückkehr.

**Experiment Ampelspiel.** Pro Zufallsstart werden „Warten“ (Arzt + U-Bahn) und „Gespräch“ (Nachbar + Kollegin) aus je 400 Schritten gebaut, jeweils mit selbst gelerntem Handlungswissen. Zwei Spieler spielen je 30 Runden mit denselben Zufallszahlen: ohne Vorwissen und mit beiden Schemata. Gemessen: Siegquote in Runde 1–10 und 11–30, Unfälle, Runde des ersten Siegs, ob und wann die Schnittmenge gefunden wurde und ob Autos, Gelb und Grün richtig zugeordnet sind. Zusätzlich sucht der Spieler ohne Vorwissen nach dem Spiel eine Schnittmenge in seinem fertigen Spielmodell. Ausgegeben wird außerdem der gelernte Handlungserfolg pro Rolle von „Warten“.

**Experiment Meta-Schema und H13.** Sechs Situationen aus drei Familien (Warten: Arzt, U-Bahn; Anstehen: Bäcker, Post; Gespräch: Nachbar, Kollegin) werden je L Schritte erlebt, dann zweimal verdichtet (Ebene 2 mit 0,1, Ebene 3 mit 0,2, Ebene 3 zusätzlich ohne Prüfung des Handlungswissens). Gezählt wird, ob Ebene 2 genau die drei Familien bildet, ob ein Schema Familien vermischt und ob Ebene 3 genau Warten + Anstehen vereint. Dann sieht der Agent 30 Schritte einer neuen Situation (Gate, Kantine), sucht die am besten passende Scheibe der jeweiligen Ebene (`structure.best_match`) und handelt in jedem Zustand, dessen Rolle dort erfolgreich war. Richtig ist das genau dann, wenn er nur im Handlungsmoment der neuen Situation handeln würde. L läuft über 15, 30, 50, 100 und 400 (H13: sofort gegen verzögert verschmelzen), jeweils 20 Zufallsstarts.

**Experiment Spielefamilie.** Pro Zufallsstart drei Spiele mit Standard-Bauplan (Gang 4, Start 1, Schlüssel 0, Tür 3), danach drei Härtetests mit dem Schema aus allen drei Spielen: gespiegelt (Start 2, Schlüssel 3, Tür 0), länger (Gang 5, Tür 4), ohne Schlüssel. Ein Agent ohne Vorwissen und einer mit Schema spielen jedes Spiel 60 Tastendrücke lang mit denselben Zufallszahlen. Gemessen: Tastendrücke bis zum ersten Sieg (61, wenn keiner kam), Zahl der Siege, ob am Ende noch eine Deutung übrig ist und wie viele Übergänge das Schema kennt. 20 Zufallsstarts.

**Experiment 2D-Welt** (`grid_transfer`). Pro Zufallsstart sechs Level, jedes mit neuem Labyrinth (`random_maze`), neuen Farben und neuen Tastennamen: Level 1 bis 3 (7×7 mit 1 Falle, 9×9 mit 2, 11×11 mit 3) als Training, dann groß (15×15, 4 Fallen), ohne Schlüssel (9×9) und viele Fallen (11×11, 10 Fallen). Drei Agenten mit denselben Zufallszahlen: `StateAgent` (Entdecker über ganze Raster), `ObjectAgent` ohne und mit `RoleAdvisor`. Nach jedem Trainingslevel wird das Rollen-Schema aus dem Wissen des dritten Agenten ergänzt. 200 Tastendrücke pro Level, 20 Zufallsstarts. Gemessen: erster Sieg, Siege, Schritte in eine Falle, kürzester möglicher Weg (`shortest_win`).

**Experiment Weltmodell** (`grid_mechanics`). Pro Zufallsstart ein Spiel: zufällige Farben für alle neun Feldarten und zufällige Tastennamen, gleich für alle sechs Level. Level: Ausgang (9×9, 1 Falle), Fallen (11×11, 4), Kiste (9×9, 1 Falle, 1 Kiste), zwei Kisten (11×11, 2, 2), groß (13×13, 3, 1), Tausch (11×11, 2, 1; offene Tür und Falle tauschen die Farben). Die ersten beiden Level sind Labyrinthe ohne Schlüssel. Vier Agenten mit denselben Zufallszahlen: `StateAgent`, `ObjectAgent` aus 0.12, `ModelAgent` ohne Vorwissen und `ModelAgent` mit dem Weltmodell, das er im Level davor hatte (samt dessen Vorwissen). 300 Tastendrücke pro Level, 20 Zufallsstarts. Gemessen: erster Sieg (301, wenn keiner), Siege, Schritte in eine Falle, Anteil der Läufe, in denen ein Agent wegen eines Widerspruchs abbricht, kürzester möglicher Weg. Dazu ein Gegencheck: die sechs Level aus dem Experiment 2D-Welt mit `ObjectAgent` und `ModelAgent` (beide ohne Vorwissen, 200 Tastendrücke).

**Experiment Rollen-Weltmodell** (`grid_roles`, H14). Pro Zufallsstart zuerst Spiel A wie im Experiment Weltmodell; aus dem Modell des Agenten mit Vorwissen wird nach jedem Level ein `RoleWorld` gebildet und verbunden. Dann Spiel B: neue Farben und Tastennamen, ein neues Labyrinth jeder Art. Jedes Labyrinth gibt es zweimal, in den Farben von A und von B, beide mit Neustart-Taste. Vier `ModelAgent` mit denselben Zufallszahlen: ohne Vorwissen (B), mit dem Farbmodell aus A ohne Tasten (B), mit dem Rollen-Weltmodell aus A (B), mit dem Farbmodell aus A in den Farben von A (Bestwert). 300 Tastendrücke pro Level, 20 Zufallsstarts. Gemessen: erster Sieg (301, wenn keiner), Schritte in eine Falle, Neustarts, Anteil ohne Sieg, kürzester möglicher Weg.

**Experiment Gegenprobe** (`grid_foreign`, ab 0.15). Pro Zufallsstart zuerst Spiel A wie im Experiment Rollen-Weltmodell. Dann drei Level von Spiel B, jedes in den Farben und Tasten von B und von A, alle mit Neustart-Taste: gewohnt (11×11, 2 Fallen, 1 Kiste), Tor umgekehrt (wie gewohnt, `plate_closes`, die Kiste beginnt auf der Platte) und Eis (13×13, 2 Fallen, ohne Kiste, `ice`, kürzester Sieg mindestens 6 Tastendrücke). Ein Labyrinth wird bis zu 300-mal neu gebaut, bis es mit der fremden Mechanik lösbar ist. Sieben `ModelAgent` mit denselben Zufallszahlen: in den Farben von B ohne Vorwissen, mit Rollen aus A, mit Rollen aus A und Prüfung; in den Farben von A ohne Vorwissen, mit dem Farbmodell aus A, mit Prüfung, mit Teilprüfung. 300 Tastendrücke pro Level, 20 Zufallsstarts. Gemessen: erster Sieg (301, wenn keiner), Schaden = erster Sieg minus erster Sieg ohne Vorwissen im selben Aussehen, Anteil ohne Sieg, Anteil, in dem das Vorwissen am Ende als widerlegt gilt.

**Spielwelt gegen Alltagswelt** (`cross_world`, ab 0.15). Härtetest H11 und Gegenprobe im selben Maß: Prozent schlechter als ohne Vorwissen. Alltag: (ohne − mit) / ohne der typischen Wahrscheinlichkeit, gemittelt über 10, 40 und 160 Beobachtungen; Spiel: (mit − ohne) / ohne der mittleren Tastendrücke bis zum ersten Sieg. Zuordnung: übernehmen = starr / Farbmodell aus A, als Ganzes prüfen = geprüft / mit Prüfung, Teile korrigieren = lernend / mit Teilprüfung. Beide Welten nutzen verschiedenen Code; verglichen wird das Prinzip.

**Experiment Regeln statt Zustände** (`rule_transfer`). Familie mit wachsender Länge: Gang 4 (Tür 3), 5 (Tür 4), 6 (Tür 5), jeweils Start 1 und Schlüssel 0. Härtetests: gespiegelt, viel länger (Gang 8, Tür 7), ohne Schlüssel. Drei Agenten mit denselben Zufallszahlen: ohne Vorwissen, mit Zustands-Schema (wie Spielefamilie), mit Regel-Schema (`rules_after_game` nach jedem Familienspiel). Gemessen wie bei der Spielefamilie, dazu welche Beschreibungen nach Spiel 3 übrig sind (ohne Richtung gezählt). 20 Zufallsstarts, 60 Tastendrücke.

**Experiment Neugier.** Das Experiment Spielefamilie viermal: 60 und 200 Tastendrücke, jeweils ohne und mit Neugier (Standardwerte). Dazu ein Regler bei 200 Tastendrücken: `schema_surprise` 0,0125, 0,025, 0,05 und 0,1; gemessen die mittleren Siege des Agenten mit Schema in Spiel 2, Spiel 3 und gespiegelt sowie im Spiel ohne Schlüssel. 20 Zufallsstarts.

**Experiment Kontexterkennung.** In drei Welten (Pendeln wie H12; Lampen mit Arzt, U-Bahn, Gate; Lampen mit drei Wartesituationen und drei Gesprächen) wird gezählt, welcher Anteil der Übergänge im richtigen Kontext landet. Weil der Agent die wahren Situationen nicht kennt, bekommt jede Situation höchstens einen Kontext und umgekehrt, gierig nach Häufigkeit. 20 Zufallsstarts, Blöcke à 150 Schritte.

## 9. Der allgemeine Agent (ab 0.16, erweitert in 0.17 bis 0.21)

Paket `general/`. Ein Agent, der keine Welt kennt. Er sieht nur ein Tupel ganzer Zahlen und
wählt eine Taste aus `0 … n−1`. Jede Welt mischt Reihenfolge der Größen und Tasten neu
(`env.Wiring`), damit nichts Eingebautes zufällig passt.

**Welten** (`worlds.py`):
- `Lattice`: Raum mit `dims` Achsen und Kantenlänge `size`. Beobachtung: Position, je Achse
  und Richtung „Wand?“ (0/1), Ziel. Tasten: je Achse vor und zurück. Wahlweise rutschig
  (`slip`: so oft geht ein Schritt nicht).
- `SortedSearch`: Suchbaum mit `2^h − 1` Schlüsseln. Beobachtung: Schlüssel hier, gesuchter
  Schlüssel, „ganz unten?“, „ganz oben?“. Tasten: links hinab, rechts hinab, hinauf.

**Regeln als Programme** (`programs.py`, `synthesis.py`): Für jedes Paar (Taste, Größe) sucht
der Agent ein Programm aus `Keep`, `Shift(k)`, `Rises`, `Falls` und `When(Größe, Wert, dann,
sonst)`. Er zählt Programme nach Länge auf und nimmt das mit der kürzesten Beschreibung:
4 Bit je Baustein plus `log2(n+1)` Bit je Ausnahme (MDL). Ein Programm ohne Ausnahme beendet
die Suche. Mehr als 30 % Ausnahmen gilt als unvorhersagbar.

**Bibliothek** (`library.py`, H20): Aus Regeln ohne Ausnahme bildet der Agent durch
Anti-Unifikation Muster mit Lücken (etwa „fester Schritt, außer ein Schalter ist 1“). Pro Welt
kommen höchstens zwei neue Muster dazu, gewählt nach `Nutzungen × (Größe − 1)`. Ein Muster
kostet beim Aufruf einen Baustein. Wird es zwei Welten lang nicht genutzt, fliegt es raus.

**Form** (`form.py`, H19): Eine Größe ist eine Raumachse, wenn eine Taste sie um `+k`, eine
andere um `−k` verschiebt und alle anderen Tasten sie sicher gleich lassen. Bei `Rises`/`Falls`
statt fester Schritte ist sie eine Ordnung. Fest sind Größen, die keine Taste ändert.
Toleranz für Rauschen: `2 × Rauschpegel + 0,01`, Rauschpegel = Median der Fehlerraten.

**Ziel** (`knowledge.py`): die kleinste Menge von Paaren „Größe i = Größe j“, die bei jedem
Sieg gelten und bei keinem Nicht-Sieg alle zugleich (gierige Mengenüberdeckung).

**Planen** (`planner.py`): Im Raum A*-Suche auf den gelernten Koordinaten; Wände kennt er nur,
wo er schon war, Unbekanntes gilt als frei. In einer Ordnung eingrenzen (wird zu binärer
Suche, ohne dass sie programmiert ist). Ohne Form: einen Schritt vorausschauen. Wo er nichts
weiß, nimmt er die am wenigsten probierte Taste; nach drei gleichen Versuchen ebenfalls.

**Neue Umgebung** (`detector.py`, H18): Für jede Regel ein Binomial-Test über die letzten
20 Schritte: Wie wahrscheinlich sind so viele Fehler bei ihrer bisherigen Trefferquote?
Unter `10^-5` ist das unerwartet. Dann drei Erklärungen in dieser Reihenfolge:
1. Eine verfeinerte Regel erklärt alte und neue Daten: verfeinern (vorläufig, wird
   zurückgenommen, wenn kurz darauf doch ein Kartenwechsel folgt).
2. Eine andere Regel erklärt das Fenster seit dem ersten Fehler kürzer: neue Welt. Passt eine
   alte Karte am besten (Log-Likelihood), geht er zu ihr zurück, sonst legt er eine neue an.
3. Weder noch: Die Regel gilt als unvorhersagbar.
Überraschende Schritte lernt er erst, wenn das Fenster gezeigt hat, dass sie Rauschen waren.

**Experimente** (`experiments/general_worlds.py`, `library_transfer.py`, `new_world.py`,
`general_replay.py`): Ergebnisse 17 bis 19 im README.

### 9.1 Neu in 0.17: die Grenzen von 0.16 (H21 bis H24)

**Mehr Welten** (`worlds.py`, `env.py`):
- `Lattice(..., ice=True)`: Eis. Eine Taste lässt die Figur rutschen, bis die nächste Zelle
  versperrt ist. Runden beginnen und enden im Spielgebiet: dem größten Gebiet von
  Haltestellen, die alle voneinander aus erreichbar sind. `random_lattice` setzt auf Eis nur
  Hindernisse, die keine Falle bauen und das Spielgebiet nicht verkleinern.
- `Dials(count, size)`: Drehscheiben. Beobachtung: Stellung jeder Scheibe, Ziel. Tasten: je
  Scheibe +1 und −1, nach `size − 1` kommt 0.
- `Shuffle(tokens)`: Steine auf Plätzen. Beobachtung: Stein je Platz, Zielreihenfolge. Taste i
  tauscht Platz i und i+1. Kürzester Weg = Zahl der Fehlstellungen.
- `Padded(env, width, actions)`: füllt die Beobachtung mit Nullen auf `width` auf, Tasten ab
  `env.actions` tun nichts. So erleben alle Welten dieselbe Schnittstelle.

**Neue Bausteine** (`programs.py`): `Copy(q)` „übernimmt Größe q“ (Länge 1), `Cycle(k, m)`
„+k im Ring aus m Werten“ und `Until(k, q, v)` „+k immer wieder, bis Größe q = v“ (je Länge
2). `Until` ist die einzige Schleife; null Durchläufe sind erlaubt (Schalter schon gesetzt).
Vorausgesagt wird bei `Until` nur „bleibt“; wie weit die Schleife läuft, sagt die Regel
allein nicht.

**Vorschläge aus den Daten** (`synthesis.py`): Die neuen Bausteine werden nicht blind
aufgezählt. `Copy` nur für Größen, deren alter Wert bei jedem Wechsel der neue Wert war
(höchstens 4), mit mindestens zwei verschiedenen neuen Werten und nur aus einer Quelle,
die alle Werte der Größe schon gezeigt hat. Ein einzelner Beleg oder ein Schalter als Quelle
passt sonst zu oft zufällig (im 3D-Würfel kostete das 13,7 statt 10,8 Schritte). `Cycle` nur aus einem häufigen Schritt und einem häufigen Sprung in die
Gegenrichtung, mindestens 3 Werte, auf dem kürzeren Weg geschrieben (−11 im Ring aus 12 ist
+1). `Until` nur, wenn Sprünge über mehr als den gemeinsamen Grundschritt vorkommen. Reihenfolge
der Suche: Länge 1 (Grundbausteine, `Copy`), Länge 2 (`Cycle`, `Until`), Bibliothek, Länge 3
(Schalter-Regeln). `extended=False` schaltet alles Neue ab (Stand 0.16).

**Form als Grammatik** (`form.py`, H21): Jede Achse hat eine Art, abgelesen aus den beiden
Bausteinen, die sie bewegen: Kette (`Shift`), Ring (`Cycle` mit gleichem m), Rutschbahn
(`Until`, auch gemischt mit `Shift`), sonst Ordnung. Der Name der Form wird zusammengesetzt,
etwa „Ring × Ring × Ring“ oder „Raum mit 1 Dimension × Rutschbahn mit 1 Dimension“. Schalter
(Größen mit genau zwei Werten) sind keine Achsen. Ohne Achse: „keine bekannte Form“.

**Planen** (`planner.py`): Die A*-Suche kennt Ringe (Abstand auf dem kürzeren Weg) und
Rutschpartien: Er rutscht im Kopf weiter, solange die Karte zeigt, dass es weitergeht, und
hält an der ersten unbekannten Stelle. Dafür merkt sich die Karte (`Knowledge.passed`), über
welche Strecken eine Schleife schon lief: Dort war der Schalter nicht gesetzt (`Passage`).
Hat die Welt keine Achse, aber ein Ziel, sucht `plan_model` in vorgestellten Beobachtungen
(Breitensuche, höchstens 5000), nur mit Regeln ohne Ausnahme und mit mindestens 3 Beispielen.

**Bibliothek mit Vorprüfung** (`library.py`, H24): Ein Muster wird nur probiert, wenn seine
Bausteine mindestens 90 % der beobachteten Änderungen überhaupt erzeugen können
(`plausible`). Das liest nur die Häufigkeiten der Änderungen und prüft kein Programm.

**Neue Welt per Bayes-Faktor** (`detector.py`, H23, `Strategy.BAYES`): Ausgelöst wie bei
H18. Ab dann sammelt er alle Schritte, bis eine Erklärung klar gewinnt (sequentiell wie
Walds Test, kein festes Fenster). Verglichen wird der Vorhersage-Verlust in Bits über alle
Regeln, die zu diesen Schritten etwas sagen:
1. dieselbe Karte: je Regel und Schritt `−log2 r` bei Treffer, `−log2 (1 − r)` bei Fehler,
   r die bisherige Trefferquote (Laplace),
2. eine alte Karte: genauso mit ihren Regeln, plus `CHANGE_BITS`,
3. eine neue Karte: als Abwandlung der jetzigen. Für die k Regeln, die sich am meisten
   lohnen, neue Regeln (4 Bit je Baustein) und ihr Verlust an Schritten, aus denen sie nicht
   gelernt wurden (zweifach über Kreuz: aus jedem zweiten Schritt lernen, die anderen
   vorhersagen, nach Dawid 1984), plus `log2 (J + 1) + log2 C(J, k)` für die Auswahl und
   `CHANGE_BITS`.
`CHANGE_BITS = log2 ((1 − h) / h)` mit Wechselrate h = 1/1000 je Schritt (ohne Grundlage).
Ist die beste andere Erklärung um mindestens `5 / ln 2 ≈ 7,2` Bit besser als 1, wechselt er
(`2 ln B ≥ 10`, „sehr starker“ Beleg nach Kass & Raftery 1995). Ist 1 um so viel besser,
verfeinert er die auffälligen Regeln, falls das geht, oder hört auf zu sammeln, sobald keine
Regel mehr unerwartet danebenliegt. Solange er sammelt, lernt die Karte nicht aus den
zurückgehaltenen Schritten.

**Keine Übernahme des Ziels**: Eine neue Karte beginnt ohne das Ziel der alten. In 0.16 wurde
es übernommen; im Strom ganz verschiedener Welten führte das den Agenten in die Irre, weil
das alte Ziel in einer anderen Welt nichts bedeutet (Suchbaum 194 statt 93 Schritte,
Drehscheiben 223 statt 58). Neue Ursache, neues Wissen (Gershman 2017). Was die neue Karte
selbst gesehen hat, lernt sie dagegen ganz: Wechselt der Agent, bekommt die Karte, die jetzt
gilt, alle zurückgehaltenen Schritte mit Regeln, Orten und Ziel.

**Experimente**: `experiments/new_forms.py` (Ergebnis 20, H21 und H22), `world_stream.py`
(Ergebnis 21, H23); `library_transfer.py` hat die Bedingung „ohne Vorprüfung“ (H24),
`new_world.py` den Umgang „Bayes-Faktor“.

### 9.2 Neu in 0.18: eigene Ziele und Crafter (H25 bis H28)

**Baustein „wird v“** (`programs.Becomes`): Die Größe bekommt den Wert v, egal welchen sie
hatte. Vorgeschlagen nur, wenn jeder Wechsel bei demselben Wert endete, von mindestens zwei
Werten aus. **Übernehmen trotz Rauschen** (`synthesis._sources`): Stimmt eine Quelle bei 90 %
von mindestens 10 Wechseln, und hatte die Größe in 90 % der Schritte einen Wert, den die
Quelle auch zeigte, kommt `Copy` in Frage (ein Tier läuft durchs Bild). **Gesperrte Schritte**
(`RuleBook.blocked_moves`): Eine Bewegung, die nur danebenliegt, weil die Größe blieb (gegen
einen Baum gelaufen), zählt für die Form als verlässlich. Regeln mit Ausnahmen sucht er nach
200 neuen Schritten der Taste neu (`REFRESH`).

**Ursachen** (`causes.py`, H25): Für jedes Ereignis (Größe steigt, sinkt, wird v) und jede
Taste lernt er Bedingungen aus Literalen `Gi = v` und `Gi ≥ v`: schrittweises Abdecken, je
Literal das mit der besten gewichteten relativen Genauigkeit (Lavrač 1999), höchstens drei
Literale und vier Ursachen. Eine Ursache zählt ab zwei Treffern und einer Genauigkeit von
0,34 (Laplace). Für Ereignisse, die die Welt bewirkt (ein Angriff), dieselbe Suche über alle
Tasten zusammen (`conditions`). Rechnet mit Bitmengen.

**Teilziele** (`subgoals.py`, H25, H26): Er stellt sich vor, was eine Taste bewirkt; was er
nicht vorhersagen kann, wird „unbekannt“ und erfüllt kein Literal. Breitensuche (höchstens
200 Zustände) zu einem Zustand, in dem das Ziel gilt, oder in dem eine Ursache bereit ist.
Sonst macht er die fehlenden Literale der ersten drei Ursachen zu Teilzielen, bis Tiefe 3.
Gibt es keine verlässliche Ursache, nimmt er auch seltene (ab 5 %).

**Eigene Ziele** (`drives.py`, H27, H28), eingeschaltet mit `GeneralAgent(own_goals=True)`.
Reihenfolge je Schritt:
1. *Abwehr:* Gilt eine gefährliche Lage (danach sank Gesundheit oft, egal nach welcher
   Taste), die Taste mit dem kleinsten gelernten Schaden in den nächsten 5 Schritten
   (geschrumpft zum Mittel über alle Lagen), bei Gleichstand die, nach der er sich außer
   Gefahr denkt.
2. *Bedürfnis:* Eine Menge, die nach fast jeder Taste schon sank, ist auf die Hälfte gefallen.
3. *Ziel:* das Ziel von eben, höchstens 60 Schritte.
4. *Versuch:* eine Taste an einem Wert, den er mit ihr noch nie sah.
5. *Rekord:* eine Menge höher bringen als je zuvor an diesem Ort.
6. *Pflege:* ein Bedürfnis schon unter 90 % heben.
7. *Erkunden:* auf der Karte seiner Form geradeaus in eine Richtung (4 bis 12 Schritte), ab
   und zu die am seltensten probierte Taste.
Weiß er für ein Ziel keinen Weg, geht er dorthin zurück, wo die Größe zuletzt stieg. Tasten,
nach denen hier meist Gesundheit sank, nimmt er nie. Mengen sind Größen ohne `Copy`- oder
`Becomes`-Regel, keine Achse, die sich in 80 % der Fälle um genau 1 ändern.

**Crafter** (`adapters/crafter.py`, `experiments/crafter_run.py`, `crafter_replay.py`): siehe
[CRAFTER.md](CRAFTER.md). Der Agent importiert nie etwas aus `adapters`.

### 9.3 Neu in 0.19: Raum aus eigener Bewegung (H29 bis H31)

**Ort** (`space.Space._find_walkers`): Für jede Taste die Größe, die sich bei ihr in
mindestens 95 % ihrer Änderungen um denselben Schritt ±1 ändert, nach mindestens 20 % der
Drücke, und die schon mindestens 6 verschiedene Werte hatte (eine Blickrichtung hat weniger).
Ändert sie sich, ist er wirklich gegangen. Zwei Tasten mit derselben Größe und
entgegengesetztem Schritt sind Gegenrichtungen; ihre Belege zählen zusammen.

**Verschiebungen** (`Space._edges`): Nach jedem echten Schritt zählt er für jede Größe i und
jede Größe j, ob i jetzt den alten Wert von j hat, einmal über alle Schritte und einmal nur
über die, nach denen sich i änderte. Eine Verschiebung „j nach i“ gilt ab 20 echten Schritten
in beide Richtungen, wenn j in 90 % der Schritte passt, öfter als jede andere Größe, und bei
den Änderungen in 80 % (in beiden Richtungen: Ein Feld wie „vorne“ übernimmt beim Gehen
einen Nachbarn, gibt ihn in der Gegenrichtung aber nicht zurück). Eine Taste verschiebt den
Blick, wenn sie einen Ort hat und mindestens 4 Verschiebungen. Sicherheit einer Verschiebung:
Anteil der passenden Änderungen in beiden Richtungen, geglättet nach Laplace.

**Gitter** (`space.build`): Jede Ortsgröße ist eine Achse, jede Taste ein Schritt auf ihr. Die
sichersten Verschiebungen zuerst; eine, die nicht zum schon Gebauten passt oder zwei Felder
auf eine Stelle legen würde, fällt weg (Kruskal 1956). Danach rückt er bis zu dreimal jedes
Feld an die Stelle, für die die Mehrheit seiner Verschiebungen spricht, wenn sie frei ist.
Es bleibt das größte Stück, darin nur Felder mit mindestens zwei passenden Verschiebungen.
Alle 100 Schritte baut er neu; ein Gitter mit eigener Stelle ersetzt er nur durch ein
anderes mit eigener Stelle.

**Eigene Stelle** (`space._gap`): Kennt er mindestens 90 % des umgebenden Kastens, ist seine
Stelle die einzige freie im Inneren, und alle ihre Nachbarn sind Felder. Am Rand darf etwas
fehlen. Von ihr aus misst er Abstände (Summe der Beträge). Gruppen: alle Felder im Abstand
≤ 1, ≤ 2, ≤ 3.

**Gruppen in Ursachen** (`causes.Literal.some`, H29): Ein Literal „irgendein Feld der Gruppe
hat den Wert v“ (`Kind.SOME`). Gefahren (`conditions`) nutzen es, die Ursachen einer Taste
noch nicht. Als Teilziel geht er hin (`Layout.fetch`): Breitensuche über die Verschiebungen,
bis der Wert, den er irgendwo sieht, im Zielfeld oder in einem Feld der Gruppe steht.

**Abwehr mit Richtung** (`drives`, H30): Antworten auf eine Gefahr sind jetzt „hin“, „weg“
oder „quer“ zur nächsten Gefahr (`Layout.relation`), oder „Taste a an der Gefahr“, wenn eine
Taste mit Wirkung gerade auf eine Gefahr zeigt (ein Feld, von dem ihre Ursachen abhängen,
hat den Wert der Gefahr), sonst „Taste a“. Kosten einer Antwort: Schaden in den nächsten
5 Schritten, dazu 1, wenn die Gefahr danach noch da ist (Mowrer 1947).

**Neugier auf Sichtfelder** (`drives._curious`, H31), nur mit eigener Stelle: Hängt eine
Taste mit Wirkung von einer Größe außerhalb des Gitters ab (etwa „vorne“; ohne Ort und
Körper), und sieht er im Gitter einen Wert, den diese Größe bei der Taste noch nicht 5-mal
hatte, macht er „Größe = Wert“ zum Ziel, das Nächste zuerst. Reihenfolge der Antriebe jetzt: Abwehr, Bedürfnis, Ziel, Versuch,
Neugier, Rekord, Pflege, Erkunden. Versuche wiederholt er bis zu 5-mal (manches wirkt erst
nach mehreren Schlägen), bei unbekannten Tasten und Körpergrößen einmal. Der Ort zählt nicht
zum Körper.

### 9.4 Neu in 0.20: Überleben und Wege (H32 bis H34)

**Abwehr als Option** (`drives.Guard`, `Drives._hold`, H32): Hat er eine Antwort auf eine
Gefahr gewählt, bleibt er dabei, bis die Gefahr nicht mehr gilt oder `HARM_WINDOW` = 8
Schritte um sind (Option mit Abbruchbedingung: Sutton, Precup & Singh 1999; zeitlich
ausgedehntes Ausprobieren: Dabney, Ostrovski & Barreto 2021). Die Taste dafür sucht er in
jedem Schritt neu (`_realize`): „hin“ ist nach einem Schritt eine andere Taste, wenn der
Gegner mitläuft. Abgerechnet wird die ganze Option: Schaden in den 8 Schritten, dazu 1, wenn
die Gefahr danach noch gilt. Weiß er, wo die Gefahr ist, hat er nur wenige Antworten
(`_options`): hin, weg, quer, und „Taste a daran“ für jede Taste, an deren Wirkungsfeld schon
einmal der Wert der Gefahr stand; dafür geht er erst hin und drückt dann (Bolles 1970). Sonst
ist jede Taste eine Antwort.

**Neuer Besitz, neuer Versuch** (`Drives._carried`, H33): Versuche und Neugier zählen je
Taste, Wert und dem, was er gerade bei sich hat: Größen, die er besitzt und die keine
Bedürfnisse sind, jeweils nur, ob sie über 0 sind. Mit Holz in der Tasche ist dieselbe Lage
wieder neu (Gibson 1979; Şahin u. a. 2007: was eine Lage bietet, hängt vom Handelnden ab).

**Ort nur, wo es zurückgeht** (`Space._find_walkers`): Eine Größe ist nur dann Ort, wenn eine
andere Taste sie um den Gegenschritt ändert. Bis 0.19 galt ein Vorrat, der beim Schöpfen um 1
steigt, als Ort; dann zählte er nicht zum Körper und wurde nie ein Bedürfnis.

**Hindernisse aus eigener Bewegung** (`Space._bump`, `Space._obstacles`, H34): Nach jeder Taste
mit Schritt sieht er nach, welcher Wert im Feld in Schrittrichtung stand und ob er wirklich
ging. Ein Wert ist ein Hindernis ab 5 gescheiterten Schritten, wenn mindestens 80 % der
Schritte auf ihn scheiterten. Hingehen (`Layout.fetch`, `walk`): Breitensuche über die freien
Felder seines Gitters zur nächsten Stelle, an der das Gesuchte direkt neben ihm wäre. Zu
einem gemerkten Ort außer Sicht (`Layout.head`) nimmt er den freien Weg zu dem Feld, das dem
Ort am nächsten liegt. Teilziele (`subgoals._achieve`): Fehlt einer Ursache nur ein Literal
und sieht er, was fehlt, geht er hin.

**Fühler** (`space._mirrors`): Eine Verschiebung, die nur in eine Richtung passt (das Feld
„vorne“ übernimmt beim Gehen den Nachbarn, gibt ihn in der Gegenrichtung aber nicht zurück),
sagt: Diese Größe zeigt das Nachbarfeld in Gehrichtung. Steht der gesuchte Wert in einem
Nachbarfeld, nimmt er die Taste in diese Richtung (in Crafter dreht ihn das zum Baum, ohne
dass er geht). Was ein Sinn meldet, folgt aus dem, was beim Bewegen passiert (O'Regan & Noë
2001).

### 9.5 Neu in 0.21: Gefahren mit Unsicherheit (H35)

**Hinweisreize** (`cues.Cues`): Nach jedem Schritt zählt er für jedes Literal, das vorher galt
(jede Größe mit ihrem Wert, jede Gruppe aus `space` mit jedem Wert darin), dass es galt, und
für jede Größe, die sank, dass sie danach sank. Gefahren (`drives.dangers`) sind die Literale
über das, was er sieht (nicht Körper, nicht Ort), nach denen eine Größe wie Gesundheit
mindestens zweimal sank und deren Schadensquote mit 95 % Sicherheit (`CONFIDENCE`) über
`DANGER` = 15 % liegt. Die Quote ist Beta(Treffer + 1, Fälle − Treffer + 1)-verteilt
(Tzovara, Korn & Bach 2018); P(Quote > p) rechnet er genau als Binomial-Summe. Die
gefährlichste zuerst (höchster Mittelwert). Jede Gefahr ist ein einzelnes Literal; die
Abwehr (9.4) bleibt gleich. Das Abdecken über alle Tasten (`CauseBook.conditions`) ist
entfernt.

## 10. Qualitätsregeln für den Code

- Lesbarkeit und Einfachheit vor Cleverness (KISS, Zen of Python).
- Ein Modul, eine Aufgabe (Single Responsibility).
- Vollständige Typannotationen, geprüft mit `mypy --strict`.
- Fehler werden nie still ignoriert: ungültige Eingaben lösen `ValueError` mit verständlicher Meldung aus.
- Keine Wiederholungen (DRY): ein gemeinsames `Predictor`-Protokoll, eine Bewertungsfunktion.
- Zufall nur über einen übergebenen `random.Random`, damit jedes Ergebnis reproduzierbar ist.
- Bezeichner auf Englisch (Python-Konvention), Dokumentation und Ausgaben auf Deutsch.

## 11. Änderungen

### Version 0.21

- Gefahren als Hinweisreize mit Unsicherheit (`cues.py`, Abschnitt 9.5).
- Crafter-Messung mit „Stand 0.21“ und Gegenprobe auf 16 neuen Karten.
- Ohne `own_goals` gleiche Ausgabe wie 0.20.

### Version 0.20

- Abwehr als Option, neuer Besitz, neuer Versuch, Ort nur mit Gegenschritt, Hindernisse aus
  eigener Bewegung, Wege um sie herum, Fühler (Abschnitt 9.4).
- Crafter-Messung mit „Stand 0.20“; die Zeilen von 0.18 und 0.19 kommen aus der gespeicherten
  Messung.
- Ohne `own_goals` gleiche Ausgabe wie 0.19 (Ergebnisse 17 bis 21 Zeichen für Zeichen).

### Version 0.19

- Raum aus eigener Bewegung (`space.py`), Gruppen in Ursachen, Hingehen, Abwehr mit
  Richtung, Neugier auf Sichtfelder (Abschnitt 9.3).
- Crafter-Messung mit „Stand 0.19“; die Zeilen von 0.18 kommen aus der gespeicherten Messung.
- Ohne `own_goals` gleiche Ausgabe wie 0.18 (Ergebnisse 17 bis 21 Zeichen für Zeichen).

### Version 0.18

- Eigene Ziele (`drives.py`), Ursachen (`causes.py`), Teilziele (`subgoals.py`), Baustein
  „wird v“, Übernehmen trotz Rauschen, gesperrte Schritte (Abschnitt 9.2).
- Crafter-Adapter in einem eigenen Paket `hekmatki.adapters`, Messung und Seite
  (Ergebnis 22). Zusatzpaket `crafter`, der Kern bleibt bei der Standardbibliothek.
- Ohne `own_goals` verhält sich der Agent fast wie in 0.17; die gemeinsamen Änderungen
  verschieben einzelne Zahlen in Ergebnis 17 bis 21 leicht (siehe README).

### Version 0.17

- Neue Bausteine `Copy`, `Cycle`, `Until`, Form als Grammatik, Planen auf Ringen und
  Rutschbahnen und im gelernten Modell, Bibliothek mit Vorprüfung, Erkennen per Bayes-Faktor
  (Abschnitt 9.1).
- Neue Welten Eis, Drehscheiben, Tauschen und die Hülle `Padded`.
- Experimente `new_forms` und `world_stream` (Ergebnisse 20 und 21); Ergebnisse 18 und 19
  haben je eine Bedingung mehr. Der allgemeine Agent nutzt die neuen Teile standardmäßig,
  daher ändern sich auch die Zahlen von Ergebnis 17 bis 19 leicht. Ergebnisse 1 bis 16 sind
  unverändert.
- Eine neue Karte übernimmt nicht mehr das Ziel der alten.

### Version 0.16

- Neues Paket `general/`: ein Agent für ganz verschiedene Welten (Raum, Würfel, Suchbaum),
  Regeln als Programme, Bibliothek, Form, Planer, Erkennen einer neuen Umgebung (Abschnitt 9).
- Experimente `general_worlds`, `library_transfer`, `new_world` (Ergebnisse 17 bis 19) und die
  Seite `docs/welten.html` (`general_replay`).
- Ergebnisse 1 bis 16 sind unverändert; der alte Code ist nicht angefasst.

### Version 0.15

- Fremde Mechanik (`Mechanics`: Platte schließt, Eis); eine Kiste darf auf der Platte beginnen.
- Vorwissen prüfen: `trust.py` und `ModelAgent(checked=True)` (H17), Teilprüfung `ModelAgent(doubts_parts=True)` (H16).
- Experimente `grid_foreign` und `cross_world` (Ergebnis 16); Wiedergabe-Seite mit fünftem Fall „Tor umgekehrt“.
- Ergebnisse 1 bis 15 sind exakt gleich.

### Version 0.14

- Rollen-Weltmodell (`role_model.py`): Regeln über Rollen statt Farben, Bindung neuer Farben nur dort, wo alle besten Deutungen übereinstimmen. `WorldModel.renamed`, `ModelAgent(roles=…)`, `ModelAgent.knowledge`.
- Neustart-Taste in Welt, Simulator, Regel-Ableitung und Agent; `GridPlay.restarts`.
- Experiment `grid_roles` (Ergebnis 15, H14); Wiedergabe-Seite mit vierten Fall „Neue Farben“.
- Ergebnisse 1 bis 14 sind exakt gleich.

### Version 0.13

- Kisten, Druckplatte und Tor in der 2D-Welt; Rätsel-Generator `puzzle_maze`, allgemeiner Löser `shortest_win` (`mazes.py`, ausgelagert aus `world.py`).
- Modell-Agent mit Weltmodell: `model`, `induction`, `simulation`, `search`, `model_agent`. Er lernt um, statt abzubrechen, plant im Modell, testet gezielt, meidet Ecken und zweifelt in Stufen.
- Experiment `grid_mechanics` (Ergebnis 14) mit Vorwissen über Level hinweg; Wiedergabe-Seite mit drei Fällen.
- Der Objekt-Agent aus 0.12 meldet Widersprüche als `ContradictionError` (ein `ValueError`); `play_grid` hält das als „ausgeschieden“ fest.
- Ergebnisse 1 bis 13 sind exakt gleich.

### Version 0.12

- 2D-Welt (`grid/`): Farbraster, Objekt-Agent, Rollen-Schema; Experiment `grid_transfer`; Wiedergabe-Seite (`grid_replay`).
- Objekte statt Bilder: im 15×15-Labyrinth erster Sieg nach 41,9 statt fast nie; mit Rollen-Schema in vier von fünf Leveln drei- bis achtmal seltener in Fallen.
- Alle älteren Ergebnisse sind exakt gleich.

### Version 0.11

- Regel-Schemata (`rules.py`) und gemeinsame Ratgeber-Schnittstelle (`advisor.py`). Experiment `rule_transfer`.
- Mit Regel-Schema halbiert sich die Zeit bis zum ersten Sieg auch in längeren Gängen (Gang 8: 38,5 → 20,5); die Tür wird in 20 von 20 Läufen als „Wand“ beschrieben.
- Alle älteren Ergebnisse sind exakt gleich.

### Version 0.10

- Neugier mit Augenmaß (`curiosity.py`): Abstecher ins Unbekannte werden gegen sichere Siege abgewogen, abhängig von der verbleibenden Spieldauer. Experiment `exploration`.
- Kurz (60) kostet Neugier Siege, lang (200) bringt sie mehr Siege, vor allem im Spiel ohne Schlüssel (34 → 57). Unter 5 % zugetrauter Überraschung bleibt der Einstellungseffekt.
- Alle älteren Ergebnisse sind exakt gleich.

### Version 0.9

- Spielefamilie „Schlüssel und Tür“, Entdecker und Spiel-Schemata mit Deutungen; Experiment `discovery`.
- Ab dem zweiten Spiel halbiert das Schema die Tastendrücke bis zum ersten Sieg (≈ 9 statt ≈ 21), auch im gespiegelten Spiel. Beim längeren Gang passt es nicht mehr; ohne Schlüssel zeigt sich ein Einstellungseffekt (weniger Siege mit Schema).
- Alle älteren Ergebnisse sind exakt gleich.

### Version 0.8

- Dritte Ebene: `stack.py` mit `experience`, `Group` und `consolidate`; dieselbe Routine für jede Ebene.
- `merge_schemas` mit Prüfung des Handlungswissens; `Situation.action_role`; neue Familie „Anstehen“.
- Neues Experiment `meta_schema`: In allen Läufen entsteht ein Meta-Schema aus Warten und Anstehen, Gespräch bleibt getrennt. Ohne Prüfung fällt alles zusammen und der Agent handelt in neuen Situationen nie richtig. H13 gestützt: Nach 15 Schritten pro Situation vermischen 75 % der Läufe Familien, nach 100 und mehr keiner.
- Alle älteren Ergebnisse sind exakt gleich.

### Version 0.7

- Handlungswissen wird im Alltag durch Ausprobieren gelernt (`action.py`) und beim Verschmelzen ins Schema übertragen. `Schema.action_role` ist durch `Schema.action_knowledge` ersetzt.
- `merge` gibt ein `MergeResult` mit beiden Zuordnungen zurück.
- Gelernt: Erfolg beim Ereignis 0,96, sonst höchstens 0,04. Das Ampelspiel erreicht damit 55 % Siege in Runde 1–10 (0.6 mit gesetzter Rolle: 56 %). Alle anderen Ergebnisse sind exakt gleich.

### Version 0.6

- Kontexterkennung sammelt Belege für „neuer Kontext“ über mehrere Schritte (`new_context_share`, Standard 0,03). In der Welt mit sechs Situationen landen 90 % statt 75 % der Übergänge im richtigen Kontext.
- Neues Experiment `recognition`. „Mehrere Schemata“ nutzt wieder Blöcke à 150 Schritte.
- Alle Ergebnisse, die von der Kontexterkennung abhängen, sind neu berechnet.

### Version 0.5.1

- Neues Modul `structure.py` mit der gemeinsamen Strukturabbildung (`embeddings`, `mapping_distance`, `best_match`). `merge` und `find_overlap` nutzen sie beide; `structural_distance` und die zweite Suche in `overlap.py` sind entfallen.
- Alle Ergebnisse sind unverändert.

### Version 0.5

- Mehrere Schemata im `WakeSleepAgent`, `schemas_or_flat_model` für neue Kontexte, Gesprächssituationen.
- Neue Module `game.py`, `overlap.py`, `player.py`; `Schema.action_role`; `role_names`.
- `experiments.py` ist ein Paket mit einem Modul pro Experiment.
- Die Ergebnisse von H11, Härtetest, H12, 0.3 und 0.4 sind unverändert.

### Version 0.4

- Neues Modul `wake_sleep.py` mit `WakeSleepAgent`: Erfahrungsgedächtnis pro Kontext, eigene Schlafregel, Schema wächst mit jeder passenden Situation.
- Die Schlaf-Logik existiert nur noch dort; das Experiment aus 0.3 nutzt den Agenten mit `maturity=None` und liefert unveränderte Zahlen.
- `MarkovModel.total_count()` und die Testsituation „Kasse“ sind neu.

### Version 0.3

- Kontextwechsel und Schemata sind verbunden (Abschnitt 6), mit eigenem Experiment.
- `OnlineMixture` ersetzt `Mixture`: Die Mischung lernt jetzt Schritt für Schritt weiter und kann deshalb selbst als Kontext dienen.
- Gemeinsames Protokoll `LearningPredictor` (vorhersagen und lernen) für alle Modelle, die ein Kontext sein können.
- Die Ergebnisse von H11, Härtetest und H12 sind gegenüber 0.2 unverändert.

### Version 0.2

- Ehrliche Messgröße (geometrisches Mittel) statt einfachem Mittel. Alle Zahlen wurden neu berechnet; die Aussagen von H11 und H12 bleiben bestehen.
- Härtetest mit abweichenden und gestörten Situationen.
- Schema als Vorwissen (lernend) und Schema mit Passungsprüfung (geprüft) zusätzlich zum starren Schema.
- Eine gemeinsame Klasse `Mixture` ersetzt die frühere `SchemaPredictor`-Klasse.
