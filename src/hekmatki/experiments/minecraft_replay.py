"""Seite „Minecraft“ (nach 0.20): eine Runde des Agenten in Minecraft zum Anschauen.

Die Messung (`minecraft_run play ... --wiedergabe wiedergabe.json`) zeichnet die letzte Runde
Schritt für Schritt auf: die Landschaft um die Figur von oben, Tiere und Monster, Leben,
Hunger, Schnellleiste, die gedrückte Taste und neue Fortschritte. Diese Seite spielt das ab und
zeigt, wenn vorhanden, die Tabelle der Messung daneben. Die Namen kennt nur die Seite; der
Agent sieht nur gemischte Zahlen.

Aufruf:
`python -m hekmatki.experiments.minecraft_replay seite.html wiedergabe-*.json --bericht bericht.txt`
"""

import argparse
import json
from pathlib import Path
from typing import Final

TEMPLATE: Final = Path(__file__).with_name("minecraft_replay_template.html")
PLACEHOLDER: Final = "/*MINECRAFT_DATA*/null"


def build_page(replays: list[Path], report: str) -> str:
    """Die Seite mit den Wiedergaben und dem Bericht der Messung."""
    data = {
        "replays": [json.loads(path.read_text(encoding="utf-8")) for path in replays],
        "report": report,
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"Platzhalter {PLACEHOLDER} fehlt in {TEMPLATE.name}.")
    # "</" würde den <script>-Block beenden.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, payload)


def main() -> None:
    """Befehlszeile: Seite aus Wiedergaben und optionalem Bericht bauen."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("replays", type=Path, nargs="+")
    parser.add_argument("--bericht", type=Path, default=None, dest="report")
    arguments = parser.parse_args()
    report = arguments.report.read_text(encoding="utf-8") if arguments.report else ""
    arguments.out.write_text(build_page(arguments.replays, report), encoding="utf-8")


if __name__ == "__main__":
    main()
