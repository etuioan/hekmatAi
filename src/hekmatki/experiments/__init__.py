"""Die Experimente des Prototyps, ein Modul pro Fragestellung.

- `schema_learning`: H11 und Härtetest (lernt der Agent schneller mit Schema?)
- `forgetting`: H12 (vergisst er weniger mit Kontextwechsel?)
- `sleep`: Kontextwechsel + Scheiben, Wach-Schlaf, mehrere Schemata
- `traffic_light`: Ampelspiel mit Schnittmenge
- `recognition`: Wie gut hält der Agent Situationen auseinander?
- `meta_schema`: Dritte Ebene und H13 (sofort oder verzögert verschmelzen?)
- `discovery`: Spielefamilie, in der der Agent Regeln selbst entdeckt und überträgt
- `exploration`: Bleibende Neugier und Vertrauen ins Schema
- `rule_transfer`: Regel-Schemata, die auch auf andere Ganglängen passen
- `grid_transfer`: 2D-Welt mit Farbrastern: Bilder, Objekte und Rollen-Schema im Vergleich
- `grid_mechanics`: Kisten, Druckplatten und Tore: Weltmodell mit und ohne Vorwissen
- `grid_roles`: Rollen-Weltmodell: Wissen aus einem Spiel in einem Spiel mit neuen Farben
- `grid_foreign`: Gegenprobe: schadet Vorwissen, wenn ein Spiel eine fremde Mechanik hat?
- `cross_world`: Spielwelt gegen Alltagswelt: gilt dieselbe Lehre über Vorwissen?
- `grid_replay`: Wiedergabe mehrerer Level als Seite zum Anschauen
- `general_worlds`: Ein allgemeiner Agent in drei ganz verschiedenen Welten (H19)
- `library_transfer`: Bibliothek über Welten hinweg, bei gleicher Rechenzeit gemessen (H20)
- `new_world`: Eine neue Umgebung an unerwarteter Unsicherheit erkennen (H18)
- `general_replay`: Seite „Ein Agent, drei Welten“ zum Anschauen
"""

from hekmatki.experiments.cross_world import CrossRow, compare_worlds
from hekmatki.experiments.discovery import DiscoveryResult, DiscoveryRow, run_discovery
from hekmatki.experiments.exploration import ExplorationResult, run_exploration
from hekmatki.experiments.forgetting import H12Result, run_h12
from hekmatki.experiments.grid_foreign import ForeignRow, run_foreign
from hekmatki.experiments.grid_mechanics import MechanicsRow, run_mechanics
from hekmatki.experiments.grid_roles import RoleRow, run_roles
from hekmatki.experiments.grid_transfer import GridRow, run_grid_transfer
from hekmatki.experiments.meta_schema import MetaRow, run_meta_schema
from hekmatki.experiments.recognition import RecognitionRow, run_recognition
from hekmatki.experiments.rule_transfer import TransferResult, TransferRow, run_rule_transfer
from hekmatki.experiments.schema_learning import (
    H11Result,
    H11Row,
    StressRow,
    run_h11,
    run_h11_stress,
)
from hekmatki.experiments.sleep import (
    CombinedRow,
    MultiSchemaRow,
    WakeSleepRow,
    run_combined,
    run_multi_schema,
    run_wake_sleep,
)
from hekmatki.experiments.traffic_light import GameResult, GameRow, run_traffic_light_game

__all__ = [
    "CombinedRow",
    "CrossRow",
    "DiscoveryResult",
    "DiscoveryRow",
    "ExplorationResult",
    "ForeignRow",
    "GameResult",
    "GameRow",
    "GridRow",
    "H11Result",
    "H11Row",
    "H12Result",
    "MechanicsRow",
    "MetaRow",
    "MultiSchemaRow",
    "RecognitionRow",
    "RoleRow",
    "StressRow",
    "TransferResult",
    "TransferRow",
    "WakeSleepRow",
    "compare_worlds",
    "run_combined",
    "run_discovery",
    "run_exploration",
    "run_foreign",
    "run_grid_transfer",
    "run_h11",
    "run_h11_stress",
    "run_h12",
    "run_mechanics",
    "run_meta_schema",
    "run_multi_schema",
    "run_recognition",
    "run_roles",
    "run_rule_transfer",
    "run_traffic_light_game",
    "run_wake_sleep",
]
