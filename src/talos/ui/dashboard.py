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

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from talos.formulas import (
    DEFAULT_LOT_SIZE,
    DEFAULT_VELOCITY_TARGET_DAYS,
)
from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
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


# Default budget UI (10k EUR) - modificabile dall'utente.
DEFAULT_BUDGET_EUR: float = 10_000.0
# Tenant default per persistenza (MVP single-tenant, ADR-0015).
DEFAULT_TENANT_ID: int = 1
# Chiave config override per soglia ROI (CHG-050).
CONFIG_KEY_VETO_ROI: str = "veto_roi_pct"


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
                _render_loaded_session_detail(loaded)


def _render_loaded_session_detail(loaded: LoadedSession) -> None:
    """Render del dettaglio di una `LoadedSession` (post-`load_session_by_id`)."""
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


def main() -> None:
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

    uploaded = st.file_uploader(
        "Carica Listino di Sessione (CSV)",
        type=["csv"],
        help=f"Colonne richieste: {', '.join(REQUIRED_INPUT_COLUMNS)}.",
    )

    locked_in_raw = st.text_input(
        "ASIN Locked-in (separati da virgola)",
        value="",
        help="R-04: ASIN forzati con priorita' infinita prima del Pass 2 Tetris.",
    )
    locked_in = parse_locked_in(locked_in_raw)

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
            _render_loaded_session_detail(loaded)


if __name__ == "__main__":  # pragma: no cover - run via streamlit CLI
    main()
