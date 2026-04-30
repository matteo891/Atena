"""Unit test per `talos.orchestrator` (CHG-2026-04-30-039, ADR-0018).

Pipeline end-to-end: `run_session(SessionInput) -> SessionResult`. Compone
F1..F5 + ROI + fee_fba (formulas) + min_max_normalize + compute_vgp_score
(vgp) + allocate_tetris + build_panchina (tetris) + compounding_t1 (F3).
"""

from __future__ import annotations

import pandas as pd
import pytest

from talos.orchestrator import (
    KILLED_STATUSES,
    REQUIRED_INPUT_COLUMNS,
    SessionInput,
    SessionResult,
    run_session,
)
from talos.tetris import Cart, InsufficientBudgetError

pytestmark = pytest.mark.unit


def _samsung_listino() -> pd.DataFrame:
    """Mini listino realistic Samsung-like.

    BuyBox >= 122 EUR (fee_fba_manual L11b non raise). ROI > 8% per la
    maggior parte (R-08 lascia passare). v_tot > 0, s_comp piccoli.
    """
    return pd.DataFrame(
        [
            # asin, buy_box, cost, ref_pct, v_tot, s_comp, status
            ("AAA111", 200.0, 100.0, 0.08, 60.0, 2, "MATCH"),
            ("BBB222", 500.0, 300.0, 0.15, 30.0, 1, "MATCH"),
            ("CCC333", 1000.0, 600.0, 0.08, 15.0, 0, "MATCH"),
            ("DDD444", 250.0, 240.0, 0.08, 45.0, 4, "MATCH"),  # ROI bassissimo -> R-08
            ("EEE555", 300.0, 150.0, 0.10, 20.0, 1, "MISMATCH"),  # killed (R-05)
        ],
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


# Defaults & metadata


def test_required_input_columns_match_doc() -> None:
    """REQUIRED_INPUT_COLUMNS allineato alla documentazione (ADR-0015 listino_items)."""
    expected = {
        "asin",
        "buy_box_eur",
        "cost_eur",
        "referral_fee_pct",
        "v_tot",
        "s_comp",
        "match_status",
    }
    assert set(REQUIRED_INPUT_COLUMNS) == expected


def test_killed_statuses_includes_mismatch_and_killed() -> None:
    """KILLED_STATUSES include almeno MISMATCH e KILLED (NLP filter)."""
    assert "MISMATCH" in KILLED_STATUSES
    assert "KILLED" in KILLED_STATUSES


# Pipeline end-to-end


def test_run_session_returns_session_result() -> None:
    """Smoke test: run_session ritorna SessionResult con i 4 attributi."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    assert isinstance(result, SessionResult)
    assert isinstance(result.cart, Cart)
    assert isinstance(result.panchina, pd.DataFrame)
    assert isinstance(result.budget_t1, float)
    assert isinstance(result.enriched_df, pd.DataFrame)


def test_run_session_enriched_df_has_all_columns() -> None:
    """Enriched_df contiene tutte le colonne calcolate + score."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    expected_cols = {
        "asin",
        "buy_box_eur",
        "cost_eur",
        "fee_fba_eur",
        "cash_inflow_eur",
        "cash_profit_eur",
        "roi",
        "q_m",
        "velocity_monthly",
        "qty_target",
        "qty_final",
        "kill_mask",
        "roi_norm",
        "velocity_norm",
        "cash_profit_norm",
        "vgp_score_raw",
        "veto_roi_passed",
        "vgp_score",
    }
    assert expected_cols.issubset(set(result.enriched_df.columns))


def test_run_session_enriched_sorted_by_vgp_desc() -> None:
    """Enriched_df e' ordinato per vgp_score DESC (contratto allocator)."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    scores = list(result.enriched_df["vgp_score"])
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_run_session_killed_asin_has_zero_score() -> None:
    """ASIN con match_status=MISMATCH ha vgp_score=0 (R-05)."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    killed = result.enriched_df[result.enriched_df["asin"] == "EEE555"].iloc[0]
    assert bool(killed["kill_mask"]) is True
    assert float(killed["vgp_score"]) == pytest.approx(0.0)


def test_run_session_low_roi_asin_vetoed() -> None:
    """ASIN con ROI sotto 8% (R-08) ha veto_roi_passed=False e vgp_score=0."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    # DDD444: ROI = (250-fee-250*0.08-240)/240 = decisamente sotto 8%
    vetoed = result.enriched_df[result.enriched_df["asin"] == "DDD444"].iloc[0]
    assert bool(vetoed["veto_roi_passed"]) is False
    assert float(vetoed["vgp_score"]) == pytest.approx(0.0)


def test_run_session_cart_excludes_vetoed_and_killed() -> None:
    """Cart non contiene ne' i vetati ne' i killed."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=10000.0)
    result = run_session(inp)
    cart_asins = set(result.cart.asin_list())
    assert "EEE555" not in cart_asins  # killed
    assert "DDD444" not in cart_asins  # vetoed


