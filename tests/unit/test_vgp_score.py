"""Unit test per `talos.vgp.score` (CHG-2026-04-30-035, ADR-0018).

Formula VGP composita con pesi 0.4/0.4/0.2 verbatim PROJECT-RAW.md sez. 6.3
(L04 Round 3 + L04b Round 4). R-05 KILL-SWITCH (riga 223) + R-08 VETO ROI
(riga 226) applicati vettoriale.
"""

from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from talos.vgp.score import (
    CASH_PROFIT_WEIGHT,
    ROI_WEIGHT,
    VELOCITY_WEIGHT,
    compute_vgp_score,
)

pytestmark = pytest.mark.unit


def _baseline_df() -> pd.DataFrame:
    """3 ASIN distinti, no kill, tutti passano R-08."""
    return pd.DataFrame(
        {
            "roi": [0.10, 0.15, 0.30],
            "velocity_monthly": [1.0, 2.0, 4.0],
            "cash_profit_eur": [50.0, 100.0, 200.0],
            "kill_mask": [False, False, False],
        },
    )


# Snapshot deterministici


def test_weights_sum_to_one() -> None:
    """Invariante ADR-0018: pesi 0.4+0.4+0.2 = 1.0 esatti."""
    assert pytest.approx(1.0, abs=1e-12) == ROI_WEIGHT + VELOCITY_WEIGHT + CASH_PROFIT_WEIGHT


def test_baseline_no_kill_no_veto() -> None:
    """3 ASIN: il top ha tutti i max -> vgp_score = 1.0; il bottom ha tutti i min -> 0.0."""
    df = _baseline_df()
    out = compute_vgp_score(df)

    # Tutti passano R-08 (ROI >= 0.08 per i 3 ASIN: 0.10, 0.15, 0.30)
    assert list(out["veto_roi_passed"]) == [True, True, True]

    # Bottom (idx 0): tutti min -> 0.0
    assert out["vgp_score"].iloc[0] == pytest.approx(0.0)
    # Top (idx 2): tutti max -> 1.0
    assert out["vgp_score"].iloc[2] == pytest.approx(1.0)
    # Middle (idx 1): roi_norm=0.25, vel_norm=cp_norm=1/3 -> score = 0.10 + (1/3)*(0.4+0.2)
    expected_middle = 0.25 * ROI_WEIGHT + (1 / 3) * VELOCITY_WEIGHT + (1 / 3) * CASH_PROFIT_WEIGHT
    assert out["vgp_score"].iloc[1] == pytest.approx(expected_middle, abs=1e-9)


def test_input_dataframe_not_mutated() -> None:
    """compute_vgp_score restituisce copia: input invariato."""
    df = _baseline_df()
    cols_before = list(df.columns)
    _ = compute_vgp_score(df)
    assert list(df.columns) == cols_before


def test_added_columns_present() -> None:
    """6 colonne aggiunte attese."""
    out = compute_vgp_score(_baseline_df())
    expected = {
        "roi_norm",
        "velocity_norm",
        "cash_profit_norm",
        "vgp_score_raw",
        "veto_roi_passed",
        "vgp_score",
    }
    assert expected.issubset(set(out.columns))


def test_r05_kill_zeros_score() -> None:
    """R-05 KILL-SWITCH: la riga con kill_mask=True ha vgp_score=0 anche se top-ranker."""
    df = _baseline_df()
    df.loc[2, "kill_mask"] = True  # il top viene killato
    out = compute_vgp_score(df)
    assert out["vgp_score"].iloc[2] == pytest.approx(0.0)
    # Le altre 2 sono normalizzate sul range eligible [0.10, 0.15]
    assert out["vgp_score"].iloc[0] == pytest.approx(0.0)  # bottom
    assert out["vgp_score"].iloc[1] > 0.0  # middle ora e' il top eligible


