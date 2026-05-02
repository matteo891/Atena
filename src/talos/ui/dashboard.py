"""Dashboard Streamlit MVP (ADR-0016) - mono-page CHG-2026-04-30-040.

Entrypoint: `uv run streamlit run src/talos/ui/dashboard.py`.

Layout MVP (single page):
- Sidebar parametri sessione (budget, velocity_target, veto_threshold, lot_size).
- Main: file upload listino CSV + input ASIN locked-in + bottone "Esegui sessione".
- Output: metric (saturazione + budget T+1) + tabelle Cart, Panchina, enriched_df.

Helper testabili (non Streamlit-dipendenti) sono esportati per unit test:
- `parse_locked_in(raw)`: parser comma-separated con strip + filter empty.
- `DEFAULT_BUDGET_EUR`: default UI per il budget di sessione.

Refactor multi-page ADR-0016 compliant (`pages/`, `components/`,
`state.py`) e' scope di CHG successivi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
import streamlit as st
import structlog

from talos.formulas import (
    DEFAULT_LOT_SIZE,
    DEFAULT_VELOCITY_TARGET_DAYS,
)
from talos.observability import (
    bind_request_context,
    bind_session_context,
    clear_request_context,
    is_request_context_bound,
)
from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, replay_session, run_session
from talos.persistence import (
    KEY_REFERRAL_FEE_PCT,
    SCOPE_CATEGORY,
    LoadedSession,
    SessionSummary,
    create_app_engine,
    delete_config_override,
    find_session_by_hash,
    get_config_override_numeric,
    list_category_referral_fees,
    list_recent_sessions,
    load_session_by_id,
    load_session_full,
    make_session_factory,
    save_session_result,
    session_scope,
    set_config_override_numeric,
)
from talos.persistence.session_repository import _listino_hash
from talos.tetris import InsufficientBudgetError
from talos.vgp import DEFAULT_ROI_VETO_THRESHOLD

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

    from talos.orchestrator import SessionResult
    from talos.ui.listino_input import ResolvedRow


# Default budget UI (10k EUR) - modificabile dall'utente.
DEFAULT_BUDGET_EUR: float = 10_000.0
# Tenant default per persistenza (MVP single-tenant, ADR-0015).
DEFAULT_TENANT_ID: int = 1
# Chiave config override per soglia ROI (CHG-050).
CONFIG_KEY_VETO_ROI: str = "veto_roi_pct"

_logger = structlog.get_logger(__name__)


# CHG-2026-05-01-040: colonne semanticamente "frazione decimale" che la UI
# rende come percentuale (1 decimale) tramite Streamlit `column_config`. La
# pipeline interna mantiene frazione (zero blast radius su formule/test/DB).
# `confidence_pct` NON è qui: è già 0-100 (compute_confidence) ed è renderizzato
# come badge stringa via format_confidence_badge.
_PERCENTAGE_COLUMNS: frozenset[str] = frozenset(
    {
        "roi",
        "vgp_score",
        "vgp_score_raw",
        "roi_norm",
        "velocity_norm",
        "cash_profit_norm",
        "referral_fee_pct",
        "referral_fee_resolved",
        "fee_pct",  # tabella sidebar referral fee per categoria
    },
)


def _pct_column_config(
    columns: pd.Index | list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """Build column_config per colonne percentage (printf-style format).

    CHG-2026-05-02-002 fix: Streamlit 1.57 `NumberColumn.format` accetta
    SOLO printf-style (sprintf-js) o preset stringa, NON d3-format. Il
    valore numerico atteso e' gia' moltiplicato x100 (vedi
    `_percentage_view`). Format `"%.1f%%"` -> "22.5%".
    """
    return {
        col: st.column_config.NumberColumn(format="%.1f%%")
        for col in columns
        if col in _PERCENTAGE_COLUMNS
    }


def _percentage_view(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Ritorna (df_display, column_config) per rendering con `st.dataframe`.

    CHG-2026-05-02-002: pre-moltiplica x100 le colonne percentage perche'
    Streamlit 1.57 `NumberColumn.format` NON supporta d3-format auto-x100.
    Il df originale resta intatto (copy-on-write); display layer ha
    valori in [0, 100] + format printf `"%.1f%%"`. Se il df non ha
    colonne percentage, ritorna l'originale senza copy (no-op).
    """
    pct_cols = [c for c in df.columns if c in _PERCENTAGE_COLUMNS]
    if not pct_cols:
        return df, {}
    df_display = df.copy()
    for col in pct_cols:
        df_display[col] = df_display[col].astype(float) * 100.0
    return df_display, _pct_column_config(pct_cols)


def _emit_ui_resolve_started(*, n_rows: int, has_factory: bool) -> None:
    """Emette evento canonico `ui.resolve_started` (catalogo ADR-0021).

    Helper puro: testabile via caplog senza dipendenza da Streamlit.
    Tracking quote SERP/Keepa pre-resolve nel flow descrizione+prezzo.
    """
    _logger.debug(
        "ui.resolve_started",
        n_rows=n_rows,
        has_factory=has_factory,
    )


def _emit_ui_resolve_confirmed(
    *,
    n_total: int,
    n_resolved: int,
    n_ambiguous: int,
) -> None:
    """Emette evento canonico `ui.resolve_confirmed` (catalogo ADR-0021).

    Helper puro: testabile via caplog senza dipendenza da Streamlit.
    Tracking conversion rate listino umano → run_session.
    """
    _logger.debug(
        "ui.resolve_confirmed",
        n_total=n_total,
        n_resolved=n_resolved,
        n_ambiguous=n_ambiguous,
    )


def _emit_ui_override_applied(*, n_overrides: int, n_eligible: int) -> None:
    """Emette evento canonico `ui.override_applied` (catalogo ADR-0021).

    Helper puro: testabile via caplog senza dipendenza da Streamlit.
    Tracking adoption rate dell'override CFO sul flow descrizione+prezzo
    (A3 hardening CHG-023): `n_overrides / n_eligible` = % righe ambigue
    su cui il CFO ha cambiato il top-1 automatico del resolver.
    """
    _logger.debug(
        "ui.override_applied",
        n_overrides=n_overrides,
        n_eligible=n_eligible,
    )


def _emit_ui_resolve_failed(*, reason: str, n_rows: int) -> None:
    """Emette evento canonico `ui.resolve_failed` (catalogo ADR-0021).

    Helper puro: testabile via caplog senza dipendenza da Streamlit.
    Tracking fail mode pre-resolve. `reason` è enum-string aperto:
    `"keepa_key_missing"` (oggi unico path), `"exception"` (futuro).
    """
    _logger.debug(
        "ui.resolve_failed",
        reason=reason,
        n_rows=n_rows,
    )


def get_session_factory_or_none() -> sessionmaker[Session] | None:
    """Prova a creare un session factory ORM dal config (`TALOS_DB_URL`).

    Ritorna `None` se la URL non e' settata o se la creazione dell'engine
    fallisce per qualunque motivo. La dashboard usa il factory per persistere
    `SessionResult` su click bottone; senza factory la persistenza e'
    disabilitata gracefully (nessun crash UI).
    """
    try:
        engine = create_app_engine()
    except (RuntimeError, ValueError, Exception):  # noqa: BLE001 - dashboard graceful degrade
        return None
    return make_session_factory(engine)


