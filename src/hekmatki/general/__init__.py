"""Der allgemeine Agent (ab 0.16, erweitert in 0.17): eine Routine für ganz verschiedene
Umgebungen.

- `env`: die Schnittstelle (nur Zahlen und Tasten), die Mischung jeder Welt, die Hülle
  `Padded` für gleiche Schnittstelle
- `worlds`: Raum mit beliebig vielen Dimensionen (auch aus Eis), Suche in einem sortierten
  Datenbestand, Drehscheiben, Steine tauschen
- `programs`: Regeln als Programme aus allgemeinen Bausteinen, ab 0.17 mit Übernehmen, Ring
  und Schleife
- `library`: die Hekmat-Bibliothek: Regel-Muster mit Wiederverwendungs-Zähler
- `synthesis`: Regeln suchen, kürzeste Beschreibung zuerst
- `knowledge`: Regeln, Ziel, Karte und Überraschung einer Umgebung
- `form`: die Form der Umgebung aus den Regeln ablesen, als Produkt von Achsen
- `planner`: planen je nach Form, ohne Form im gelernten Modell
- `detector`: eine neue Umgebung an unerwarteter Überraschung erkennen, ab 0.17 auch per
  Bayes-Faktor
- `agent`: der allgemeine Agent
- `run`: Runden spielen und messen
"""
