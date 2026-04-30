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

import pandas as pd
import streamlit as st

from talos.formulas import (
    DEFAULT_LOT_SIZE,
    DEFAULT_VELOCITY_TARGET_DAYS,
)
from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.tetris import InsufficientBudgetError
from talos.vgp import DEFAULT_ROI_VETO_THRESHOLD

# Default budget UI (10k EUR) - modificabile dall'utente.
DEFAULT_BUDGET_EUR: float = 10_000.0


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


def _render_sidebar() -> tuple[float, int, float, int]:
    """Sidebar: parametri sessione configurabili dal CFO.

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
    veto_threshold = st.sidebar.slider(
        "Veto ROI Minimo",
        min_value=0.01,
        max_value=0.50,
        value=DEFAULT_ROI_VETO_THRESHOLD,
        step=0.01,
        format="%.2f",
        help="R-08: ASIN con ROI sotto soglia hanno vgp_score=0 (default 8%).",
    )
    lot_size = st.sidebar.number_input(
        "Lot Size Fornitore",
        min_value=1,
        value=DEFAULT_LOT_SIZE,
        step=1,
        help="F5: Floor(qty_target / lot) * lot. Default Samsung MVP = 5.",
    )
    return float(budget), int(velocity_target), float(veto_threshold), int(lot_size)


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

    budget, velocity_target, veto_threshold, lot_size = _render_sidebar()

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

    inp = SessionInput(
        listino_raw=listino,
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


if __name__ == "__main__":  # pragma: no cover - run via streamlit CLI
    main()
