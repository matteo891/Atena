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
    DEFAULT_BUDGET_EUR,
    parse_locked_in,
)

__all__ = [
    "DEFAULT_BUDGET_EUR",
    "parse_locked_in",
]