def test_run_session_panchina_excludes_killed_vetoed_and_cart() -> None:
    """Panchina = idonei (vgp_score>0) NON in cart."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=200.0)  # budget tight
    result = run_session(inp)
    panchina_asins = set(result.panchina["asin"])
    cart_asins = set(result.cart.asin_list())
    # Nessuna sovrapposizione cart/panchina
    assert panchina_asins.isdisjoint(cart_asins)
    # Nessun vetato/killed in panchina
    assert "EEE555" not in panchina_asins
    assert "DDD444" not in panchina_asins


def test_run_session_budget_t1_equals_budget_plus_cart_profits() -> None:
    """budget_t1 = budget + somma(cash_profit_per_unit * qty) per item nel cart."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=10000.0)
    result = run_session(inp)
    expected_profits = 0.0
    for item in result.cart.items:
        row = result.enriched_df[result.enriched_df["asin"] == item.asin].iloc[0]
        expected_profits += float(row["cash_profit_eur"]) * item.qty
    assert result.budget_t1 == pytest.approx(inp.budget + expected_profits, abs=1e-6)


# Locked-in (R-04)


def test_run_session_locked_in_added_first() -> None:
    """Locked-in entra prima del Pass 2 anche se non top VGP."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=10000.0,
        locked_in=["AAA111"],  # forziamo AAA111 come locked
    )
    result = run_session(inp)
    assert result.cart.items[0].asin == "AAA111"
    assert result.cart.items[0].locked is True


def test_run_session_locked_in_insufficient_budget_raises() -> None:
    """Locked-in con cost > budget -> InsufficientBudgetError propagata."""
    inp = SessionInput(
        listino_raw=_samsung_listino(),
        budget=50.0,  # budget irrisorio
        locked_in=["CCC333"],  # 1000*qty, costera' molto di piu'
    )
    with pytest.raises(InsufficientBudgetError):
        run_session(inp)


# Validazioni input (R-01)


def test_run_session_missing_columns_raises() -> None:
    """Listino senza colonne richieste -> ValueError."""
    bad_df = pd.DataFrame({"asin": ["A"], "buy_box_eur": [200.0]})  # mancano altre 5
    inp = SessionInput(listino_raw=bad_df, budget=1000.0)
    with pytest.raises(ValueError, match="colonne richieste mancanti"):
        run_session(inp)


def test_run_session_invalid_budget_propagates_from_allocator() -> None:
    """budget <= 0 -> ValueError dall'allocator."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=0.0)
    with pytest.raises(ValueError, match="budget"):
        run_session(inp)


def test_run_session_low_buy_box_propagates_fee_fba_error() -> None:
    """BuyBox sotto soglia (scorporato < 100) -> fee_fba_manual raise propagato."""
    bad_listino = pd.DataFrame(
        [("X", 50.0, 30.0, 0.08, 10.0, 0, "MATCH")],  # buy_box=50, scorporato=40.98 < 100
        columns=list(REQUIRED_INPUT_COLUMNS),
    )
    inp = SessionInput(listino_raw=bad_listino, budget=1000.0)
    with pytest.raises(ValueError, match=r"(?i)scorporato|buy_box"):
        run_session(inp)


# Defaults SessionInput


def test_session_input_defaults() -> None:
    """SessionInput defaults: locked_in=[], days=15, threshold=0.08, lot=5."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=1000.0)
    assert inp.locked_in == []
    assert inp.velocity_target_days == 15
    assert inp.veto_roi_threshold == pytest.approx(0.08)
    assert inp.lot_size == 5


def test_session_input_is_frozen() -> None:
    """SessionInput frozen=True -> immutable."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=1000.0)
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError o equivalent
        inp.budget = 2000.0  # type: ignore[misc]


# Edge cases


def test_run_session_empty_listino() -> None:
    """Listino vuoto -> Cart vuoto, panchina vuota, budget_t1 = budget."""
    empty_df = pd.DataFrame(columns=list(REQUIRED_INPUT_COLUMNS))
    inp = SessionInput(listino_raw=empty_df, budget=1000.0)
    result = run_session(inp)
    assert len(result.cart.items) == 0
    assert len(result.panchina) == 0
    assert result.budget_t1 == pytest.approx(1000.0)


def test_run_session_all_killed_listino() -> None:
    """Listino con tutti gli ASIN killed -> cart vuoto, panchina vuota."""
    df = pd.DataFrame(
        [
            ("A", 200.0, 100.0, 0.08, 30.0, 0, "MISMATCH"),
            ("B", 500.0, 300.0, 0.15, 20.0, 1, "MISMATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )
    inp = SessionInput(listino_raw=df, budget=10000.0)
    result = run_session(inp)
    assert len(result.cart.items) == 0
    assert len(result.panchina) == 0
    assert result.budget_t1 == pytest.approx(10000.0)


def test_run_session_input_listino_not_mutated() -> None:
    """Il listino raw passato come input non viene modificato in place."""
    listino = _samsung_listino()
    cols_before = list(listino.columns)
    inp = SessionInput(listino_raw=listino, budget=2000.0)
    _ = run_session(inp)
    assert list(listino.columns) == cols_before  # nessuna colonna aggiunta
