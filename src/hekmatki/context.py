"""Kontextinferenz: erkennen, welche Scheibe gerade gilt, und nur diese lernen lassen.

Vereinfachte Form der Latent-Cause-Modelle (Gershman, Blei & Niv 2010) und von COIN
(Heald, Lengyel & Wolpert 2021): Der Agent führt eine Wahrscheinlichkeit über Kontexte,
die über die Zeit Belege sammelt. Auch die Option „neuer Kontext“ sammelt Belege über
mehrere Schritte. Erklärt keiner der bekannten Kontexte die letzten Beobachtungen gut, gewinnt
sie, und ein neuer Kontext entsteht.

Wie ein neuer Kontext beginnt, ist austauschbar: leer, oder aus einem Schema erzeugt.
"""

from collections.abc import Callable, Iterable

from hekmatki.markov import DEFAULT_PSEUDOCOUNT, MarkovModel
from hekmatki.online import LearningPredictor

ModelFactory = Callable[[], LearningPredictor]
"""Erzeugt das Startmodell für einen neu erkannten Kontext."""

DEFAULT_NEW_CONTEXT_SHARE = 0.03
"""Anteil eines Wechsels, der auf „neuer Kontext“ statt auf einen bekannten Kontext entfällt."""


class ContextInference:
    """Online-Lerner mit mehreren Situationsmodellen und Kontextwechsel."""

    def __init__(
        self,
        alphabet: Iterable[str],
        stay_probability: float = 0.95,
        pseudocount: float = DEFAULT_PSEUDOCOUNT,
        new_context_model: ModelFactory | None = None,
        new_context_share: float = DEFAULT_NEW_CONTEXT_SHARE,
    ) -> None:
        if not 0.0 < stay_probability < 1.0:
            raise ValueError(
                f"stay_probability muss zwischen 0 und 1 liegen, war {stay_probability}."
            )
        if not 0.0 < new_context_share < 1.0:
            raise ValueError(
                f"new_context_share muss zwischen 0 und 1 liegen, war {new_context_share}."
            )
        self.alphabet = tuple(sorted(set(alphabet)))
        self.stay_probability = stay_probability
        self.pseudocount = pseudocount
        self.new_context_share = new_context_share
        self.contexts: list[LearningPredictor] = []
        self._belief: list[float] = []
        """Wahrscheinlichkeit jedes Kontexts; die letzte Stelle gehört zu „neuer Kontext“."""
        self.active: int | None = None
        self._new_context_model: ModelFactory = new_context_model or self._empty_model
        self._candidate = self._new_context_model()

    def replace_new_context_model(self, factory: ModelFactory) -> None:
        """Legt fest, womit künftige neue Kontexte starten, z. B. nach einer Schlafphase."""
        self._new_context_model = factory
        self._candidate = factory()

    def step(self, previous: str, following: str) -> float:
        """Sagt `following` vorher, aktualisiert die Kontextwahrscheinlichkeit und lernt."""
        options = [*self.contexts, self._candidate]
        prior = self._prior()
        likelihoods = [m.probability(previous, following) for m in options]
        predicted = sum(p * lik for p, lik in zip(prior, likelihoods, strict=True))
        posterior = [p * lik / predicted for p, lik in zip(prior, likelihoods, strict=True)]

        winner = max(range(len(posterior)), key=posterior.__getitem__)
        if winner == len(self.contexts):
            # Die Option „neuer Kontext“ hat gewonnen: Sie wird zu einem echten Kontext,
            # und eine frische Option „neuer Kontext“ beginnt ohne Belege.
            self.contexts.append(self._candidate)
            self._candidate = self._new_context_model()
            posterior.append(0.0)
        self._belief = posterior
        self.active = winner
        self.contexts[winner].observe(previous, following)  # Gating: nur dieser Kontext lernt.
        return predicted

    def _prior(self) -> list[float]:
        """Klebrige Vorannahme für den nächsten Schritt.

        Mit `stay_probability` bleibt alles, wie es war, auch gesammelte Belege für „neu“.
        Der Rest ist ein möglicher Wechsel: Davon geht `new_context_share` an „neuer
        Kontext“, der Rest gleichmäßig an die bekannten Kontexte.
        """
        if not self.contexts:
            return [1.0]
        switch = 1.0 - self.stay_probability
        to_each_known = switch * (1.0 - self.new_context_share) / len(self.contexts)
        prior = [self.stay_probability * b + to_each_known for b in self._belief[:-1]]
        prior.append(self.stay_probability * self._belief[-1] + switch * self.new_context_share)
        return self._normalized(prior)

    def _empty_model(self) -> MarkovModel:
        return MarkovModel(self.alphabet, self.pseudocount)

    @staticmethod
    def _normalized(values: list[float]) -> list[float]:
        total = sum(values)
        if total <= 0.0:
            raise ValueError("Wahrscheinlichkeiten lassen sich nicht normieren (Summe 0).")
        return [v / total for v in values]
