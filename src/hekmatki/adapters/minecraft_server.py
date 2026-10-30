"""Einen offiziellen Minecraft-Server für Messungen vorbereiten (nach 0.20).

Schreibt in einen Ordner, was der Server beim Start braucht: `server.properties` (Startwert
der Welt, kein Online-Login, kein Spawnschutz), `ops.json` (die Brücke darf Befehle wie
`/spreadplayers` für den Rundenbeginn nutzen) und `eula.txt`.

Den Server selbst lädt man von Mojang (siehe docs/MINECRAFT.md). Wer ihn startet, nimmt damit
Mojangs Lizenz (EULA) an: https://aka.ms/MinecraftEULA. Deshalb schreibt dieses Modul
`eula=true` nur, wenn man es ausdrücklich mit `--eula-angenommen` aufruft.

Aufruf: `python -m hekmatki.adapters.minecraft_server ORDNER STARTWERT --eula-angenommen`
"""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

PROPERTIES = {
    "online-mode": "false",
    "spawn-protection": "0",
    "difficulty": "easy",
    "gamemode": "survival",
    "view-distance": "4",
    "simulation-distance": "4",
    "max-players": "4",
    "motd": "HekmatKI",
    "enable-command-block": "false",
    "spawn-monsters": "true",
}


def offline_uuid(username: str) -> uuid.UUID:
    """Die UUID, die ein Server ohne Online-Login einem Namen gibt (Java `nameUUIDFromBytes`)."""
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{username}".encode()).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # Version 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # Variante RFC 4122
    return uuid.UUID(bytes=bytes(digest))


def prepare(folder: Path, seed: int, username: str = "hekmat", *, eula_accepted: bool) -> None:
    """Schreibt die Dateien für einen Server mit Weltstartwert `seed`."""
    folder.mkdir(parents=True, exist_ok=True)
    properties = {**PROPERTIES, "level-seed": str(seed)}
    lines = [f"{key}={value}" for key, value in properties.items()]
    (folder / "server.properties").write_text("\n".join(lines) + "\n", encoding="utf-8")
    op = {"uuid": str(offline_uuid(username)), "name": username, "level": 4}
    (folder / "ops.json").write_text(json.dumps([op], indent=2), encoding="utf-8")
    (folder / "eula.txt").write_text(f"eula={str(eula_accepted).lower()}\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("seed", type=int)
    parser.add_argument("--username", default="hekmat")
    parser.add_argument("--eula-angenommen", dest="eula", action="store_true")
    arguments = parser.parse_args()
    prepare(arguments.folder, arguments.seed, arguments.username, eula_accepted=arguments.eula)
