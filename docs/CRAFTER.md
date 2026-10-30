# Crafter: der allgemeine Agent im kleinen Minecraft (ab 0.18)

Crafter (Hafner 2021) ist ein 2D-Minecraft mit 22 Erfolgen: Holz sammeln, Werkbank bauen,
Werkzeuge herstellen, Stein, Kohle, Eisen und Diamanten abbauen, essen, trinken, schlafen,
Zombies abwehren. Es ist ein Prüfstein, kein Ziel: Der Agent soll allgemein bleiben.

## Trennung

- `src/hekmatki/general/` ist der Agent. Er kennt keine Welt und importiert nie etwas aus
  `hekmatki.adapters` oder ein Spielpaket; ein Test prüft das (`tests/test_drives.py`).
- `src/hekmatki/adapters/crafter.py` übersetzt Crafter in die allgemeine Schnittstelle: Zahlen
  und Tasten, gemischt mit einem festen Startwert (`Wiring`).
- `src/hekmatki/experiments/crafter_run.py` misst, `crafter_replay.py` baut die Seite
  [crafter.html](crafter.html). Nur diese beiden kennen die Namen der Erfolge.

## Was der Agent bekommt

| Teil | Zahlen | Bemerkung |
|---|---:|---|
| Sicht | 63 | 9 × 7 Felder um die Figur, je Feld die Nummer dessen, was dort ist (Crafters „semantische“ Karte) |
| Vorne | 1 | Nummer des Felds, auf das die Figur schaut; darauf wirken Abbauen, Trinken, Angreifen, Bauen |
| Inventar | 16 | darunter Gesundheit, Essen, Trinken, Wachheit |
| Blickrichtung | 2 | |
| Schlaf | 1 | |
| Position | 2 | |
| Tasten | 17 | ohne Namen, gemischt |
| Ziel erreicht | ja/nein | ein Erfolg, den es in dieser Runde noch nicht gab |

Die Wahrnehmung ist geschenkt: Aus Pixeln müsste der Agent erst lernen, was ein Feld ist.

## Messen

```bash
pip install -e ".[crafter]"
PYTHONPATH=src python -m hekmatki.experiments.crafter_run messung.json 8   # 8 Karten-Startwerte
PYTHONPATH=src python -m hekmatki.experiments.crafter_replay docs/crafter.html messung.json
```

Es spielen Zufall, Tabelle, Stand 0.17 und der neueste Stand (seit 0.19 „Stand 0.19“, mit Raum aus eigener Bewegung). Die Zeilen von 0.18 in `docs/crafter_messung.json` stammen aus der gespeicherten Messung von 0.18.

Jeder Agent spielt 30 Runden hintereinander und behält sein Wissen; jede Runde ist eine neue
Karte. Gezählt werden die Runden 11 bis 30. Wertung wie im Paper: geometrisches Mittel der
Erfolgsquoten, `exp(mittel(ln(1 + 100·Quote))) − 1`.

Zum Vergleich die Werte aus dem Crafter-Paper nach einer Million Schritten (nicht selbst
nachgemessen): Zufall 1,6 %, Plan2Explore 2,1 %, RND 2,0 %, PPO 4,6 %, DreamerV2 10,0 %,
Menschen 50,5 %. Unser Agent spielt nur etwa 5000 Schritte.

## Minecraft und andere Spiele

Für MineRL oder MineDojo gilt dasselbe Muster: ein eigener Adapter in `hekmatki.adapters`,
der Agent bleibt unverändert. Eine Prüfung vom 29. Oktober 2026 kam zu dem Schluss, dass
zuerst Crafter sinnvoll ist (kleiner, schneller, ohne Java).
