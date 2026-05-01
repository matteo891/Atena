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


def parse_descrizione_prezzo_csv(
    df: pd.DataFrame,
) -> tuple[list[DescrizionePrezzoRow], list[str]]:
    """Valida e converte un DataFrame raw in lista `DescrizionePrezzoRow`.

    Ritorna `(rows, warnings)`. Le righe non parsabili vengono
    skippate con warning esplicito (R-01 UX-side: l'utente sa cosa
    e' stato escluso). Solleva `ValueError` se mancano colonne
    obbligatorie.

    Colonne opzionali con default:
    - `v_tot`: 0
    - `s_comp`: 0
    - `category_node`: None
    """
    missing = [c for c in REQUIRED_DESCRIZIONE_PREZZO_COLUMNS if c not in df.columns]
    if missing:
        msg = (
            f"CSV non valido: colonne mancanti {missing}. "
            f"Attese: {list(REQUIRED_DESCRIZIONE_PREZZO_COLUMNS)}."
        )
        raise ValueError(msg)

    rows: list[DescrizionePrezzoRow] = []
    warnings: list[str] = []

    for idx, raw in df.iterrows():
        try:
            descrizione = str(raw["descrizione"]).strip()
            prezzo_raw = raw["prezzo"]
            prezzo = Decimal(str(prezzo_raw)) if prezzo_raw is not None else None
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


def _is_finite(value: object) -> bool:
    """`True` se il valore e' non-NaN/None (helper pandas-friendly)."""
    if value is None:
        return False
    try:
        # pandas NaN: float('nan') != float('nan')
        return value == value  # noqa: PLR0124 — NaN check
    except Exception:  # noqa: BLE001
        return True


def resolve_listino_with_cache(
    rows: list[DescrizionePrezzoRow],
    *,
    factory: sessionmaker[Session] | None,
    resolver_provider: Callable[[], AsinResolverProtocol],
    tenant_id: int = 1,
) -> list[ResolvedRow]:
    """Risolve ogni riga consultando prima la cache `description_resolutions`.

    Pattern:
    1. Hash della descrizione normalizzata (`compute_description_hash`).
    2. `find_resolution_by_hash` -> hit ⇒ usa cached asin/confidence
       (no chiamata SERP/Keepa, no quota consumata).
    3. Miss ⇒ `resolver_provider()` lazy-init + `resolve_description`
       + `upsert_resolution` per cache write.
    4. Errori del resolver per riga -> `notes` annotato + ResolvedRow
       con `asin=""` (R-01 UX-side: row esposta in tabella).

    `factory=None` (DB non disponibile) -> bypass cache, sempre resolve
    (no upsert). Pattern coerente con `get_session_factory_or_none`.
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
                    notes=(),
                    # Cache `description_resolutions` salva solo asin+confidence,
                    # non il Buy Box (varia col tempo). Cache hit -> None ->
                    # `build_listino_raw_from_resolved` fa fallback a prezzo_eur.
                    verified_buybox_eur=None,
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

    Cache hit (`description_resolutions`) -> `verified_buybox_eur=None`
    -> fallback a `prezzo_eur`: la cache non salva il buybox, che
    varia col tempo. Per re-acquisire il buybox reale, il CFO
    deve invalidare la cache (scope futuro: cache TTL).

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
        record: dict[str, object] = {
            "asin": r.asin,
            "buy_box_eur": buy_box,
            "cost_eur": float(r.prezzo_eur),
            "referral_fee_pct": referral_fee_pct,
            "v_tot": r.v_tot,
            "s_comp": r.s_comp,
            "match_status": match_status,
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
