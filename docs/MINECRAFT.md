# Minecraft

Der allgemeine Agent spielt echtes Minecraft, ohne etwas über Minecraft zu wissen. Er sieht
dieselbe Art von Welt wie überall: gemischte Zahlen und Tasten ohne Namen.

## Aufbau

```
Agent (hekmatki.general)          weiß nichts von Minecraft
   │ Zahlen, Tasten, „Ziel erreicht“
Adapter (adapters/minecraft.py)   mischt Zahlen und Tasten mit einer Wiring je Startwert
   │ JSON-Zeilen über stdin/stdout
Brücke (minecraft_bridge/bridge.js, Node + Mineflayer)   einziger Code, der Minecraft kennt
   │ Minecraft-Protokoll
Minecraft-Server (offiziell, 1.20.4)   ohne Grafikkarte, ohne Bildschirm
```

`hekmatki.general` importiert nie etwas aus `hekmatki.adapters` (ein Test prüft das).

## Was der Agent sieht und tut

- 130 Zahlen: Blöcke in 5 × 5 Feldern auf drei Höhen, Wesen in 5 × 5 Feldern, Block und Wesen
  im Fadenkreuz, Schnellleiste (Ding, Anzahl), gewähltes Fach, Leben, Hunger, Blickrichtung,
  Position, Tageszeit. Die Nummern sind Minecrafts eigene, ohne Namen.
- 23 Tasten: nichts, vor, zurück, links, rechts, springen, links/rechts drehen, hoch/runter
  schauen, angreifen (abbauen oder schlagen), benutzen (setzen, essen, öffnen), nächstes/voriges
  Fach und neun Rezepte (Bretter, Stöcke, Werkbank, Holz- und Steinwerkzeuge, Ofen, Fackel).
- „Ziel erreicht“: ein neuer Fortschritt (Advancement), den das Spiel anzeigt. Rezepte und
  versteckte Einträge zählen nicht.
- Jede Runde: leeres Inventar, volles Leben, Tag, neuer Ort (`/spreadplayers`). Sie endet mit
  dem Tod oder nach 2000 Schritten.

Geschenkt ist, wie bei Crafter, die Wahrnehmung: Der Agent bekommt Blocknummern statt Pixel.
Auch die Rezept-Tasten sind ein Geschenk (in Minecraft legt man Dinge im Menü ins Raster).

## Messung

In GitHub Actions: Workflow „Minecraft-Messung“. Jeder Job lädt den offiziellen Server frisch
von Mojang, nimmt die EULA an (Entscheidung von Tenshira, 2026-10-30) und lässt einen Agenten
auf einer Karte spielen. Lokal:

```bash
pip install -e .
(cd src/hekmatki/adapters/minecraft_bridge && npm ci --omit=dev)
python -m hekmatki.adapters.minecraft_server minecraft-server 0 --eula-angenommen
# server.jar 1.20.4 von Mojang nach minecraft-server/ laden, dann:
(cd minecraft-server && java -jar server.jar nogui) &
python -m hekmatki.experiments.minecraft_run play "Stand 0.20" 0 teil.json --episodes 6
```

Zum Ausprobieren ohne Mojangs Server gibt es `minecraft_bridge/testserver.js` (flying-squid,
frei, `npm ci` mit Entwicklungspaketen). Er ist stark vereinfacht und taugt nicht zum Messen.

## Live zuschauen (auf dem eigenen Rechner)

Server und Agent laufen bei dir, du schaust mit deiner eigenen **Minecraft Java Edition** zu
(nicht Bedrock). Einmal installieren:

- Python 3.12 oder neuer: https://www.python.org/downloads/
- Java 21 (zum Beispiel Temurin): https://adoptium.net/
- Node 22: https://nodejs.org/
- Das Repo herunterladen und im Ordner `pip install -e .` ausführen.

Starten (Windows: Eingabeaufforderung, Mac: Terminal, jeweils im Repo-Ordner):

```bash
python -m hekmatki.experiments.minecraft_live --eula-angenommen --mein-name DEIN_MINECRAFT_NAME
```

Auf dem Mac geht die Einrichtung mit Homebrew: `brew install python@3.12 node git` und
`brew install --cask temurin@21`, danach im Repo-Ordner `python3.12 -m venv .venv`,
`source .venv/bin/activate` und `pip install -e .`.

Der Server ist Version **1.20.4**: Im Minecraft-Launcher unter „Installationen“ eine
Installation mit dieser Version anlegen, sonst lässt der Server dich nicht hinein.

Beim ersten Mal lädt das Skript den Server von Mojang und installiert die Brücke. Sobald
„Server bereit“ erscheint: Minecraft starten → Mehrspieler → Direkt verbinden → `localhost`.
Dann im Chat `/gamemode spectator` und `/spectate hekmat`, um ihm über die Schulter zu schauen.
Im normalen Modus kannst du auch neben ihm herlaufen; solche Runden zählen nicht als Messung.
Beenden mit Strg+C. Im Fenster steht nach jeder Runde, welche Fortschritte er geschafft hat.

## Wiedergabe der Messungen

Jeder Lauf in GitHub zeichnet die letzte Runde jedes Agenten auf. Der Sammel-Job baut daraus
`minecraft.html` (Landschaft von oben, Tiere und Monster, Leben, Hunger, Schnellleiste, Taste,
Fortschritte) und legt alles auf dem Branch `minecraft-messungen` ab, Ordner `lauf-<Nummer>`.

## Lizenzen

Mineflayer und flying-squid: MIT. Der offizielle Server gehört Mojang und wird nie mit dem
Repo verteilt; wer ihn startet, nimmt die Minecraft-EULA an (https://aka.ms/MinecraftEULA).
