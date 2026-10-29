"""Die 2D-Welt (ab 0.12): Labyrinthe als Farbraster, wie bei ARC-AGI-3.

- `world`: das Spiel selbst (Labyrinth, Farben, Tasten, Neustart-Taste, fremde Mechanik)
- `mazes`: Labyrinthe und Rätsel erzeugen, kürzeste Lösung
- `perception`: was der Agent im Raster erkennt (Farben, Felder, wer sich bewegt hat)
- `effects`: was das Betreten einer Farbe bewirkt
- `planner`: Wege im Raster planen, mit dem, was der Agent über Farben weiß
- `agent`: der Objekt-Agent, der Tasten und Farbwirkungen selbst lernt
- `roles`: Rollen-Schema, das Farbwirkungen auf neue Farben überträgt
- `model`: das Weltmodell aus Regeln (ab 0.13)
- `induction`: Regeln aus Beobachtungen ableiten
- `simulation`, `search`: im Modell vorausdenken und Pläne suchen
- `model_agent`: der Modell-Agent
- `role_model`: das Weltmodell über Rollen statt Farben (ab 0.14)
- `trust`: Vorwissen erst nutzen, wenn es sich bewährt hat (ab 0.15)
- `baseline`: der alte Entdecker, für den jedes Raster ein eigener Zustand ist
- `play`: ein Spiel durchspielen und auf Wunsch aufzeichnen
"""
