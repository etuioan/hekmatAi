"""Minecraft live zuschauen (nach 0.20): Server und Agent auf dem eigenen Rechner starten.

Ein Befehl lädt beim ersten Mal den offiziellen Minecraft-Server von Mojang, startet ihn und
lässt den Agenten Runde um Runde spielen. Man verbindet sich mit der eigenen Minecraft Java
Edition über „Mehrspieler“ → `localhost` und sieht den Agenten als Spieler „hekmat“. Mit
`/gamemode spectator` und `/spectate hekmat` schaut man ihm über die Schulter.

Der Server läuft ohne Online-Anmeldung (der Agent hat kein Konto) und ist nur auf diesem
Rechner und im eigenen Heimnetz erreichbar. Wer ihn startet, nimmt Mojangs EULA an
(https://aka.ms/MinecraftEULA), deshalb verlangt das Skript `--eula-angenommen`.

Braucht Python 3.12+, Java 21+ und Node 18+. Aufruf aus dem Repo-Ordner:
`pip install -e .`
`python -m hekmatki.experiments.minecraft_live --eula-angenommen --mein-name DEIN_NAME`
Beenden mit Strg+C.
"""

import argparse
import json
import random
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Final

from hekmatki.adapters.minecraft import BRIDGE, BridgeProcess, MinecraftWorld
from hekmatki.adapters.minecraft_server import offline_uuid, prepare
from hekmatki.experiments.minecraft_run import MAKERS, Agent, play_round

VERSION: Final = "1.20.4"
MANIFEST: Final = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
READY_TIMEOUT: Final = 300


def download_server(folder: Path, version: str = VERSION) -> None:
    """Lädt `server.jar` von Mojang, falls noch nicht da."""
    jar = folder / "server.jar"
    if jar.exists():
        return
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Lade den offiziellen Minecraft-Server {version} von Mojang …")
    versions = _json(MANIFEST)["versions"]
    url = next(v["url"] for v in versions if v["id"] == version)
    urllib.request.urlretrieve(_json(url)["downloads"]["server"]["url"], jar)


def add_operator(folder: Path, name: str) -> None:
    """Gibt dem Menschen Befehle wie `/spectate`, neben dem Agenten."""
    ops_file = folder / "ops.json"
    ops = json.loads(ops_file.read_text(encoding="utf-8"))
    ops.append({"uuid": str(offline_uuid(name)), "name": name, "level": 4})
    ops_file.write_text(json.dumps(ops, indent=2), encoding="utf-8")


def start_server(folder: Path) -> subprocess.Popen[str]:
    """Startet den Server (Ausgabe nach `server.log`) und wartet, bis er bereit ist."""
    log = folder / "server.log"
    with log.open("w", encoding="utf-8") as output:
        server = subprocess.Popen(
            ["java", "-Xmx2G", "-jar", "server.jar", "nogui"],
            cwd=folder,
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
        )
    deadline = time.monotonic() + READY_TIMEOUT
    while time.monotonic() < deadline and server.poll() is None:
        if "Done (" in log.read_text(encoding="utf-8", errors="replace"):
            print("Server bereit. In Minecraft: Mehrspieler → Direkt verbinden → localhost")
            return server
        time.sleep(1)
    server.kill()
    raise RuntimeError(f"Der Server ist nicht hochgefahren; siehe {log}.")


def install_bridge() -> None:
    """Installiert Mineflayer für die Brücke, falls noch nicht da."""
    folder = BRIDGE.parent
    if not (folder / "node_modules").exists():
        print("Installiere die Brücke (npm) …")
        npm = shutil.which("npm") or "npm"
        subprocess.run([npm, "ci", "--omit=dev"], cwd=folder, check=True)


def play_forever(agent: Agent, seed: int, rounds: int | None) -> None:
    """Der Agent spielt Runde um Runde und lernt weiter; jede Runde an einem neuen Ort."""
    connection = BridgeProcess()
    try:
        world = MinecraftWorld(seed, connection)
        learner = MAKERS[agent](world.actions)
        rng = random.Random(seed)
        played = 0
        while rounds is None or played < rounds:
            result = play_round(learner, world, rng)
            played += 1
            found = ", ".join(sorted(result.names)) or "keine"
            print(f"Runde {played}: {result.steps} Schritte, Fortschritte: {found}")
    finally:
        connection.close()


def _json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url) as response:
        data: dict[str, Any] = json.load(response)
    return data


def main() -> None:
    """Befehlszeile."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--eula-angenommen", dest="eula", action="store_true")
    parser.add_argument("--mein-name", dest="name", default=None)
    parser.add_argument("--agent", choices=list(MAKERS), default="Stand 0.21")
    parser.add_argument("--startwert", dest="seed", type=int, default=0)
    parser.add_argument("--runden", dest="rounds", type=int, default=None)
    parser.add_argument("--ordner", dest="folder", type=Path, default=Path("minecraft-server"))
    arguments = parser.parse_args()
    if not arguments.eula:
        sys.exit(
            "Bitte mit --eula-angenommen starten (Mojangs EULA: https://aka.ms/MinecraftEULA)."
        )
    for tool in ("java", "node"):
        if shutil.which(tool) is None:
            sys.exit(f"{tool} fehlt. Siehe docs/MINECRAFT.md, Abschnitt „Live zuschauen“.")

    download_server(arguments.folder)
    prepare(arguments.folder, arguments.seed, eula_accepted=True)
    if arguments.name:
        add_operator(arguments.folder, arguments.name)
    install_bridge()
    server = start_server(arguments.folder)
    try:
        play_forever(arguments.agent, arguments.seed, arguments.rounds)
    except KeyboardInterrupt:
        print("\nBeende …")
    finally:
        if server.poll() is None:
            assert server.stdin is not None
            server.stdin.write("stop\n")
            server.stdin.flush()
            server.wait(timeout=60)


if __name__ == "__main__":
    main()
