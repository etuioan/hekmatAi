# Warum dieses Projekt?

*Ein persönlicher Text von Tenshira, der das Projekt begonnen hat.*

Hallo zusammen!

Bevor ich unser Projekt als Open Source veröffentliche, möchte ich ein bisschen erzählen, wie ich überhaupt hier gelandet bin und welche Gedanken dahinterstecken.

Ich bin einfach ein interessierter Mensch, der sich gerne Dinge im Kopf ausdenkt. Lange hätte ich mich als jemanden beschrieben, der ständig Ideen hat, aber kaum eine davon umsetzt. Einer, der nicht immer so genau weiß, was er da eigentlich tut, aber trotzdem neugierig ist. Dank KI habe ich inzwischen nicht mehr nur verrückte Ideen, sondern auch ein Werkzeug, das mir hilft, sie tatsächlich auszuprobieren.

Mich hat schon immer gereizt, gegen den Strom zu schwimmen. Deshalb habe ich mich gefragt: Könnte man eine gute Alternative zu LLMs bauen? Etwas, das anders funktioniert und ihnen vielleicht in bestimmten Bereichen sogar überlegen ist? Nicht unbedingt eine KI, die sofort alles besser kann. Erst einmal etwas Eigenes, das einen anderen Weg ausprobiert.

## Erster Versuch: eigene Neuronen

Meine erste Idee war: Was wäre, wenn ich selbst Neuronen programmiere, die sich miteinander verbinden, selbstständig gruppieren und durch evolutionäre Prozesse weiterentwickeln? Ich wollte sogar Wetterdaten als äußere Quelle für unvorhersehbare Einflüsse einbauen. Damals dachte ich, dadurch würde der Prozess irgendwie natürlicher. Wetterdaten liefern natürlich nicht automatisch „echten Zufall“, aber so ungefähr war mein Gedankengang.

Meine Hoffnung war, dass bei genügend Millionen künstlicher Neuronen vielleicht irgendwann etwas Interessantes emergiert. Also etwas entsteht, das ich nicht ausdrücklich einprogrammiert habe.

Ich muss allerdings zugeben: Von Neuronen hatte ich damals kaum Ahnung.

Irgendwann wurde das Projekt riesig und der Code immer unübersichtlicher. Damit ging auch die Lust verloren, weiterzumachen. Gleichzeitig habe ich gemerkt, dass es längst etablierte Open-Source-Projekte gibt, die sich mit solchen Fragen beschäftigen.

Bei meiner Beschäftigung mit den Arbeiten von Alan Hodgkin und Andrew Huxley wurde mir außerdem klar, wie weit die mathematische Beschreibung einzelner Nervenzellen schon zurückreicht – und wie aufwendig es werden kann, viele davon biologisch detailliert zu simulieren. Ich hatte mich ziemlich auf die Vorstellung verlassen, dass aus genügend Details schon irgendwann Intelligenz entstehen würde. Einen klaren Plan dafür hatte ich aber nicht. Deshalb habe ich diesen Ansatz irgendwann aufgegeben.

## Zweiter Versuch: eine Gesellschaft aus Agenten

Ungefähr ein halbes Jahr später kam die nächste Idee. Das war kurz nach dem großen Hype um DeepSeek, als ich selbst gerade anfing, mich intensiver mit KI-Agenten zu beschäftigen.

Ich wollte eine kleine Gesellschaft aus Agenten bauen. Sie sollten eine gemeinsame Umgebung haben, miteinander interagieren, Wissen ablegen und gegenseitig darauf zugreifen können. Meine Vorstellung war: Wenn mehrere Agenten eine Antwort prüfen, diskutieren und überarbeiten, könnte dabei vielleicht etwas Besseres herauskommen als bei einem einzelnen Modell.

Halluzinationen waren für mich dabei ein großes Thema. Ich hoffte, dass sich die Agenten gegenseitig auf Fehler aufmerksam machen könnten. Im Grunde war das mein Versuch, durch Zusammenarbeit und vielleicht auch Emergenz zuverlässigere Ergebnisse zu bekommen.

In der Praxis war die Koordination allerdings ziemlich quälend. Es war viel Aufwand nötig, bis überhaupt etwas Brauchbares herauskam. Außerdem bedeutet die Zustimmung mehrerer Agenten noch lange nicht, dass eine Antwort stimmt. Nach ein paar Tagen oder vielleicht auch Wochen habe ich auch dieses Projekt erst einmal liegen gelassen.

