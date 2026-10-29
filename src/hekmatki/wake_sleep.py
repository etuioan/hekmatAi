"""Wach-Schlaf-Agent: erkennt im Wachen Kontexte und verdichtet sie im Schlaf zu Schemata.

Im Wachen merkt sich der Agent pro Kontext, was er dort erlebt hat (wie der Hippocampus).
Hat ein Kontext genug Erfahrung gesammelt, schläft der Agent und baut diese Erfahrung in
das passende Schema ein (Konsolidierung, wie der Übertrag in den Neokortex). Passt sie zu
keinem Schema, kann sie zusammen mit einem ähnlichen Kontext ein neues Schema gründen.
Ab dann startet jeder neu erkannte Kontext aus den aktuellen Schemata.
"""

from collections.abc import Iterable
from functools import partial
from itertools import combinations

from hekmatki.context import ContextInference
from hekmatki.markov import MarkovModel
from hekmatki.schema import DEFAULT_MERGE_THRESHOLD, Schema, merge, schemas_or_flat_model

DEFAULT_MATURITY = 100
"""Ab so vielen erlebten Übergängen gilt ein Kontext als gereift."""


class WakeSleepAgent:
    """Kontextinferenz plus Schlafphasen, in denen gereifte Kontexte in Schemata wandern.

    Mit `maturity=None` schläft der Agent nie von selbst, sondern nur, wenn `sleep()` von
    außen aufgerufen wird. Dann zählt jeder Kontext als gereift.
    Mit `max_schemas` lässt sich die Zahl der Schemata begrenzen (Vergleich mit Version 0.4).
    """

    def __init__(
        self,
        alphabet: Iterable[str],
        maturity: int | None = DEFAULT_MATURITY,
        threshold: float = DEFAULT_MERGE_THRESHOLD,
        max_schemas: int | None = None,
    ) -> None:
        if maturity is not None and maturity < 1:
            raise ValueError(f"maturity muss mindestens 1 sein oder None, war {maturity}.")
        if max_schemas is not None and max_schemas < 1:
            raise ValueError(f"max_schemas muss mindestens 1 sein oder None, war {max_schemas}.")
        self.alphabet = tuple(sorted(set(alphabet)))
        self.maturity = maturity
        self.threshold = threshold
        self.max_schemas = max_schemas
        self.inference = ContextInference(self.alphabet)
        self.schemas: list[Schema] = []
        self.sleeps = 0
        self._experience: list[MarkovModel] = []
        self._schema_of: dict[int, int] = {}
        self._mature_at_last_sleep = 0

    @property
    def context_count(self) -> int:
        """Wie viele Kontexte der Agent bisher gefunden hat."""
        return len(self.inference.contexts)

    @property
    def contexts_in_schemas(self) -> int:
        """Wie viele Kontexte bereits in ein Schema eingeflossen sind."""
        return len(self._schema_of)

    def step(self, previous: str, following: str) -> float:
        """Wachen: vorhersagen, Kontext erkennen, lernen und die Erfahrung merken.

        Ist seit dem letzten Schlaf ein Kontext neu gereift, schläft der Agent danach.
        """
        predicted = self.inference.step(previous, following)
        self._remember(previous, following)
        if self._wants_to_sleep():
            self.sleep()
        return predicted

    def sleep(self) -> None:
        """Schlafen: ordnet gereifte Kontexte, die noch in keinem Schema stecken, Schemata zu.

        Erst tritt jeder solche Kontext dem Schema bei, zu dem er am besten passt. Dann
        gründet das ähnlichste Paar der übrigen ein neues Schema. Das wiederholt sich, bis
        sich nichts mehr ändert. Was nirgends passt, wird beim nächsten Schlaf erneut geprüft.
        """
        self.sleeps += 1
        mature = self._mature()
        self._mature_at_last_sleep = len(mature)
        while True:
            for index in self._outside(mature):
                self._join_closest_schema(index)
            if not self._found_schema(self._outside(mature)):
                break
        if self.schemas:
            self.inference.replace_new_context_model(
                partial(schemas_or_flat_model, tuple(self.schemas), self.alphabet)
            )

    def _remember(self, previous: str, following: str) -> None:
        """Episodisches Gedächtnis: zählt den Übergang beim gerade aktiven Kontext."""
        active = self.inference.active
        if active is None:
            raise RuntimeError("Nach einem Schritt muss ein Kontext aktiv sein.")
        while len(self._experience) < self.context_count:
            self._experience.append(MarkovModel(self.alphabet))
        self._experience[active].observe(previous, following)

    def _mature(self) -> list[int]:
        """Kontexte mit genug Erfahrung für den Schlaf."""
        if self.maturity is None:
            return list(range(len(self._experience)))
        return [
            i
            for i, experience in enumerate(self._experience)
            if experience.total_count() >= self.maturity
        ]

    def _outside(self, contexts: list[int]) -> list[int]:
        """Die Kontexte, die noch in keinem Schema stecken."""
        return [i for i in contexts if i not in self._schema_of]

    def _wants_to_sleep(self) -> bool:
        return self.maturity is not None and len(self._mature()) > self._mature_at_last_sleep

    def _join_closest_schema(self, index: int) -> None:
        """Baut die Erfahrung eines Kontexts in das Schema ein, zu dem sie am besten passt."""
        if not self.schemas:
            return
        attempts = [
            merge(schema.model, self._experience[index], schema.name, self.threshold)
            for schema in self.schemas
        ]
        best = min(range(len(attempts)), key=lambda k: attempts[k].distance)
        merged = attempts[best].schema
        if merged is not None:
            self.schemas[best] = merged
            self._schema_of[index] = best

    def _found_schema(self, candidates: list[int]) -> bool:
        """Gründet ein neues Schema aus dem ähnlichsten passenden Paar. True, wenn es klappt."""
        if self.max_schemas is not None and len(self.schemas) >= self.max_schemas:
            return False
        name = f"Schema {len(self.schemas) + 1}"
        attempts = [
            (merge(self._experience[a], self._experience[b], name, self.threshold), a, b)
            for a, b in combinations(candidates, 2)
        ]
        if not attempts:
            return False
        closest, first, second = min(attempts, key=lambda attempt: attempt[0].distance)
        if closest.schema is None:
            return False
        self._schema_of.update({first: len(self.schemas), second: len(self.schemas)})
        self.schemas.append(closest.schema)
        return True
