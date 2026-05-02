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

import structlog
from rapidfuzz import fuzz

if TYPE_CHECKING:
    from collections.abc import Callable
    from decimal import Decimal

    from talos.io_.fallback_chain import ProductData
    from talos.io_.serp_search import AmazonSerpAdapter

_logger = structlog.get_logger(__name__)


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

    `bsr_root` (CHG-2026-05-02-003): BSR root Amazon dal lookup Keepa.
    Usato a valle da `velocity_estimator.estimate_v_tot_from_bsr`
    quando il CSV non specifica `v_tot`.
    """

    asin: str
    title: str
    buybox_eur: Decimal | None
    fuzzy_title_pct: float
    delta_price_pct: float | None
    confidence_pct: float
    bsr_root: int | None = None
    # CHG-2026-05-02-036: campi ancillari Arsenale 180k (pull-only).
    # Popolati dal lookup Keepa (CHG-035), propagati a `ResolvedRow` poi
    # alle colonne `enriched_df` per `compute_vgp_score` (CHG-031/032).
    drops_30: int | None = None
    buy_box_avg90: Decimal | None = None
    amazon_buybox_share: float | None = None
    # CHG-2026-05-02-040: fee_fba atomica Keepa (errata alpha-prime invertita).
    # `None` → fallback fee_fba_manual L11b (Samsung-specific) downstream.
    fee_fba_eur: Decimal | None = None


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


def _fuzzy_title_ratio(description: str, title: str) -> float:
    """Score 0-100 via `rapidfuzz.fuzz.token_set_ratio` (CHG-018).

    `token_set_ratio` e' robusto a:
    - ordine token diverso ("Galaxy S24 256GB" vs "S24 Galaxy 256 GB")
    - parole extra nel titolo Amazon (descrizione fornitore corta vs
      titolo lungo con specifiche)
    - duplicati e whitespace.

    Restituisce direttamente 0-100 compatibile con `compute_confidence`.
    """
    return float(fuzz.token_set_ratio(description, title))


def _delta_price_pct(buybox_eur: Decimal | None, input_price_eur: Decimal) -> float | None:
    """Delta prezzo percentuale `|buybox - input| / input * 100`.

    None se `buybox_eur is None` (lookup live failed). `input_price_eur`
    deve essere > 0 (validato dal caller).
    """
    if buybox_eur is None:
        return None
    diff = abs(buybox_eur - input_price_eur)
    return float(diff / input_price_eur * 100)


class _LiveAsinResolver:
    """Composer SERP + lookup live per descrizione->ASIN (CHG-018).

    Implementa `AsinResolverProtocol` (CHG-016) componendo:
    1. `serp_adapter.search(description)` -> top-N candidati
    2. `lookup_callable(candidate.asin)` -> `ProductData` per ottenere
       `buybox_eur` (di norma da Keepa NEW via `lookup_product`)
    3. Per ogni candidato calcola fuzzy_title (rapidfuzz token_set) e
       delta_price (verifica prezzo). Compone `confidence_pct`.
    4. `selected` = candidato con max `confidence_pct`. Tie-break
       implicito: ordine SERP preserve (top-1 vince a parita').

    `lookup_callable` e' iniettato per disaccoppiamento: in produzione
    e' `partial(lookup_product, keepa=..., scraper=None, page=None,
    ocr=None)` Keepa-only (no Chromium overhead per la verifica
    prezzo dei N candidati). In test e' un mock pure-Python.

    R-01 NO SILENT DROPS:
    - lookup fallito per un candidato -> buybox=None +
      `delta_price=None` -> confidence ridotta ma candidato ESPOSTO
      in `candidates` (UX-side R-01).
    - SERP vuota -> ResolutionResult(selected=None, candidates=(),
      is_ambiguous=True, notes=("zero risultati SERP",)).
    - Validazione input: prezzo<=0, descrizione vuota -> ValueError
      esplicito al caller (contratto).
    """

    def __init__(
        self,
        serp_adapter: AmazonSerpAdapter,
        lookup_callable: Callable[[str], ProductData],
        *,
        max_candidates: int = 5,
    ) -> None:
        if max_candidates <= 0:
            msg = f"max_candidates deve essere > 0 (ricevuto {max_candidates})"
            raise ValueError(msg)
        self._serp = serp_adapter
        self._lookup = lookup_callable
        self._max_candidates = max_candidates

    def resolve_description(
        self,
        description: str,
        input_price_eur: Decimal,
    ) -> ResolutionResult:
        if not description.strip():
            msg = "description vuota / whitespace-only"
            raise ValueError(msg)
        if input_price_eur <= 0:
            msg = f"input_price_eur deve essere > 0 (ricevuto {input_price_eur})"
            raise ValueError(msg)

        serp_results = self._serp.search(description, max_results=self._max_candidates)
        if not serp_results:
            return ResolutionResult(
                description=description,
                input_price_eur=input_price_eur,
                selected=None,
                candidates=(),
                is_ambiguous=True,
                notes=("zero risultati SERP",),
            )

        notes: list[str] = []
        candidates: list[ResolutionCandidate] = []
        for serp_item in serp_results:
            buybox: Decimal | None = None
            bsr_root: int | None = None
            drops_30: int | None = None
            buy_box_avg90: Decimal | None = None
            amazon_buybox_share: float | None = None
            fee_fba_eur_keepa: Decimal | None = None
            try:
                product = self._lookup(serp_item.asin)
                # CHG-2026-05-02-037 hotfix: defensive `getattr` per tolleranza
                # a `ProductData` cached da Streamlit (`@st.cache_data` può
                # servire oggetti pre-CHG-035 senza i 3 nuovi attributi).
                buybox = getattr(product, "buybox_eur", None)
                # CHG-2026-05-02-003: propaga BSR per estimator v_tot.
                bsr_root = getattr(product, "bsr", None)
                # CHG-2026-05-02-036: propaga 3 campi ancillari Arsenale.
                drops_30 = getattr(product, "drops_30", None)
                buy_box_avg90 = getattr(product, "buy_box_avg90", None)
                amazon_buybox_share = getattr(product, "amazon_buybox_share", None)
                # CHG-2026-05-02-040: propaga fee_fba atomica Keepa.
                fee_fba_eur_keepa = getattr(product, "fee_fba_eur", None)
            except Exception as exc:  # noqa: BLE001 — lookup puo' lanciare KeepaTransient/Rate/Selector*; tutti -> note + buybox=None
                notes.append(
                    f"candidato {serp_item.asin} lookup failed: {type(exc).__name__}",
                )
            fuzzy = _fuzzy_title_ratio(description, serp_item.title)
            delta = _delta_price_pct(buybox, input_price_eur)
            confidence = compute_confidence(fuzzy, delta)
            candidates.append(
                ResolutionCandidate(
                    asin=serp_item.asin,
                    title=serp_item.title,
                    buybox_eur=buybox,
                    fuzzy_title_pct=fuzzy,
                    delta_price_pct=delta,
                    confidence_pct=confidence,
                    bsr_root=bsr_root,
                    drops_30=drops_30,
                    buy_box_avg90=buy_box_avg90,
                    amazon_buybox_share=amazon_buybox_share,
                    fee_fba_eur=fee_fba_eur_keepa,
                ),
            )

        # Selected = max confidence; tie-break implicito: primo per ordine SERP.
        selected = max(candidates, key=lambda c: c.confidence_pct)
        return ResolutionResult(
            description=description,
            input_price_eur=input_price_eur,
            selected=selected,
            candidates=tuple(candidates),
            is_ambiguous=is_ambiguous(selected.confidence_pct),
            notes=tuple(notes),
        )
