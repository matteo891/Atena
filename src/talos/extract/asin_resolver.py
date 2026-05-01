"""AsinResolver — risoluzione (descrizione, prezzo) -> ASIN candidato.

Inaugurato in CHG-2026-05-01-016 (skeleton tipi + Protocol + helper di
scoring, mock-testable). Sblocca il flusso d'uso reale del Leader: il
listino fornitore arriva con descrizione e prezzo, NON con ASIN. Il
sistema risolve ogni riga in un ASIN candidato verificato contro il
prezzo Buy Box reale, prima di passare a `acquire_and_persist`
(CHG-2026-05-01-010) e alla pipeline VGP esistente.

Decisioni Leader 2026-05-01 round 4:

- **Canale (1)**: SERP Amazon primario (zero quota), Keepa search
  fallback. Adapter live in CHG-2026-05-01-017+.
- **Strategia (2 alpha-prime)**: top-1 SERP + verifica prezzo via
  `lookup_product` live. Calcola `confidence_pct` composito (fuzzy
  title 60% + (1 - delta prezzo) 40%). NESSUN match scartato
  silenziosamente: tutti esposti alla UI con il loro
  `confidence_pct`.
- **Soglia ambiguita' (3 i-prime)**: `DEFAULT_AMBIGUOUS_THRESHOLD_PCT
  = 70` abilita solo il flag `is_ambiguous` per highlight UI. NON e'
  threshold di scarto. Coerente con feedback Leader "match ambigui
  con confidence" (memory `feedback_ambigui_con_confidence.md`).

R-01 NO SILENT DROPS: invariante a tutti i livelli. Mai una riga
scartata silente. Eccezioni esplicite per stati impossibili (prezzo
negativo, descrizione vuota), AMBIGUOUS marcato visibile altrimenti.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from decimal import Decimal


# Range valido `fuzzy_title_pct` (0-100, output `rapidfuzz` ratio).
_FUZZY_PCT_MIN: float = 0.0
_FUZZY_PCT_MAX: float = 100.0

# Soglia di evidenziamento "AMBIGUO" in UI. Non e' un threshold di scarto:
# tutti i match restano nella pipeline. Sotto questa soglia il flag
# `is_ambiguous` si attiva e la UI applica highlight visivo.
# Override-abile via `TalosSettings.asin_resolver_ambiguous_threshold` (CHG futuro).
DEFAULT_AMBIGUOUS_THRESHOLD_PCT: float = 70.0

# Pesi composito confidence: fuzzy title vs prezzo. Sommano a 1.0.
# Razionale (decisione Leader 2-alpha-prime): il titolo conta piu' del
# prezzo perche' il listino fornitore puo' avere prezzi promozionali /
# sconti diversi dal Buy Box, ma se il titolo combacia siamo
# abbastanza sicuri.
CONFIDENCE_WEIGHT_TITLE: float = 0.6
CONFIDENCE_WEIGHT_PRICE: float = 0.4


@dataclass(frozen=True)
class ResolutionCandidate:
    """Singolo candidato ASIN risultato di una SERP.

    `title` e' il titolo Amazon raw (top-N risultato della SERP);
    `buybox_eur` e' il prezzo Buy Box live (via `lookup_product`,
    None se non risolto).

    `delta_price_pct`: |buybox - prezzo_input| / prezzo_input * 100;
    None se buybox=None (lookup live failed).
    """

    asin: str
    title: str
    buybox_eur: Decimal | None
    fuzzy_title_pct: float
    delta_price_pct: float | None
    confidence_pct: float


@dataclass(frozen=True)
class ResolutionResult:
    """Output `resolve_description` per una singola riga di listino.

    Il `selected` e' il candidato top-1 (massimo `confidence_pct`).
    `candidates` contiene tutti i candidati esaminati (top-N SERP),
    permettendo alla UI di mostrare alternative se il CFO scarta il
    `selected`. `is_ambiguous` flag se `selected.confidence_pct <
    DEFAULT_AMBIGUOUS_THRESHOLD_PCT`.

    R-01 NO SILENT DROPS: anche `selected=None` (zero candidati SERP)
    NON e' silente. Caller riceve `is_ambiguous=True`,
    `confidence_pct=0.0`, `notes` valorizzato con la causa
    ("no SERP results", "lookup failed", ecc.).
    """

    description: str
    input_price_eur: Decimal
    selected: ResolutionCandidate | None
    candidates: tuple[ResolutionCandidate, ...] = field(default_factory=tuple)
    is_ambiguous: bool = True  # default conservativo: ambiguo finche' non smentito
    notes: tuple[str, ...] = field(default_factory=tuple)


class AsinResolverProtocol(Protocol):
    """Interfaccia minimal del resolver (composizione SERP + lookup live)."""

    def resolve_description(
        self,
        description: str,
        input_price_eur: Decimal,
    ) -> ResolutionResult:
        """Risolve una singola riga listino in un ASIN candidato.

        R-01: non solleva su zero candidati / lookup failure; ritorna
        sempre un `ResolutionResult` con `is_ambiguous=True` e `notes`
        valorizzato. Solleva solo su input invalido (prezzo<=0,
        descrizione vuota): contratto chiaro con il caller.
        """
        ...


def compute_confidence(
    fuzzy_title_pct: float,
    delta_price_pct: float | None,
) -> float:
    """Composito 0-100 da fuzzy title (60%) e prezzo (40%).

    Il termine prezzo e' `max(0, 100 - delta_price_pct)` saturato in
    [0, 100]: delta 0% -> 100, delta 100% (prezzo doppio o zero) -> 0.
    Se `delta_price_pct is None` (lookup live fallito, no buybox), il
    termine prezzo e' 0 (penalizza il candidato senza buttarlo).

    Pesi pre-validati in costanti modulo-level (somma = 1.0).

    >>> round(compute_confidence(95.0, 2.0), 2)  # title forte, prezzo combacia
    96.2
    >>> round(compute_confidence(60.0, 50.0), 2)  # entrambi scarsi
    56.0
    >>> round(compute_confidence(80.0, None), 2)  # lookup price failed
    48.0
    """
    if not _FUZZY_PCT_MIN <= fuzzy_title_pct <= _FUZZY_PCT_MAX:
        msg = f"fuzzy_title_pct out of range [0,100]: {fuzzy_title_pct}"
        raise ValueError(msg)
    if delta_price_pct is not None and delta_price_pct < 0:
        msg = f"delta_price_pct negativo invalido: {delta_price_pct}"
        raise ValueError(msg)

    price_score = 0.0 if delta_price_pct is None else max(0.0, _FUZZY_PCT_MAX - delta_price_pct)

    return fuzzy_title_pct * CONFIDENCE_WEIGHT_TITLE + price_score * CONFIDENCE_WEIGHT_PRICE


def is_ambiguous(
    confidence_pct: float,
    *,
    threshold: float = DEFAULT_AMBIGUOUS_THRESHOLD_PCT,
) -> bool:
    """`True` sotto soglia. Solo flag UI, NON criterio di scarto."""
    return confidence_pct < threshold
