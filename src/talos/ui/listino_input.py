"""Helper puri per il flow "descrizione + prezzo -> ASIN" UI (CHG-020).

Modulo SENZA dipendenza da Streamlit, testabile in unit puri. Il
modulo `dashboard.py` (Streamlit-side) importa questi helper e
gestisce solo il rendering.

Flusso:
1. CFO carica CSV con colonne `descrizione`, `prezzo` (+ opzionali
   `v_tot`, `s_comp`, `category_node`).
2. `parse_descrizione_prezzo_csv` valida e ritorna lista di
   `DescrizionePrezzoRow` + warnings.
3. `resolve_listino_with_cache` per ogni riga: cache hit
   (`description_resolutions` CHG-019) → ResolvedRow con
   confidence storica; cache miss → `_LiveAsinResolver` (CHG-018)
   + `upsert_resolution` post-resolve.
4. `build_listino_raw_from_resolved` costruisce il DataFrame
   `listino_raw` con le 7 colonne richieste da `REQUIRED_INPUT_COLUMNS`
   (CHG-039), riempiendo i defaults minimi non risolvibili dal
   resolver.

Decisioni Leader 2026-05-01 round 4 ratificate (delta=A
convivenza CSV legacy + nuovo flow). I default per `v_tot=0`,
`s_comp=0`, `match_status=SICURO`, `referral_fee_pct=0.08` sono
proposte per MVP — il CFO puo' override colonne nel CSV se
ha valori migliori. Il campo `referral_fee_pct` e' una FRAZIONE
DECIMALE in [0, 1] (0.08 = 8%), coerente con il contratto di
`cash_inflow_eur(referral_fee_rate)` (CHG-038 fix unit drift).

R-01 NO SILENT DROPS (ADR-0021): le righe del CSV non parsabili
o non risolte vengono accumulate in `warnings` (parse) e
`notes` (resolve) ed esposte alla UI, NON scartate silenziosamente.
Gli eventi canonici upstream (`keepa.miss`, `scrape.selector_fail`)
sono emessi dai canali sottostanti (`KeepaClient`,
`_LiveAmazonSerpAdapter`) durante il resolve, propagati alla
UI via `ResolutionResult.notes` (CHG-018 R-01 UX-side).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import TYPE_CHECKING

import structlog

from talos.extract.asin_resolver import (
    DEFAULT_AMBIGUOUS_THRESHOLD_PCT,
)
from talos.extract.asin_resolver import (
    is_ambiguous as _is_ambiguous_threshold,
)
from talos.extract.velocity_estimator import V_TOT_SOURCE_BSR_ESTIMATE, resolve_v_tot
from talos.io_.scraper import parse_eur
from talos.persistence.asin_resolver_repository import (
    compute_description_hash,
    find_resolution_by_hash,
    upsert_resolution,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import pandas as pd
    from sqlalchemy.orm import Session, sessionmaker

    from talos.extract.asin_resolver import (
        AsinResolverProtocol,
        ResolutionCandidate,
        ResolutionResult,
    )
    from talos.io_.fallback_chain import ProductData

_logger = structlog.get_logger(__name__)

# Identifica la cache per gli eventi canonici `cache.hit` / `cache.miss`
# (catalogo ADR-0021, errata CHG-2026-05-01-025).
_CACHE_TABLE_DESCRIPTION_RESOLUTIONS: str = "description_resolutions"


def _emit_cache_hit(*, table: str) -> None:
    """Emette evento canonico `cache.hit` (catalogo ADR-0021).

    Helper puro: testabile via LogCapture. Tracking efficacia cache
    `description_resolutions`: `n_hits / (n_hits + n_misses)` =
    cache hit rate per tenant.

    CHG-2026-05-01-037 (B1.4): `tenant_id` rimosso dalla firma; ora
    ereditato dal bind context UI (`bind_request_context` in
    `_render_descrizione_prezzo_flow`).
    """
    _logger.debug("cache.hit", table=table)


def _emit_cache_miss(*, table: str) -> None:
    """Emette evento canonico `cache.miss` (catalogo ADR-0021).

    Helper puro: testabile via LogCapture. Cache miss → resolve live
    + `upsert_resolution` (consumo quota Keepa/SERP). Tracking costo
    operativo del flow descrizione+prezzo.

    CHG-2026-05-01-037 (B1.4): `tenant_id` rimosso dalla firma; ora
    ereditato dal bind context UI.
    """
    _logger.debug("cache.miss", table=table)


# Colonne obbligatorie del CSV "umano" descrizione+prezzo.
REQUIRED_DESCRIZIONE_PREZZO_COLUMNS: tuple[str, ...] = ("descrizione", "prezzo")

# CHG-2026-05-02-023: alias accettati per auto-detect colonne CSV.
# Il CFO non deve riformattare il proprio export: header diversi
# (`Articolo`/`Costo unitario`/...) vengono riconosciuti via alias o
# heuristica price-parseable (vedi `_detect_columns`).
DESCRIZIONE_HEADER_ALIASES: frozenset[str] = frozenset(
    {
        "descrizione",
        "description",
        "prodotto",
        "product",
        "title",
        "titolo",
        "nome",
        "name",
        "articolo",
        "item",
    },
)
PREZZO_HEADER_ALIASES: frozenset[str] = frozenset(
    {
        "prezzo",
        "price",
        "costo",
        "cost",
        "prezzo_fornitore",
        "prezzo_eur",
        "costo_eur",
        "costo_unitario",
        "cst",
        "eur",
    },
)
# Soglie heuristica auto-detect (R-01: deterministiche, no fuzzy).
_PRICE_PARSEABLE_THRESHOLD: float = 0.8  # ≥80% righe parseable -> candidato prezzo
_DESC_MIN_AVG_LEN: float = 4.0  # avg string length per essere candidato descrizione
_MIN_COLUMNS_REQUIRED: int = 2  # vincolo: descrizione + prezzo separate

# Default per le 5 colonne `REQUIRED_INPUT_COLUMNS` non risolvibili dal
# resolver (ADR-0017 + CHG-039). Override-abili dal CSV: se la colonna
# esiste, vince sulla default.
# CHG-2026-05-01-038: corretto da 8.0 a 0.08 (fix unit drift —
# `cash_inflow_eur` valida `referral_fee_rate` in [0, 1] frazione decimale).
DEFAULT_REFERRAL_FEE_PCT: float = 0.08
DEFAULT_V_TOT: int = 0
DEFAULT_S_COMP: int = 0
DEFAULT_MATCH_STATUS: str = "SICURO"

# Soglie per `format_confidence_badge` (R-01 UX visibility).
_CONFIDENCE_PCT_MIN: float = 0.0
_CONFIDENCE_PCT_MAX: float = 100.0
_CONFIDENCE_HIGH_THRESHOLD_PCT: float = 85.0  # >= -> OK
_CONFIDENCE_MEDIUM_THRESHOLD_PCT: float = 70.0  # >= -> DUB; < -> AMB


@dataclass(frozen=True)
class DescrizionePrezzoRow:
    """Riga raw del listino "umano" del CFO."""

    descrizione: str
    prezzo_eur: Decimal
    v_tot: int
    s_comp: int
    category_node: str | None  # opzionale per L12 referral_fee per categoria


@dataclass(frozen=True)
class ResolvedRow:
    """Risultato risoluzione per riga listino: input + ASIN + confidence + cache hit?

    `verified_buybox_eur` è il prezzo Buy Box live recuperato da Keepa/Scraper
    durante il resolve (CHG-018 → propagato in CHG-022). `None` quando:
    - il resolver non ha risolto la riga (`asin=""`);
    - il lookup live ha fallito sul candidato selected (`buybox=None`);
    - cache hit (la cache `description_resolutions` salva solo asin+confidence,
      non il buybox; serve un re-resolve per averlo). In questi casi il
      `build_listino_raw_from_resolved` fa fallback a `prezzo_eur` come
      `buy_box_eur` (semantica conservativa ereditata da CHG-020).

    `candidates` (CHG-023): tutti i candidati top-N esaminati dal resolver
    (cache miss only — cache hit ha tuple vuota). Permette al CFO di
    override il candidato selezionato per righe ambigue (UX A3 R-01
    rafforzato: tutti i match esposti con possibilità di scelta umana).
    """

    descrizione: str
    prezzo_eur: Decimal
    asin: str
    confidence_pct: float
    is_ambiguous: bool
    is_cache_hit: bool
    v_tot: int
    s_comp: int
    category_node: str | None
    notes: tuple[str, ...]
    verified_buybox_eur: Decimal | None = None
    candidates: tuple[ResolutionCandidate, ...] = field(default_factory=tuple)
    # CHG-2026-05-02-003: BSR root da Keepa per stima v_tot quando CSV
    # non specifica `v_tot` esplicito. None se cache hit + lookup fail
    # oppure resolver senza buybox/bsr disponibili.
    bsr_root: int | None = None
    # CHG-2026-05-02-036: campi ancillari Arsenale 180k propagati da
    # `ProductData` (CHG-035) → `enriched_df` per filtri pull-only
    # `compute_vgp_score` (CHG-031/032) e `resolve_v_tot(drops_30=...)`
    # (CHG-034 errata Dynamic Floor preferred source).
    drops_30: int | None = None
    buy_box_avg90: Decimal | None = None
    amazon_buybox_share: float | None = None


def _column_price_parseable_ratio(series: pd.Series) -> float:
    """Frazione di valori parseable come EUR via `parse_eur` o numerici nativi.

    CHG-2026-05-02-023: oracle price-detection per `_detect_columns`.
    Tratta `int/float` nativi pandas come prezzi validi (CSV con
    tipi inferiti). Stringhe parsate via `parse_eur` (italiano/anglo).
    Bool esclusi (CSV potrebbe avere flag boolean che NON sono prezzi).
    NaN/None contano nel denominatore solo se ci sono valori non-null
    nella colonna (denominatore = righe non-null).
    """
    n_total = 0
    n_parseable = 0
    for value in series:
        if value is None or not _is_finite(value):
            continue
        n_total += 1
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float, Decimal)):
            n_parseable += 1
            continue
        text = str(value).strip()
        if not text:
            continue
        if parse_eur(text) is not None:
            n_parseable += 1
    return n_parseable / n_total if n_total else 0.0


def _column_avg_string_length(series: pd.Series) -> float:
    """Avg lunghezza stringhe (escluse NaN/None/empty) — oracle desc-detection."""
    lengths: list[int] = []
    for value in series:
        if value is None or not _is_finite(value):
            continue
        text = str(value).strip()
        if text:
            lengths.append(len(text))
    return sum(lengths) / len(lengths) if lengths else 0.0


def _detect_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Identifica le 2 colonne descrizione/prezzo via alias + heuristica.

    CHG-2026-05-02-023: il CFO non deve riformattare il CSV. Strategia
    deterministica:

    1. **Match per alias canonico** (`DESCRIZIONE_HEADER_ALIASES` /
       `PREZZO_HEADER_ALIASES`). Header già normalizzati (strip+lower).
    2. Per le colonne mancanti via alias: **heuristica price-parseable**
       (≥80% righe via `parse_eur` o numerico nativo) per il prezzo,
       **avg length ≥4 char** per la descrizione.
    3. Tie esatto sul max → `ValueError` esplicito (no guess silente).

    R-01 NO SILENT DROPS: errori espliciti per <2 colonne / 0 candidati
    prezzo / tie ambiguo / 0 candidati descrizione.

    Le colonne opzionali (`v_tot`/`s_comp`/`category_node`) NON sono
    soggette a detection: continuano a matchare per nome canonico nel
    chiamante (zero behavior change).
    """
    cols = [str(c) for c in df.columns]

    if len(cols) < _MIN_COLUMNS_REQUIRED:
        msg = (
            f"CSV non valido: rilevate {len(cols)} colonne. "
            f"Servono almeno 2 colonne separate (descrizione + prezzo). "
            f"Verifica il separatore CSV."
        )
        raise ValueError(msg)

    desc_col = next((c for c in cols if c in DESCRIZIONE_HEADER_ALIASES), None)
    prezzo_col = next(
        (c for c in cols if c != desc_col and c in PREZZO_HEADER_ALIASES),
        None,
    )

    # Heuristica per le colonne non risolte via alias.
    excluded = {c for c in (desc_col, prezzo_col) if c is not None}
    remaining = [c for c in cols if c not in excluded]

    if prezzo_col is None:
        ratios = [(c, _column_price_parseable_ratio(df[c])) for c in remaining]
        candidates = sorted(
            [(c, r) for c, r in ratios if r >= _PRICE_PARSEABLE_THRESHOLD],
            key=lambda x: -x[1],
        )
        if not candidates:
            msg = (
                f"CSV non valido: nessuna colonna riconosciuta come prezzo. "
                f"Aliases supportati: {sorted(PREZZO_HEADER_ALIASES)}. "
                f"In alternativa una colonna deve contenere almeno "
                f"{int(_PRICE_PARSEABLE_THRESHOLD * 100)}% di valori EUR parseable."
            )
            raise ValueError(msg)
        if len(candidates) > 1 and candidates[0][1] == candidates[1][1]:
            tied = [c for c, r in candidates if r == candidates[0][1]]
            msg = (
                f"CSV ambiguo: piu' colonne candidate prezzo con ratio identico "
                f"({candidates[0][1]:.2f}): {tied}. "
                f"Specifica un header esplicito tra {sorted(PREZZO_HEADER_ALIASES)}."
            )
            raise ValueError(msg)
        prezzo_col = candidates[0][0]
        remaining = [c for c in remaining if c != prezzo_col]

    if desc_col is None:
        lengths = [(c, _column_avg_string_length(df[c])) for c in remaining]
        candidates = sorted(
            [(c, length) for c, length in lengths if length >= _DESC_MIN_AVG_LEN],
            key=lambda x: -x[1],
        )
        if not candidates:
            msg = (
                f"CSV non valido: nessuna colonna riconosciuta come descrizione. "
                f"Aliases supportati: {sorted(DESCRIZIONE_HEADER_ALIASES)}. "
                f"In alternativa una colonna deve contenere stringhe di almeno "
                f"{_DESC_MIN_AVG_LEN:.0f} caratteri media."
            )
            raise ValueError(msg)
        if len(candidates) > 1 and candidates[0][1] == candidates[1][1]:
            tied = [c for c, length in candidates if length == candidates[0][1]]
            msg = (
                f"CSV ambiguo: piu' colonne candidate descrizione con avg length identica "
                f"({candidates[0][1]:.2f}): {tied}. "
                f"Specifica un header esplicito tra {sorted(DESCRIZIONE_HEADER_ALIASES)}."
            )
            raise ValueError(msg)
        desc_col = candidates[0][0]

    return desc_col, prezzo_col


