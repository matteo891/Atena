"""UI Streamlit (ADR-0016) - cruscotto militare CFO.

Inaugurato in CHG-2026-04-30-040 con `dashboard.py` mono-page MVP:
file upload listino + parametri sessione + chiamata `run_session` +
output Cart/Panchina/Budget_T+1.

Multi-page (`pages/analisi.py`, `pages/storico.py`, `pages/panchina.py`,
`pages/config.py`) + componenti (`components/grid.py`,
`components/slider.py`, `components/carrello.py`) + `state.py` sono
scope di CHG successivi (refactor ADR-0016 compliant).

Modulo non importato dalla pipeline core: per lanciare l'app
`uv run streamlit run src/talos/ui/dashboard.py`.
"""

from talos.ui.dashboard import (
    CONFIG_KEY_VETO_ROI,
    DEFAULT_BUDGET_EUR,
    DEFAULT_TENANT_ID,
    build_session_input,
    fetch_category_referral_fees_or_empty,
    fetch_existing_session_for_listino,
    fetch_loaded_session_or_none,
    fetch_recent_sessions_or_empty,
    fetch_veto_roi_threshold_or_default,
    get_session_factory_or_none,
    parse_locked_in,
    try_delete_category_referral_fee,
    try_delete_veto_roi_threshold,
    try_persist_category_referral_fee,
    try_persist_session,
    try_persist_veto_roi_threshold,
)

__all__ = [
    "CONFIG_KEY_VETO_ROI",
    "DEFAULT_BUDGET_EUR",
    "DEFAULT_TENANT_ID",
    "build_session_input",
    "fetch_category_referral_fees_or_empty",
    "fetch_existing_session_for_listino",
    "fetch_loaded_session_or_none",
    "fetch_recent_sessions_or_empty",
    "fetch_veto_roi_threshold_or_default",
    "get_session_factory_or_none",
    "parse_locked_in",
    "try_delete_category_referral_fee",
    "try_delete_veto_roi_threshold",
    "try_persist_category_referral_fee",
    "try_persist_session",
    "try_persist_veto_roi_threshold",
]