Ganz aufgehört habe ich trotzdem nicht.

## Weltmodelle, JEPA und Active Inference

Ich habe weiter herumexperimentiert und bin irgendwann bei Yann LeCun und JEPA gelandet. Ehrlich gesagt habe ich damals weder seine Arbeit noch die genaue Funktionsweise wirklich verstanden. Ein Interview hatte mich neugierig gemacht, aber neugierig sein und etwas verstehen sind eben zwei verschiedene Dinge.

Danach bin ich auf Karl Fristons Free-Energy-Prinzip und Active Inference gestoßen. Besonders spannend fand ich die Frage: Wie nutzt ein Agent sein Weltmodell, um wahrzunehmen, zu lernen und zu handeln?

Daraus entstanden wieder einige kleine Prototypen. Zum Beispiel die Idee einer Haus-KI, die Gewohnheiten ihrer Nutzer lernt, Erwartungen entwickelt und mit Unsicherheit umgeht. Oder Experimente mit Schach, bei denen ich ausprobieren wollte, welche Rolle Unsicherheit bei Entscheidungen spielen könnte. Ich habe auch darüber nachgedacht, ob sich solche Ansätze auf Aktienkurse anwenden lassen.

Das hat Spaß gemacht. Aber es waren vor allem Experimente und Spielereien, keine ausgereiften Systeme oder Belege dafür, dass meine Ideen funktionieren.

## Kontextwechsel und die „Scheiben“

Irgendwann habe ich mich dann gefragt: Warum schaue ich nicht genauer darauf, was in meinem eigenen Alltag passiert? Wie denke ich? Wie erkenne ich, was gerade wichtig ist? Und wie schaffe ich es, mich auf eine neue Situation einzustellen?

Dabei bin ich immer wieder beim Thema **Kontextwechsel** gelandet. Bei einem Spaziergang hatte ich mehrere Sachen gleichzeitig im Kopf. Ich dachte an Luhmanns Systemtheorie und die Unterschiede zwischen Systemen, an einen Filmnamen, dann an Hamburger, CDs und Scheiben. Wie genau ich dabei von einem Gedanken zum nächsten gekommen bin, kann ich selbst nicht mehr sagen. Irgendwann war da einfach das Wort Kontext. Ich habe mir das bildlich wie Scheiben im Gehirn vorgestellt. Jede Scheibe steht dabei für ein Modell oder bestimmte Erfahrungen. In einer Situation können mehrere dieser Scheiben zusammenpassen und sich überlagern, weil sie ähnliche Aspekte enthalten.

Zwischen den Scheiben ist etwas Abstand, aber sie sind durch eine Art Netz miteinander verbunden, ungefähr wie durch Spinnweben. Je näher sich die Themen sind, desto näher liegen in meiner Vorstellung auch die Scheiben beieinander. Sie können sich also nicht nur überlagern, sondern auch nebeneinanderliegen und miteinander verknüpft sein.

In meinem Kopf war das eine ganze 3D-Welt, irgendwie wie ein Rechenzentrum, haha. So habe ich mir vorgestellt, dass Erfahrungen zusammenhängen und je nach Situation unterschiedliche Verbindungen wichtig werden. Das ist erst einmal nur mein gedankliches Bild davon, keine Behauptung darüber, wie das Gehirn tatsächlich aufgebaut ist.

Daraufhin habe ich mich gefragt, wie unser Gehirn und Kontext vielleicht zusammenhängen. Wie erkennen wir, in welcher Situation wir gerade sind, und wie wechseln wir gedanklich in eine andere? Dabei fiel mir auf, dass mir selbst dieser Wechsel nicht immer leichtfällt. Manchmal möchte ich mit einer Handlung anfangen, bin aber im Kopf noch ganz woanders. So bin ich nach und nach beim Thema Kontextwechsel gelandet.

Ich habe selbst ADHS. Wenn ich lernen möchte, dauert es manchmal ziemlich lange, bis ich wirklich beim Lernen angekommen bin. Ich sitze vielleicht schon vor meinen Unterlagen, aber meine Gedanken sind noch überall. Für mich fühlt sich das manchmal so an, als würde ich den passenden inneren Zustand für die Situation nicht richtig finden oder nicht halten können.

Das ist meine persönliche Beschreibung dieser Erfahrung, keine vollständige Erklärung von ADHS. Aber daraus ist bei mir eine Frage entstanden: Wie wählt ein System eigentlich aus, welcher Kontext gerade relevant ist, und wie bleibt es darin, ohne unflexibel zu werden?