def test_r08_veto_zeros_score() -> None:
    """R-08 VETO ROI: ROI < 0.08 -> vgp_score=0, veto_roi_passed=False."""
    df = pd.DataFrame(
        {
            "roi": [0.05, 0.15, 0.30],  # idx 0 sotto soglia
            "velocity_monthly": [1.0, 2.0, 4.0],
            "cash_profit_eur": [50.0, 100.0, 200.0],
            "kill_mask": [False, False, False],
        },
    )
    out = compute_vgp_score(df)
    assert not bool(out["veto_roi_passed"].iloc[0])
    assert out["vgp_score"].iloc[0] == pytest.approx(0.0)
    # Idx 1 e 2 passano
    assert bool(out["veto_roi_passed"].iloc[1])
    assert bool(out["veto_roi_passed"].iloc[2])


def test_r08_boundary_inclusive() -> None:
    """R-08 boundary: ROI esattamente == 0.08 PASSA (boundary inclusivo)."""
    df = pd.DataFrame(
        {
            "roi": [0.08, 0.08, 0.08],
            "velocity_monthly": [1.0, 2.0, 3.0],
            "cash_profit_eur": [10.0, 20.0, 30.0],
            "kill_mask": [False, False, False],
        },
    )
    out = compute_vgp_score(df)
    assert all(out["veto_roi_passed"])


def test_all_killed_all_zero() -> None:
    """Tutti killed -> tutti vgp_score=0 (e tutti i norm=0 by convention)."""
    df = _baseline_df()
    df["kill_mask"] = [True, True, True]
    out = compute_vgp_score(df)
    assert list(out["vgp_score"]) == [0.0, 0.0, 0.0]
    assert list(out["roi_norm"]) == [0.0, 0.0, 0.0]


def test_all_vetoed_all_zero() -> None:
    """Tutti sotto soglia ROI -> tutti vgp_score=0."""
    df = pd.DataFrame(
        {
            "roi": [0.01, 0.02, 0.03],
            "velocity_monthly": [1.0, 2.0, 3.0],
            "cash_profit_eur": [10.0, 20.0, 30.0],
            "kill_mask": [False, False, False],
        },
    )
    out = compute_vgp_score(df)
    assert list(out["veto_roi_passed"]) == [False, False, False]
    assert list(out["vgp_score"]) == pytest.approx([0.0, 0.0, 0.0])


def test_mixed_kill_and_veto() -> None:
    """Mix: 1 ASIN killed + 1 ASIN vetato + 1 ASIN attivo."""
    df = pd.DataFrame(
        {
            "roi": [0.20, 0.05, 0.20],  # idx 1 vetato
            "velocity_monthly": [2.0, 2.0, 4.0],
            "cash_profit_eur": [100.0, 100.0, 200.0],
            "kill_mask": [True, False, False],  # idx 0 killato
        },
    )
    out = compute_vgp_score(df)
    assert out["vgp_score"].iloc[0] == pytest.approx(0.0)  # killed
    assert out["vgp_score"].iloc[1] == pytest.approx(0.0)  # vetato
    assert out["vgp_score"].iloc[2] > 0.0  # attivo


def test_threshold_override() -> None:
    """Soglia configurabile: con threshold=0.20, ROI=0.15 viene vetato."""
    df = _baseline_df()
    out = compute_vgp_score(df, veto_roi_threshold=0.20)
    # Idx 0 (0.10) e idx 1 (0.15) ora sotto soglia
    assert list(out["veto_roi_passed"]) == [False, False, True]
    assert out["vgp_score"].iloc[2] > 0.0


def test_threshold_invalid_raises() -> None:
    """veto_roi_threshold fuori (0,1] -> ValueError."""
    df = _baseline_df()
    with pytest.raises(ValueError, match="threshold"):
        compute_vgp_score(df, veto_roi_threshold=0.0)
    with pytest.raises(ValueError, match="threshold"):
        compute_vgp_score(df, veto_roi_threshold=1.5)