def parse_descrizione_prezzo_csv(
    df: pd.DataFrame,
) -> tuple[list[DescrizionePrezzoRow], list[str]]:
    """Valida e converte un DataFrame raw in lista `DescrizionePrezzoRow`.

    Ritorna `(rows, warnings)`. Le righe non parsabili vengono
    skippate con warning esplicito (R-01 UX-side: l'utente sa cosa
    e' stato escluso). Solleva `ValueError` se mancano colonne
    obbligatorie o se l'auto-detect non riesce a identificarle.

    CHG-2026-05-02-011: header normalizzati (strip + lower) per tolleranza
    Excel italiano / variazioni di case.

    CHG-2026-05-02-023: auto-detect colonne descrizione/prezzo. Header
    canonici NON obbligatori: il parser identifica le 2 colonne via
    alias (`prodotto`/`articolo`/`costo`/...) o heuristica
    price-parseable (≥80% righe EUR-parseable per il prezzo,
    avg-len ≥4 char per la descrizione). Le colonne riconosciute
    vengono rinominate internamente a `descrizione`/`prezzo`.
    Vincolo invariato: 2 colonne separate (no concatenazione).

    Colonne opzionali con default (sempre per nome canonico):
    - `v_tot`: 0
    - `s_comp`: 0
    - `category_node`: None
    """
    df = df.rename(columns=lambda c: str(c).strip().lower() if c is not None else c)
    desc_col, prezzo_col = _detect_columns(df)
    rename_map: dict[str, str] = {}
    if desc_col != "descrizione":
        rename_map[desc_col] = "descrizione"
    if prezzo_col != "prezzo":
        rename_map[prezzo_col] = "prezzo"
    if rename_map:
        df = df.rename(columns=rename_map)

    rows: list[DescrizionePrezzoRow] = []
    warnings: list[str] = []

    for idx, raw in df.iterrows():
        try:
            descrizione = str(raw["descrizione"]).strip()
            prezzo_raw = raw["prezzo"]
            prezzo = _coerce_prezzo(prezzo_raw)
        except (ValueError, TypeError, ArithmeticError) as exc:
            warnings.append(f"Riga {idx}: parse fallito ({exc!s})")
            continue

        if not descrizione:
            warnings.append(f"Riga {idx}: descrizione vuota, skippata")
            continue
        if prezzo is None or prezzo <= 0:
            warnings.append(f"Riga {idx}: prezzo invalido ({prezzo}), skippata")
            continue

        v_tot = (
            int(raw["v_tot"])
            if "v_tot" in df.columns and _is_finite(raw["v_tot"])
            else DEFAULT_V_TOT
        )
        s_comp = (
            int(raw["s_comp"])
            if "s_comp" in df.columns and _is_finite(raw["s_comp"])
            else DEFAULT_S_COMP
        )
        category_node = (
            str(raw["category_node"]).strip()
            if "category_node" in df.columns and _is_finite(raw["category_node"])
            else None
        )
        rows.append(
            DescrizionePrezzoRow(
                descrizione=descrizione,
                prezzo_eur=prezzo,
                v_tot=v_tot,
                s_comp=s_comp,
                category_node=category_node or None,
            ),
        )

    return rows, warnings


