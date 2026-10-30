"""Prüft ein installiertes Paket: Liegen alle Dateien bei, die keine Python-Module sind?

Die Tests laufen gegen den Quellbaum und merken nicht, wenn im gebauten Paket etwas fehlt
(zum Beispiel die HTML-Vorlagen der Wiedergabeseiten). Deshalb baut die CI das Paket,
installiert es in eine leere Umgebung und ruft dieses Skript außerhalb des Repos auf:

    python tests/check_package.py src/hekmatki
"""

import argparse
import sys
from importlib.resources import files
from pathlib import Path

import hekmatki

SKIPPED_PARTS = frozenset({"__pycache__", "node_modules"})


def data_files(source: Path) -> list[Path]:
    """Alle Dateien im Quellbaum, die keine Python-Module sind, relativ zu `source`."""
    return sorted(
        path.relative_to(source)
        for path in source.rglob("*")
        if path.is_file()
        and path.suffix not in {".py", ".pyc"}
        and not SKIPPED_PARTS.intersection(path.parts)
    )


def missing(source: Path) -> list[Path]:
    """Die Dateien aus `source`, die dem installierten Paket fehlen."""
    installed = files(hekmatki)
    return [path for path in data_files(source) if not installed.joinpath(*path.parts).is_file()]


def main() -> None:
    """Bricht mit einer Fehlermeldung ab, wenn eine Datei fehlt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Quellordner des Pakets, z. B. src/hekmatki")
    source = parser.parse_args().source.resolve()
    location = Path(hekmatki.__file__).resolve().parent
    if location == source:
        sys.exit(f"Geprüft wird der Quellbaum ({location}), nicht das installierte Paket.")
    if not data_files(source):
        sys.exit(f"Im Quellordner {source} liegen keine Dateien zum Prüfen.")
    if lost := missing(source):
        sys.exit("Im installierten Paket fehlen:\n" + "\n".join(f"  {path}" for path in lost))
    print(f"Alle {len(data_files(source))} Dateien liegen im installierten Paket ({location}).")


if __name__ == "__main__":
    main()