Beim Lesen über Traumafolgen kam mir eine verwandte Frage aus einer ganz anderen Richtung. Ein Geräusch kann in einer sicheren Alltagssituation vorkommen und trotzdem Erinnerungen oder Alarmreaktionen auslösen, die mit einer früheren Gefahr verbunden sind. Mich hat daran beschäftigt, wie frühere Erfahrungen die Interpretation einer gegenwärtigen Situation beeinflussen können.

Ich möchte ADHS und eine posttraumatische Belastungsstörung damit nicht gleichsetzen oder auf ein gemeinsames Problem reduzieren. Mich hat vielmehr die allgemeinere Frage interessiert: Wie unterscheiden wir zwischen dem, was gerade passiert, und dem, was wir aufgrund früherer Erfahrungen erwarten oder befürchten?

## Gemeinsame Strukturen

Mein zweiter Gedanke war, dass viele Situationen in unserem Alltag gemeinsame Strukturen haben.

Beim Arzt zu warten und auf die Bahn zu warten sind unterschiedliche Situationen. Trotzdem muss ich in beiden Fällen mit Wartezeit umgehen, Geduld haben und mich vielleicht irgendwie beschäftigen. Gleichzeitig gelten unterschiedliche Regeln: Im Wartezimmer verhalte ich mich anders als auf einem Bahnsteig.

Ich stelle mir deshalb vor, dass ein künstlicher Agent nicht für jede Situation alles von vorne lernen müsste. Vielleicht könnte er gemeinsame Bestandteile wiederverwenden und sie je nach Kontext anders zusammensetzen. Eine Art allgemeines Verständnis von „Warten“, ergänzt durch das Wissen darüber, worauf, wo und unter welchen Bedingungen gewartet wird.

Ob unser Gehirn das tatsächlich genau so organisiert, weiß ich nicht. Für mich ist das zunächst eine Vorstellung, mit der ich beim Bauen eines Agenten arbeiten möchte.

Auch soziale Regeln passen für mich in diese Überlegung. Als kleines Kind wissen wir noch nicht automatisch, welches Verhalten in welcher Umgebung erwartet wird. Vieles lernen wir durch Beobachtung, durch unsere Eltern und durch eigene Erfahrungen. Mich interessiert, wie ein Agent solche Gemeinsamkeiten und Unterschiede lernen könnte, ohne dass ich ihm jede einzelne Regel vorgeben muss.

Dann gibt es noch die Idee von **Ankern für einen Kontextwechsel**. Vielleicht können bestimmte Signale oder Handlungen dabei helfen, den passenden Kontext zu aktivieren. Beim Autofahren könnte das beispielsweise das Einsteigen, das Anfassen des Lenkrads oder das Treten der Kupplung sein. Welche Hinweise reichen aus, damit ein System erkennt: Jetzt ist eine andere Situation, jetzt brauche ich andere Erwartungen und anderes Verhalten?

## Der aktuelle Ansatz

Aus solchen Fragen entsteht mein aktueller Ansatz: ein Agent, der Erfahrungen nicht nur sammelt, sondern Gemeinsamkeiten zwischen Situationen erkennt, Wissen wiederverwendet und lernt, welcher Kontext gerade passt.

Ich behaupte damit nicht, das Gehirn verstanden oder eine Lösung für allgemeine künstliche Intelligenz gefunden zu haben. Ich möchte meine Gedanken ausprobieren und herausfinden, welche davon etwas taugen. Vielleicht funktionieren manche. Vielleicht merke ich bei anderen wieder, dass ich komplett falschliege. Das gehört für mich inzwischen dazu.

Genau deshalb möchte ich das Projekt offen machen. Ich würde mich freuen, wenn andere hineinschauen, Fragen stellen, Fehler entdecken oder eigene Ideen einbringen. Ich lerne noch und kann Unterstützung gut gebrauchen – auch dann, wenn sie darin besteht, mir zu erklären, warum etwas so nicht funktionieren kann.

Sorry für den langen Text. Ich bin neu in diesem GitHub-Game, aber ich meine es ernst. Ich möchte diesmal weiterkommen als bis zum nächsten halbfertigen Experiment.

Viel Spaß mit meinen Agenten. Vielleicht habt ihr ja Lust, ein Stück mitzubauen.