def _coerce_prezzo(value: object) -> Decimal | None:
    """Convert prezzo single-cell a Decimal con fallback su `parse_eur`.

    CHG-2026-05-02-023: coerente con `_column_price_parseable_ratio`
    (detect oracle). Numeri nativi → Decimal diretto. Stringhe → prima
    Decimal diretto (fast path per "549.00"), poi `parse_eur` (formato
    italiano/anglo "€ 549,99"). `None` se non parsabile.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (ValueError, ArithmeticError):
        return parse_eur(text)


def _is_finite(value: object) -> bool:
    """`True` se il valore e' non-NaN/None (helper pandas-friendly)."""
    if value is None:
        return False
    try:
        # pandas NaN: float('nan') != float('nan')
        return value == value  # noqa: PLR0124 — NaN check
    except Exception:  # noqa: BLE001
        return True


@dataclass(frozen=True)
class _LiveLookupSnapshot:
    """Snapshot live `lookup_product` per cache hit (CHG-2026-05-02-036).

    Estende `_fetch_buybox_live_or_none` da 3-tuple a struct named.
    Campi: tutti `None` se `lookup_callable=None` o lookup failed.
    """

    buybox_eur: Decimal | None = None
    bsr_root: int | None = None
    drops_30: int | None = None
    buy_box_avg90: Decimal | None = None
    amazon_buybox_share: float | None = None
    notes: tuple[str, ...] = ()


