"""Der allgemeine Agent (ab 0.16): eine Routine für ganz verschiedene Umgebungen.

- `env`: die Schnittstelle (nur Zahlen und Tasten) und die Mischung jeder Welt
- `worlds`: Raum mit beliebig vielen Dimensionen, Suche in einem sortierten Datenbestand
- `programs`: Regeln als Programme aus fünf allgemeinen Bausteinen
- `library`: die Hekmat-Bibliothek: Regel-Muster mit Wiederverwendungs-Zähler
- `synthesis`: Regeln suchen, kürzeste Beschreibung zuerst
- `knowledge`: Regeln, Ziel, Karte und Überraschung einer Umgebung
- `form`: die Form der Umgebung aus den Regeln ablesen
- `planner`: planen je nach Form
- `detector`: eine neue Umgebung an unerwarteter Überraschung erkennen
- `agent`: der allgemeine Agent
- `run`: Runden spielen und messen
"""
