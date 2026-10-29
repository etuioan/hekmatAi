# Mitmachen

Schön, dass du hier bist! HekmatKI ist ein offenes Experiment. Warum es das Projekt gibt,
steht in [MOTIVATION.md](MOTIVATION.md). Jede Art von Beitrag hilft, auch eine Frage oder
die Erklärung, warum eine Idee so nicht funktionieren kann.

## Wie du beitragen kannst

- **Fragen stellen und Fehler melden:** Öffne ein Issue. Beschreibe, was du erwartet hast,
  was passiert ist und wie man es nachstellen kann.
- **Kritik an Ideen oder Hypothesen:** Ausdrücklich erwünscht. Wenn du ein Paper kennst, das
  einer Hypothese (H1, H2, …) widerspricht, verlinke es im Issue.
- **Code beitragen:** Fork, eigener Branch, Pull Request. Kleine, gut erklärte Änderungen
  lassen sich am leichtesten prüfen.

Issues und Pull Requests dürfen auf Deutsch oder Englisch sein.

## Entwicklungsumgebung

Benötigt wird Python 3.12 oder neuer. Der Prototyp selbst nutzt nur die Standardbibliothek.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Vor jedem Pull Request sollten alle Prüfungen grün sein (sie laufen auch automatisch auf
GitHub):

```bash
ruff check .
ruff format --check .
mypy
pytest
```

## Regeln für den Code

Sauberer Code ist diesem Projekt sehr wichtig.

- **Lesbar und einfach (KISS):** Lieber zwei klare Funktionen als eine schlaue.
- **Modular:** Jedes Modul und jede Funktion hat eine Aufgabe (Single Responsibility).
  Keine Wiederholungen (DRY).
- **Typannotationen überall:** `mypy` läuft im strikten Modus.
- **Explizit statt implizit:** Fehler werden nie still geschluckt.
- **Tests:** Neues Verhalten bekommt einen Test in `tests/`.

## Forschung und Code gehören zusammen

Jedes Modul geht auf Paper, ein Prinzip (P1–P8) oder eine Hypothese (H1–H20) zurück.
Die Zuordnung steht in [docs/PAPER_ZUORDNUNG.md](docs/PAPER_ZUORDNUNG.md).

- Wenn du ein Modul hinzufügst oder stark änderst, ergänze dort die Zeile.
- Ideen ohne Paper sind willkommen, bekommen aber den Vermerk **ohne Grundlage**.
- Ergebnisse werden ehrlich berichtet, auch wenn eine Hypothese widerlegt wird.
  Siehe den Abschnitt „Grenzen“ im [README](README.md).

## Umgangston

Freundlich, geduldig und konkret. Hier lernen alle noch, auch wer das Projekt gestartet hat.