def _fetch_buybox_live_or_none(
    lookup_callable: Callable[[str], ProductData] | None,
    asin: str,
) -> _LiveLookupSnapshot:
    """Recupera snapshot live tramite `lookup_callable` (Keepa via lookup_product).

    CHG-2026-05-01-039 (buybox live cache hit) + CHG-2026-05-02-003
    (bsr_root) + CHG-2026-05-02-036 (drops_30/avg90/amazon_share).
    Helper isolato per garantire che i 5 campi live siano fresh anche
    su cache hit (la mappatura desc→ASIN è invariante, gli altri no).
    Errori (KeepaMiss / RateLimit / Transient / Selector*) → snapshot
    vuoto + nota (R-01 UX-side: row esposta in tabella con nota esplicita).
    """
    if lookup_callable is None:
        return _LiveLookupSnapshot()
    try:
        product = lookup_callable(asin)
    except Exception as exc:  # noqa: BLE001 — Keepa* / Selector* / network: tutti -> note
        return _LiveLookupSnapshot(
            notes=(f"buybox lookup live failed: {type(exc).__name__}",),
        )
    # CHG-2026-05-02-037 hotfix: defensive `getattr` per tolleranza a
    # `ProductData` cached da Streamlit (`@st.cache_data` può servire
    # oggetti pre-CHG-035 senza i 3 nuovi attributi). Default None mantiene
    # il filtro pull-only graceful.
    return _LiveLookupSnapshot(
        buybox_eur=getattr(product, "buybox_eur", None),
        bsr_root=getattr(product, "bsr", None),
        drops_30=getattr(product, "drops_30", None),
        buy_box_avg90=getattr(product, "buy_box_avg90", None),
        amazon_buybox_share=getattr(product, "amazon_buybox_share", None),
    )


