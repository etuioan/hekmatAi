"""Adapter: fremde Welten an die allgemeine Schnittstelle anschließen (ab 0.18).

Ein Adapter ist das einzige Stück Code, das eine fremde Welt kennt. Er übersetzt sie in das,
was der allgemeine Agent sieht (`hekmatki.general.env`): eine Reihe ganzer Zahlen und
Tasten ohne Namen, gemischt mit einer zufälligen `Wiring`. Kein Name, keine Belohnung und
kein Wissen über die Welt gehen an den Agenten. Umgekehrt importiert `hekmatki.general` nie
etwas aus `hekmatki.adapters` (ein Test prüft das).

- `crafter`: Crafter (Hafner 2021), ein kleines 2D-Minecraft für die Forschung. Braucht das
  Zusatzpaket: `pip install -e ".[crafter]"`.
- `minecraft`: echtes Minecraft über eine Node-Brücke (Mineflayer) zu einem Server. Braucht
  Node und `npm ci` in `minecraft_bridge/`, dazu einen Server (siehe docs/MINECRAFT.md).
"""