def try_persist_session(
    factory: sessionmaker[Session],
    *,
    session_input: SessionInput,
    result: SessionResult,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[bool, int | None, str | None]:
    """Persiste il `SessionResult` via `save_session_result` con error handling.

    Post-save (success path): chiama `bind_session_context` per
    arricchire il context con `session_id` + `listino_hash` reali
    (CHG-2026-05-01-036, B1.3). Eventuali emit successivi nello stesso
    rerun Streamlit ereditano i metadati di sessione.

    :returns: tupla `(success, session_id, error_message)`. Esattamente uno
        tra `session_id` ed `error_message` e' `None`.
    """
    try:
        with session_scope(factory) as db_session:
            sid = save_session_result(
                db_session,
                session_input=session_input,
                result=result,
                tenant_id=tenant_id,
            )
    except Exception as exc:  # noqa: BLE001 - graceful UI feedback
        return False, None, str(exc)
    # Post-save: bind session context per arricchire eventi successivi.
    bind_session_context(
        session_id=sid,
        listino_hash=_listino_hash(session_input.listino_raw),
        velocity_target=session_input.velocity_target_days,
        budget_eur=session_input.budget,
    )
    # CHG-2026-05-02-010: telemetry session.persisted per audit aggregato.
    _logger.debug(
        "session.persisted",
        session_id=sid,
        n_cart_items=len(result.cart.items),
        n_panchina_items=len(result.panchina),
    )
    return True, sid, None


def parse_locked_in(raw: str) -> list[str]:
    """Parser ASIN locked-in da stringa comma-separated.

    >>> parse_locked_in("AAA, BBB,CCC")
    ['AAA', 'BBB', 'CCC']
    >>> parse_locked_in("")
    []
    >>> parse_locked_in(",,,A,, B, ")
    ['A', 'B']
    """
    return [a.strip() for a in raw.split(",") if a.strip()]


def _render_sidebar(  # noqa: C901, PLR0912 — UI orchestrator, complessità accettabile
    factory: sessionmaker[Session] | None = None,
) -> tuple[float, int, float, int]:
    """Sidebar: parametri sessione configurabili dal CFO.

    Se `factory` e' disponibile, la soglia veto ROI viene pre-caricata da
    `config_overrides` (override persistente per tenant — CHG-050).
    Bottone "Salva default tenant" per persistere la soglia corrente.

    Returns: (budget, velocity_target_days, veto_roi_threshold, lot_size).
    """
    st.sidebar.header("Parametri Sessione")
    budget = st.sidebar.number_input(
        "Budget di Sessione (EUR)",
        min_value=100.0,
        value=DEFAULT_BUDGET_EUR,
        step=500.0,
        format="%.2f",
    )
    velocity_target = st.sidebar.slider(
        "Velocity Target (giorni)",
        min_value=7,
        max_value=30,
        value=DEFAULT_VELOCITY_TARGET_DAYS,
        step=1,
        help="L05: slider 7..30 giorni, default 15. Modifica la quantita' target F4.",
    )
    # CHG-2026-05-01-040: input in percentuale (8.0 invece di 0.08), conversione
    # ÷100 prima di passare alla pipeline (che resta in frazione decimale [0, 1]).
    persisted_threshold = fetch_veto_roi_threshold_or_default(factory)
    veto_threshold_pct = st.sidebar.slider(
        "Veto ROI Minimo (%)",
        min_value=1.0,
        max_value=50.0,
        value=persisted_threshold * 100.0,
        step=0.5,
        format="%.1f%%",
        help="R-08: ASIN con ROI sotto soglia hanno vgp_score=0 (default 8.0%).",
    )
    veto_threshold = veto_threshold_pct / 100.0
    if factory is not None:
        col_save, col_reset = st.sidebar.columns(2)
        if col_save.button("Salva soglia ROI", key="save_threshold_btn"):
            ok, err = try_persist_veto_roi_threshold(factory, threshold=float(veto_threshold))
            if ok:
                st.sidebar.success("Soglia salvata.")
            else:  # pragma: no cover - UI-only error path
                st.sidebar.error(f"Salvataggio fallito: {err}")
        if col_reset.button("Reset al default", key="reset_threshold_btn"):
            ok, err = try_delete_veto_roi_threshold(factory)
            if ok:
                st.sidebar.success(
                    f"Soglia resettata al default {DEFAULT_ROI_VETO_THRESHOLD * 100:.1f}%.",
                )
            else:  # pragma: no cover - UI-only error path
                st.sidebar.error(f"Reset fallito: {err}")

    if factory is not None:
        _render_sidebar_referral_fees(factory)

    lot_size = st.sidebar.number_input(
        "Lotto fornitore",
        min_value=1,
        value=DEFAULT_LOT_SIZE,
        step=1,
        help="F5: Floor(qty_target / lot) * lot. Default Samsung MVP = 5.",
    )

    if factory is not None:
        with st.sidebar.expander("Manutenzione cache"):
            st.caption(
                "La cache `description_resolutions` mappa descrizione → ASIN. "
                "Svuotala se vuoi forzare il re-resolve live SERP+Keepa.",
            )
            # CHG-2026-05-02-014: confirm 2-step (cliccabile distruttivo).
            if st.session_state.get("cache_reset_confirm_pending"):
                st.warning("Confermi? L'operazione è irreversibile.")
                col_yes, col_no = st.columns(2)
                if col_yes.button("Sì, svuota", key="cache_reset_yes", type="primary"):
                    ok, n_deleted, err = try_clear_description_cache(factory)
                    st.session_state["cache_reset_confirm_pending"] = False
                    if ok:
                        st.toast(f"Cache svuotata: {n_deleted} righe rimosse.", icon="🧹")
                        st.success(f"Cache svuotata: {n_deleted} righe rimosse.")
                    else:
                        st.error(f"Reset fallito: {err}")  # pragma: no cover
                if col_no.button("Annulla", key="cache_reset_no"):
                    st.session_state["cache_reset_confirm_pending"] = False
                    st.rerun()
            elif st.button("Svuota cache risoluzioni", key="clear_cache_btn"):
                st.session_state["cache_reset_confirm_pending"] = True
                st.rerun()

    return float(budget), int(velocity_target), float(veto_threshold), int(lot_size)


def try_clear_description_cache(
    factory: sessionmaker[Session],
    *,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[bool, int, str | None]:
    """Svuota cache `description_resolutions` per il tenant. Ritorna (ok, n_rimosse, err)."""
    from sqlalchemy import text  # noqa: PLC0415

    try:
        with session_scope(factory) as db:
            n_before = int(
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM description_resolutions WHERE tenant_id = :tid",
                    ),
                    {"tid": tenant_id},
                ).scalar_one(),
            )
            db.execute(
                text("DELETE FROM description_resolutions WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            )
            return True, n_before, None
    except Exception as exc:  # noqa: BLE001 - UI graceful
        return False, 0, str(exc)


def _render_sidebar_referral_fees(factory: sessionmaker[Session]) -> None:
    """Sidebar section: CRUD `Referral_Fee` per categoria (L12 PROJECT-RAW Round 5).

    Form input (categoria + fee) + bottone "Salva" + lista esistenti
    (st.dataframe). Override DB-level usabili dal futuro orchestrator
    per correggere `referral_fee_pct` per riga del listino in base a
    `asin_master.category_node`.
    """
    with st.sidebar.expander("Referral Fee per categoria"):
        existing = fetch_category_referral_fees_or_empty(factory)
        if existing:
            ref_fees_df = pd.DataFrame(
                [{"category": c, "fee_pct": v} for c, v in sorted(existing.items())],
            )
            ref_fees_view, ref_fees_cfg = _percentage_view(ref_fees_df)
            st.dataframe(
                ref_fees_view,
                use_container_width=True,
                column_config=ref_fees_cfg,
            )
        else:
            st.caption("Nessun override registrato.")

        category = st.text_input("Categoria", key="ref_fee_cat_input").strip()
        # CHG-2026-05-01-040: input in percentuale (8.0%), conversion ÷100.
        fee_pct = st.number_input(
            "Fee (%)",
            min_value=0.0,
            max_value=100.0,
            value=8.0,
            step=0.1,
            format="%.1f",
            key="ref_fee_value_input",
        )
        fee = fee_pct / 100.0
        col_save, col_reset = st.columns(2)
        if col_save.button("Salva", key="save_ref_fee_btn"):
            if not category:
                st.warning("Inserisci una categoria non vuota.")
            else:
                ok, err = try_persist_category_referral_fee(
                    factory,
                    category_node=category,
                    referral_fee_pct=float(fee),
                )
                if ok:
                    st.success(f"Referral fee per `{category}` salvato.")
                else:  # pragma: no cover - UI-only
                    st.error(f"Salvataggio fallito: {err}")
        if col_reset.button("Reset", key="reset_ref_fee_btn"):
            if not category:
                st.warning("Inserisci la categoria da resettare.")
            else:
                ok, err = try_delete_category_referral_fee(
                    factory,
                    category_node=category,
                )
                if ok:
                    st.success(f"Override per `{category}` rimosso.")
                else:  # pragma: no cover - UI-only
                    st.error(f"Reset fallito: {err}")


def _render_metrics(saturation: float, budget_t1: float) -> None:
    """Metric in alto: saturazione cart + Budget T+1."""
    col1, col2 = st.columns(2)
    col1.metric("Saturazione Cart", f"{saturation:.1%}")
    col2.metric("Budget T+1 (R-07)", f"€ {budget_t1:,.2f}")


def _render_cart_table(cart_items: list[dict[str, object]]) -> None:
    """Tabella Cart (ASIN allocati) + bottone export CSV."""
    _section("4", "Cart · ASIN allocati (R-04 Locked-in + R-06 Tetris)")
    if not cart_items:
        st.markdown(
            """
            <div class="talos-empty">
              <div class="talos-empty-icon">◇ ◇ ◇</div>
              <div>Cart vuoto. Nessun ASIN allocato in questa sessione.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    cart_df = pd.DataFrame(cart_items)
    cart_view, cart_cfg = _percentage_view(cart_df)
    st.dataframe(cart_view, use_container_width=True, column_config=cart_cfg)
    st.download_button(
        "⬇ Esporta Cart (CSV)",
        data=cart_df.to_csv(index=False).encode("utf-8"),
        file_name="talos_cart.csv",
        mime="text/csv",
        key="export_cart_btn",
    )


def fetch_recent_sessions_or_empty(
    factory: sessionmaker[Session],
    *,
    limit: int = 20,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> list[dict[str, object]]:
    """Carica le sessioni recenti come list-of-dict per Streamlit dataframe.

    Ritorna lista vuota se la query fallisce per qualunque motivo
    (graceful UI: lo storico e' nice-to-have, non critico).
    """
    try:
        with session_scope(factory) as db:
            summaries = list_recent_sessions(db, limit=limit, tenant_id=tenant_id)
    except Exception:  # noqa: BLE001 - graceful UI fallback
        return []
    return [
        {
            "id": s.id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "budget_eur": float(s.budget_eur),
            "velocity_target": s.velocity_target,
            "n_cart": s.n_cart_items,
            "n_panchina": s.n_panchina_items,
            "hash": s.listino_hash[:12] + "...",
        }
        for s in summaries
    ]


def fetch_loaded_session_or_none(
    factory: sessionmaker[Session],
    session_id: int,
    *,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> LoadedSession | None:
    """Carica una sessione storica via `load_session_by_id` con error handling.

    Ritorna `None` se non esiste, tenant mismatch, o query fallisce.
    """
    try:
        with session_scope(factory) as db:
            return load_session_by_id(db, session_id, tenant_id=tenant_id)
    except Exception:  # noqa: BLE001 - graceful UI fallback
        return None


def fetch_veto_roi_threshold_or_default(
    factory: sessionmaker[Session] | None,
    *,
    tenant_id: int = DEFAULT_TENANT_ID,
    default: float = DEFAULT_ROI_VETO_THRESHOLD,
) -> float:
    """Lookup persistente della soglia veto ROI per il tenant; fallback a `default`.

    Ritorna `default` se factory e' None, query fallisce, o nessun override
    e' stato registrato. Pattern: la UI carica al boot la soglia salvata,
    ma graceful degrade se DB non disponibile.
    """
    if factory is None:
        return default
    try:
        with session_scope(factory) as db:
            value = get_config_override_numeric(
                db,
                key=CONFIG_KEY_VETO_ROI,
                tenant_id=tenant_id,
            )
    except Exception:  # noqa: BLE001 - graceful UI fallback
        return default
    return float(value) if value is not None else default


def try_persist_veto_roi_threshold(
    factory: sessionmaker[Session],
    *,
    threshold: float,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[bool, str | None]:
    """UPSERT della soglia veto ROI come override persistente per il tenant.

    :returns: tupla `(success, error_message)`.
    """
    try:
        with session_scope(factory) as db:
            set_config_override_numeric(
                db,
                key=CONFIG_KEY_VETO_ROI,
                value=threshold,
                tenant_id=tenant_id,
            )
    except Exception as exc:  # noqa: BLE001 - graceful UI feedback
        return False, str(exc)
    return True, None


def fetch_category_referral_fees_or_empty(
    factory: sessionmaker[Session] | None,
    *,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> dict[str, float]:
    """Lookup mappa `category_node → referral_fee_pct` per il tenant; graceful empty.

    Ritorna dict vuoto se factory None, query fallisce o nessun override.
    """
    if factory is None:
        return {}
    try:
        with session_scope(factory) as db:
            decimals = list_category_referral_fees(db, tenant_id=tenant_id)
    except Exception:  # noqa: BLE001 - graceful UI fallback
        return {}
    return {cat: float(v) for cat, v in decimals.items()}


def try_persist_category_referral_fee(
    factory: sessionmaker[Session],
    *,
    category_node: str,
    referral_fee_pct: float,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[bool, str | None]:
    """UPSERT del referral fee per la categoria (`scope="category"`).

    :returns: tupla `(success, error_message)`.
    """
    try:
        with session_scope(factory) as db:
            set_config_override_numeric(
                db,
                key=KEY_REFERRAL_FEE_PCT,
                value=referral_fee_pct,
                tenant_id=tenant_id,
                scope=SCOPE_CATEGORY,
                scope_key=category_node,
            )
    except Exception as exc:  # noqa: BLE001 - graceful UI feedback
        return False, str(exc)
    return True, None


def try_delete_veto_roi_threshold(
    factory: sessionmaker[Session],
    *,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[bool, str | None]:
    """Cancella l'override soglia veto ROI (reset al default applicativo).

    :returns: tupla `(success, error_message)`. `success=True` anche se
        non c'era un override (idempotenza, nessun errore mostrato al CFO).
    """
    try:
        with session_scope(factory) as db:
            delete_config_override(
                db,
                key=CONFIG_KEY_VETO_ROI,
                tenant_id=tenant_id,
            )
    except Exception as exc:  # noqa: BLE001 - graceful UI feedback
        return False, str(exc)
    return True, None


def try_delete_category_referral_fee(
    factory: sessionmaker[Session],
    *,
    category_node: str,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[bool, str | None]:
    """Cancella l'override referral fee per la categoria (reset al raw).

    :returns: tupla `(success, error_message)`.
    """
    try:
        with session_scope(factory) as db:
            delete_config_override(
                db,
                key=KEY_REFERRAL_FEE_PCT,
                tenant_id=tenant_id,
                scope=SCOPE_CATEGORY,
                scope_key=category_node,
            )
    except Exception as exc:  # noqa: BLE001 - graceful UI feedback
        return False, str(exc)
    return True, None


def compare_session_kpis(
    loaded: LoadedSession,
    replayed: SessionResult,
) -> dict[str, dict[str, float]]:
    """Confronto KPI originale (loaded) vs replay (replayed).

    Helper puro testabile senza Streamlit. Espone i KPI chiave per
    rendering side-by-side: budget, saturazione, budget_t1, cart_count,
    panchina_count.

    Differenza vs leggere direttamente i campi: normalizza i tipi
    (Decimal/float) e centralizza le derivazioni (saturazione del
    LoadedSession non e' precalcolata, va dedotta da
    `sum(unit_cost * qty) / budget`).

    :returns: dict con chiavi `original` / `replayed`, valori dict con
        chiavi `budget`, `saturation`, `budget_t1`, `cart_count`,
        `panchina_count`.
    """
    original_budget = float(loaded.summary.budget_eur)
    original_total = 0.0
    for row in loaded.cart_rows:
        cost = row.get("cost_total")
        if isinstance(cost, (int, float)):
            original_total += float(cost)
    original_saturation = min(original_total / original_budget, 1.0) if original_budget > 0 else 0.0
    return {
        "original": {
            "budget": original_budget,
            "saturation": original_saturation,
            # `budget_t1` non e' nel LoadedSession (non persistito): NaN
            # placeholder per il confronto. Frontend rendera' "—".
            "budget_t1": float("nan"),
            "cart_count": float(len(loaded.cart_rows)),
            "panchina_count": float(len(loaded.panchina_rows)),
        },
        "replayed": {
            "budget": float(replayed.cart.budget),
            "saturation": float(replayed.cart.saturation),
            "budget_t1": float(replayed.budget_t1),
            "cart_count": float(len(replayed.cart.items)),
            "panchina_count": float(len(replayed.panchina)),
        },
    }


def try_replay_session(
    factory: sessionmaker[Session],
    session_id: int,
    *,
    locked_in_override: list[str] | None = None,
    budget_override: float | None = None,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[SessionResult | None, str | None]:
    """Carica una sessione via `load_session_full` e applica `replay_session`.

    :returns: tupla `(result, error_message)`. `result=None` se la sessione
        non esiste o se il replay fallisce; `error_message=None` su
        successo. R-04 fail (`InsufficientBudgetError`) ritorna messaggio
        per l'utente, NON eccezione.
    """
    try:
        with session_scope(factory) as db:
            loaded = load_session_full(db, session_id, tenant_id=tenant_id)
            if loaded is None:
                return None, f"Sessione id={session_id} non trovata o non accessibile."
            replayed = replay_session(
                loaded,
                locked_in_override=locked_in_override,
                budget_override=budget_override,
            )
    except InsufficientBudgetError as exc:
        return None, f"R-04 fallito: {exc}"
    except ValueError as exc:
        return None, f"Validazione fallita: {exc}"
    except Exception as exc:  # noqa: BLE001 - graceful UI feedback su DB/IO
        return None, f"Errore inatteso: {exc}"
    return replayed, None


def build_session_input(  # noqa: PLR0913 — 7 parametri sessione = la firma del cruscotto
    factory: sessionmaker[Session] | None,
    listino_raw: pd.DataFrame,
    *,
    budget: float,
    locked_in: list[str],
    velocity_target_days: int,
    veto_roi_threshold: float,
    lot_size: int,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> SessionInput:
    """Costruisce `SessionInput` includendo le `referral_fee_overrides` da DB.

    Carica la mappa `category_node → referral_fee_pct` per il tenant via
    `fetch_category_referral_fees_or_empty` (graceful empty se factory
    None o DB down). Se la mappa e' vuota, passa `referral_fee_overrides=None`
    al `SessionInput` (`None` invece di `{}` perche' l'orchestrator
    tratta entrambi identici, ma `None` e' la "intent" piu' chiara).

    Pattern: questo helper isola la logica di wiring DB↔orchestrator dal
    flow Streamlit di `main()`, rendendola testabile senza streamlit.
    """
    overrides_floats = fetch_category_referral_fees_or_empty(factory, tenant_id=tenant_id)
    overrides = overrides_floats or None
    return SessionInput(
        listino_raw=listino_raw,
        budget=budget,
        locked_in=locked_in,
        velocity_target_days=velocity_target_days,
        veto_roi_threshold=veto_roi_threshold,
        lot_size=lot_size,
        referral_fee_overrides=overrides,
    )


def fetch_existing_session_for_listino(
    factory: sessionmaker[Session],
    listino_raw: pd.DataFrame,
    *,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> SessionSummary | None:
    """Calcola l'hash del listino e cerca una sessione gia' persistita.

    Ritorna `None` se nessuna sessione del tenant ha quel hash, o se la
    query fallisce (graceful UI). Usato pre-save per warning duplicate.
    """
    try:
        listino_hash = _listino_hash(listino_raw)
    except Exception:  # noqa: BLE001 - graceful UI fallback
        return None
    try:
        with session_scope(factory) as db:
            return find_session_by_hash(db, listino_hash=listino_hash, tenant_id=tenant_id)
    except Exception:  # noqa: BLE001 - graceful UI fallback
        return None


def _render_history(
    factory: sessionmaker[Session],
    *,
    tenant_id: int,
    limit: int = 20,
) -> None:
    """Expander con lista delle sessioni precedenti + form ricarica per id."""
    with st.expander("Storico Sessioni (lista recente)"):
        rows = fetch_recent_sessions_or_empty(factory, limit=limit, tenant_id=tenant_id)
        if not rows:
            st.caption("Nessuna sessione precedente trovata.")
            return
        sessions_df = pd.DataFrame(rows)
        sessions_view, sessions_cfg = _percentage_view(sessions_df)
        st.dataframe(sessions_view, use_container_width=True, column_config=sessions_cfg)

        st.divider()
        st.caption("Ricarica una sessione storica (incolla l'id dalla colonna sopra)")
        col_id, col_btn = st.columns([3, 1])
        # rows[0]["id"] e' tipato `object` dal dict literal; cast esplicito.
        first_id = int(str(rows[0]["id"]))
        sid_input = col_id.number_input(
            "ID sessione",
            min_value=1,
            value=first_id,
            step=1,
            key="load_sid_input",
        )
        if col_btn.button("Carica dettaglio", key="load_session_btn"):
            loaded = fetch_loaded_session_or_none(factory, int(sid_input), tenant_id=tenant_id)
            if loaded is None:
                st.error(f"Sessione id={sid_input} non trovata o non accessibile.")
            else:
                _render_loaded_session_detail(loaded, factory)


def _render_loaded_session_detail(
    loaded: LoadedSession,
    factory: sessionmaker[Session] | None = None,
) -> None:
    """Render del dettaglio di una `LoadedSession` (post-`load_session_by_id`).

    Se `factory` e' fornito, espone anche un sub-expander "What-if
    Re-allocate" (CHG-057) che permette al CFO di ri-allocare la
    sessione corrente con `locked_in`/`budget` override senza
    ri-eseguire enrichment (consumer di `replay_session`).
    """
    s = loaded.summary
    st.subheader(f"Dettaglio Sessione id={s.id}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Budget (EUR)", f"€ {float(s.budget_eur):,.2f}")
    col2.metric("Velocity Target", f"{s.velocity_target} gg")
    col3.metric("# Cart / Panchina", f"{s.n_cart_items} / {s.n_panchina_items}")

    if loaded.cart_rows:
        st.caption("Cart")
        cart_df = pd.DataFrame(loaded.cart_rows)
        cart_view, cart_cfg = _percentage_view(cart_df)
        st.dataframe(cart_view, use_container_width=True, column_config=cart_cfg)
    else:
        st.caption("Cart: nessun item allocato.")

    if loaded.panchina_rows:
        st.caption("Panchina (idonei scartati per cassa)")
        panchina_df = pd.DataFrame(loaded.panchina_rows)
        panchina_view, panchina_cfg = _percentage_view(panchina_df)
        st.dataframe(panchina_view, use_container_width=True, column_config=panchina_cfg)
    else:
        st.caption("Panchina: vuota.")

    if factory is not None:
        _render_replay_what_if(factory, loaded)


def _render_replay_what_if(
    factory: sessionmaker[Session],
    loaded: LoadedSession,
) -> None:
    """Sub-expander "What-if Re-allocate" + compare side-by-side (CHG-057+059).

    Permette al CFO di modificare `budget` o `locked_in` e ottenere
    un nuovo `SessionResult` via `replay_session`, senza ri-eseguire
    enrichment. Mostra confronto KPI originale vs replay.
    """
    session_id = loaded.summary.id
    original_budget = float(loaded.summary.budget_eur)
    with st.expander("What-if — Re-allocate questa sessione"):
        st.caption(
            "Modifica budget o locked-in e ottieni un nuovo Cart senza ricaricare il listino. "
            "Niente persistenza: il replay e' in memoria.",
        )
        new_budget = st.number_input(
            "Budget override (EUR)",
            min_value=100.0,
            value=original_budget,
            step=500.0,
            format="%.2f",
            key=f"replay_budget_{session_id}",
        )
        new_locked_raw = st.text_input(
            "Locked-in override (ASIN separati da virgola; vuoto = stessi locked-in originali)",
            value="",
            key=f"replay_locked_{session_id}",
        )
        if st.button("Re-allocate (what-if)", key=f"replay_btn_{session_id}"):
            locked_override = parse_locked_in(new_locked_raw) if new_locked_raw.strip() else None
            replayed, err = try_replay_session(
                factory,
                session_id,
                locked_in_override=locked_override,
                budget_override=float(new_budget),
            )
            if err is not None or replayed is None:
                st.error(err or "Replay fallito.")
            else:
                _render_compare_view(loaded, replayed)


def _render_compare_view(loaded: LoadedSession, replayed: SessionResult) -> None:
    """Render side-by-side dei KPI originale (loaded) vs replay (replayed) — CHG-059."""
    st.success("Replay completato (in memoria). Confronto:")
    kpis = compare_session_kpis(loaded, replayed)
    col_orig, col_rep = st.columns(2)

    with col_orig:
        st.markdown("**Originale**")
        st.metric("Budget (EUR)", f"€ {kpis['original']['budget']:,.2f}")
        st.metric("Saturazione", f"{kpis['original']['saturation']:.1%}")
        st.metric("Budget T+1", "—")  # non persistito
        st.metric(
            "# Cart / Panchina",
            f"{int(kpis['original']['cart_count'])} / {int(kpis['original']['panchina_count'])}",
        )
        if loaded.cart_rows:
            cart_df_orig = pd.DataFrame(loaded.cart_rows)
            orig_view, orig_cfg = _percentage_view(cart_df_orig)
            st.dataframe(orig_view, use_container_width=True, column_config=orig_cfg)

    with col_rep:
        st.markdown("**Replay**")
        st.metric(
            "Budget (EUR)",
            f"€ {kpis['replayed']['budget']:,.2f}",
            delta=f"{kpis['replayed']['budget'] - kpis['original']['budget']:+,.2f}",
        )
        sat_delta_pp = (kpis["replayed"]["saturation"] - kpis["original"]["saturation"]) * 100
        st.metric(
            "Saturazione",
            f"{kpis['replayed']['saturation']:.1%}",
            delta=f"{sat_delta_pp:+.1f} pp",
        )
        st.metric("Budget T+1 (R-07)", f"€ {kpis['replayed']['budget_t1']:,.2f}")
        st.metric(
            "# Cart / Panchina",
            f"{int(kpis['replayed']['cart_count'])} / {int(kpis['replayed']['panchina_count'])}",
            delta=int(kpis["replayed"]["cart_count"] - kpis["original"]["cart_count"]),
        )
        if replayed.cart.items:
            cart_view = [
                {
                    "asin": ci.asin,
                    "qty": ci.qty,
                    "cost_total": ci.cost_total,
                    "vgp_score": ci.vgp_score,
                    "locked": ci.locked,
                }
                for ci in replayed.cart.items
            ]
            cart_df_rep = pd.DataFrame(cart_view)
            rep_view, rep_cfg = _percentage_view(cart_df_rep)
            st.dataframe(rep_view, use_container_width=True, column_config=rep_cfg)


def _render_replay_result(replayed: SessionResult) -> None:
    """Render del SessionResult prodotto dal replay (no persist)."""
    st.success("Replay completato (in memoria).")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saturazione Cart", f"{replayed.cart.saturation:.1%}")
    col2.metric("Budget T+1 (R-07)", f"€ {replayed.budget_t1:,.2f}")
    col3.metric("# Cart / Panchina", f"{len(replayed.cart.items)} / {len(replayed.panchina)}")

    if replayed.cart.items:
        cart_view = [
            {
                "asin": ci.asin,
                "qty": ci.qty,
                "cost_total": ci.cost_total,
                "vgp_score": ci.vgp_score,
                "locked": ci.locked,
            }
            for ci in replayed.cart.items
        ]
        st.caption("Nuovo Cart")
        cart_df = pd.DataFrame(cart_view)
        cart_view_df, cart_cfg = _percentage_view(cart_df)
        st.dataframe(cart_view_df, use_container_width=True, column_config=cart_cfg)

    if not replayed.panchina.empty:
        st.caption("Nuova Panchina")
        cols = [c for c in ("asin", "vgp_score", "qty_final", "roi") if c in replayed.panchina]
        panchina_view, panchina_cfg = _percentage_view(replayed.panchina[cols])
        st.dataframe(panchina_view, use_container_width=True, column_config=panchina_cfg)


def _render_panchina_table(panchina: pd.DataFrame) -> None:
    """Tabella Panchina (R-09: idonei scartati per cassa, ordinati VGP DESC) + export CSV."""
    _section("5", "Panchina · Idonei scartati per capienza (R-09)")
    if panchina.empty:
        st.markdown(
            """
            <div class="talos-empty">
              <div class="talos-empty-icon">◇ ◇ ◇</div>
              <div>Panchina vuota. Tutti gli idonei sono in Cart.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    display_cols = [
        c for c in ["asin", "vgp_score", "roi", "cost_eur", "qty_final"] if c in panchina.columns
    ]
    panchina_subset = panchina[display_cols]
    panchina_view, panchina_cfg = _percentage_view(panchina_subset)
    st.dataframe(panchina_view, use_container_width=True, column_config=panchina_cfg)
    st.download_button(
        "⬇ Esporta Panchina (CSV)",
        data=panchina_subset.to_csv(index=False).encode("utf-8"),
        file_name="talos_panchina.csv",
        mime="text/csv",
        key="export_panchina_btn",
    )


def _render_descrizione_prezzo_flow(
    factory: sessionmaker[Session] | None,
) -> pd.DataFrame | None:
    """Flow nuovo CHG-2026-05-01-020: listino con descrizione+prezzo (no ASIN).

    Step:
    1. Upload CSV con colonne `descrizione`, `prezzo` (+ opzionali).
    2. Parse + warnings su righe invalide.
    3. Bottone "Risolvi descrizioni" -> resolve con cache `description_resolutions`
       (CHG-019) + fallback `_LiveAsinResolver` (CHG-018) per cache miss.
    4. Tabella preview con `confidence_pct` esposto + badge OK/DUB/AMB
       (R-01 UX-side: tutti i match esposti, ambigui inclusi).
    5. Bottone "Conferma listino" -> ritorna DataFrame 7-col compatibile
       con `run_session`.

    Bind request context (CHG-2026-05-01-036, B1.3): all'ingresso del
    flow `bind_request_context(tenant_id=DEFAULT_TENANT_ID)` arricchisce
    tutti gli emit UI (`ui.resolve_started/confirmed/override_applied/
    resolve_failed` + `cache.hit/miss`) e gli eventi downstream
    (`run_session` con pattern is_outer = orchestrator riusa il bind UI).

    Ritorna `None` se l'utente non ha ancora confermato il listino
    (UI in progress); altrimenti il DataFrame `listino_raw` pronto per
    `build_session_input`.
    """
    is_outer = not is_request_context_bound()
    bind_request_context(tenant_id=DEFAULT_TENANT_ID)
    try:
        return _render_descrizione_prezzo_flow_body(factory)
    finally:
        if is_outer:
            clear_request_context()


def _render_descrizione_prezzo_flow_body(  # noqa: C901, PLR0911, PLR0915 — flow Streamlit multi-step inerentemente complesso
    factory: sessionmaker[Session] | None,
) -> pd.DataFrame | None:
    """Body del flow descrizione+prezzo (CHG-036 ha estratto il wrapper bind context)."""
    # Lazy import per non penalizzare boot quando il flow non e' attivo.
    from functools import partial  # noqa: PLC0415

    from talos.config.settings import TalosSettings  # noqa: PLC0415
    from talos.extract.asin_resolver import _LiveAsinResolver  # noqa: PLC0415
    from talos.io_.fallback_chain import lookup_product  # noqa: PLC0415
    from talos.io_.keepa_client import KeepaClient  # noqa: PLC0415
    from talos.io_.scraper import _PlaywrightBrowserPage  # noqa: PLC0415
    from talos.io_.serp_search import _LiveAmazonSerpAdapter  # noqa: PLC0415
    from talos.ui.listino_input import (  # noqa: PLC0415
        apply_candidate_overrides,
        build_listino_raw_from_resolved,
        count_eligible_for_overrides,
        count_resolved,
        format_buybox_verified_caption,
        format_cache_hit_caption,
        format_confidence_badge,
        parse_descrizione_prezzo_csv,
        resolve_listino_with_cache,
    )

    _section("2", "Risoluzione descrizione → ASIN")
    st.caption(
        "Carica un CSV con colonne `descrizione` e `prezzo`. Il sistema risolve "
        "ogni descrizione in un ASIN candidato verificato con Keepa.",
    )
    # CHG-2026-05-02-005: chiarisce semantica `prezzo` (bug semantico
    # rilevato live: CFO può confondere prezzo Amazon con costo fornitore).
    st.warning(
        "**Importante**: il campo `prezzo` è il **costo fornitore** (quanto "
        "paghi al fornitore per acquistare l'ASIN), NON il prezzo di vendita "
        "Amazon. Il prezzo Amazon (Buy Box) viene verificato live via Keepa.",
        icon="⚠️",
    )

    uploaded = st.file_uploader(
        "Carica listino (CSV / XLSX / PDF / DOCX)",
        type=["csv", "xlsx", "xls", "pdf", "docx"],
        help=(
            "Colonne minime: `descrizione`, `prezzo` (costo fornitore EUR). "
            "Opzionali: `v_tot` (vendite mensili stimate), `s_comp`, `category_node`. "
            "PDF/DOCX devono contenere tabelle native (no scansioni)."
        ),
        key="descrizione_prezzo_uploader",
    )
    if uploaded is None:
        st.info("Carica un listino per iniziare.")
        return None

    from talos.ui.document_parser import parse_uploaded_document  # noqa: PLC0415

    suffix = uploaded.name.rsplit(".", 1)[-1] if "." in uploaded.name else ""
    try:
        df_raw = parse_uploaded_document(uploaded, suffix)
    except (pd.errors.ParserError, ValueError) as exc:  # pragma: no cover - UI-only
        st.error(f"Errore parsing file: {exc}")
        return None

    try:
        rows, parse_warnings = parse_descrizione_prezzo_csv(df_raw)
    except ValueError as exc:
        st.error(f"CSV non valido: {exc}")
        return None

    for w in parse_warnings:
        st.warning(w)
    if not rows:
        st.warning("Nessuna riga valida nel CSV.")
        return None

    st.dataframe(df_raw.head(20), use_container_width=True)
    st.caption(f"Anteprima ({min(len(df_raw), 20)} righe). Premi 'Risolvi descrizioni'.")

    if "resolved_rows" not in st.session_state:
        st.session_state.resolved_rows = None

    if st.button("Risolvi descrizioni", key="resolve_descriptions_btn"):
        settings = TalosSettings()
        api_key = settings.keepa_api_key
        if api_key is None:
            _emit_ui_resolve_failed(reason="keepa_key_missing", n_rows=len(rows))
            st.error(
                "TALOS_KEEPA_API_KEY non impostata. Imposta la chiave Keepa per "
                "abilitare la risoluzione live (vedi `.env.example`).",
            )
            return None

        _emit_ui_resolve_started(n_rows=len(rows), has_factory=factory is not None)

        # CHG-2026-05-01-039: rate limit da settings (env
        # TALOS_KEEPA_RATE_LIMIT_PER_MINUTE) invece di hardcoded 20.
        # Default 60/min troppo basso per N rows x top-N candidati SERP
        # + N cache-hit lookup (CHG-039 buybox live); env consente tuning.
        keepa_client = KeepaClient(
            api_key=api_key,
            rate_limit_per_minute=settings.keepa_rate_limit_per_minute,
        )
        with _PlaywrightBrowserPage() as page:
            serp_adapter = _LiveAmazonSerpAdapter(browser_factory=lambda: page)
            lookup_callable = partial(
                lookup_product,
                keepa=keepa_client,
                scraper=None,
                page=None,
                ocr=None,
            )

            def resolver_provider() -> _LiveAsinResolver:
                return _LiveAsinResolver(
                    serp_adapter=serp_adapter,
                    lookup_callable=lookup_callable,
                    max_candidates=3,
                )

            with st.status(
                f"Risoluzione di {len(rows)} descrizioni in corso…",
                expanded=False,
            ) as status:
                status.write("◈ Apertura browser headless (Chromium)")
                status.write("◈ Query SERP Amazon.it (top-3 candidati per riga)")
                status.write("◈ Verifica live Keepa (Buy Box + BSR)")
                status.write("◈ Confidence score (fuzzy title 60% + price delta 40%)")
                resolved = resolve_listino_with_cache(
                    rows,
                    factory=factory,
                    resolver_provider=resolver_provider,
                    tenant_id=DEFAULT_TENANT_ID,
                    # CHG-2026-05-01-039: passa lookup_callable per fetch
                    # buybox live anche su cache hit (cache solo desc→ASIN
                    # invariante; buybox volatile va sempre verificato).
                    lookup_callable=lookup_callable,
                )
                status.update(
                    label=f"Risolte {len(resolved)} righe ✓",
                    state="complete",
                    expanded=False,
                )
        st.session_state.resolved_rows = resolved

    resolved = st.session_state.resolved_rows
    if resolved is None:
        return None

    # Override candidati per righe ambigue (CHG-023, A3).
    # Espande R-01 UX-side: il CFO può scegliere fra i top-N candidati
    # invece di accettare il top-1 selected automatico.
    overrides = _render_ambiguous_candidate_overrides(resolved)
    resolved_with_overrides = apply_candidate_overrides(resolved, overrides)
    if overrides:
        n_eligible = count_eligible_for_overrides(resolved)
        _emit_ui_override_applied(n_overrides=len(overrides), n_eligible=n_eligible)

    # Tabella preview con confidence + badge esposti (R-01 UX-side).
    # `buy_box_verificato` espone il prezzo Amazon NEW recuperato live
    # (CHG-022). "—" se non verificato (cache hit / lookup fail).
    preview_df = pd.DataFrame(
        [
            {
                "descrizione": r.descrizione,
                "prezzo_fornitore": float(r.prezzo_eur),
                "buy_box_verificato": (
                    float(r.verified_buybox_eur) if r.verified_buybox_eur is not None else None
                ),
                "asin": r.asin or "(non risolto)",
                "confidence": format_confidence_badge(r.confidence_pct),
                "ambiguo": "Sì" if r.is_ambiguous else "No",
                "cache_hit": "Sì" if r.is_cache_hit else "No",
                "note": "; ".join(r.notes) if r.notes else "",
            }
            for r in resolved_with_overrides
        ],
    )
    st.markdown("**Anteprima risoluzione:**")
    preview_view, preview_cfg = _percentage_view(preview_df)
    st.dataframe(preview_view, use_container_width=True, column_config=preview_cfg)

    n_resolved = count_resolved(resolved_with_overrides)
    n_total = len(resolved_with_overrides)
    n_ambiguous = sum(1 for r in resolved_with_overrides if r.is_ambiguous and r.asin)
    n_overrides = len(overrides)
    cache_caption = format_cache_hit_caption(resolved_with_overrides)
    buybox_caption = format_buybox_verified_caption(resolved_with_overrides)
    caption = (
        f"Risolti {n_resolved}/{n_total} (di cui {n_ambiguous} ambigui)."
        + (f" Override CFO applicati: {n_overrides}." if n_overrides else "")
        + (f" {cache_caption}" if cache_caption else "")
        + (f" {buybox_caption}" if buybox_caption else "")
        + " Le righe ambigue restano nel listino: il CFO valuta caso per caso."
    )
    st.caption(caption)

    if st.button("Conferma listino e crea sessione", key="confirm_resolved_listino_btn"):
        listino_df = build_listino_raw_from_resolved(resolved_with_overrides)
        if listino_df.empty:
            st.error("Nessun ASIN risolto nel listino. Impossibile procedere.")
            return None
        _emit_ui_resolve_confirmed(
            n_total=n_total,
            n_resolved=n_resolved,
            n_ambiguous=n_ambiguous,
        )
        st.session_state.resolved_rows = None  # reset per next batch
        return listino_df

    return None


def _render_ambiguous_candidate_overrides(
    resolved: list[ResolvedRow],
) -> dict[int, str]:
    """Render selectbox top-N per ogni riga ambigua + ritorna override map.

    Helper Streamlit-side. Ritorna `{idx_riga: chosen_asin}` con SOLO
    le righe che il CFO ha effettivamente cambiato dal default
    (selectbox a default = no override). Cache hit (candidates vuota)
    e righe con un solo candidato non sono interattive.

    UX:
    - Expander chiuso di default (CFO accetta i top-1 a meno che non
      voglia esplicitamente intervenire).
    - Per ogni riga ambigua con N>1 candidati: caption descrizione +
      `st.selectbox` con format compatto (asin + truncated title +
      confidence%).
    """
    eligible_rows: list[tuple[int, ResolvedRow]] = [
        (idx, r)
        for idx, r in enumerate(resolved)
        if r.is_ambiguous and r.asin and len(r.candidates) > 1
    ]
    if not eligible_rows:
        return {}

    overrides: dict[int, str] = {}
    with st.expander(
        f"Override candidati ambigui ({len(eligible_rows)} righe sopra soglia AMB)",
        expanded=False,
    ):
        st.caption(
            "Per ogni riga ambigua il sistema mostra i top-N candidati. "
            "Il default è il top-1 a confidence (selezione automatica). "
            "Cambia se conosci una scelta migliore.",
        )
        for idx, row in eligible_rows:
            current_idx = next(
                (i for i, c in enumerate(row.candidates) if c.asin == row.asin),
                0,
            )
            chosen = st.selectbox(
                f"`{row.descrizione[:60]}` (€{float(row.prezzo_eur):.2f})",
                options=list(row.candidates),
                index=current_idx,
                format_func=lambda c: f"{c.asin} | {c.title[:50]} | conf {c.confidence_pct:.1f}%",
                key=f"override_select_{idx}",
            )
            if chosen.asin != row.asin:
                overrides[idx] = chosen.asin
    return overrides


_TALOS_CSS = """
<style>
  /* =============== Tipografia & base =============== */
  html, body, [class*="css"] { font-family: 'Georgia', 'Cambria', serif; }
  h1, h2, h3 { letter-spacing: 0.5px; font-weight: 600; }

  /* =============== Portale brand header =============== */
  .talos-portal-hero {
    text-align: center;
    padding: 3rem 2rem 2.5rem 2rem;
    margin-bottom: 2rem;
    background: linear-gradient(180deg, #161B22 0%, #0E1117 100%);
    border: 1px solid #C9A96122;
    border-radius: 16px;
    position: relative;
  }
  .talos-portal-hero::before {
    content: '';
    position: absolute; top: 0; left: 50%;
    width: 80px; height: 2px;
    background: linear-gradient(90deg, transparent, #C9A961, transparent);
    transform: translateX(-50%);
  }
  .talos-portal-mark {
    font-size: 3.6rem; line-height: 1; margin: 0;
    color: #C9A961; letter-spacing: 0.3rem;
  }
  .talos-portal-title {
    font-size: 2.8rem; font-weight: 700; color: #E6EDF3;
    margin: 0.6rem 0 0 0; letter-spacing: 0.08rem;
  }
  .talos-portal-tagline {
    color: #C9A961; font-size: 0.85rem; letter-spacing: 0.4rem;
    text-transform: uppercase; margin-top: 0.6rem;
  }
  .talos-portal-subtitle {
    color: #8B949E; font-size: 1rem; margin-top: 1.2rem;
    max-width: 640px; margin-left: auto; margin-right: auto;
    font-style: italic;
  }
  .talos-section-label {
    color: #8B949E; font-size: 0.7rem; letter-spacing: 0.3rem;
    text-transform: uppercase; text-align: center; margin: 2rem 0 1rem 0;
  }

  /* =============== Module cards (portale) =============== */
  .talos-module-card {
    border: 1px solid #C9A96133;
    border-radius: 12px;
    padding: 1.8rem 1.6rem;
    background: linear-gradient(180deg, #161B22 0%, #11161D 100%);
    transition: all 200ms cubic-bezier(0.2, 0.8, 0.2, 1);
    box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    margin-bottom: 1rem;
  }
  .talos-module-card:hover {
    border-color: #C9A961;
    box-shadow: 0 8px 24px rgba(201, 169, 97, 0.12);
    transform: translateY(-2px);
  }
  .talos-module-icon {
    color: #C9A961; font-size: 1.6rem;
    letter-spacing: 0.2rem; margin-bottom: 0.4rem;
  }
  .talos-module-name {
    color: #E6EDF3; font-size: 1.4rem; font-weight: 600;
    margin: 0 0 0.2rem 0; letter-spacing: 0.05rem;
  }
  .talos-module-codename {
    color: #C9A961; font-size: 0.7rem; letter-spacing: 0.25rem;
    text-transform: uppercase; margin-bottom: 0.8rem;
  }
  .talos-module-desc {
    color: #8B949E; font-size: 0.9rem; line-height: 1.5;
    margin-bottom: 1rem; min-height: 3rem;
  }
  .talos-module-disabled {
    opacity: 0.45;
  }
  .talos-module-status {
    display: inline-block;
    padding: 0.15rem 0.6rem; border-radius: 999px;
    font-size: 0.65rem; letter-spacing: 0.15rem;
    text-transform: uppercase; font-weight: 600;
  }
  .talos-module-status.live { background: #C9A96122; color: #C9A961; border: 1px solid #C9A96155; }
  .talos-module-status.soon { background: #8B949E22; color: #8B949E; border: 1px solid #8B949E33; }

  /* =============== Modulo: breadcrumb + header =============== */
  .talos-breadcrumb {
    color: #8B949E; font-size: 0.8rem; letter-spacing: 0.15rem;
    text-transform: uppercase; margin-bottom: 0.4rem;
  }
  .talos-breadcrumb a, .talos-breadcrumb .crumb-current {
    color: #C9A961;
  }
  .talos-module-header {
    padding: 0.5rem 0 1.2rem 0;
    border-bottom: 1px solid #C9A96122;
    margin-bottom: 1.6rem;
  }
  .talos-module-header h1 {
    font-size: 2rem; color: #E6EDF3; margin: 0;
  }
  .talos-module-header .subtitle {
    color: #8B949E; font-size: 0.95rem; margin-top: 0.4rem; font-style: italic;
  }

  /* =============== Section divider con accent oro =============== */
  .talos-section {
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid #21262D;
    position: relative;
  }
  .talos-section::after {
    content: ''; position: absolute; bottom: -1px; left: 0;
    width: 48px; height: 2px; background: #C9A961;
  }
  .talos-section h2 {
    color: #E6EDF3; font-size: 1.15rem; margin: 0;
    letter-spacing: 0.05rem;
  }
  .talos-section .section-num {
    color: #C9A961; font-weight: 700; margin-right: 0.6rem;
  }

  /* =============== Hero metric (KPI tile) =============== */
  [data-testid="stMetric"] {
    background: linear-gradient(180deg, #161B22 0%, #11161D 100%);
    border: 1px solid #21262D;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    transition: border-color 150ms ease;
  }
  [data-testid="stMetric"]:hover { border-color: #C9A96155; }
  [data-testid="stMetricValue"] {
    font-size: 1.9rem; font-weight: 700; color: #E6EDF3;
    letter-spacing: 0.02rem;
  }
  [data-testid="stMetricLabel"] {
    color: #C9A961; text-transform: uppercase;
    letter-spacing: 0.18rem; font-size: 0.7rem; font-weight: 600;
  }
  [data-testid="stMetricDelta"] { font-size: 0.85rem; }

  /* =============== Bottoni =============== */
  .stButton > button {
    border: 1px solid #C9A96155;
    transition: all 150ms ease-in-out;
    letter-spacing: 0.05rem;
    font-weight: 500;
  }
  .stButton > button:hover {
    border-color: #C9A961;
    background: #C9A96115;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(201, 169, 97, 0.1);
  }
  .stButton > button[kind="primary"] {
    background: linear-gradient(180deg, #C9A961 0%, #B8985A 100%);
    color: #0E1117; border: none; font-weight: 600;
  }
  .stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(201, 169, 97, 0.3);
  }

  /* =============== Sidebar polished =============== */
  [data-testid="stSidebar"] {
    background: #11161D;
    border-right: 1px solid #21262D;
  }
  [data-testid="stSidebar"] h2 {
    color: #C9A961; font-size: 0.85rem;
    letter-spacing: 0.25rem; text-transform: uppercase;
    border-bottom: 1px solid #21262D; padding-bottom: 0.4rem;
  }

  /* =============== Tabelle =============== */
  [data-testid="stDataFrame"] {
    border: 1px solid #21262D;
    border-radius: 8px;
    padding: 0.4rem;
  }

  /* =============== Caption / info =============== */
  .stCaption { color: #8B949E !important; font-style: italic; }
  [data-testid="stAlert"] { border-radius: 8px; }

  /* =============== Empty state container =============== */
  .talos-empty {
    text-align: center; padding: 3rem 1rem;
    color: #8B949E; border: 1px dashed #21262D;
    border-radius: 12px; background: #0E111722;
  }
  .talos-empty-icon {
    font-size: 2.4rem; color: #C9A96155;
    margin-bottom: 0.8rem; letter-spacing: 0.4rem;
  }

  /* =============== Footer =============== */
  .talos-footer {
    margin-top: 4rem; padding-top: 1.2rem;
    border-top: 1px solid #21262D;
    text-align: center; color: #6B7280;
    font-size: 0.75rem; letter-spacing: 0.15rem;
    text-transform: uppercase;
  }

  /* =============== Animazioni =============== */
  @keyframes talos-fade-in {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .talos-portal-hero, .talos-module-card { animation: talos-fade-in 480ms ease-out; }
  .talos-module-card:nth-child(2) { animation-delay: 60ms; animation-fill-mode: backwards; }
  .talos-module-card:nth-child(3) { animation-delay: 120ms; animation-fill-mode: backwards; }
  @keyframes talos-pulse-gold {
    0%, 100% { box-shadow: 0 0 0 0 rgba(201, 169, 97, 0.4); }
    50% { box-shadow: 0 0 0 12px rgba(201, 169, 97, 0); }
  }
  .stButton > button[kind="primary"]:focus-visible,
  .stButton > button[kind="primary"]:focus {
    animation: talos-pulse-gold 1.6s ease-out infinite;
  }
  /* Hero mark gradient text */
  .talos-portal-mark {
    background: linear-gradient(135deg, #C9A961 0%, #E8D08B 50%, #C9A961 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
  }

  /* =============== Status indicator (sidebar) =============== */
  .talos-status {
    padding: 0.6rem 0.8rem;
    border: 1px solid #21262D; border-radius: 8px;
    background: #0E1117; margin-bottom: 0.6rem;
    font-size: 0.78rem; color: #8B949E;
    display: flex; align-items: center; gap: 0.5rem;
  }
  .talos-status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    flex-shrink: 0;
  }
  .talos-status-dot.ok    { background: #3FB950; box-shadow: 0 0 8px #3FB95066; }
  .talos-status-dot.warn  { background: #D29922; box-shadow: 0 0 8px #D2992266; }
  .talos-status-dot.off   { background: #6B7280; }
  .talos-status-label { color: #C9A961; font-weight: 600; letter-spacing: 0.05rem; }
</style>
"""


def _render_sidebar_status() -> None:
    """Status indicators sistema (DB / Keepa) in cima alla sidebar."""
    from talos.config import get_settings  # noqa: PLC0415

    settings = get_settings()
    db_url = settings.db_url
    keepa_key = settings.keepa_api_key

    db_dot = "ok" if db_url else "off"
    db_label = "Connesso" if db_url else "Disabilitato"
    keepa_dot = "ok" if keepa_key else "warn"
    keepa_label = "Configurata" if keepa_key else "Non configurata"

    st.sidebar.markdown(
        f"""
        <div class="talos-status">
          <span class="talos-status-dot {db_dot}"></span>
          <span><span class="talos-status-label">DB</span> · {db_label}</span>
        </div>
        <div class="talos-status">
          <span class="talos-status-dot {keepa_dot}"></span>
          <span><span class="talos-status-label">Keepa API</span> · {keepa_label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_portal() -> None:
    """Portale TALOS: hero + lista moduli (Demetra MVP, futuri locked)."""
    st.markdown(
        """
        <div class="talos-portal-hero">
          <div class="talos-portal-mark">◆</div>
          <div class="talos-portal-title">TALOS</div>
          <div class="talos-portal-tagline">Operational Intelligence Suite</div>
          <div class="talos-portal-subtitle">
            Hedge fund algoritmico per FBA Wholesale High-Ticket.
            Suite modulare di moduli decisionali per il CFO.
          </div>
        </div>
        <div class="talos-section-label">Moduli disponibili</div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="talos-module-card">
              <div class="talos-module-icon">◈</div>
              <div class="talos-module-codename">Demetra</div>
              <div class="talos-module-name">Scaler 500k</div>
              <div class="talos-module-desc">
                Pipeline algoritmica FBA Wholesale: listino → ASIN verificati live →
                VGP score → allocazione Tetris budget → carrello + panchina.
              </div>
              <div class="talos-module-status live">Live · MVP CFO</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Apri Demetra ▸",
            key="open_demetra",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.current_module = "demetra"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div class="talos-module-card talos-module-disabled">
              <div class="talos-module-icon">◇</div>
              <div class="talos-module-codename">Hermes</div>
              <div class="talos-module-name">Order Dispatcher</div>
              <div class="talos-module-desc">
                Ordering automation: dal carrello Demetra all'invio ordini fornitori
                + tracking conferme. R-03 ORDER-DRIVEN MEMORY end-to-end.
              </div>
              <div class="talos-module-status soon">Coming soon</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="talos-module-card talos-module-disabled">
              <div class="talos-module-icon">◇</div>
              <div class="talos-module-codename">Atena</div>
              <div class="talos-module-name">Strategic Cockpit</div>
              <div class="talos-module-desc">
                Cruscotto direzionale: KPI multi-sessione, calibrazione algoritmi,
                analisi storico ordini, governance ADR.
              </div>
              <div class="talos-module-status soon">Coming soon</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="talos-footer">
          TALOS · powered by VGP/Tetris algorithm · ADR-driven governance
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_module_header(*, codename: str, module_name: str, subtitle: str) -> None:
    """Header sezione modulo: breadcrumb + back button + titolo."""
    col_back, col_title = st.columns([1, 9])
    with col_back:
        if st.button("◂ Portale", key="back_to_portal"):
            st.session_state.current_module = None
            st.rerun()
    with col_title:
        st.markdown(
            f"""
            <div class="talos-module-header">
              <div class="talos-breadcrumb">
                TALOS · <span class="crumb-current">{codename} · {module_name}</span>
              </div>
              <h1>{codename} — {module_name}</h1>
              <div class="subtitle">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _section(num: str, title: str) -> None:
    """Render section divider con accent oro + numerazione."""
    st.markdown(
        f"""
        <div class="talos-section">
          <h2><span class="section-num">{num}</span>{title}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Entrypoint Streamlit. Dispatcher portale TALOS / modulo Demetra."""
    st.set_page_config(
        page_title="TALOS · Operational Intelligence Suite",
        layout="wide",
        page_icon="◆",
        initial_sidebar_state="expanded",
    )
    st.markdown(_TALOS_CSS, unsafe_allow_html=True)

    if "current_module" not in st.session_state:
        st.session_state.current_module = None

    if st.session_state.current_module is None:
        _render_portal()
        return

    if st.session_state.current_module == "demetra":
        _render_demetra_module()
        return

    # Fallback: modulo sconosciuto -> reset.
    st.session_state.current_module = None
    st.rerun()


def _render_demetra_module() -> None:  # noqa: C901, PLR0911, PLR0912, PLR0915 — entry-point Streamlit multi-step
    """Modulo Demetra · Scaler 500k. Pipeline VGP/Tetris end-to-end."""
    _render_module_header(
        codename="Demetra",
        module_name="Scaler 500k",
        subtitle="Listino → ASIN verificati live → VGP score → allocazione Tetris budget.",
    )

    _render_sidebar_status()
    factory_for_sidebar = get_session_factory_or_none()
    budget, velocity_target, veto_threshold, lot_size = _render_sidebar(factory_for_sidebar)

    # Decisione Leader 2026-05-01 round 4 (delta=A): convivenza dei 2 flow
    # CSV. Default = nuovo (descrizione+prezzo); legacy disponibile per
    # CSV gia' strutturati con ASIN noto.
    _section("1", "Listino di sessione")
    mode = st.radio(
        "Formato sorgente",
        options=("Descrizione + prezzo", "ASIN già noto"),
        horizontal=True,
        key="listino_input_mode",
        help="Scegli il formato del file fornitore. Default consigliato: descrizione+prezzo.",
    )

    locked_in_raw = st.text_input(
        "ASIN Locked-in (separati da virgola, opzionale)",
        value="",
        help="R-04: ASIN forzati con priorità infinita prima del Pass 2 Tetris.",
    )
    locked_in = parse_locked_in(locked_in_raw)

    listino: pd.DataFrame | None = None
    if mode == "Descrizione + prezzo":
        listino = _render_descrizione_prezzo_flow(factory_for_sidebar)
        if listino is None:
            return
    else:
        uploaded = st.file_uploader(
            "Carica listino strutturato (CSV / XLSX)",
            type=["csv", "xlsx", "xls"],
            help=f"Colonne richieste: {', '.join(REQUIRED_INPUT_COLUMNS)}.",
            key="listino_legacy_uploader",
        )
        if uploaded is None:
            st.info("Carica un listino per iniziare.")
            return

        from talos.ui.document_parser import parse_uploaded_document  # noqa: PLC0415

        suffix = uploaded.name.rsplit(".", 1)[-1] if "." in uploaded.name else ""
        try:
            listino = parse_uploaded_document(uploaded, suffix)
        except (pd.errors.ParserError, ValueError) as exc:  # pragma: no cover - UI-only
            st.error(f"Errore parsing file: {exc}")
            return

        if not st.button("Esegui sessione", type="primary"):
            st.dataframe(listino.head(20), use_container_width=True)
            st.caption(f"Anteprima ({min(len(listino), 20)} righe). Premi 'Esegui sessione'.")
            return

    inp = build_session_input(
        factory_for_sidebar,
        listino,
        budget=budget,
        locked_in=locked_in,
        velocity_target_days=velocity_target,
        veto_roi_threshold=veto_threshold,
        lot_size=lot_size,
    )
    try:
        result = run_session(inp)
    except InsufficientBudgetError as exc:  # pragma: no cover - UI-only
        st.error(f"R-04 fallito: {exc}")
        return
    except ValueError as exc:  # pragma: no cover - UI-only
        st.error(f"Validazione fallita: {exc}")
        return

    _render_metrics(saturation=result.cart.saturation, budget_t1=result.budget_t1)

    # CHG-2026-05-02-006: caption audit V_tot source extracted to helper.
    from talos.ui.listino_input import format_v_tot_source_caption  # noqa: PLC0415

    v_tot_caption = format_v_tot_source_caption(result.enriched_df)
    if v_tot_caption:
        st.caption(v_tot_caption)

    cart_items_view = [
        {
            "asin": item.asin,
            "qty": item.qty,
            "cost_total": item.cost_total,
            "vgp_score": item.vgp_score,
            "locked": item.locked,
        }
        for item in result.cart.items
    ]
    _render_cart_table(cart_items_view)
    _render_panchina_table(result.panchina)

    with st.expander("Listino completo enriched (audit / debug)"):
        enriched_view, enriched_cfg = _percentage_view(result.enriched_df)
        st.dataframe(enriched_view, use_container_width=True, column_config=enriched_cfg)

    # Persistenza opzionale: graceful degrade se DB non disponibile.
    factory = get_session_factory_or_none()
    _section("6", "Persistenza & storico")
    if factory is None:
        st.info(
            "Persistenza disabilitata. Per attivarla, imposta `TALOS_DB_URL` "
            "nell'ambiente (es. `postgresql+psycopg://...`).",
        )
        return

    # Pre-save check: questo listino esiste gia' come sessione persistita?
    existing = fetch_existing_session_for_listino(
        factory,
        inp.listino_raw,
        tenant_id=DEFAULT_TENANT_ID,
    )
    if existing is not None:
        _render_existing_session_warning(factory, existing)
    elif st.button("Salva sessione su DB", key="save_session_btn"):
        success, sid, err = try_persist_session(
            factory,
            session_input=inp,
            result=result,
            tenant_id=DEFAULT_TENANT_ID,
        )
        if success:
            st.toast(f"Sessione #{sid} salvata", icon="✓")
            st.success(f"Sessione persistita. id = `{sid}`.")
            st.session_state["last_saved_session_id"] = sid
        else:  # pragma: no cover - UI-only error path
            st.toast(f"Persistenza fallita: {err}", icon="⚠️")
            st.error(f"Persistenza fallita: {err}")

    # CHG-2026-05-02-017: R-03 ORDER-DRIVEN MEMORY wiring.
    # Bottone "Conferma ordini" scrive `storico_ordini` per ogni cart_item
    # della sessione persistita. Idempotente lato repository.
    last_sid = st.session_state.get("last_saved_session_id")
    if last_sid is not None:
        already_count = _count_orders_already_recorded(factory, last_sid)
        if already_count > 0:
            st.info(f"Sessione #{last_sid}: {already_count} ordini già nel registro.")
        elif st.button(
            f"Conferma ordini sessione #{last_sid} → registro permanente",
            key="confirm_orders_btn",
            type="primary",
        ):
            ok, n_recorded, err = try_record_orders(
                factory,
                session_id=last_sid,
                tenant_id=DEFAULT_TENANT_ID,
            )
            if ok:
                st.toast(f"{n_recorded} ordini registrati", icon="✓")
                st.success(
                    f"R-03 OK · {n_recorded} ordini scritti su `storico_ordini` "
                    f"(sessione #{last_sid}).",
                )
            else:  # pragma: no cover - UI-only
                st.toast(f"Registrazione fallita: {err}", icon="⚠️")
                st.error(f"Registrazione ordini fallita: {err}")

    _render_history(factory, tenant_id=DEFAULT_TENANT_ID)


def try_record_orders(
    factory: sessionmaker[Session],
    *,
    session_id: int,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> tuple[bool, int, str | None]:
    """Wrapper graceful per `record_orders_from_session`. Ritorna (ok, n, err)."""
    from talos.persistence import record_orders_from_session  # noqa: PLC0415

    try:
        with session_scope(factory) as db:
            n = record_orders_from_session(
                db,
                session_id=session_id,
                tenant_id=tenant_id,
            )
            return True, n, None
    except Exception as exc:  # noqa: BLE001 - graceful UI
        return False, 0, str(exc)


def _count_orders_already_recorded(
    factory: sessionmaker[Session],
    session_id: int,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> int:
    """Quanti `storico_ordini` esistono già per la sessione (idempotenza UX)."""
    from talos.persistence import count_orders_for_session  # noqa: PLC0415

    try:
        with session_scope(factory) as db:
            return count_orders_for_session(
                db,
                session_id=session_id,
                tenant_id=tenant_id,
            )
    except Exception:  # noqa: BLE001 - graceful UI
        return 0


def _render_existing_session_warning(
    factory: sessionmaker[Session],
    existing: SessionSummary,
) -> None:
    """Warning quando il listino corrente e' gia' stato eseguito.

    Mostra info riassuntive + bottone "Apri sessione esistente". Il
    save (`save_session_result`) e' bloccato dall'UNIQUE INDEX
    `ux_sessions_tenant_hash`; un futuro `upsert_session` sbloccera'
    il bottone "Forza nuova".
    """
    st.warning(
        f"Sessione gia' presente nel DB con questo listino. "
        f"id = `{existing.id}` — eseguita {existing.started_at.isoformat(timespec='minutes')}, "
        f"cart={existing.n_cart_items}, panchina={existing.n_panchina_items}.",
    )
    st.caption(
        "Salvataggio bloccato dall'UNIQUE INDEX `ux_sessions_tenant_hash` "
        "(CHG-2026-04-30-047). Per ri-salvare serve `upsert_session` (scope futuro).",
    )
    if st.button("Apri sessione esistente", key="open_existing_btn"):
        loaded = fetch_loaded_session_or_none(factory, existing.id)
        if loaded is None:
            st.error(f"Impossibile caricare la sessione id={existing.id}.")
        else:
            _render_loaded_session_detail(loaded, factory)


if __name__ == "__main__":  # pragma: no cover - run via streamlit CLI
    main()