def resolve_listino_with_cache(
    rows: list[DescrizionePrezzoRow],
    *,
    factory: sessionmaker[Session] | None,
    resolver_provider: Callable[[], AsinResolverProtocol],
    tenant_id: int = 1,
    lookup_callable: Callable[[str], ProductData] | None = None,
) -> list[ResolvedRow]:
    """Risolve ogni riga consultando prima la cache `description_resolutions`.

    Pattern:
    1. Hash della descrizione normalizzata (`compute_description_hash`).
    2. `find_resolution_by_hash` -> hit ⇒ riusa cached asin/confidence
       (no chiamata SERP, no scraping). Se `lookup_callable` fornito,
       chiama Keepa live per il Buy Box (CHG-2026-05-01-039: cache hit
       NON annulla la verifica prezzo, che è il dato volatile).
    3. Miss ⇒ `resolver_provider()` lazy-init + `resolve_description`
       + `upsert_resolution` per cache write.
    4. Errori del resolver per riga -> `notes` annotato + ResolvedRow
       con `asin=""` (R-01 UX-side: row esposta in tabella).

    `factory=None` (DB non disponibile) -> bypass cache, sempre resolve
    (no upsert). Pattern coerente con `get_session_factory_or_none`.

    `lookup_callable=None` -> retro-compat: cache hit ritorna
    `verified_buybox_eur=None` (comportamento pre-CHG-039, fallback a
    prezzo_eur in `build_listino_raw_from_resolved`). Test mock-only
    e CLI tools possono ometterlo.
    """
    out: list[ResolvedRow] = []
    resolver_instance: AsinResolverProtocol | None = None

    for row in rows:
        try:
            description_hash = compute_description_hash(row.descrizione)
        except ValueError:
            out.append(_unresolved_row(row, ("descrizione vuota dopo normalizzazione",)))
            continue

        cached_asin: str | None = None
        cached_confidence: float | None = None
        if factory is not None:
            with factory() as db_session:
                cached = find_resolution_by_hash(
                    db_session,
                    tenant_id=tenant_id,
                    description_hash=description_hash,
                )
                if cached is not None:
                    cached_asin = cached.asin.strip()
                    cached_confidence = float(cached.confidence_pct)
                    _emit_cache_hit(table=_CACHE_TABLE_DESCRIPTION_RESOLUTIONS)
                else:
                    _emit_cache_miss(table=_CACHE_TABLE_DESCRIPTION_RESOLUTIONS)

        if cached_asin is not None and cached_confidence is not None:
            snap = _fetch_buybox_live_or_none(lookup_callable, cached_asin)
            out.append(
                ResolvedRow(
                    descrizione=row.descrizione,
                    prezzo_eur=row.prezzo_eur,
                    asin=cached_asin,
                    confidence_pct=cached_confidence,
                    is_ambiguous=cached_confidence < DEFAULT_AMBIGUOUS_THRESHOLD_PCT,
                    is_cache_hit=True,
                    v_tot=row.v_tot,
                    s_comp=row.s_comp,
                    category_node=row.category_node,
                    notes=snap.notes,
                    # CHG-2026-05-01-039: buybox live anche su cache hit.
                    verified_buybox_eur=snap.buybox_eur,
                    # CHG-2026-05-02-003: BSR per stima v_tot.
                    bsr_root=snap.bsr_root,
                    # CHG-2026-05-02-036: 3 campi ancillari Arsenale.
                    drops_30=snap.drops_30,
                    buy_box_avg90=snap.buy_box_avg90,
                    amazon_buybox_share=snap.amazon_buybox_share,
                ),
            )
            continue

        # Cache miss: resolve live + upsert post.
        if resolver_instance is None:
            resolver_instance = resolver_provider()

        try:
            result = resolver_instance.resolve_description(row.descrizione, row.prezzo_eur)
        except (ValueError, RuntimeError) as exc:
            out.append(_unresolved_row(row, (f"resolve failed: {type(exc).__name__}: {exc}",)))
            continue

        out.append(_resolved_row_from_result(row, result, is_cache_hit=False))

        # Upsert cache: solo se selected non None e factory disponibile.
        if factory is not None and result.selected is not None:
            with factory() as db_session, db_session.begin():
                upsert_resolution(
                    db_session,
                    tenant_id=tenant_id,
                    description_hash=description_hash,
                    asin=result.selected.asin,
                    confidence_pct=Decimal(str(round(result.selected.confidence_pct, 2))),
                )

    return out


def _resolved_row_from_result(
    row: DescrizionePrezzoRow,
    result: ResolutionResult,
    *,
    is_cache_hit: bool,
) -> ResolvedRow:
    if result.selected is None:
        return ResolvedRow(
            descrizione=row.descrizione,
            prezzo_eur=row.prezzo_eur,
            asin="",
            confidence_pct=0.0,
            is_ambiguous=True,
            is_cache_hit=is_cache_hit,
            v_tot=row.v_tot,
            s_comp=row.s_comp,
            category_node=row.category_node,
            notes=result.notes,
            verified_buybox_eur=None,
            candidates=result.candidates,
        )
    return ResolvedRow(
        descrizione=row.descrizione,
        prezzo_eur=row.prezzo_eur,
        asin=result.selected.asin,
        confidence_pct=result.selected.confidence_pct,
        is_ambiguous=result.is_ambiguous,
        is_cache_hit=is_cache_hit,
        v_tot=row.v_tot,
        s_comp=row.s_comp,
        category_node=row.category_node,
        notes=result.notes,
        verified_buybox_eur=result.selected.buybox_eur,
        candidates=result.candidates,
        # CHG-2026-05-02-003: BSR del candidato selected per stima v_tot.
        bsr_root=result.selected.bsr_root,
        # CHG-2026-05-02-036: campi ancillari Arsenale propagati dal candidato.
        drops_30=result.selected.drops_30,
        buy_box_avg90=result.selected.buy_box_avg90,
        amazon_buybox_share=result.selected.amazon_buybox_share,
    )


