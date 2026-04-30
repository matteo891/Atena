"""Unit test per `referral_fee_overrides` (CHG-2026-04-30-053).

Verifica che `_enrich_listino` (e tramite `run_session`) risolva la
`referral_fee` da una mappa `category_node → fee_pct` quando fornita,
con fallback al `referral_fee_pct` raw negli altri casi.
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.orchestrator import (
    CATEGORY_NODE_COLUMN,
    REQUIRED_INPUT_COLUMNS,
    SessionInput,
    _resolve_referral_fee,
    run_session,
)

pytestmark = pytest.mark.unit


def _listino_with_categories() -> pd.DataFrame:
    """Mini listino con colonna `category_node` (BuyBox sopra soglia fee_fba)."""
    cols = [*REQUIRED_INPUT_COLUMNS, CATEGORY_NODE_COLUMN]
    return pd.DataFrame(
        [
            ("AA01", 200.0, 100.0, 0.08, 50.0, 1, "MATCH", "Books"),
            ("AA02", 500.0, 300.0, 0.15, 30.0, 1, "MATCH", "Electronics"),
            ("AA03", 1000.0, 600.0, 0.08, 15.0, 0, "MATCH", "Books"),
        ],
        columns=cols,
    )


def _listino_without_categories() -> pd.DataFrame:
    """Mini listino legacy senza colonna `category_node`."""
    return pd.DataFrame(
        [
            ("BB01", 200.0, 100.0, 0.08, 50.0, 1, "MATCH"),
            ("BB02", 500.0, 300.0, 0.15, 30.0, 1, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_resolve_referral_fee_no_overrides_uses_raw() -> None:
    """`overrides=None` → usa sempre `referral_fee_pct`."""
    row = pd.Series({"referral_fee_pct": 0.12, CATEGORY_NODE_COLUMN: "Books"})
    assert _resolve_referral_fee(row, None) == pytest.approx(0.12)


def test_resolve_referral_fee_no_category_col_uses_raw() -> None:
    """Colonna `category_node` mancante → usa `referral_fee_pct` raw."""
    row = pd.Series({"referral_fee_pct": 0.10})
    assert _resolve_referral_fee(row, {"Books": 0.05}) == pytest.approx(0.10)


def test_resolve_referral_fee_category_in_map_uses_override() -> None:
    """Override applicato quando `category_node` matcha una chiave della mappa."""
    row = pd.Series({"referral_fee_pct": 0.10, CATEGORY_NODE_COLUMN: "Books"})
    assert _resolve_referral_fee(row, {"Books": 0.05}) == pytest.approx(0.05)


def test_resolve_referral_fee_category_not_in_map_fallback_raw() -> None:
    """`category_node` non nella mappa → fallback `referral_fee_pct` raw."""
    row = pd.Series({"referral_fee_pct": 0.12, CATEGORY_NODE_COLUMN: "Toys"})
    assert _resolve_referral_fee(row, {"Books": 0.05}) == pytest.approx(0.12)


def test_run_session_applies_overrides_to_cash_inflow() -> None:
    """End-to-end: override → `cash_inflow_eur` calcolato con fee scontata."""
    overrides = {"Books": 0.04, "Electronics": 0.20}  # Books riduce, Electronics aumenta
    inp_with = SessionInput(
        listino_raw=_listino_with_categories(),
        budget=10_000.0,
        referral_fee_overrides=overrides,
    )
    inp_without = SessionInput(
        listino_raw=_listino_with_categories(),
        budget=10_000.0,
    )
    result_with = run_session(inp_with)
    result_without = run_session(inp_without)

    enriched_with = result_with.enriched_df.set_index("asin")
    enriched_without = result_without.enriched_df.set_index("asin")

    # AA01 (Books): override 0.04 vs raw 0.08 → cash_inflow_with > cash_inflow_without
    assert (
        enriched_with.loc["AA01", "cash_inflow_eur"]
        > enriched_without.loc["AA01", "cash_inflow_eur"]
    )
    # AA02 (Electronics): override 0.20 vs raw 0.15 → cash_inflow_with < cash_inflow_without
    assert (
        enriched_with.loc["AA02", "cash_inflow_eur"]
        < enriched_without.loc["AA02", "cash_inflow_eur"]
    )
    # `referral_fee_resolved` colonna presente in entrambi i casi
    assert "referral_fee_resolved" in enriched_with.columns
    assert "referral_fee_resolved" in enriched_without.columns
    assert enriched_with.loc["AA01", "referral_fee_resolved"] == pytest.approx(0.04)
    assert enriched_without.loc["AA01", "referral_fee_resolved"] == pytest.approx(0.08)


def test_run_session_legacy_listino_without_category_node() -> None:
    """Listino senza `category_node` continua a funzionare (fallback raw)."""
    inp = SessionInput(
        listino_raw=_listino_without_categories(),
        budget=5000.0,
        referral_fee_overrides={"Books": 0.05},  # ignorato
    )
    result = run_session(inp)
    enriched = result.enriched_df.set_index("asin")
    # `referral_fee_resolved` == `referral_fee_pct` raw per ogni riga.
    assert enriched.loc["BB01", "referral_fee_resolved"] == pytest.approx(0.08)
    assert enriched.loc["BB02", "referral_fee_resolved"] == pytest.approx(0.15)


def test_run_session_empty_overrides_dict_uses_raw() -> None:
    """`overrides={}` (truthy False) → identico a `overrides=None`."""
    inp_empty = SessionInput(
        listino_raw=_listino_with_categories(),
        budget=10_000.0,
        referral_fee_overrides={},
    )
    inp_none = SessionInput(
        listino_raw=_listino_with_categories(),
        budget=10_000.0,
    )
    enriched_empty = run_session(inp_empty).enriched_df.set_index("asin")
    enriched_none = run_session(inp_none).enriched_df.set_index("asin")
    for asin in ("AA01", "AA02", "AA03"):
        assert enriched_empty.loc[asin, "cash_inflow_eur"] == pytest.approx(
            enriched_none.loc[asin, "cash_inflow_eur"],
        )
