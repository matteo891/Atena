"""Golden test mini-Samsung — snapshot byte-exact pipeline e2e.

CHG-2026-04-30-041, ADR-0019.

Scenario fissato 10 ASIN che copre tutti i casi canonici:
- Top/High/Mid/Low VGP (R-06 ranking)
- Locked-in (R-04: S004_GOOD forzato)
- Vetoed ROI < 8% (R-08: S006_VETO, S007_VETO2)
- Killed match status (R-05: S008_KILL `MISMATCH`, S009_KILL2 `KILLED`)
- F5 Floor azzera (S010_TINY: q_m=2 -> qty_final=0 -> Pass 2 skip)
- Saturazione parziale (cart non satura il budget)
- Panchina popolata

Lo snapshot e' byte-exact (tolerance 1e-6 EUR / 1e-9 score). Differenza
oltre soglia = pipeline cambiata. Aggiornare lo snapshot e' un'azione
deliberata (errata corrige ADR-0018 o nuovo CHG documentato).

Differenza vs `tests/unit/test_value_chain.py` (CHG-028/033):
- value_chain testa la **catena scalare** (F1->F2->F3 + ROI + Veto), riga per riga.
- questo golden testa la **pipeline vettoriale completa** (run_session) con
  output `SessionResult` snapshot. Sentinella complementare.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from talos.orchestrator import SessionInput, SessionResult, run_session

pytestmark = pytest.mark.golden

# Tolleranze: pandas float64 + sequenza di operazioni →
# - score: snapshot a 6 decimali (round print), drift float reale entro 1e-5.
# - EUR: byte-exact entro 1e-6.
_TOL_EUR = 1e-6
_TOL_SCORE = 1e-5


def _golden_listino() -> pd.DataFrame:
    """Listino fissato Samsung-like, 10 ASIN. NON modificare senza nuovo CHG."""
    return pd.DataFrame(
        [
            ("S001_TOP", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("S002_HIGH", 800.0, 480.0, 0.10, 40.0, 0, "MATCH"),
            ("S003_MID", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            ("S004_GOOD", 400.0, 240.0, 0.08, 20.0, 1, "MATCH"),
            ("S005_LOW", 300.0, 180.0, 0.12, 15.0, 0, "MATCH"),
            ("S006_VETO", 250.0, 240.0, 0.08, 25.0, 1, "MATCH"),
            ("S007_VETO2", 200.0, 195.0, 0.12, 18.0, 2, "MATCH"),
            ("S008_KILL", 600.0, 350.0, 0.10, 30.0, 1, "MISMATCH"),
            ("S009_KILL2", 700.0, 400.0, 0.08, 25.0, 0, "KILLED"),
            ("S010_TINY", 180.0, 120.0, 0.08, 10.0, 4, "MATCH"),
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


# Snapshot atteso (calcolato 2026-04-30 post CHG-041 fix qty=0 in Pass 2).
# NON aggiornare senza un nuovo CHG che documenti il cambio di pipeline.

_EXPECTED_CART_ASINS: tuple[str, ...] = ("S004_GOOD", "S005_LOW", "S003_MID")
_EXPECTED_CART_LOCKED: tuple[bool, ...] = (True, False, False)
_EXPECTED_CART_QTY: tuple[int, ...] = (5, 5, 5)
_EXPECTED_CART_COST_TOTAL = 3600.0
_EXPECTED_CART_SATURATION = 0.72

_EXPECTED_PANCHINA_ASINS: tuple[str, ...] = ("S002_HIGH", "S001_TOP", "S010_TINY")

_EXPECTED_BUDGET_T1 = 6187.208180

_EXPECTED_VGP_SCORES: dict[str, float] = {
    "S001_TOP": 0.894737,
    "S002_HIGH": 0.929800,
    "S003_MID": 0.487911,
    "S004_GOOD": 0.568778,
    "S005_LOW": 0.546107,
    "S006_VETO": 0.0,
    "S007_VETO2": 0.0,
    "S008_KILL": 0.0,
    "S009_KILL2": 0.0,
    "S010_TINY": 0.328097,
}

_EXPECTED_VETO_PASSED: dict[str, bool] = {
    "S001_TOP": True,
    "S002_HIGH": True,
    "S003_MID": True,
    "S004_GOOD": True,
    "S005_LOW": True,
    "S006_VETO": False,
    "S007_VETO2": False,
    "S008_KILL": True,  # ROI passa, ma killed
    "S009_KILL2": True,  # ROI passa, ma killed
    "S010_TINY": True,
}

_EXPECTED_KILL_MASK: dict[str, bool] = {
    "S001_TOP": False,
    "S002_HIGH": False,
    "S003_MID": False,
    "S004_GOOD": False,
    "S005_LOW": False,
    "S006_VETO": False,
    "S007_VETO2": False,
    "S008_KILL": True,  # MISMATCH
    "S009_KILL2": True,  # KILLED
    "S010_TINY": False,
}


def _run_golden_session() -> SessionResult:
    """Helper: esegue run_session sul listino golden con parametri fissati."""
    inp = SessionInput(
        listino_raw=_golden_listino(),
        budget=5000.0,
        locked_in=["S004_GOOD"],
    )
    return run_session(inp)


def test_cart_asin_list_byte_exact() -> None:
    """Cart contiene esattamente i 3 ASIN attesi nell'ordine fissato."""
    result = _run_golden_session()
    assert tuple(result.cart.asin_list()) == _EXPECTED_CART_ASINS