def _unresolved_row(row: DescrizionePrezzoRow, notes: tuple[str, ...]) -> ResolvedRow:
    return ResolvedRow(
        descrizione=row.descrizione,
        prezzo_eur=row.prezzo_eur,
        asin="",
        confidence_pct=0.0,
        is_ambiguous=True,
        is_cache_hit=False,
        v_tot=row.v_tot,
        s_comp=row.s_comp,
        category_node=row.category_node,
        notes=notes,
        verified_buybox_eur=None,
    )


def build_listino_raw_from_resolved(
    resolved_rows: list[ResolvedRow],
    *,
    referral_fee_pct: float = DEFAULT_REFERRAL_FEE_PCT,
    match_status: str = DEFAULT_MATCH_STATUS,
) -> pd.DataFrame:
    """Costruisce DataFrame `listino_raw` 7-col da ResolvedRow[].

    Schema output coerente con `REQUIRED_INPUT_COLUMNS` (CHG-039):
    `asin`, `buy_box_eur`, `cost_eur`, `referral_fee_pct`, `v_tot`,
    `s_comp`, `match_status`. Opzionale `category_node` se almeno
    una riga ha valore.

    Defaults applicati per MVP UI (decisione delta=A round 4 +
    estensione CHG-2026-05-01-022):
    - `buy_box_eur` = `verified_buybox_eur` (Keepa NEW live) se
      disponibile, altrimenti fallback a `prezzo_eur` del CFO.
      Estensione CHG-022 separa il prezzo Amazon (vendita) dal
      costo fornitore (acquisto): ROI/VGP più accurati senza
      richiedere al CFO di compilare due colonne.
    - `cost_eur` = `prezzo_eur` (sempre il prezzo fornitore CFO).
    - `referral_fee_pct = 0.08` default (frazione decimale in [0, 1],
      0.08 = 8%; override CFO via slider futuro).
    - `match_status = SICURO` (no NLP filter applicato).

    Cache hit (`description_resolutions`) -> CHG-2026-05-01-039:
    `verified_buybox_eur` ora è valorizzato live anche su cache hit
    (1 lookup Keepa per ASIN cached, ~1 token). La cache mappa solo
    desc→ASIN (invariante); il Buy Box è volatile e va sempre verificato.
    Solo se `lookup_callable=None` (test/CLI senza Keepa) o se Keepa
    fallisce su quel candidato, il fallback a `prezzo_eur` viene usato.

    Righe non risolte (`asin=""`) vengono SKIPPATE: il listino
    finale contiene solo ASIN validi. Le righe ambigue ma con
    asin valorizzato vengono incluse (CFO ha visto il warning UI).
    """
    import pandas as pd  # noqa: PLC0415 — lazy import per non penalizzare boot test puri senza pandas

    valid_rows = [r for r in resolved_rows if r.asin]
    if not valid_rows:
        return pd.DataFrame(
            columns=[
                "asin",
                "buy_box_eur",
                "cost_eur",
                "referral_fee_pct",
                "v_tot",
                "s_comp",
                "match_status",
            ],
        )

    has_category_node = any(r.category_node for r in valid_rows)

    records: list[dict[str, object]] = []
    for r in valid_rows:
        # Buy Box reale (Keepa NEW) se il resolver l'ha verificato live;
        # altrimenti fallback al prezzo fornitore (semantica CHG-020).
        buy_box = (
            float(r.verified_buybox_eur)
            if r.verified_buybox_eur is not None
            else float(r.prezzo_eur)
        )
        # CHG-2026-05-02-003: hybrid v_tot resolution
        # CSV override (>0) > BSR estimate MVP > 0 default.
        # Sblocca MVP CFO Path B': listino con CSV minimal (solo
        # descrizione+prezzo) ottiene v_tot stimato dal BSR Keepa
        # invece di 0 (che azzerava qty_final e svuotava il cart).
        # CHG-2026-05-02-036: drops_30 promosso a fonte preferita (errata
        # ADR-0018, CHG-034). Pull-only: None → fallback BSR placeholder.
        # CHG-2026-05-02-038 hotfix: defensive try/except per tolleranza a
        # `velocity_estimator.resolve_v_tot` legacy (Streamlit hot-reload
        # module skew: listino_input.py reloaded ma velocity_estimator.py no).
        try:
            v_tot_resolved, v_tot_source = resolve_v_tot(
                csv_v_tot=r.v_tot,
                bsr_root=r.bsr_root,
                drops_30=r.drops_30,
            )
        except TypeError:
            # Legacy resolve_v_tot senza kwarg drops_30 (pre-CHG-034).
            v_tot_resolved, v_tot_source = resolve_v_tot(
                csv_v_tot=r.v_tot,
                bsr_root=r.bsr_root,
            )
        # CHG-2026-05-02-005: telemetria evento canonico ADR-0021 (errata).
        # Emit solo quando la stima viene effettivamente da BSR (audit
        # aggregato CFO: quanti ASIN hanno v_tot stimato vs override CSV).
        if v_tot_source == V_TOT_SOURCE_BSR_ESTIMATE:
            _logger.debug(
                "v_tot.estimated_from_bsr",
                asin=r.asin,
                bsr=r.bsr_root,
                v_tot_estimated=v_tot_resolved,
            )
        record: dict[str, object] = {
            "asin": r.asin,
            "buy_box_eur": buy_box,
            "cost_eur": float(r.prezzo_eur),
            "referral_fee_pct": referral_fee_pct,
            "v_tot": v_tot_resolved,
            "v_tot_source": v_tot_source,
            "s_comp": r.s_comp,
            "match_status": match_status,
            # CHG-2026-05-02-036: 3 colonne Arsenale per filtri pull-only
            # in `compute_vgp_score` (CHG-031/032). None se Keepa lookup
            # fail / cache hit senza lookup_callable / KeepaProduct miss.
            "buy_box_avg90": (float(r.buy_box_avg90) if r.buy_box_avg90 is not None else None),
            "amazon_buybox_share": r.amazon_buybox_share,
            "drops_30": r.drops_30,
        }
        if has_category_node:
            record["category_node"] = r.category_node or ""
        records.append(record)
    return pd.DataFrame(records)