def test_missing_columns_raises() -> None:
    """Colonne attese mancanti -> ValueError esplicito (R-01 NO SILENT DROPS)."""
    df = pd.DataFrame({"roi": [0.1], "velocity_monthly": [1.0]})  # mancano cash_profit + kill
    with pytest.raises(ValueError, match="colonne richieste mancanti"):
        compute_vgp_score(df)


def test_custom_column_names() -> None:
    """Override dei nomi colonna funziona end-to-end."""
    df = pd.DataFrame(
        {
            "my_roi": [0.10, 0.30],
            "my_vel": [1.0, 4.0],
            "my_cp": [50.0, 200.0],
            "my_kill": [False, False],
        },
    )
    out = compute_vgp_score(
        df,
        roi_col="my_roi",
        velocity_col="my_vel",
        cash_profit_col="my_cp",
        kill_col="my_kill",
    )
    assert out["vgp_score"].iloc[0] == pytest.approx(0.0)
    assert out["vgp_score"].iloc[1] == pytest.approx(1.0)


def test_index_preserved() -> None:
    """Index originale preservato in output."""
    df = _baseline_df()
    df.index = pd.Index(["a", "b", "c"])
    out = compute_vgp_score(df)
    assert list(out.index) == ["a", "b", "c"]


# Property-based (Hypothesis - ADR-0018 + ADR-0019)


@given(
    rois=st.lists(st.floats(min_value=0.08, max_value=2.0), min_size=2, max_size=20),
    velocities=st.lists(st.floats(min_value=0.0, max_value=10.0), min_size=2, max_size=20),
    cps=st.lists(st.floats(min_value=-100.0, max_value=1000.0), min_size=2, max_size=20),
)
@settings(suppress_health_check=[HealthCheck.differing_executors])
def test_property_score_in_unit_range_when_active(
    rois: list[float],
    velocities: list[float],
    cps: list[float],
) -> None:
    """Property: con tutti R-08 passati e nessun kill, vgp_score ∈ [0,1]."""
    n = min(len(rois), len(velocities), len(cps))
    assume(n >= 2)
    rois, velocities, cps = rois[:n], velocities[:n], cps[:n]
    # Serve discriminazione su almeno una dimensione (altrimenti tutti norm=0)
    assume(min(rois) != max(rois) or min(velocities) != max(velocities) or min(cps) != max(cps))
    df = pd.DataFrame(
        {
            "roi": rois,
            "velocity_monthly": velocities,
            "cash_profit_eur": cps,
            "kill_mask": [False] * n,
        },
    )
    out = compute_vgp_score(df)
    assert (out["vgp_score"] >= 0.0).all()
    assert (out["vgp_score"] <= 1.0).all()


@given(
    rois=st.lists(st.floats(min_value=0.08, max_value=2.0), min_size=2, max_size=10),
    velocities=st.lists(st.floats(min_value=0.0, max_value=10.0), min_size=2, max_size=10),
    cps=st.lists(st.floats(min_value=-100.0, max_value=1000.0), min_size=2, max_size=10),
    kill_idx=st.integers(min_value=0, max_value=9),
)
@settings(suppress_health_check=[HealthCheck.differing_executors])
def test_property_killed_row_score_zero(
    rois: list[float],
    velocities: list[float],
    cps: list[float],
    kill_idx: int,
) -> None:
    """Property: la riga con kill_mask=True ha sempre vgp_score=0 (R-05)."""
    n = min(len(rois), len(velocities), len(cps))
    assume(n >= 2)
    assume(kill_idx < n)
    rois, velocities, cps = rois[:n], velocities[:n], cps[:n]
    kill = [False] * n
    kill[kill_idx] = True
    df = pd.DataFrame(
        {
            "roi": rois,
            "velocity_monthly": velocities,
            "cash_profit_eur": cps,
            "kill_mask": kill,
        },
    )
    out = compute_vgp_score(df)
    assert out["vgp_score"].iloc[kill_idx] == pytest.approx(0.0)
