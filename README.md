# HekmatKI

Ein offenes Experiment für eine andere Art von KI: kein großes Sprachmodell, sondern ein
kleiner Agent, der Gemeinsamkeiten zwischen Situationen erkennt, Wissen wiederverwendet und
lernt, welcher Kontext gerade passt. Hekmat bedeutet Weisheit.

**Warum es dieses Projekt gibt, erzähle ich in [MOTIVATION.md](MOTIVATION.md).**
Bitte lies das zuerst, wenn du verstehen willst, worum es mir geht.

- **Idee:** Ähnliche Situationen (beim Arzt warten, auf die Bahn warten) liegen wie
  „Scheiben“ übereinander. Der Agent lernt das Gemeinsame („Warten“) einmal und wechselt
  zwischen den Kontexten.
- **Stand:** Forschungsprototyp in Python, nur Standardbibliothek, 217 Tests.
  Spielwelten (ähnlich ARC-AGI-3) sind das Testfeld, nicht das Ziel.
- **Ehrlich:** Hier wird nichts behauptet, was nicht gemessen ist. Widerlegte Hypothesen
  stehen genauso im README wie gestützte (siehe [Grenzen](#grenzen)).

## Schnellstart

```bash
git clone https://github.com/etuioan/hekmatAi.git
cd hekmatAi
PYTHONPATH=src python -m hekmatki     # alle Experimente, Ausgabe auf Deutsch
```

Benötigt Python 3.12 oder neuer. Für Tests und Prüfungen siehe [CONTRIBUTING.md](CONTRIBUTING.md).

## Mitmachen

Fragen, Kritik, Fehlerberichte und eigene Ideen sind sehr willkommen, auch die Erklärung,
warum etwas so nicht funktionieren kann. Wie das geht, steht in
[CONTRIBUTING.md](CONTRIBUTING.md).

## Lizenz

[MIT](LICENSE)

---

## HekmatKI Prototyp 0.16: Schema-Stapel, Kontextwechsel, Weltmodell und ein Agent für ganz andere Welten

Ein kleiner, vollständig nachvollziehbarer Test der Idee, ähnliche Alltagssituationen als
übereinanderliegende „Scheiben“ zu modellieren und zwischen ihnen zu wechseln.
Die Hintergründe stehen im Forschungsdossier, die genaue Funktionsweise in
[docs/SPEZIFIKATION.md](docs/SPEZIFIKATION.md).
Welches Modul auf welches Paper, Prinzip und welche Hypothese zurückgeht, steht in
[docs/PAPER_ZUORDNUNG.md](docs/PAPER_ZUORDNUNG.md).

Alle Werte unten sind die typische Wahrscheinlichkeit, die der Agent dem tatsächlich
folgenden Ereignis gibt (geometrisches Mittel, gemittelt über 20 Zufallsstarts). Kein Agent
kann im Durchschnitt das „Optimum“ übertreffen, also das wahre Modell der Simulation.
Vollständige Ausgabe: [docs/ergebnisse.txt](docs/ergebnisse.txt).

## Ergebnis 1: Scheiben beschleunigen das Lernen (H11)

Aus „Warten beim Arzt“ und „Warten auf die U-Bahn“ entsteht automatisch ein gemeinsames
Schema „Warten“. Damit ist der Agent bei „Warten am Flughafen-Gate“ nach 20 Beobachtungen
praktisch am Optimum; ohne Schema erreicht er das auch nach 160 noch nicht ganz.
„Plaudern“, eine Situation ohne Wartestruktur, wird korrekt **nicht** verschmolzen.

| Beobachtungen | ohne Schema | mit Schema | Optimum |
|---:|---:|---:|---:|
| 5 | 0.439 | 0.591 | 0.674 |
| 10 | 0.539 | 0.644 | 0.674 |
| 20 | 0.609 | 0.672 | 0.674 |
| 160 | 0.665 | 0.672 | 0.674 |

## Ergebnis 2: Härtetest, wenn die Situation vom Schema abweicht

Vier Gate-Varianten: normal, Verspätung (sehr langes Warten), sofort Boarding (sehr kurzes
Warten) und mit 20 % zufälligen Störungen.

| Variante | Beob. | ohne | starr | lernend | geprüft | Optimum |
|---|---:|---:|---:|---:|---:|---:|
| normal | 10 | 0.497 | **0.604** | 0.587 | 0.577 | 0.674 |
| normal | 160 | 0.666 | **0.672** | 0.668 | 0.668 | 0.674 |
| Verspätung | 10 | 0.777 | 0.708 | 0.756 | **0.778** | 0.874 |
| Verspätung | 160 | 0.852 | 0.734 | **0.862** | 0.856 | 0.874 |
| sofort Boarding | 10 | 0.597 | 0.639 | **0.650** | 0.649 | 0.732 |
| sofort Boarding | 160 | 0.720 | 0.632 | **0.721** | 0.720 | 0.732 |
| Störungen | 10 | 0.350 | 0.269 | **0.365** | 0.359 | 0.446 |
| Störungen | 160 | 0.422 | 0.286 | **0.423** | **0.423** | 0.446 |

- **starr** (Schema wird unverändert übernommen) ist nur gut, wenn die Situation genau passt.
  Bei Verspätung und Störungen ist es sogar schlechter als gar kein Schema.
- **lernend** (Schema als Vorwissen, das die Beobachtungen korrigieren) ist überall nahe am
  Besten und nie deutlich schlechter als ohne Schema.
- **geprüft** (lernend plus die Frage „passt das Schema überhaupt?“) verhindert zusätzlich
  den Nachteil bei wenigen Beobachtungen in einer stark abweichenden Situation.
  Dafür kostet es etwas, wenn das Schema genau passt.

Das deckt sich mit der Hirnforschung im Dossier: Ein Schema beschleunigt das Lernen
(Tse 2007), neue Information wird aber weiter eingebaut, und das Gehirn regelt dynamisch,
wie stark (Marcos et al. 2026).

## Ergebnis 3: Kontextwechsel verhindert Vergessen (H12)

Hin- und Rückweg beim Pendeln nutzen dieselben Symbole, aber gegensätzliche Abläufe.
Direkt nach der Rückkehr in eine bekannte Situation erreicht der Agent mit
Kontextinferenz 0,579, ein Agent mit einem gemeinsamen Modell nur 0,423 (Optimum 0,658).
Er findet im Mittel 2,1 Kontexte, richtig wären 2 (seit 0.6, siehe Ergebnis 8).

## Ergebnis 4: Neue Situation sofort aus dem Schema

Jetzt arbeiten Scheiben und Kontextwechsel zusammen, wie ein Wach-Schlaf-Zyklus:

1. **Wach:** Der Agent erlebt Arzt und U-Bahn im Wechsel und findet die Kontexte selbst.
2. **Schlaf:** Er verschmilzt seine zwei ähnlichsten Kontexte zum Schema „Warten“.
3. **Wach:** Das Gate taucht auf. Der Agent erkennt „neue Situation“ und baut ihr Modell
   sofort aus dem Schema, mit Prüfung, ob das Schema überhaupt passt.

Alle drei Orte zeigen dieselben vier Lampen, aber jede Farbe bedeutet an jedem Ort etwas
anderes. Der Agent sieht nur Farben und muss am Ablauf erkennen, wo er ist.

| Agent | neue Situation (erstes Gate) | bekannte Situationen | Kontexte |
|---|---:|---:|---:|
| ein Modell | 0.034 | 0.311 | – |
| Kontexte | 0.418 | 0.635 | 3.00 |
| **Kontexte + Schema** | **0.497** | **0.637** | 3.00 |
| Optimum | 0.674 | 0.697 | – |

- In der neuen Situation schließt das Schema knapp ein Drittel der Lücke zum Optimum
  (0,418 → 0,497). In bekannten Situationen schadet es nicht.
- Ein einziges Modell scheitert fast völlig, weil die Farben sich widersprechen.
- Der Vorteil hängt davon ab, wie früh man misst: in den ersten 10 Schritten
  0,330 statt 0,257, über den ganzen Block 0,610 statt 0,582.
- Die Schlafphase vergleicht alle Paare eigener Kontexte und nimmt das ähnlichste, statt
  blind die ersten beiden. So stört auch ein überzähliger Kontext nicht.
- Seit 0.6 erkennt der Agent eine neue Situation etwas vorsichtiger (Ergebnis 8). Hier
  kostet das ein wenig: In 0.5 waren es 0,430 und 0,539.

## Ergebnis 5: Der Agent entscheidet selbst, wann er schläft

Der Agent merkt sich pro Kontext, was er dort erlebt hat. Sobald ein Kontext 100 Übergänge
gesammelt hat, schläft er und baut diese Erfahrung ins Schema ein. Niemand gibt ihm mehr
vor, wann. Strom: Arzt, U-Bahn, Arzt, U-Bahn, **Gate (neu)**, Arzt, Gate, **Kasse (neu)**,
U-Bahn, Kasse.

| Agent | Gate neu | Kasse neu | bekannte | Schlafphasen | Kontexte im Schema |
|---|---:|---:|---:|---:|---:|
| Kontexte, kein Schlaf | 0.418 | 0.409 | 0.629 | – | – |
| fester Schlaf (wie 0.3) | 0.497 | 0.480 | 0.630 | 1 | 2 |
| **eigener Schlaf** | **0.494** | **0.478** | **0.630** | 4 | 4 |
| Optimum | 0.674 | 0.671 | 0.681 | – | – |

- Der Agent schläft in allen 20 Läufen genau viermal, jeweils wenn Arzt, U-Bahn, Gate und
  Kasse genug Erfahrung haben, und alle vier Orte landen im Schema „Warten“.
- Er ist damit genauso gut wie der Agent mit vorgegebenem Schlaf, braucht aber keinen
  Zeitplan von außen.
- Überzählige Kontexte, die nur kurz entstehen, reifen nie und kommen deshalb nie ins
  Schema. Die Reifeschwelle filtert sie aus.
- Ehrlich: Dass das Gate im Schema steckt, hilft der Kasse hier **nicht** messbar. Alle
  vier Orte haben dieselbe Struktur, das Schema aus Arzt und U-Bahn kannte sie schon.
  Ein größeres Schema sollte erst helfen, wenn die ersten Situationen allein ein
  unvollständiges Bild geben.
- Die Kasse profitiert jetzt etwa so viel wie das Gate (+0,07 und +0,08). In 0.5 waren es
  nur +0,06 gegenüber +0,11. Meine Vermutung damals war, dass der Agent bei vielen
  bekannten Kontexten länger braucht, um „das ist neu“ zu erkennen. Mit der besseren
  Erkennung aus 0.6 ist der Unterschied verschwunden, das stützt die Vermutung.

## Ergebnis 6: Mehrere Schemata

Passt eine Situation nicht zu „Warten“, kann der Agent im Schlaf ein zweites Schema gründen.
Getestet mit Wartesituationen und Gesprächen (Frage, Antwort, Zustimmung, neues Thema) im
Wechsel, alle mit denselben vier Lampen: sechs Situationen, darunter neu das Gate und das
Gespräch mit dem Freund.

| Agent | Gate neu | Freund neu | bekannte | Schemata |
|---|---:|---:|---:|---:|
| Kontexte, kein Schlaf | 0.371 | 0.350 | 0.553 | – |
| ein Schema (wie 0.4) | 0.436 | 0.347 | 0.558 | 1 |
| **mehrere Schemata** | **0.428** | **0.363** | **0.559** | 1.95 |
| Optimum | 0.667 | 0.651 | 0.667 | – |

- Der Agent bildet in 19 von 20 Läufen genau die zwei richtigen Schemata „Warten“ und
  „Gespräch“, ohne dass ihm jemand sagt, welche Situation wohin gehört.
- Mit der besseren Kontexterkennung aus 0.6 sind alle Werte deutlich gestiegen (in 0.5,
  mit doppelt so langen Blöcken: Freund neu 0,239, bekannte 0,541).
- Das zweite Schema hilft dem neuen Gespräch aber nur wenig (0,363 statt 0,347). Gespräche
  sind schwerer vorherzusagen als Warten, und die ersten Schritte verbringt der Agent noch
  in einem alten Kontext, bevor er „neu“ erkennt.

## Ergebnis 7: Ampelspiel, „Warten“ als Schnittmenge

Das Spiel: Autos fahren eine Weile, dann wird die Ampel gelb, dann grün. Warten ist immer
sicher. Laufen gewinnt nur bei Grün, sonst gibt es einen Unfall. Wer bei Grün wartet,
verpasst die Chance. Der Agent kennt die Schemata „Warten“ und „Gespräch“ aus dem Alltag.

Neu in 0.7: Niemand sagt ihm mehr, wo im Ablauf er selbst handeln soll. Im Alltag
probiert er ab und zu, loszugehen (in 10 % der Schritte), und merkt sich nur, ob es
geklappt hat. Klappen tut es nur direkt beim Ereignis (Aufruf, Zug kommt). Im Schlaf
wandert dieses Handlungswissen mit ins Schema, über dieselbe Zuordnung wie beim
Verschmelzen:

| Rolle in „Warten“ | beschäftigen | hinweis | ereignis | weitergehen |
|---|---:|---:|---:|---:|
| gelernter Handlungserfolg | 0,01 | 0,04 | **0,96** | 0,04 |

Sein Spielmodell hat sechs Zustände, das Schema „Warten“ nur vier Rollen. Verschmelzen ist
also gar nicht möglich. Stattdessen sucht der Agent nach jeder Runde, ob die Struktur eines
Schemas vollständig in einem Teil seines Spielmodells steckt: die **Schnittmenge**. Findet
er sie, merkt er sich nur die Zuordnung. Schema und Spielmodell bleiben getrennt.

| Spieler | Siege Runde 1–10 | Siege Runde 11–30 | Unfälle pro Spiel | erster Sieg in Runde |
|---|---:|---:|---:|---:|
| ohne Vorwissen | 26 % | 90 % | 6,0 | 7,8 |
| **mit Schemata** | **55 %** | **100 %** | **3,0** | **5,1** |
| Optimum | 100 % | 100 % | 0 | 1 |

- In allen 20 Läufen findet der Agent nach etwa 5 Runden die Schnittmenge, immer mit
  „Warten“ und nie mit „Gespräch“, und immer richtig: Autos = sich beschäftigen,
  Gelb = Hinweis, Grün = Ereignis.
- Aus dem Schema weiß er: Beim Ereignis lohnt sich Handeln, sonst nicht. Also läuft er
  bei Grün und nirgends sonst. Alle seine Unfälle passieren vor dem Fund, danach keiner.
- Das Ergebnis ist praktisch gleich wie in 0.6, als die Handlungsrolle noch von Hand
  gesetzt war (56 % statt 55 %). Die Abkürzung ist also weg, ohne dass es schlechter wird.
- Auch der Spieler ohne Vorwissen findet die Schnittmenge, wenn er nach dem Spiel sein
  fertiges Spielmodell mit den Schemata vergleicht (20 von 20 Läufen).
- In 70 % der Funde ordnet der Agent „drüben“ der Rolle „weitergehen“ zu, sonst „verpasst“.
  Beides ist strukturell richtig: Danach geht es jeweils mit der nächsten Runde weiter.

## Ergebnis 8: Bessere Kontexterkennung (neu in 0.6)

Bisher musste ein einzelner Schritt reichen, um „das ist neu“ zu beschließen. Passte der
Schritt zufällig zu irgendeinem alten Kontext, sprang der Agent dorthin und lernte dort
Falsches. Jetzt sammeln sich Belege für „neu“ über mehrere Schritte, genau wie für die
bekannten Kontexte. Dafür beginnt „neu“ mit kleinerer Vorab-Wahrscheinlichkeit
(`new_context_share` = 0,03), sonst zerlegt der Agent Situationen in zu viele Teile.

Gemessen wird, welcher Anteil der Übergänge im richtigen Kontext landet:

| Welt | Situationen | Kontexte 0.5 → 0.6 | richtig 0.5 → 0.6 |
|---|---:|---:|---:|
| Pendeln (H12) | 2 | 2,00 → 2,10 | 98,1 % → 96,4 % |
| Lampen: Warten | 3 | 3,00 → 3,00 | 98,8 % → 99,0 % |
| **Lampen: Warten + Gespräche** | 6 | 4,90 → 6,45 | **75,0 % → 89,9 %** |

- In der schweren Welt landen jetzt 90 % statt 75 % der Übergänge im richtigen Kontext.
  Vorher wurden im Mittel nur 4,9 von 6 Situationen auseinandergehalten.
- In den leichten Welten ändert sich fast nichts. Ehrlicher Preis: In H12 zerlegt der
  Agent in 2 von 20 Läufen eine Situation in zwei Kontexte, und eine neue Situation wird
  ein paar Schritte später erkannt (Ergebnis 4).
- Getestet habe ich die Anteile 0,001 bis 0,1 und eine Variante, bei der Belege für „neu“
  schnell verblassen. Ab 0,05 und bei der verblassenden Variante entstehen zu viele
  Kontexte; 0,01 bis 0,03 sind alle gut, 0,03 ist in der schweren Welt am besten.

## Ergebnis 9: Dritte Ebene (Meta-Schema) und H13 (neu in 0.8)

Der Agent erlebt sechs Alltagssituationen aus drei Familien: **Warten** (Arzt, U-Bahn),
**Anstehen** (Bäcker, Post) und **Gespräch** (Nachbar, Kollegin). Anstehen ähnelt Warten,
hat aber andere Zeiten: Das Vorrücken dauert, und nach dem Dransein bleibt man noch beim
Bezahlen. Nebenbei probiert er wie in Ergebnis 7 aus, wo Handeln klappt.

Im Schlaf verdichtet er mit **derselben Routine** zweimal (`stack.consolidate`): Immer das
ähnlichste passende Paar verschmilzt, bis keines mehr nah genug ist. Ebene 2 nutzt den
Schwellenwert 0,1, Ebene 3 den großzügigeren Wert 0,2. Neu ist eine Prüfung: Zwei Scheiben
dürfen nur verschmelzen, wenn sich ihr Handlungswissen nicht widerspricht.

Nach 400 Schritten pro Situation (20 Läufe):

| Ebene | Scheiben | richtig gehandelt am Gate | in der Kantine |
|---|---:|---:|---:|
| Ebene 2 (Warten, Anstehen, Gespräch) | 3 | 100 % | 80 % |
| **Ebene 3 (Meta-Schema + Gespräch)** | **2** | **100 %** | **85 %** |
| Ebene 3 ohne Prüfung (alles in einem) | 1 | 0 % | 0 % |

- In allen 20 Läufen entstehen genau die drei Schemata und darüber ein Meta-Schema aus
  Warten und Anstehen: „Man wartet, bis man dran ist, dann handelt man.“ Das ist das
  Meta-Schema aus dem Dossier („eine knappe Sache wird nacheinander vergeben“).
- Gespräch bleibt draußen, obwohl sein Ablauf nah genug wäre (Abstand 0,15): Dort klappt
  Handeln nirgends, bei Warten schon. Ohne diese Prüfung fällt alles in ein Meta-Schema,
  und der Agent würde in neuen Situationen nie im richtigen Moment handeln (0 %).
- Spannend: Die beste reine Strukturzuordnung zwischen Warten und Anstehen ist „verdreht“
  (die lange Vorrückphase passt besser zum Beschäftigen als zum Hinweis). Erst die Prüfung
  des Handlungswissens erzwingt die Zuordnung „dran sein = Ereignis“.
- Was die dritte Ebene bringt, ist **Verdichtung**: 2 statt 3 Scheiben, und die
  Entscheidungen bleiben gleich gut. Besser vorhersagen kann der Agent damit nicht; in
  dieser kleinen Welt schafft das schon Ebene 2.
- Kantine liegt unter 100 %, weil 30 Schritte nicht immer reichen, um die Rollen sicher
  zuzuordnen. Mit 100 Schritten sind es auf beiden Ebenen 100 %.

**H13: Sofort oder verzögert verschmelzen?** Dieselbe Prüfung mit weniger Erfahrung vor
dem Schlaf:

| Schritte pro Situation | Schemata richtig | Familien vermischt | Meta-Schema richtig | richtig gehandelt |
|---:|---:|---:|---:|---:|
| 15 | 10 % | 75 % | 25 % | 20 % |
| 30 | 40 % | 55 % | 25 % | 45 % |
| 50 | 75 % | 15 % | 50 % | 70 % |
| 100 | 100 % | 0 % | 85 % | 82 % |
| **400** | **100 %** | **0 %** | **100 %** | **92 %** |

- H13 wird gestützt: Wer nach wenig Erfahrung verschmilzt, wirft Familien zusammen
  (übertriebene Verallgemeinerung) und handelt danach oft im falschen Moment.
- Der Grund steckt in beiden Teilen: Die Abläufe sind nach 15 Schritten noch zu ungenau
  geschätzt, und es gibt kaum Handlungsversuche, also auch keine Widersprüche, die ein
  falsches Verschmelzen verhindern könnten.
- Angepasst habe ich den Test aus dem Dossier: Dort heißt es „nach 1, 3 oder 10 ähnlichen
  Situationen“, hier variiert die Erfahrung pro Situation. Was es kostet, *zu lange* zu
  warten (in der Zwischenzeit hat der Agent kein Schema), misst dieses Experiment nicht.

## Ergebnis 10: Spielefamilie, Regeln selbst entdecken (neu in 0.9)

Bisher hat der Agent die Welt nur beobachtet. Jetzt muss er handeln, um etwas zu lernen,
wie bei ARC-AGI-3. Die Spiele „Schlüssel und Tür“: ein Gang aus vier Feldern, links ein
Schlüssel, rechts eine Tür. Wer mit dem Schlüssel an der Tür „benutzen“ drückt, gewinnt
und beginnt von vorn. Jedes Spiel hat **andere Symbole** (etwa „lila stern“) und **eine
andere Tastenbelegung**. Der Agent weiß nichts davon, nicht einmal, welche Taste nach
links geht.

Der **Entdecker** probiert gezielt aus, was er noch nicht kennt (Neugier), und geht den
kürzesten Weg zum Sieg, sobald er einen kennt. Nach jedem Spiel macht er aus seinem
Spielmodell ein **Schema** ohne Aussehen. Im nächsten Spiel hält er mehrere **Deutungen**
bereit (eine pro möglicher Tastenbelegung). Jede Beobachtung streicht die Deutungen, die
ihr widersprechen. Er folgt der Taste, die die meisten noch möglichen Deutungen empfehlen.

Tastendrücke bis zum ersten Sieg und Siege in 60 Tastendrücken (20 Läufe):

| Spiel | 1. Sieg ohne Schema | mit Schema | bestenfalls | Siege ohne | mit Schema | höchstens |
|---|---:|---:|---:|---:|---:|---:|
| Spiel 1 | 20,9 | 20,9 | 6 | 7,1 | 7,1 | 10 |
| **Spiel 2** | 22,4 | **9,2** | 6 | 7,0 | **9,0** | 10 |
| **Spiel 3** | 18,7 | **10,3** | 6 | 7,5 | **8,9** | 10 |
| gespiegelt | 21,1 | **9,1** | 6 | 7,0 | **9,0** | 10 |
| länger | 25,6 | 22,6 | 7 | 5,5 | 5,9 | 8 |
| ohne Schlüssel | 13,9 | **8,7** | 3 | **12,3** | 9,6 | 20 |

- **Übertragung klappt:** Ab dem zweiten Spiel braucht der Agent nur noch halb so viele
  Versuche bis zum ersten Sieg, obwohl alles anders aussieht und die Tasten vertauscht
  sind. Das ist H11 in der Form, die das Dossier vorschlägt.
- **Gespiegelt** hilft das Schema genauso: Für die Strukturabbildung ist ein gespiegelter
  Gang dasselbe Spiel mit vertauschten Links- und Rechts-Tasten. Das hatte ich nicht
  eingeplant.
- **Länger** (5 statt 4 Felder): Das Schema passt nicht mehr, in 85 % der Läufe sind am
  Ende alle Deutungen widerlegt. Es hilft trotzdem ein wenig, weil der Anfang des Spiels
  passt. Ein Schema über Zustände kann nicht ausdrücken, dass nur der Gang länger ist.
- **Ohne Schlüssel** zeigt den Preis von Vorwissen: Mit Schema gewinnt der Agent zwar
  schneller das erste Mal, holt aber jedes Mal brav den unnötigen Schlüssel. Ob die Tür
  auch so aufgeht, prüft er nur in 1 von 20 Läufen. Deshalb gewinnt er seltener (9,6 statt
  12,3). In der Psychologie heißt das Einstellungseffekt.
- Spiel 3 ist nicht besser als Spiel 2. Das zweite Spiel ergänzt das Schema kaum (17,7 →
  18,4 von 24 Übergängen), weil der Agent nach dem ersten Sieg nur noch den bekannten Weg
  geht und nichts Neues mehr ausprobiert.

## Ergebnis 11: Neugier, die bleibt (neu in 0.10)

Bisher hörte der Entdecker auf zu probieren, sobald er einen Weg zum Sieg kannte. Jetzt wägt
er vor jedem Schritt ab, ob sich ein **Abstecher** zu einer nie gedrückten Taste lohnt
(`curiosity.py`):

    Überraschungschance × zusätzliche Siege, falls Abkürzung − Siege, die der Umweg kostet

Das ist eine einfache Form des epistemischen Werts aus der aktiven Inferenz: Wissen ist
umso mehr wert, je länger man es noch nutzen kann. Einer nie probierten Taste traut er eine
Abkürzung mit 10 % zu, einer Taste, für die sein Schema „nichts passiert“ vorhersagt, mit 5 %.

Summe der Siege in den fünf Spielen nach Spiel 1 (20 Läufe):

| Spieldauer | ohne Schema | + Neugier | mit Schema | + Neugier |
|---|---:|---:|---:|---:|
| 60 Tastendrücke | **39,3** | 35,7 | **42,4** | 31,6 |
| 200 Tastendrücke | 163,0 | **170,1** | 156,8 | **165,1** |

- **Kurz** lohnt sich Neugier nicht: Der Agent verliert 9 bis 26 % seiner Siege.
- **Lang** lohnt sie sich: Im Spiel ohne Schlüssel steigt der Agent mit Schema von 34 auf
  57 Siege (höchstens 66). Der Einstellungseffekt aus Ergebnis 10 ist damit behoben. Das
  Schema wird außerdem fast vollständig (23,1 statt 18,4 von 24 Übergängen).
- **Der Preis:** In den Spielen, in denen das Schema stimmt, gewinnt der neugierige Agent
  etwas weniger (rund 28 statt 32 Siege), weil er auch dort die Abkürzungen prüft. Sein
  Vorsprung durch das Schema ist dort dann weg.

**Wie sehr soll der Agent seinem Schema trauen?** Je kleiner die Überraschung, die er
dem Schema zutraut, desto weniger prüft er nach (200 Tastendrücke, mit Schema und Neugier):

| zugetraute Überraschung | Siege, wenn das Schema stimmt | Siege ohne Schlüssel |
|---:|---:|---:|
| 1,25 % | 29,9 | 30,0 |
| 2,5 % | 29,9 | 30,0 |
| 5 % | 28,2 | 57,2 |
| 10 % | 28,2 | 57,2 |

- Es gibt eine scharfe Grenze: Unter 5 % prüft der Agent die Tür ohne Schlüssel nie und
  bleibt im Einstellungseffekt. Ab 5 % findet er die Abkürzung, zahlt aber in den normalen
  Spielen etwa 1,7 Siege. Das ist genau der Regler zwischen „Vorwissen nutzen“ und „Neues
  zulassen“, den das Dossier aus der Hirnforschung ableitet (G6).
- Die Werte 10 % und 5 % sind von Hand gewählt. Eine Lernregel, die die Überraschung aus
  eigener Erfahrung schätzt, habe ich ausprobiert; sie brachte nichts Besseres und bleibt
  deshalb draußen.

## Ergebnis 12: Regeln statt Zustände (neu in 0.11)

Das Spiel-Schema aus Ergebnis 10 merkt sich einzelne Zustände. Auf einen längeren Gang
passt es deshalb nicht. Ein **Regel-Schema** (`rules.py`) merkt sich stattdessen, *wo*
etwas passiert: „Benutzen an der Wand auf der einen Seite wechselt etwas (Schlüssel),
danach gewinnt Benutzen an der Wand auf der anderen Seite.“

Dafür bekommt der Agent ein Stück **Kernwissen** mit, wie es ARC voraussetzt: Das Spiel ist
ein Gang mit einer Taste vorwärts, einer rückwärts und einer zum Benutzen. Welche Taste
welche ist, weiß er nicht. Für jede der sechs Belegungen zeichnet er eine Karte. Einen Ort
beschreibt er auf zwei Arten: als **Wand** in einer Richtung oder als **Schritte vom
Start**. Nach jedem Spiel behält er die Beschreibungen, die zu allen Spielen passen.

Jetzt wird jedes Spiel der Familie länger (4, 5, 6 Felder). Tastendrücke bis zum ersten Sieg
(20 Läufe, 60 Tastendrücke pro Spiel):

| Spiel | Länge | ohne Vorwissen | Zustands-Schema | Regel-Schema | bestenfalls |
|---|---:|---:|---:|---:|---:|
| Spiel 1 | 4 | 20,9 | 20,9 | 20,9 | 6 |
| Spiel 2 | 5 | 25,8 | 22,4 | **13,3** | 7 |
| Spiel 3 | 6 | 27,6 | 28,6 | **14,4** | 8 |
| gespiegelt | 4 | 21,4 | **10,2** | 12,2 | 6 |
| viel länger | 8 | 38,5 | 34,9 | **20,5** | 10 |
| ohne Schlüssel | 4 | 15,6 | 9,4 | **8,9** | 3 |

- **Übertragung auf andere Größen klappt:** Mit Regel-Schema braucht der Agent nur gut halb
  so viele Versuche, auch im Gang mit 8 Feldern, den er nie gesehen hat. Das
  Zustands-Schema hilft dort kaum.
- **Er findet die richtige Beschreibung selbst:** Nach Spiel 3 beschreibt er die Tür in
  20 von 20 Läufen nur noch als „Wand“. „2 Schritte vom Start“ hat Spiel 2 widerlegt. Den
  Schlüssel beschreibt er weiter auf beide Arten („1 Schritt vom Start“ und „Wand“), denn
  in allen drei Spielen trifft beides zu. Erst ein Spiel, das beides trennt, könnte ihm
  zeigen, welche stimmt.
- **Gleich große Spiele** (gespiegelt) löst das Zustands-Schema etwas schneller. Es kennt
  jeden Übergang; das Regel-Schema muss erst die Tasten herausfinden.
- **Ohne Schlüssel** gewinnt der Agent mit Regel-Schema am häufigsten (12,7 Siege, ohne
  Vorwissen 10,7). Das ist aber Zufall, keine Einsicht: In 8 von 20 Läufen schickt ihn eine
  gespiegelte Deutung zuerst zur Tür, und er merkt, dass sie offen ist (18,5 Siege). In den
  anderen 12 holt er brav den Schlüssel (8,8 Siege).
- Zwei Fehler im ersten Entwurf sind lehrreich. **Abstimmen** wie beim Zustands-Schema
  geht hier nicht: Gespiegelte Deutungen erklären alles gleich gut und stimmen immer
  gegeneinander, also pendelte der Agent hin und her. Jetzt **folgt er einer Deutung, bis
  sie widerlegt ist**. Und eine Wand, die er nie angestoßen hat, ist kein Gegenbeweis: Nur
  ein Feld dahinter schließt sie aus.

## Ergebnis 13: 2D-Welt wie ARC-AGI-3 (neu in 0.12)

Bisher sah der Agent ein Symbol pro Zustand. Jetzt sieht er, wie bei ARC-AGI-3, ein ganzes
**Farbraster**: ein Labyrinth mit seiner Figur, Wänden, einem Schlüssel, einer Tür und
Fallen. Betritt er den Schlüssel, wechselt die Tür die Farbe und lässt sich betreten (Sieg).
Fallen schicken ihn zum Start. Jedes Level hat **neue Farben, neue Tastennamen und ein
neues Labyrinth**. Was welche Farbe ist, sagt ihm niemand.

Der **Objekt-Agent** (`grid/`) vergleicht die Raster vor und nach jedem Tastendruck:
- Das einzige Feld, das sich bewegt, ist er selbst. Die Verschiebung ist die Richtung der
  Taste.
- Was das Betreten einer Farbe bewirkt (blockiert, frei, Auslöser, zurück, Ziel), liest er
  aus dem Unterschied ab. Das gilt sofort für jedes Feld dieser Farbe.
- Er plant kürzeste Wege mit dem, was er weiß, und geht sonst zur nächsten unbekannten Farbe.

Nach jedem Level benennt er die Farben nach ihrer Wirkung (**Rollen**) und merkt sich, wie
sie aussehen: ein Feld oder viele, am Rand oder innen. Im nächsten Level ordnet er die neuen
Farben Rollen zu und folgt einer Deutung, bis sie widerlegt ist, wie in Ergebnis 12.

Tastendrücke bis zum ersten Sieg (20 Läufe, 200 Tastendrücke pro Level):

| Level | Größe | Bilder (alt) | Objekte | Objekte + Schema | bestenfalls |
|---|---:|---:|---:|---:|---:|
| Level 1 | 7×7 | 59,2 | 28,2 | 28,2 | 7,7 |
| Level 2 | 9×9 | 114,4 | 27,2 | **25,9** | 12,2 |
| Level 3 | 11×11 | 159,7 | 30,6 | **28,6** | 17,1 |
| groß | 15×15 | 186,8 | 41,9 | **39,8** | 26,9 |
| ohne Schlüssel | 9×9 | 54,0 | 27,6 | **26,1** | 5,7 |
| viele Fallen | 11×11 | 97,5 | 24,5 | **24,1** | 10,6 |

Schritte in eine Falle (ab Level 2, wo es ein Schema gibt):

| Level | Bilder (alt) | Objekte | Objekte + Schema |
|---|---:|---:|---:|
| Level 2 | 4,5 | 0,8 | **0,1** |
| Level 3 | 3,5 | 0,8 | **0,1** |
| groß | 2,0 | 0,9 | **0,2** |
| ohne Schlüssel | 0,7 | 0,5 | **0,3** |
| viele Fallen | 8,4 | 1,0 | **0,3** |

- **Objekte statt Bilder ist der große Schritt.** Im Labyrinth mit 15×15 Feldern gewinnt
  der alte Ansatz in 200 Tastendrücken fast nie (1,8 Siege). Der Objekt-Agent gewinnt nach
  rund 42 Tastendrücken zum ersten Mal und danach fast so oft wie möglich (9,1 von 9,9).
  Einmal gegen eine Wand gelaufen, kennt er alle Wände.
- **Das Rollen-Schema vermeidet vor allem Fallen:** In vier von fünf Leveln tritt der Agent
  drei- bis achtmal seltener hinein, obwohl die Fallen in jedem Level eine andere Farbe haben. Den ersten Sieg bringt es nur
  1 bis 2 Tastendrücke früher. Schlüssel und Tür sehen für ihn gleich aus (je ein Feld
  innen), welches welches ist, muss er also trotzdem ausprobieren. Die Tasten muss er in
  jedem Level neu lernen.
- **Zum Anschauen:** [docs/wiedergabe.html](docs/wiedergabe.html), Fall „Labyrinth (0.12)“,
  zeigt Level „groß“ aus Lauf 3 Schritt für Schritt, alle drei Agenten nebeneinander, mit
  dem, was jeder gerade über die Farben weiß oder vermutet.

## Ergebnis 14: Ein Weltmodell, das umlernt (neu in 0.13)

Die 2D-Welt bekommt Spielregeln, wie sie in ARC-AGI-3 vorkommen:
- **Kisten** lassen sich schieben, wenn dahinter Platz ist.
- Eine **Druckplatte** öffnet ein **Tor**, solange etwas auf ihr liegt. Steht die Figur
  selbst darauf, kommt sie nicht durchs Tor. Sie muss also eine Kiste auf die Platte schieben.
- Ein **Spiel** hat jetzt sechs Level mit denselben Farben und Tasten, jedes mit neuem
  Labyrinth (wie in ARC-AGI-3). Im letzten Level tauschen Ausgang und Falle die Farben.

Für den Objekt-Agenten aus 0.12 ist eine Kiste ein Widerspruch: Dieselbe Farbe blockiert
einmal (Wand dahinter) und gibt ein andermal nach. Er bricht ab. Der neue **Modell-Agent**
(`grid/model_agent.py`) baut sich stattdessen ein **Weltmodell** aus Regeln:
- **Eine Regel pro Farbe** (blockiert, frei, schiebbar, zurück, Ziel): die einfachste, die zu
  allen Versuchen passt. Passt keine mehr, gilt der neueste Versuch, und er notiert, was er
  umgelernt hat.
- **Fernwirkungen:** Was wechselt anderswo die Farbe, wenn eine Farbe verdeckt oder
  aufgedeckt wird? (Platte verdeckt: Tor offen.) Geschehen zwei Dinge zugleich, merkt er
  sich die Ursache als unsicher und prüft sie gezielt, sobald ein Schritt sie klären kann.
- **Vorausdenken:** Er spielt Tastendrücke im Modell durch und sucht den kürzesten Plan zum
  Sieg. Gibt es keinen, geht er zur nächsten offenen Frage („Was passiert auf grau?“,
  „Lässt sich braun auf gelb schieben?“) und probiert sie aus. Pläne, die eine Kiste in eine
  Ecke schieben, meidet er.
- **Zweifel in Stufen**, wenn nichts mehr geht: erst am Vorwissen, dann an Wänden (eine
  Kiste vor der Wand sieht aus wie eine Wand), zuletzt nutzt er Fallen als Neustart.
- **Vorwissen:** Der vierte Agent startet jedes Level mit seinem Modell aus den Leveln davor.

Tastendrücke bis zum ersten Sieg (20 Spiele, 300 Tastendrücke pro Level, kein Sieg = 301):

| Level | Größe | Bilder | Objekte 0.12 | Weltmodell | Weltmodell + Vorwissen | bestenfalls |
|---|---:|---:|---:|---:|---:|---:|
| Ausgang | 9×9 | 70,3 | 21,1 | **19,1** | **19,1** | 7,7 |
| Fallen | 11×11 | 86,0 | 22,4 | 21,9 | **7,9** | 7,8 |
| Kiste | 9×9 | 240,7 | 301 | 61,9 | **47,0** | 17,4 |
| zwei Kisten | 11×11 | 278,9 | 301 | 76,5 | **32,5** | 28,8 |
| groß | 13×13 | 284,8 | 301 | 78,7 | **36,5** | 35,2 |
| Tausch | 11×11 | 298,7 | 301 | 77,0 | **51,1** | 26,4 |

Schritte in eine Falle:

| Level | Bilder | Objekte 0.12 | Weltmodell | Weltmodell + Vorwissen |
|---|---:|---:|---:|---:|
| Ausgang | 0,3 | 0,4 | 0,4 | 0,4 |
| Fallen | 1,4 | 0,5 | 0,5 | **0,0** |
| Kiste | 1,9 | 0,2 | 0,5 | 0,2 |
| zwei Kisten | 2,1 | 0,5 | 0,8 | **0,1** |
| groß | 2,6 | 0,7 | 1,1 | **0,0** |
| Tausch | 2,9 | **0,7** | 0,9 | 1,1 |

- **Umlernen statt abbrechen ist der große Schritt.** Der Objekt-Agent aus 0.12 scheidet in
  95 bis 100 % der Level mit Kisten aus und gewinnt dort nie. Der Modell-Agent gewinnt 156 von
  160 Kisten-Level, ohne Vorwissen nach 62 bis 79 Tastendrücken.
- **Vorwissen macht ihn fast perfekt:** Im großen Level gewinnt er mit seinem Modell aus
  den vier Leveln davor nach 36,5 Tastendrücken; kürzer geht es nur um 1,3. Er tritt dort in
  keine Falle mehr.
- **Falsches Vorwissen schadet kaum:** Im Level „Tausch“ läuft er erst in die alte
  Ausgangsfarbe (eine Falle), lernt um und zweifelt dann gezielt an allem, was er nur aus
  früheren Leveln weiß. Trotzdem gewinnt er nach 51 statt 77 Tastendrücken.
- **Kein Rückschritt:** Auf den sechs Labyrinthen aus Ergebnis 13 ist der Modell-Agent so schnell wie der
  Objekt-Agent oder etwas schneller (groß 41,0 statt 41,9; viele Fallen 23,7 statt 24,5).
- **Grenze:** In 4 von 240 Läufen schiebt er eine Kiste beim Ausprobieren so, dass sie
  festsitzt, bevor er weiß, dass sie eine Kiste ist. Ohne erreichbare Falle gibt es keinen
  Neustart. ARC-AGI-3 hat dafür eine Taste, diese Welt noch nicht.
- **Zum Anschauen:** [docs/wiedergabe.html](docs/wiedergabe.html) zeigt drei Fälle mit allen
  Agenten nebeneinander: ein Kisten-Rätsel, das Level mit falschem Vorwissen und das
  Labyrinth aus Ergebnis 13. Neu erzeugen:
  `PYTHONPATH=src python -m hekmatki.experiments.grid_replay docs/wiedergabe.html`

## Ergebnis 15: Wissen, das die Farbe wechselt (neu in 0.14)

Bisher galt das Weltmodell nur innerhalb eines Spiels: „braun ist schiebbar“ hilft nichts,
wenn im nächsten Spiel die Kiste gelb ist. Hypothese H14 aus dem Dossier sagt: Regeln
sollen an **Rollen** hängen, nicht an Farben (Struktur und Inhalt getrennt, wie im
Tolman-Eichenbaum-Modell, in Schema Networks und OPINE-World).

- **Rollen-Weltmodell** (`grid/role_model.py`): Nach einem Spiel benennt der Agent jede
  Farbe nach ihrer Rolle („ich“, „schiebbar“, „auslöser“, „verschlossen“, „geöffnet“,
  „ziel“ …) und merkt sich, wie die Rolle im ersten Bild aussah.
- **Bindung im neuen Spiel:** Jede neue Farbe kann jede Rolle mit passendem Aussehen haben.
  Beobachtungen streichen Rollen, die nicht passen. Der Agent übernimmt nur, worin **alle**
  besten Deutungen übereinstimmen; wo sie sich widersprechen, testet er selbst. So wird
  Neugier genau dort geweckt, wo das Vorwissen mehrdeutig ist. Sieht er, dass eine Platte
  ein Tor öffnet, folgt daraus: Platte = Auslöser, Tor = verschlossen, und die neue Farbe
  ist „geöffnet“.
- **Neustart-Taste** wie RESET in ARC-AGI-3: Der Agent kennt sie und nutzt sie, wenn nichts
  mehr zu lernen ist und eine Kiste festsitzt.

Versuch: Der Agent spielt ein ganzes Spiel A (wie Ergebnis 14). Dann kommen neue Level in
den Farben und mit den Tasten eines **neuen Spiels B**. Jedes Labyrinth gibt es auch in den
Farben von A, als Bestwert. Tastendrücke bis zum ersten Sieg (20 Läufe, 300 pro Level,
kein Sieg = 301):

| Level | ohne Vorwissen | Farben aus A | Rollen aus A | gleiches Spiel | bestenfalls |
|---|---:|---:|---:|---:|---:|
| Ausgang | 16,8 | 41,0 | **16,6** | 6,9 | 6,9 |
| Fallen | 21,1 | 48,2 | **16,9** | 10,1 | 10,1 |
| Kiste | 56,2 | 138,6 | **50,5** | 21,0 | 20,7 |
| zwei Kisten | 63,1 | 136,8 | **53,2** | 26,0 | 25,8 |
| groß | 79,5 | 206,6 | **73,2** | 33,6 | 33,4 |
| Tausch | 57,2 | 127,9 | **49,6** | 41,5 | 24,4 |

Schritte in eine Falle: Fallen 0,8 → **0,0**, zwei Kisten 0,8 → **0,3**, Tausch 0,8 →
**0,3** (ohne Vorwissen → Rollen aus A).

- **Farbwissen geht in neuen Farben in die Irre.** „Farben aus A“ braucht zwei- bis
  dreimal so lange wie ganz ohne Vorwissen und gewinnt in 5 bis 55 % der Level gar nicht.
  Genau das war die Grenze von 0.13.
- **Rollen-Wissen überträgt sich (H14 teilweise bestätigt).** In fünf von sechs Leveln
  gewinnt „Rollen aus A“ schneller als ohne Vorwissen, um 8 bis 20 %, und tritt seltener in
  Fallen. Im Level „Fallen“ tritt er in keine einzige.
- **Die Lücke zum Bestwert bleibt groß.** Zwei Gründe: Tasten haben in Spiel B neue Namen
  und müssen neu gelernt werden (schon im Level „Ausgang“ kostet das etwa 10 Tastendrücke),
  und Ausgang, Falle, Kiste, Platte und Tor sehen im ersten Bild gleich aus (ein Feld,
  innen). Welche Farbe welche Rolle hat, klärt sich erst durchs Ausprobieren.
- **Neustart-Taste:** „Ohne Vorwissen“, „Rollen aus A“ und „gleiches Spiel“ gewinnen jedes
  Level (in Ergebnis 14 ohne Taste blieben 4 von 240 Kisten-Läufen ohne Sieg). Sie drücken
  die Taste selten (höchstens 0,2-mal pro Level), nur wenn eine Kiste festsitzt.
- **Beim Testen gefunden und behoben:** Eine falsche Figurenfarbe aus dem Vorwissen wurde
  nie korrigiert. Jetzt gilt: Bewegt sich allein eine andere Farbe, ist sie die Figur.
- **Zum Anschauen:** Der neue Fall „Neue Farben“ in
  [docs/wiedergabe.html](docs/wiedergabe.html) zeigt alle vier Agenten im großen Level.

## Ergebnis 16: Gegenprobe, wenn Vorwissen nicht passt (neu in 0.15)

Bisher wurde nur gemessen, wie viel Vorwissen nützt. Runde 5 des Dossiers sagt: Die
gefährlichste Lage ist ein ähnliches Spiel mit anderer Mechanik (falsche Analogie). Diese
Version misst deshalb auch den **Schaden** durch Vorwissen (negative Übertragung, Wang
2019) und prüft zwei Gegenmittel aus Runde 5.

Versuch (`experiments/grid_foreign.py`): Nach einem ganzen Spiel A kommen drei Level eines
Spiels B. Das „Modell aus A“ spielt sie in den Farben und mit den Tasten von A: Sie sehen aus
wie A, sind es aber nicht immer.

- **gewohnt:** Kisten-Rätsel mit den Regeln von A (Vergleich).
- **Tor umgekehrt:** Die Druckplatte schließt das Tor, statt es zu öffnen. Die Kiste steht zu
  Beginn auf der Platte; man muss sie herunterschieben.
- **Eis:** Die Figur rutscht, bis etwas sie aufhält. Das passt in keine der fünf Regelarten,
  die der Agent kennt: ein Test außerhalb dessen, was wir eingebaut haben.

Zwei Gegenmittel:

- **Prüfung** (`grid/trust.py`, H17 in einfacher Form): Vorwissen erst nach zwei
  Bestätigungen nutzen, nach einem Widerspruch nie mehr.
- **Teilprüfung** (H16): Vorwissen sofort nutzen, aber sobald der Agent feststeckt, jeden
  Teil testen, den er in diesem Level nicht selbst gesehen hat (neue Zweifel-Stufe im
  Modell-Agenten).

Tastendrücke bis zum ersten Sieg (20 Läufe, 300 pro Level, kein Sieg = 301), alle im
Aussehen von A:

| Level | ohne Vorwissen | Modell aus A | + Prüfung | + Teilprüfung | bestenfalls |
|---|---:|---:|---:|---:|---:|
| gewohnt | 61,4 | 22,9 | 25,5 | **22,9** | 22,4 |
| Tor umgekehrt | 49,5 | 195,6 | 198,1 | **54,6** | 24,8 |
| Eis | 127,2 | 131,8 | 134,9 | 131,8 | 7,7 |

Ohne Sieg beim umgekehrten Tor: Modell aus A 40 %, + Prüfung 40 %, + Teilprüfung 0 %.

- **Falsches Vorwissen schadet stark.** Beim umgekehrten Tor braucht das Modell aus A viermal
  so lange wie ganz ohne Vorwissen und gewinnt in 40 % der Läufe gar nicht. Die Ursache ist
  in der Wiedergabe zu sehen: Er hält die Kiste für bekannt („schiebbar“) und probiert sie
  nie aus. Gerade der Test, der sein Vorwissen widerlegen würde, unterbleibt wegen des
  Vorwissens. Das ist der Einstellung-Effekt aus Runde 5 (Bilalić 2008).
- **Als Ganzes prüfen hilft nicht.** Boden und Wand sind in jedem Spiel gleich und bestätigen
  das Vorwissen nach ein bis zwei Schritten. Widerlegt wird es nur in 55 % der Läufe, wenn
  der Agent zufällig doch die Kiste bewegt, und dann oft spät (in acht Stichproben nach 7
  bis 255 Tastendrücken). Kommt der Widerspruch früh, wirft der Agent auch die richtigen
  Teile weg. Bestätigungen an Teilen, die überall gleich sind, sagen nichts über die Teile,
  die sich geändert haben. H17 in dieser einfachen Form ist damit widerlegt.
- **Teile einzeln prüfen hilft (H16 gestützt).** Der Schaden fällt von +146 auf +5
  Tastendrücke, kein Lauf bleibt ohne Sieg, und wo das Vorwissen passt, kostet es nichts.
- **Rollen aus A schaden nicht** (8 und 5 Tastendrücke schneller als ohne Vorwissen in den
  Farben von B), auch nicht beim umgekehrten Tor. Rollen werden vorsichtig gebunden, und was
  mehrdeutig ist, testet der Agent ohnehin.
- **Eis schafft keiner.** Mit und ohne Vorwissen brauchen alle etwa 130 statt 8
  Tastendrücke. Rutschen ist keine der fünf Regelarten des Agenten; er kann es nicht einmal
  vermuten. Das ist die Grenze G4 aus Runde 5: Der Agent findet nur, was wir vorgesehen
  haben.

**Spielwelt gegen Alltagswelt** (`experiments/cross_world.py`). Gilt die Lehre auch außerhalb
der Spiele? Der Härtetest aus Ergebnis 2 hat dieselben drei Arten, mit Vorwissen umzugehen:
starr übernehmen, als Ganzes prüfen („geprüft“), Teile korrigieren („lernend“). Im selben
Maß, Prozent schlechter als ohne Vorwissen (negativ heißt: Vorwissen hilft):

| Welt | Lage | übernehmen | als Ganzes prüfen | Teile korrigieren |
|---|---|---:|---:|---:|
| Alltag | normal | −9,4 % | −6,7 % | −7,4 % |
| Alltag | sehr lang | +11,7 % | −0,2 % | +0,3 % |
| Alltag | sehr kurz | +5,0 % | −2,9 % | −3,0 % |
| Alltag | gestört | +27,6 % | −1,3 % | −1,9 % |
| Spiel | gewohnt | −62,7 % | −58,4 % | −62,7 % |
| Spiel | Tor umgekehrt | +295,4 % | +300,6 % | **+10,5 %** |
| Spiel | Eis | +3,5 % | +6,1 % | +3,5 % |

- **In beiden Welten** schadet unverändert übernommenes Vorwissen, wenn es nicht passt, und
  Teile einzeln korrigieren hält den Schaden klein. Diese Lehre gilt über die Spielwelt
  hinaus.
- **Als Ganzes prüfen reicht nur in der Alltagswelt.** Dort kommen die Beobachtungen von
  selbst, egal was der Agent glaubt. In der Spielwelt wählt er durch sein Handeln, was er
  sieht, und sein Vorwissen hält ihn von der entscheidenden Beobachtung fern. Für jeden
  handelnden Agenten, nicht nur im Spiel, heißt das: Vorwissen muss die Neugier auf seine
  ungeprüften Teile wach halten, statt sie zu ersetzen.
- **Grenze:** Beide Welten nutzen verschiedenen Code (Übergänge zählen gegen Regeln
  ableiten). Gleich ist das Prinzip, nicht der Mechanismus. Ob ein gemeinsamer Mechanismus
  beides kann, ist offen.
- **Zum Anschauen:** Der neue Fall „Tor umgekehrt“ in
  [docs/wiedergabe.html](docs/wiedergabe.html) zeigt das Modell aus A, das an der Kiste
  vorbeiläuft, neben dem Agenten mit Teilprüfung.

## Ergebnis 17: Ein Agent, drei ganz verschiedene Welten (neu in 0.16, H19)

Bis 0.15 war alles, was der Agent kennt, auf die 2D-Spielwelt zugeschnitten: Raster, Farben,
vier Richtungen, fünf Regelarten. Runde 6 des Dossiers fragt: Was, wenn die neue Umgebung
plötzlich dreidimensional ist, oder eine Datenmenge, in der man unter Millionen Einträgen
etwas finden muss? Diese Version baut dafür einen neuen, allgemeinen Agenten
(`general/`, Spezifikation Abschnitt 9). Er sieht nur ein Tupel ganzer Zahlen und drückt
Tasten ohne Namen. Jede Welt mischt die Reihenfolge der Zahlen und der Tasten neu.

Was er tut, in drei Schritten:

1. **Regeln als kleine Programme.** Für jede Taste und jede Zahl sucht er das kürzeste
   Programm, das erklärt, wie sich die Zahl ändert (Bausteine: bleibt, +k, steigt, fällt,
   wenn-dann). Beispiel aus dem 2D-Raum, wörtlich: „Taste 0: G4 +1, außer G3 = 1 (dann bleibt
   sie)“. Übersetzt: „+x verschiebt die Position x um 1, außer an einer Wand.“
2. **Erst die Form.** Aus den Regeln erkennt er die Form der Welt: Eine Zahl, die eine Taste
   erhöht und eine andere gleich weit senkt, ist eine Raumachse; eine, die steigt oder fällt,
   eine Ordnung. Dazu lernt er das Ziel als „Zahl i = Zahl j“.
3. **Dann planen.** Im Raum sucht er einen Weg auf seiner Karte (A*). In einer Ordnung grenzt
   er ein. Das wird von selbst zur binären Suche, ohne dass sie programmiert wurde.

Versuch (`experiments/general_worlds.py`): Lehrplan in kleinen Welten (je 6 Runden), dann
5 Prüfrunden in der großen Welt. 10 Läufe, mittlere Schritte bis zum Ziel (nicht erreicht
zählt als 2000):

| Welt | Größe | Zufall | Tabelle | Regeln ohne Form | Form + Regeln | bestenfalls |
|---|---|---:|---:|---:|---:|---:|
| 2D-Raum | 25×25 | 1583,2 | 1415,9 | 52,4 | **23,2** | 17,8 |
| 3D-Raum | 10×10×10 | 1082,5 | 1062,7 | 19,0 | **10,8** | 9,1 |
| Suche | 1.048.575 Schlüssel | 2000 (nie) | 2000 (nie) | 2000 (nie) | **18,0** | 18,0 |

- **Die Form findet er in allen 30 Läufen selbst:** „Raum mit 2 Dimensionen“, „Raum mit 3
  Dimensionen“, „Ordnung“. Niemand hat ihm gesagt, welche Zahl eine Position ist.
- **Im Suchbaum ist er optimal.** Er findet einen von über einer Million Schlüsseln in so
  wenigen Schritten wie möglich (etwa 18), während alle anderen Agenten in 2000 Schritten
  nie ankommen. Er hat dafür nur kleine Bäume mit 7 bis 31 Schlüsseln gesehen.
- **Ohne Form bleibt er im Raum stecken** (doppelt so viele Schritte) und in der Suche ganz.
  „Regeln ohne Form“ hat dieselben Regeln, plant aber nur einen Schritt voraus und hat
  keine Karte; der Abstand misst also Form und Karte zusammen.
- Die Tabelle (Q-Lernen) kann nichts auf Neues übertragen und ist kaum besser als Zufall.
- **Zum Anschauen:** [docs/welten.html](docs/welten.html) zeigt nebeneinander, was der Agent
  sieht (nur Zahlen), was wirklich passiert (Raum, Würfel in Schichten, Suchbaum) und was er
  herausgefunden hat, in seinen Worten und übersetzt.

## Ergebnis 18: Eine Bibliothek, die nur behält, was wiederverwendet wird (neu in 0.16, H20)

Aus Regeln ohne Ausnahme bildet der Agent Muster mit Lücken (Anti-Unifikation wie bei
DreamCoder und Stitch), etwa „fester Schritt, außer ein Schalter ist 1 (dann bleibt sie)“.
In der nächsten Welt probiert er sie früh. Jedes Muster hat einen Zähler; wird es zwei Welten
lang nicht genutzt, fliegt es raus. Gemessen wird, wie Berlot-Attwell 2026 fordert, bei
gleicher Rechenarbeit und gegen eine Zufallsbibliothek (zwei sinnlose Muster gleicher Länge).

Geprüfte Programme bei der Regelsuche (`experiments/library_transfer.py`, 10 Läufe;
Suchen mit Erfolg / alle Suchen):

| Reihenfolge | Welt | ohne Bibliothek | mit Bibliothek | Zufallsbibliothek |
|---|---|---:|---:|---:|
| 2D → 3D → Suche | 3D-Raum | 762 / 6714 | **364** / 6204 | 1279 / 12810 |
| 2D → 3D → Suche | Suche | 211 / 703 | 232 / 690 | 311 / 930 |
| Suche → 2D → 3D | 2D-Raum | 421 / 2785 | **321** / 3006 | 688 / 4888 |
| Suche → 2D → 3D | 3D-Raum | 762 / 6714 | **416** / 7024 | 1279 / 12810 |

- **Das Muster aus dem 2D-Raum wird im 3D-Raum sechsmal wiederverwendet** und halbiert dort
  die Suche nach den Regeln, die es gibt. Im Suchbaum passt es nicht und wird nicht genutzt.
- **Die Zufallsbibliothek schadet** (fast doppelt so viel Suche). Es kommt also auf den
  Inhalt an, nicht darauf, dass es eine Bibliothek gibt.
- **Über alle Suchen ist der Gewinn klein oder negativ** (−8 % bis +8 %), weil die Bibliothek
  auch bei Zahlen mitprobiert wird, die sich nicht vorhersagen lassen (etwa die Wand am
  nächsten Ort). Mit knappem Budget (20 Programme je Suche) erreicht er das Ziel im 3D-Raum
  mit und ohne Bibliothek gleich oft (98 % und 100 %). H20 ist damit nur im ersten Teil
  gestützt: Die Bibliothek lernt das Richtige und verwirft das Falsche; gesamt spart sie
  noch nichts. Den zweiten Teil der Hypothese (Mechaniken wie das Eis finden) prüft diese
  Version nicht: Die Bausteine kennen noch kein „wiederholen“.

## Ergebnis 19: Eine neue Umgebung erkennen (neu in 0.16, H18)

Rauschen ist keine neue Welt. Der Agent prüft für jede Regel, wie wahrscheinlich die Fehler
der letzten 20 Schritte bei ihrer bisherigen Trefferquote sind (Binomial-Test). Erst unter
10⁻⁵ ist das „unerwartet“ (Yu & Dayan 2002). Dann sucht er drei Erklärungen: Die Regel war
nur unvollständig (verfeinern), eine andere Karte erklärt es besser (neue Karte oder zurück
zu einer alten, Sanders 2020), oder die Größe ist einfach unvorhersagbar.

Versuch (`experiments/new_world.py`): rutschiger Raum A (jeder zehnte Schritt geht nicht),
dann Raum B mit vertauschten Tasten, dann wieder A, je 15 Runden. 10 Läufe, mittlere
Schritte je Runde (in Klammern: die ersten drei Runden der Phase):

| Umgang mit Überraschung | A | B | A wieder | Karten | Fehlalarme | alte Karte wieder |
|---|---:|---:|---:|---:|---:|---:|
| ohne Erkennung | 21,8 (61) | 104,7 (104) | 134,5 (150) | 1 | – | – |
| jede Überraschung | 53,4 (89) | 53,0 (53) | 30,8 (32) | 21,6 | 416,4 | 40 % |
| nie neue Karte (nur umlernen) | 17,6 (60) | 54,0 (68) | 23,6 (50) | 1 | – | – |
| erwartet / unerwartet | 17,6 (60) | 53,1 (66) | 24,8 (**18**) | 2,1 | 0,1 | **90 %** |

- **Rauschen löst fast nie eine neue Karte aus** (0,1 Fehlalarme gegen 416, wenn jede
  Überraschung zählt), und Raum A lernt er dabei genauso gut wie ohne Erkennung.
- **Bei der Rückkehr nimmt er in 90 % der Läufe seine alte Karte wieder** und ist in den
  ersten drei Runden sofort schnell (18 Schritte statt 50 beim Umlernen und 150 ohne
  Erkennung). Das ist der Nutzen getrennter Karten: Das alte Wissen bleibt erhalten.
- **B erkennt er in 80 % der Läufe** in den ersten 30 Schritten. Sonst lernt er um, was
  hier nicht schadet. In B selbst ist er nicht schneller als beim Umlernen.
- Bisher wechseln nur die Tasten. Ein Wechsel zwischen ganz verschiedenen Welten (Raum zu
  Suchbaum) im selben Strom ist noch nicht geprüft.

## Grenzen

- Der allgemeine Agent (Ergebnisse 17 bis 19) kennt nur zwei Formen aus einer festen Liste
  (Raum, Ordnung). Eine Welt mit anderer Form (Kreis, Graph, Zählwerk) erkennt er nicht und
  fällt auf „Regeln ohne Form“ zurück. Die Bausteine kennen kein „wiederholen“; das Eis aus
  Ergebnis 16 kann er so noch nicht ausdrücken.
- Seine Wahrnehmung ist geschenkt: Er bekommt saubere Zahlen, keine Bilder. Wände und Ziel
  sind eigene Zahlen.
- Viele Werte im allgemeinen Agenten sind von Hand gewählt (4 Bit je Baustein, 30 %
  Fehlergrenze, Fenster 20, Grenze 10⁻⁵, Zweifel 0,85, zwei Welten Geduld, drei Versuche bis
  zum Ausweichen). Sie stehen als „ohne Grundlage“ in der Paper-Zuordnung.
- Die Welt ist absichtlich winzig: vier Symbole pro Situation, Markov-Modelle erster Ordnung.
- Verschmelzen funktioniert nur bei gleich vielen Symbolen; für Teile gibt es die
  Schnittmenge.
- Der Stapel hat drei Ebenen. Die Schwellenwerte (0,1 und 0,2) sind von Hand gewählt.
- Ebene 3 läuft bisher nur im eigenen Experiment, noch nicht im Wach-Schlaf-Agenten mit
  Kontexterkennung.
- Die Spiele sind deterministisch und winzig (höchstens 16 Zustände, 3 Tasten).
- Die 2D-Welt ist einfach: eine Figur aus einem Feld, vier Richtungen, Regeln hängen nur
  von der Farbe ab. Der Modell-Agent lernt um, kennt aber nur fünf Arten von Regeln und
  Fernwirkungen als Farbtausch. „Aussehen“ heißt im Rollen-Schema bisher nur: ein Feld oder
  viele, am Rand oder innen.
- Das Rollen-Weltmodell (Ergebnis 15) unterscheidet Rollen im ersten Bild nur am Aussehen
  „ein Feld oder viele, Rand oder innen“. Ausgang, Falle, Kiste, Platte und Tor sehen damit
  gleich aus; der Agent muss sie erst ausprobieren. Tastenwissen überträgt es gar nicht.
- Die Gegenprobe (Ergebnis 16) hat nur zwei fremde Mechaniken. Die Teilprüfung greift erst,
  wenn der Agent feststeckt; ein falsches Teil, das nur Umwege kostet, bemerkt sie nicht.
  Die Schwelle von zwei Bestätigungen und die Mindestlänge der Eis-Level (6) sind von Hand
  gewählt. Neue Regelarten wie Rutschen kann der Agent nicht erfinden.
- Spielwelt und Alltagswelt nutzen verschiedenen Code; verglichen wird nur das Prinzip.
- Als festsitzend erkennt der Modell-Agent nur Kisten in Ecken. Die Neustart-Taste nutzt er
  erst, wenn es nichts mehr zu lernen gibt; ob sich ein früher Neustart lohnt, lernt er
  nicht. Die Suche hört nach 30 000 Szenen auf.
- Regel-Schemata setzen voraus, dass das Spiel ein Gang mit drei Tasten ist. Dieses
  Kernwissen ist fest eingebaut, nicht gelernt. Orte kennen nur zwei Beschreibungen (Wand,
  Schritte vom Start).
- Die Neugier rechnet nur mit einer Art Überraschung: dass eine Taste sofort gewinnt.
  Ihre Chancen (10 % und 5 %) sind von Hand gewählt (Ergebnis 11).
- Die Kontexterkennung ist besser geworden, liegt bei sechs Situationen mit denselben vier
  Lampen aber noch bei 90 % (Ergebnis 8). Neue Situationen werden erst nach ein paar
  Schritten erkannt.
- Der Anteil für „neuer Kontext“ (0,03) ist von Hand gewählt, nach Tests mit 0,001 bis 0,1.
- Das Ausprobieren im Alltag ändert den Ablauf der Situation nicht, und die Weltregel
  „Handeln klappt nur beim Ereignis“ ist fest in der Simulation (Ergebnis 7).
- Verschmelzen und Schnittmenge probieren alle Zuordnungen aus. Ab 9 Symbolen bricht der
  Code bewusst mit einer Fehlermeldung ab.
- Die Reifeschwelle (100 Übergänge) ist fest eingestellt und nicht vom Agenten gelernt.
- Kontexte werden hart zugeordnet (nur der Gewinner lernt). Dadurch landen einzelne
  mehrdeutige Übergänge manchmal im falschen Kontext.

## Starten

Benötigt Python 3.12 oder neuer, keine weiteren Pakete.

```bash
PYTHONPATH=src python -m hekmatki
```

Qualitätsprüfungen (einmalig `pip install -e ".[dev]"`):

```bash
pytest            # 217 Tests
mypy              # strikte Typprüfung
ruff check .      # Linter
ruff format --check .
```

## Aufbau

Ein Modul, eine Aufgabe:

| Modul | Aufgabe |
|---|---|
| `situations.py` | Die simulierte Welt: Situationen mit wahrer Dynamik, Varianten und Störungen |
| `markov.py` | Situationsmodell: zählt Übergänge und sagt vorher |
| `structure.py` | Strukturabbildung: das eine Werkzeug hinter Verschmelzen und Schnittmenge |
| `schema.py` | Schemata, Bindungen, Verschmelzen, Schema als Vorwissen, `OnlineMixture` |
| `context.py` | Kontextinferenz: welche Scheibe gilt, nur diese lernt; austauschbares Startmodell |
| `wake_sleep.py` | Wach-Schlaf-Agent: Erfahrung pro Kontext merken, selbst schlafen, Schemata bilden |
| `action.py` | Handlungswissen: im Alltag ausprobieren, Erfolge zählen, Widersprüche erkennen |
| `stack.py` | Schema-Stapel: Situation erleben, jede Ebene mit derselben Routine verdichten |
| `puzzle.py` | Spielefamilie „Schlüssel und Tür“: Bauplan, Aussehen, Tastenbelegung |
| `game_schema.py` | Spiel-Schemata, Deutungen prüfen, kürzeste Wege, Schemata ergänzen |
| `explorer.py` | Entdecker: eigener Plan, Rat des Vorwissens oder Neugier |
| `advisor.py` | Was der Entdecker von Vorwissen braucht (`Advisor`), Mehrheitsentscheid |
| `rules.py` | Regel-Schemata: Tastendeutung, Karte des Gangs, Orte, Ratgeber für neue Größen |
| `curiosity.py` | Neugier mit Augenmaß: Wert eines Abstechers ins Unbekannte |
| `grid/` | 2D-Welt: `world` (Feldarten, Farben, Tasten, Spielregeln, fremde Mechanik), `mazes` (Labyrinthe und Rätsel erzeugen, kürzeste Lösung), `perception` (wer hat sich bewegt), `effects` (Wirkung einer Farbe), `knowledge` (was der Objekt-Agent lernt), `planner` (kürzeste Wege), `agent` (Objekt-Agent), `roles` (Rollen-Schema), `model` (Weltmodell), `induction` (Regeln aus Beobachtungen), `simulation` (im Modell vorausdenken), `search` (Pläne suchen), `model_agent` (Modell-Agent), `role_model` (Weltmodell über Rollen), `trust` (Vorwissen prüfen), `baseline` (alter Entdecker), `play` (Spiel und Aufzeichnung) |
| `game.py` | Das Ampelspiel: Regeln, Zustände, Aktionen |
| `overlap.py` | Schnittmenge: steckt ein Schema in einem Teil eines größeren Modells? |
| `player.py` | Spieler für das Ampelspiel, nutzt Schnittmengen als Vorwissen |
| `online.py` | Protokolle `LearningPredictor`/`OnlineLearner`, Vergleichsagent mit einem Modell |
| `evaluation.py` | Gemeinsame Schnittstelle `Predictor` und ehrliche Bewertung |
| `experiments/` | Ein Modul pro Experiment: `schema_learning` (H11, Härtetest), `forgetting` (H12), `sleep` (Kontextwechsel, Wach-Schlaf, mehrere Schemata), `traffic_light` (Ampelspiel), `recognition` (Kontexterkennung), `meta_schema` (dritte Ebene, H13), `discovery` (Spielefamilie), `exploration` (Neugier), `rule_transfer` (Regeln statt Zustände), `grid_transfer` (2D-Welt), `grid_mechanics` (Weltmodell), `grid_roles` (Rollen-Weltmodell), `grid_foreign` (Gegenprobe mit fremder Mechanik), `cross_world` (Spielwelt gegen Alltagswelt), `grid_replay` (Wiedergabe-Seite), `general_worlds`, `library_transfer`, `new_world`, `general_replay` (allgemeiner Agent, Seite „Ein Agent, drei Welten“), dazu `blocks` mit gemeinsamen Werkzeugen |
| `general/` | Allgemeiner Agent ab 0.16: `env` (Schnittstelle, Mischung), `worlds` (Raum, Würfel, Suchbaum), `programs` (Bausteine), `synthesis` (kürzestes Programm), `library` (Bibliothek), `knowledge` (Regelbuch, Ziel), `form` (Form der Welt), `planner` (Wege, Eingrenzen), `detector` (neue Umgebung), `agent` (der Agent), `run` (Runden, Vergleichsagenten) |
| `general_report.py` | Ausgabe der Ergebnisse 17 bis 19 |
| `__main__.py` | Ausgabe der Ergebnisse |

Grundsätze: Lesbarkeit vor Cleverness, nur Standardbibliothek, vollständige
Typannotationen (`mypy --strict`), ungültige Eingaben lösen immer einen `ValueError` mit
verständlicher Meldung aus, Zufall nur über einen übergebenen `random.Random`.
Bezeichner sind englisch (Python-Konvention), Dokumentation und Ausgaben deutsch.

## Änderungen in 0.16

- Neues Paket `general/`: ein Agent, der nur Zahlen und Tasten sieht und drei ganz
  verschiedene Welten lernt (Raum, Würfel, Suchbaum mit über einer Million Schlüsseln).
- Regeln als Programme mit kürzester Beschreibung, Bibliothek mit Wiederverwendungs-Zähler,
  Form der Welt, Planen auf der gelernten Karte, Erkennen einer neuen Umgebung.
- Experimente `general_worlds`, `library_transfer`, `new_world` (Ergebnisse 17 bis 19) und
  die Seite [docs/welten.html](docs/welten.html) (`general_replay`).
- Tests in `tests/test_general.py` und `tests/test_general_experiments.py`.
- Der alte Code ist nicht angefasst; Ergebnisse 1 bis 16 sind gleich geblieben.

## Änderungen in 0.15

- Fremde Mechanik in der 2D-Welt (`Mechanics` in `grid/world.py`): Druckplatte schließt das
  Tor, Eis. Eine Kiste darf jetzt zu Beginn auf der Platte stehen.
- Zwei Gegenmittel gegen falsches Vorwissen im Modell-Agenten: Prüfung (`grid/trust.py`,
  `ModelAgent(checked=True)`) und Teilprüfung (`ModelAgent(doubts_parts=True)`, Zweifel-Stufe
  4d).
- Neue Experimente `grid_foreign` (Gegenprobe) und `cross_world` (Spielwelt gegen
  Alltagswelt), Ergebnis 16.
- Wiedergabe-Seite mit fünftem Fall „Tor umgekehrt“.
- Tests in `tests/test_foreign.py`; `tests/grid_puzzle.py` baut jetzt auch Level ohne Platte.
- Ergebnisse 1 bis 15 sind exakt gleich geblieben.

## Änderungen in 0.14

- Rollen-Weltmodell (`grid/role_model.py`): Regeln hängen an Rollen statt an Farben und
  gehen so auf Spiele mit neuen Farben über. `WorldModel.renamed`, `ModelAgent(roles=…)`,
  `ModelAgent.knowledge`. Neues Experiment `grid_roles`, Ergebnis 15 (H14).
- Neustart-Taste wie in ARC-AGI-3 (`GridGame(restart=…)`), bekannt in Simulator, Regel-
  Ableitung und Agent.
- Vorwissen über die Figur wird korrigiert, wenn sich allein eine andere Farbe bewegt
  (`induction.py`); der Agent plant nur mit einer Figur, die in jedem Raster ein Feld hat.
- Wiedergabe-Seite mit viertem Fall „Neue Farben“.
- Tests: gemeinsames Test-Rätsel in `tests/grid_puzzle.py`, neue Tests in
  `tests/test_role_model.py`.
- Ergebnisse 1 bis 14 sind exakt gleich geblieben.

## Änderungen in 0.13

- Kisten, Druckplatte und Tor in der 2D-Welt. Labyrinth-Erzeugung und Löser stehen jetzt in
  `grid/mazes.py`.
- Modell-Agent mit Weltmodell (`model`, `induction`, `simulation`, `search`,
  `model_agent`). Neues Experiment `grid_mechanics`, Ergebnis 14.
- Der Objekt-Agent meldet Widersprüche als `ContradictionError` (ein `ValueError`);
  `play_grid` hält das als „ausgeschieden“ fest, statt abzustürzen.
- Wiedergabe-Seite mit drei Fällen.
- Ergebnisse 1 bis 13 sind exakt gleich geblieben.

## Änderungen in 0.12

- Neue 2D-Welt im Paket `grid/` mit Objekt-Agent und Rollen-Schema. Experiment
  `grid_transfer`, Ergebnis 13.
- Wiedergabe-Seite `docs/wiedergabe.html`, erzeugt von `experiments/grid_replay.py`.
- Ergebnisse 1 bis 12 sind exakt gleich geblieben.

## Änderungen in 0.11

- Regel-Schemata: `rules.py` liest aus einem Spiel ab, wo Benutzen etwas bewirkt, und
  verbindet das über Spiele hinweg (`revised`). Neues Experiment `rule_transfer`,
  Ergebnis 12.
- Gemeinsame Schnittstelle `Advisor` (`advisor.py`) für beide Arten von Vorwissen; der
  Entdecker kennt nur noch sie.
- `discovery.schema_after_game` ist jetzt öffentlich, weil zwei Experimente es nutzen.
- Ergebnisse 1 bis 11 sind exakt gleich geblieben.

## Änderungen in 0.10

- Neugier, die bleibt: `curiosity.py` bewertet Abstecher ins Unbekannte; der Entdecker
  nutzt das, wenn man ihm `Curiosity` mitgibt. Neues Experiment `exploration`, Ergebnis 11.
- `Explorer.choose` bekommt die verbleibenden Tastendrücke (`steps_left`).
- `game_schema.shortest_paths` berechnet alle kürzesten Wege auf einmal.
- Ergebnisse 1 bis 10 sind exakt gleich geblieben.

## Änderungen in 0.9

- Spielefamilie „Schlüssel und Tür“ (`puzzle.py`), Entdecker (`explorer.py`) und
  Spiel-Schemata mit Deutungen (`game_schema.py`). Neues Experiment `discovery`, Ergebnis 10.
- Ergebnisse 1 bis 9 sind exakt gleich geblieben.

## Änderungen in 0.8

- Dritte Ebene: `stack.py` verdichtet jede Ebene mit derselben Routine (`consolidate`).
  Neues Experiment `meta_schema` mit Ergebnis 9 (Meta-Schema und H13).
- `merge_schemas` verschmilzt Scheiben jeder Ebene samt Handlungswissen und verbietet
  Zuordnungen, unter denen sich das Handlungswissen widerspricht. `merge` ist jetzt die
  Kurzform für Modelle ohne Handlungswissen.
- Situationen wissen selbst, wo Handeln gelingt (`Situation.action_role`).
  Neue Familie „Anstehen“ (Bäcker, Post, Kantine).
- Ergebnisse 1 bis 8 sind exakt gleich geblieben.

## Änderungen in 0.7

- Handlungswissen wird gelernt statt gesetzt: neues Modul `action.py`. Der Agent probiert
  im Alltag aus, wo Handeln klappt, und das Wissen wandert beim Verschmelzen ins Schema.
- `Schema.action_role` ist ersetzt durch `Schema.action_knowledge` (Erfolg pro Rolle).
- `merge` gibt die beiden Zuordnungen zurück (`MergeResult`), damit Wissen pro Symbol
  auf Rollen übertragen werden kann.
- Ergebnisse 1 bis 6 und 8 sind exakt gleich geblieben; Ergebnis 7 fast (55 % statt 56 %).

## Änderungen in 0.6

- Kontexterkennung: Belege für „neuer Kontext“ sammeln sich über mehrere Schritte, mit
  kleinerer Vorab-Wahrscheinlichkeit (`new_context_share`). Ergebnis 8.
- Neues Experiment `recognition` misst, wie viele Übergänge im richtigen Kontext landen.
- „Mehrere Schemata“ läuft wieder mit normalen Blöcken (150 statt 300 Schritte).
- Alle Zahlen, die von der Kontexterkennung abhängen (Ergebnisse 3 bis 6), sind neu
  berechnet. Ergebnisse 1, 2 und 7 sind unverändert.

## Änderungen in 0.5.1

- Verschmelzen und Schnittmenge nutzen jetzt dieselbe Suche (`structure.py`). Verschmelzen
  ist der Sonderfall, dass die Schnittmenge alle Symbole umfasst. Vorher gab es zwei
  getrennte Suchen mit eigener Abstandsberechnung. Alle Zahlen sind exakt gleich geblieben.

## Änderungen gegenüber 0.4

- Mehrere Schemata im Wach-Schlaf-Agenten (Ergebnis 6), neue Gesprächssituationen.
- Ampelspiel, Schnittmenge und Spieler (Ergebnis 7); Schemata können eine Handlungsrolle haben.
- `experiments.py` ist in ein Paket mit einem Modul pro Experiment aufgeteilt.
- Alle Zahlen von Ergebnis 1 bis 5 sind exakt gleich geblieben.

## Änderungen gegenüber 0.3

- Neu: `WakeSleepAgent` mit eigenem Erfahrungsgedächtnis pro Kontext und eigener
  Schlafregel (Ergebnis 5). Neue Situationen wachsen ins Schema hinein.
- Das Experiment aus 0.3 nutzt jetzt denselben Agenten (Schlaf von außen ausgelöst).
  Dadurch gibt es die Schlaf-Logik nur noch einmal; alle Zahlen sind gleich geblieben.
- Neue Testsituation „Kasse“ mit denselben vier Lampen.

## Änderungen gegenüber 0.2

- Neu: Kontextwechsel und Scheiben verbunden (Ergebnis 4), mit Wach-Schlaf-Ablauf und
  der Lampen-Testwelt.
- `OnlineMixture` ersetzt `Mixture` und lernt Schritt für Schritt weiter, damit sie selbst
  ein Kontext sein kann.
- Die Zahlen von Ergebnis 1 bis 3 sind exakt gleich geblieben.

## Änderungen gegenüber 0.1

- Messgröße korrigiert: 0.1 nutzte das einfache Mittel, das übertriebene Sicherheit belohnt.
  Alle Zahlen sind neu berechnet; die Aussagen von H11 und H12 bleiben bestehen.
- Härtetest und die Varianten „lernend“ und „geprüft“ sind neu.

## Nächste Schritte

1. Formen nicht aus einer Liste wählen, sondern aus einer kleinen Grammatik suchen (Kette,
   Ring, Baum, Gitter, Produkt davon), wie Kemp & Tenenbaum 2008 (H19 ohne feste Liste).
2. Den Baustein „wiederholen, bis“ ergänzen und damit das Eis aus Ergebnis 16 im
   allgemeinen Agenten testen (zweiter Teil von H20).
3. Ein Strom, der zwischen ganz verschiedenen Welten wechselt (Raum, Suchbaum, Alltagswelt),
   damit H18 nicht nur vertauschte Tasten erkennt.
4. Die Bibliothek nur bei Größen mitprobieren, die vorhersagbar wirken, damit sie auch über
   alle Suchen spart (H20).
5. Die 2D-Spielwelt aus 0.12 bis 0.15 an die allgemeine Schnittstelle anschließen: derselbe
   Agent für Spiel und Raum.
6. Aus 0.15 offen: Teilprüfung früher auslösen (H16), gemeinsamer Mechanismus für Alltagswelt
   und Spielwelt, Neustart-Taste lernen, dritte Ebene im Wach-Schlaf-Agenten.