def apply_candidate_overrides(
    resolved: list[ResolvedRow],
    overrides: dict[int, str],
) -> list[ResolvedRow]:
    """Applica override manuali del CFO su righe ambigue (CHG-023).

    `overrides` mappa `idx_riga -> asin_scelto_dal_CFO`. Per ogni
    `(idx, chosen_asin)` valido (idx in range, chosen_asin presente in
    `resolved[idx].candidates`), sostituisce `asin/confidence_pct/
    is_ambiguous/verified_buybox_eur` della riga con quelli del candidato
    scelto. Aggiunge nota R-01 audit trail
    `"override manuale CFO: {chosen} (era {original})"`.

    Override invalidi (idx out-of-range, asin non in candidates,
    chosen == current asin) sono no-op silenziosi: l'override ridondante
    non è un errore del CFO. Pattern coerente con `replay_session`
    `locked_in_override` (CHG-056).

    R-01 NO SILENT DROPS: nessuna riga rimossa; nota di audit esplicita
    per ogni override applicato.
    """
    out: list[ResolvedRow] = []
    for idx, row in enumerate(resolved):
        chosen_asin = overrides.get(idx)
        if chosen_asin is None or chosen_asin == row.asin:
            out.append(row)
            continue
        match = next((c for c in row.candidates if c.asin == chosen_asin), None)
        if match is None:
            out.append(row)
            continue
        original_asin = row.asin
        out.append(
            replace(
                row,
                asin=match.asin,
                confidence_pct=match.confidence_pct,
                is_ambiguous=_is_ambiguous_threshold(match.confidence_pct),
                verified_buybox_eur=match.buybox_eur,
                # CHG-2026-05-02-003: propaga BSR del candidato override
                # per coerenza stima v_tot post-override CFO.
                bsr_root=match.bsr_root,
                # CHG-2026-05-02-036: propaga 3 campi ancillari Arsenale
                # del candidato override per coerenza filtri downstream.
                drops_30=match.drops_30,
                buy_box_avg90=match.buy_box_avg90,
                amazon_buybox_share=match.amazon_buybox_share,
                notes=(
                    *row.notes,
                    f"override manuale CFO: {match.asin} (era {original_asin or '(nessuno)'})",
                ),
            ),
        )
    return out


def count_eligible_for_overrides(resolved: list[ResolvedRow]) -> int:
    """Count righe del listino eligible per override candidato manuale (CHG-023).

    Una riga è eligible se è **ambigua** (`is_ambiguous=True`) AND ha un
    **ASIN risolto** (`asin` non vuoto) AND ha **più di un candidato**
    nel resolver (`len(candidates) > 1`). Le righe con 1 solo candidato
    o cache hit (candidates vuota) non sono interattive.

    Helper puro: condivisa fra `_render_ambiguous_candidate_overrides`
    (Streamlit-side, render selectbox) e i caller telemetria
    (`dashboard.py` per `_emit_ui_override_applied.n_eligible`).
    Single source of truth per la condizione di eligibilità.
    """
    return sum(1 for r in resolved if r.is_ambiguous and r.asin and len(r.candidates) > 1)


def count_resolved(resolved: list[ResolvedRow]) -> int:
    """Count righe risolte (ASIN truthy) — pattern simmetrico a `count_*` family.

    Helper puro single source of truth: una riga è "risolta" se
    `r.asin` è truthy (string non vuota). Cache hit + miss con
    selected != None → asin popolato. Resolver fail / cache miss
    senza candidato → `asin=""` (R-01 UX-side: row visibile ma
    non risolta). Pattern coerente con `n_resolved` inline storicamente
    usato in `dashboard.py` (CHG-2026-05-01-029 chiude duplicazione).
    """
    return sum(1 for r in resolved if r.asin)


