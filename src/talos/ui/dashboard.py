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

import logging
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from talos.formulas import (
    DEFAULT_LOT_SIZE,
    DEFAULT_VELOCITY_TARGET_DAYS,
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

_logger = logging.getLogger(__name__)


def _emit_ui_resolve_started(*, n_rows: int, has_factory: bool) -> None:
    """Emette evento canonico `ui.resolve_started` (catalogo ADR-0021).

    Helper puro: testabile via caplog senza dipendenza da Streamlit.
    Tracking quote SERP/Keepa pre-resolve nel flow descrizione+prezzo.
    """
    _logger.debug(
        "ui.resolve_started",
        extra={"n_rows": n_rows, "has_factory": has_factory},
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
        extra={
            "n_total": n_total,
            "n_resolved": n_resolved,
            "n_ambiguous": n_ambiguous,
        },
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
        extra={"n_overrides": n_overrides, "n_eligible": n_eligible},
    )


def _emit_ui_resolve_failed(*, reason: str, n_rows: int) -> None:
    """Emette evento canonico `ui.resolve_failed` (catalogo ADR-0021).

    Helper puro: testabile via caplog senza dipendenza da Streamlit.
    Tracking fail mode pre-resolve. `reason` è enum-string aperto:
    `"keepa_key_missing"` (oggi unico path), `"exception"` (futuro).
    """
    _logger.debug(
        "ui.resolve_failed",
        extra={"reason": reason, "n_rows": n_rows},
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


def _render_sidebar(
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
    persisted_threshold = fetch_veto_roi_threshold_or_default(factory)
    veto_threshold = st.sidebar.slider(
        "Veto ROI Minimo",
        min_value=0.01,
        max_value=0.50,
        value=persisted_threshold,
        step=0.01,
        format="%.2f",
        help="R-08: ASIN con ROI sotto soglia hanno vgp_score=0 (default 8%).",
    )
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
                st.sidebar.success(f"Soglia resettata al default {DEFAULT_ROI_VETO_THRESHOLD:.2f}.")
            else:  # pragma: no cover - UI-only error path
                st.sidebar.error(f"Reset fallito: {err}")

    if factory is not None:
        _render_sidebar_referral_fees(factory)

    lot_size = st.sidebar.number_input(
        "Lot Size Fornitore",
        min_value=1,
        value=DEFAULT_LOT_SIZE,
        step=1,
        help="F5: Floor(qty_target / lot) * lot. Default Samsung MVP = 5.",
    )
    return float(budget), int(velocity_target), float(veto_threshold), int(lot_size)


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
            st.dataframe(
                pd.DataFrame(
                    [{"category": c, "fee_pct": v} for c, v in sorted(existing.items())],
                ),
                use_container_width=True,
            )
        else:
            st.caption("Nessun override registrato.")

        category = st.text_input("Categoria", key="ref_fee_cat_input").strip()
        fee = st.number_input(
            "Fee %",
            min_value=0.0,
            max_value=1.0,
            value=0.08,
            step=0.01,
            format="%.4f",
            key="ref_fee_value_input",
        )
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
    """Tabella Cart (ASIN allocati)."""
    st.subheader("Cart — ASIN allocati (R-04 Locked-in + R-06 Tetris)")
    if not cart_items:
        st.info("Cart vuoto. Nessun ASIN allocato.")
        return
    cart_df = pd.DataFrame(cart_items)
    st.dataframe(cart_df, use_container_width=True)


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
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

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
        st.dataframe(pd.DataFrame(loaded.cart_rows), use_container_width=True)
    else:
        st.caption("Cart: nessun item allocato.")

    if loaded.panchina_rows:
        st.caption("Panchina (idonei scartati per cassa)")
        st.dataframe(pd.DataFrame(loaded.panchina_rows), use_container_width=True)
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
            st.dataframe(pd.DataFrame(loaded.cart_rows), use_container_width=True)

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
            st.dataframe(pd.DataFrame(cart_view), use_container_width=True)


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
        st.dataframe(pd.DataFrame(cart_view), use_container_width=True)

    if not replayed.panchina.empty:
        st.caption("Nuova Panchina")
        cols = [c for c in ("asin", "vgp_score", "qty_final", "roi") if c in replayed.panchina]
        st.dataframe(replayed.panchina[cols], use_container_width=True)


def _render_panchina_table(panchina: pd.DataFrame) -> None:
    """Tabella Panchina (R-09: idonei scartati per cassa, ordinati VGP DESC)."""
    st.subheader("Panchina — Idonei scartati per capienza (R-09)")
    if panchina.empty:
        st.info("Panchina vuota. Tutti gli idonei sono in Cart.")
        return
    display_cols = [
        c for c in ["asin", "vgp_score", "roi", "cost_eur", "qty_final"] if c in panchina.columns
    ]
    st.dataframe(panchina[display_cols], use_container_width=True)


def _render_descrizione_prezzo_flow(  # noqa: C901, PLR0911, PLR0915 — flow Streamlit multi-step inerentemente complesso
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

    Ritorna `None` se l'utente non ha ancora confermato il listino
    (UI in progress); altrimenti il DataFrame `listino_raw` pronto per
    `build_session_input`.
    """
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
        format_cache_hit_caption,
        format_confidence_badge,
        parse_descrizione_prezzo_csv,
        resolve_listino_with_cache,
    )

    st.subheader("Listino con descrizione + prezzo (nuovo)")
    st.caption(
        "Carica un CSV con colonne `descrizione` e `prezzo`. Il sistema risolve "
        "ogni descrizione in un ASIN candidato verificato con Keepa.",
    )

    uploaded = st.file_uploader(
        "Carica Listino (CSV descrizione+prezzo)",
        type=["csv"],
        help=(
            "Colonne minime: `descrizione`, `prezzo`. "
            "Opzionali: `v_tot`, `s_comp`, `category_node`."
        ),
        key="descrizione_prezzo_uploader",
    )
    if uploaded is None:
        st.info("Carica un CSV per iniziare.")
        return None

    try:
        df_raw = pd.read_csv(uploaded)
    except (pd.errors.ParserError, ValueError) as exc:  # pragma: no cover - UI-only
        st.error(f"Errore parsing CSV: {exc}")
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
        api_key = TalosSettings().keepa_api_key
        if api_key is None:
            _emit_ui_resolve_failed(reason="keepa_key_missing", n_rows=len(rows))
            st.error(
                "TALOS_KEEPA_API_KEY non impostata. Imposta la chiave Keepa per "
                "abilitare la risoluzione live (vedi `.env.example`).",
            )
            return None

        _emit_ui_resolve_started(n_rows=len(rows), has_factory=factory is not None)

        keepa_client = KeepaClient(api_key=api_key, rate_limit_per_minute=20)
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

            with st.spinner(f"Risoluzione di {len(rows)} descrizioni in corso..."):
                resolved = resolve_listino_with_cache(
                    rows,
                    factory=factory,
                    resolver_provider=resolver_provider,
                    tenant_id=DEFAULT_TENANT_ID,
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
        n_eligible = sum(1 for r in resolved if r.is_ambiguous and r.asin and len(r.candidates) > 1)
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
    st.dataframe(preview_df, use_container_width=True)

    n_resolved = sum(1 for r in resolved_with_overrides if r.asin)
    n_total = len(resolved_with_overrides)
    n_ambiguous = sum(1 for r in resolved_with_overrides if r.is_ambiguous and r.asin)
    n_overrides = len(overrides)
    cache_caption = format_cache_hit_caption(resolved_with_overrides)
    caption = (
        f"Risolti {n_resolved}/{n_total} (di cui {n_ambiguous} ambigui)."
        + (f" Override CFO applicati: {n_overrides}." if n_overrides else "")
        + (f" {cache_caption}" if cache_caption else "")
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


def main() -> None:  # noqa: C901, PLR0911, PLR0912, PLR0915 — entry-point Streamlit multi-step
    """Entrypoint Streamlit. Eseguito da `streamlit run`."""
    st.set_page_config(
        page_title="TALOS — Cruscotto Sessione",
        layout="wide",
        page_icon=":dart:",
    )
    st.title("TALOS — Scaler 500k")
    st.caption(
        "Cruscotto di sessione: input listino + budget → Cart + Panchina + Budget T+1.",
    )

    factory_for_sidebar = get_session_factory_or_none()
    budget, velocity_target, veto_threshold, lot_size = _render_sidebar(factory_for_sidebar)

    # Decisione Leader 2026-05-01 round 4 (delta=A): convivenza dei 2 flow
    # CSV. Default = nuovo (descrizione+prezzo); legacy disponibile per
    # CSV gia' strutturati con ASIN noto.
    mode = st.radio(
        "Formato listino",
        options=("Descrizione + prezzo (nuovo)", "ASIN gia' noto (legacy)"),
        horizontal=True,
        key="listino_input_mode",
    )

    locked_in_raw = st.text_input(
        "ASIN Locked-in (separati da virgola)",
        value="",
        help="R-04: ASIN forzati con priorita' infinita prima del Pass 2 Tetris.",
    )
    locked_in = parse_locked_in(locked_in_raw)

    listino: pd.DataFrame | None = None
    if mode == "Descrizione + prezzo (nuovo)":
        listino = _render_descrizione_prezzo_flow(factory_for_sidebar)
        if listino is None:
            return
    else:
        uploaded = st.file_uploader(
            "Carica Listino di Sessione (CSV)",
            type=["csv"],
            help=f"Colonne richieste: {', '.join(REQUIRED_INPUT_COLUMNS)}.",
            key="listino_legacy_uploader",
        )
        if uploaded is None:
            st.info("Carica un CSV per iniziare.")
            return

        try:
            listino = pd.read_csv(uploaded)
        except (pd.errors.ParserError, ValueError) as exc:  # pragma: no cover - UI-only
            st.error(f"Errore parsing CSV: {exc}")
            return

        if not st.button("Esegui Sessione"):
            st.dataframe(listino.head(20), use_container_width=True)
            st.caption(f"Anteprima ({min(len(listino), 20)} righe). Premi 'Esegui Sessione'.")
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
        st.dataframe(result.enriched_df, use_container_width=True)

    # Persistenza opzionale: graceful degrade se DB non disponibile.
    factory = get_session_factory_or_none()
    st.subheader("Persistenza Sessione")
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
            st.success(f"Sessione persistita. id = `{sid}`.")
        else:  # pragma: no cover - UI-only error path
            st.error(f"Persistenza fallita: {err}")

    _render_history(factory, tenant_id=DEFAULT_TENANT_ID)


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