def test_cart_locked_flags_byte_exact() -> None:
    """S004_GOOD ha locked=True (R-04), gli altri False."""
    result = _run_golden_session()
    flags = tuple(item.locked for item in result.cart.items)
    assert flags == _EXPECTED_CART_LOCKED


def test_cart_qty_byte_exact() -> None:
    """qty_final=5 per tutti e 3 (lot=5, qty_target>=5 -> Floor=5)."""
    result = _run_golden_session()
    qtys = tuple(item.qty for item in result.cart.items)
    assert qtys == _EXPECTED_CART_QTY


def test_cart_total_cost_snapshot() -> None:
    """Cart total_cost = 1200 + 900 + 1500 = 3600 (byte-exact entro tolerance EUR)."""
    result = _run_golden_session()
    assert math.isclose(
        result.cart.total_cost,
        _EXPECTED_CART_COST_TOTAL,
        abs_tol=_TOL_EUR,
    )


def test_cart_saturation_snapshot() -> None:
    """Saturazione = 3600 / 5000 = 0.72 esatto."""
    result = _run_golden_session()
    assert math.isclose(
        result.cart.saturation,
        _EXPECTED_CART_SATURATION,
        abs_tol=_TOL_SCORE,
    )


def test_panchina_asins_byte_exact() -> None:
    """Panchina ordinata VGP DESC: S002_HIGH > S001_TOP > S010_TINY."""
    result = _run_golden_session()
    panchina_asins = tuple(result.panchina["asin"])
    assert panchina_asins == _EXPECTED_PANCHINA_ASINS


def test_budget_t1_snapshot() -> None:
    """Budget T+1 byte-exact (entro tolerance EUR)."""
    result = _run_golden_session()
    assert math.isclose(
        result.budget_t1,
        _EXPECTED_BUDGET_T1,
        abs_tol=_TOL_EUR,
    )


def test_vgp_scores_snapshot() -> None:
    """vgp_score per ogni ASIN: byte-exact entro tolerance score."""
    result = _run_golden_session()
    enriched = result.enriched_df
    for _, row in enriched.iterrows():
        asin = str(row["asin"])
        actual_score = float(row["vgp_score"])
        expected = _EXPECTED_VGP_SCORES[asin]
        assert math.isclose(actual_score, expected, abs_tol=_TOL_SCORE), (
            f"{asin}: vgp_score atteso {expected}, ottenuto {actual_score}"
        )


def test_veto_passed_snapshot() -> None:
    """veto_roi_passed (R-08): boolean flag per ogni ASIN."""
    result = _run_golden_session()
    enriched = result.enriched_df
    for _, row in enriched.iterrows():
        asin = str(row["asin"])
        actual = bool(row["veto_roi_passed"])
        assert actual == _EXPECTED_VETO_PASSED[asin], (
            f"{asin}: veto_passed atteso {_EXPECTED_VETO_PASSED[asin]}, ottenuto {actual}"
        )


def test_kill_mask_snapshot() -> None:
    """kill_mask (R-05): True per S008_KILL e S009_KILL2."""
    result = _run_golden_session()
    enriched = result.enriched_df
    for _, row in enriched.iterrows():
        asin = str(row["asin"])
        actual = bool(row["kill_mask"])
        assert actual == _EXPECTED_KILL_MASK[asin], (
            f"{asin}: kill_mask atteso {_EXPECTED_KILL_MASK[asin]}, ottenuto {actual}"
        )


def test_zero_qty_excluded_from_cart() -> None:
    """Sentinella regression CHG-041: qty_final=0 -> NON in cart, MA in panchina (idoneo).

    S010_TINY ha q_m=2.0, qty_target=1.0, qty_final=Floor(1/5)*5=0.
    """
    result = _run_golden_session()
    cart_asins = set(result.cart.asin_list())
    panchina_asins = set(result.panchina["asin"])
    assert "S010_TINY" not in cart_asins
    assert "S010_TINY" in panchina_asins


def test_killed_asin_excluded_from_panchina() -> None:
    """Killed (R-05) -> vgp_score=0 -> non in cart NE in panchina."""
    result = _run_golden_session()
    cart_asins = set(result.cart.asin_list())
    panchina_asins = set(result.panchina["asin"])
    for killed_asin in ("S008_KILL", "S009_KILL2"):
        assert killed_asin not in cart_asins
        assert killed_asin not in panchina_asins


def test_vetoed_asin_excluded_from_panchina() -> None:
    """Vetoed R-08 -> vgp_score=0 -> non in cart NE in panchina."""
    result = _run_golden_session()
    cart_asins = set(result.cart.asin_list())
    panchina_asins = set(result.panchina["asin"])
    for vetoed_asin in ("S006_VETO", "S007_VETO2"):
        assert vetoed_asin not in cart_asins
        assert vetoed_asin not in panchina_asins