def count_cache_hit(resolved: list[ResolvedRow]) -> int:
    """Count righe con `is_cache_hit=True` — usato anche da `format_cache_hit_caption`.

    Helper puro: aggregazione del flag `ResolvedRow.is_cache_hit`
    (CHG-019). Cache disabilitata (`factory=None`) → `is_cache_hit=False`
    sempre, count = 0. Pattern coerente con telemetria `cache.hit`
    di CHG-025 (count aggregato lato UI vs eventi individuali lato
    consumer).
    """
    return sum(1 for r in resolved if r.is_cache_hit)


def format_v_tot_source_caption(df: pd.DataFrame) -> str:
    """Format caption per distribuzione fonte V_tot (CHG-2026-05-02-006).

    Helper puro testabile: aggrega `v_tot_source` da listino_raw output
    di `build_listino_raw_from_resolved` in caption per CFO. Trasparenza
    audit: il CFO capisce se i numeri vendite mensili vengono dal suo
    CSV (override esplicito) o dalla stima MVP placeholder da BSR.

    Lista vuota o colonna mancante -> stringa vuota (caller suppress).
    """
    if df.empty or "v_tot_source" not in df.columns:
        return ""
    counts = df["v_tot_source"].value_counts().to_dict()
    n_csv = int(counts.get("csv", 0))
    n_bsr = int(counts.get("bsr_estimate_mvp", 0))
    n_zero = int(counts.get("default_zero", 0))
    n_total = n_csv + n_bsr + n_zero
    if n_total == 0:
        return ""
    parts: list[str] = []
    if n_csv:
        parts.append(f"{n_csv} da CSV")
    if n_bsr:
        parts.append(f"{n_bsr} stimati da BSR (MVP placeholder)")
    if n_zero:
        parts.append(f"{n_zero} default zero (no BSR)")
    return f"V_tot sources ({n_total} ASIN): " + ", ".join(parts) + "."


def count_with_verified_buybox(resolved: list[ResolvedRow]) -> int:
    """Count righe con `verified_buybox_eur is not None` (Buy Box live CHG-022).

    Helper puro: aggregazione del flag `ResolvedRow.verified_buybox_eur`.
    Cache hit (CHG-022 dec. 2) o lookup fail → `None` → fallback a
    `prezzo_eur` per VGP/ROI. Una riga con buybox verificato indica
    ROI accurato (Amazon NEW reale invece del costo fornitore).
    Usato anche da `format_buybox_verified_caption`.
    """
    return sum(1 for r in resolved if r.verified_buybox_eur is not None)


def format_buybox_verified_caption(resolved: list[ResolvedRow]) -> str:
    """Caption UX rate Buy Box verificato live nel flow CFO.

    Frontend-only: aggrega `ResolvedRow.verified_buybox_eur is not None`
    su tutto il listino risolto. Espone immediatamente al CFO l'accuratezza
    del ROI calcolato downstream (Buy Box reale Amazon NEW vs fallback
    `prezzo_eur` fornitore — CHG-2026-05-01-022).

    Format: ``"Buy Box verificato: {verified}/{total} righe ({pct:.0f}%)."``
    Helper puro testabile mock-only.

    >>> format_buybox_verified_caption([])
    ''
    >>> # Casi coperti da `tests/unit/test_listino_input.py`.

    Lista vuota → stringa vuota (caller suppress dal caption finale).
    """
    if not resolved:
        return ""
    n_total = len(resolved)
    n_verified = count_with_verified_buybox(resolved)
    pct = n_verified / n_total * 100
    return f"Buy Box verificato: {n_verified}/{n_total} righe ({pct:.0f}%)."


def format_cache_hit_caption(resolved: list[ResolvedRow]) -> str:
    """Caption UX hit rate cache `description_resolutions` per il flow CFO.

    Frontend-only: aggrega `ResolvedRow.is_cache_hit` su tutto il listino
    risolto. Espone immediatamente al CFO l'efficacia della cache senza
    aspettare consumo telemetria a valle (CHG-2026-05-01-025).

    Format: ``"Cache: {hits}/{total} hit ({pct:.0f}%)."`` Helper puro
    testabile mock-only.

    >>> format_cache_hit_caption([])
    ''
    >>> # Hit/miss casi coperti da `tests/unit/test_listino_input.py`.

    Lista vuota → stringa vuota (caller suppress dal caption finale).
    """
    if not resolved:
        return ""
    n_total = len(resolved)
    n_hits = count_cache_hit(resolved)
    pct = n_hits / n_total * 100
    return f"Cache: {n_hits}/{n_total} hit ({pct:.0f}%)."


def format_confidence_badge(confidence_pct: float) -> str:
    """Stringa visiva per UI: simbolo + numero (R-01 UX visibility).

    Soglie:
    - >= 85: ✅ alto (verde)
    - 70-85: ⚠️ medio (giallo, sopra threshold ambiguo ma non eccezionale)
    - < 70: ❌ ambiguo (rosso, sotto threshold default)

    Range compreso 0-100. Out-of-range -> stringa fallback.
    """
    if not _CONFIDENCE_PCT_MIN <= confidence_pct <= _CONFIDENCE_PCT_MAX:
        return f"? {confidence_pct:.1f}%"
    if confidence_pct >= _CONFIDENCE_HIGH_THRESHOLD_PCT:
        return f"OK {confidence_pct:.1f}%"
    if confidence_pct >= _CONFIDENCE_MEDIUM_THRESHOLD_PCT:
        return f"DUB {confidence_pct:.1f}%"
    return f"AMB {confidence_pct:.1f}%"
