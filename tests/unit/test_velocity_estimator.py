"""Unit test `talos.extract.velocity_estimator` (CHG-2026-05-02-003).

Helper puri MVP per stimare V_tot da BSR. Pattern test isolato +
property-style su scaling logaritmico + sentinel sui flag audit.

> NB: questi test verificano la **forma matematica** della formula
> placeholder, NON la **calibrazione canonica** (che richiede ground
> truth, scope futuro). Cambiare le costanti senza ratifica Leader.
"""

from __future__ import annotations

import math

import pytest

from talos.extract.velocity_estimator import (
    V_TOT_SOURCE_BSR_ESTIMATE,
    V_TOT_SOURCE_CSV,
    V_TOT_SOURCE_DEFAULT_ZERO,
    estimate_v_tot_from_bsr,
    resolve_v_tot,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# `estimate_v_tot_from_bsr` — formula log-lineare placeholder
# ---------------------------------------------------------------------------


def test_estimate_returns_zero_for_none_bsr() -> None:
    """`bsr=None` -> 0.0 (caller decide se escludere o warning)."""
    assert estimate_v_tot_from_bsr(None) == 0.0


def test_estimate_returns_zero_for_invalid_bsr() -> None:
    """`bsr<=0` invalido -> 0.0."""
    assert estimate_v_tot_from_bsr(0) == 0.0
    assert estimate_v_tot_from_bsr(-100) == 0.0


def test_estimate_peak_at_bsr_1() -> None:
    """BSR=1 (best seller assoluto) -> intercept=100 v/mese."""
    assert estimate_v_tot_from_bsr(1) == pytest.approx(100.0)


def test_estimate_decays_logarithmically() -> None:
    """V_tot decresce log-lineare con BSR (formula placeholder)."""
    # log10(100)=2 -> 100 - 20*2 = 60
    assert estimate_v_tot_from_bsr(100) == pytest.approx(60.0)
    # log10(10000)=4 -> 100 - 80 = 20
    assert estimate_v_tot_from_bsr(10000) == pytest.approx(20.0)


def test_estimate_clamps_to_min_for_very_high_bsr() -> None:
    """BSR molto alto -> formula andrebbe negativa, clamp a 1.0 (R-01)."""
    # log10(1e8)=8 -> 100 - 160 = -60 -> clamp 1.0
    assert estimate_v_tot_from_bsr(100_000_000) == pytest.approx(1.0)


def test_estimate_monotonically_decreasing() -> None:
    """Property: bsr1 < bsr2 -> v_tot(bsr1) >= v_tot(bsr2)."""
    bsrs = [1, 10, 100, 1000, 10_000, 100_000]
    values = [estimate_v_tot_from_bsr(b) for b in bsrs]
    for i in range(len(values) - 1):
        assert values[i] >= values[i + 1], f"non-monotone at bsr={bsrs[i]}"


# ---------------------------------------------------------------------------
# `resolve_v_tot` — strategy hybrid CSV-override / BSR-fallback / default
# ---------------------------------------------------------------------------


def test_resolve_csv_override_wins_over_bsr() -> None:
    """Se CSV ha v_tot>0, ignora BSR (override esplicito CFO)."""
    v, source = resolve_v_tot(csv_v_tot=50, bsr_root=10000)
    assert v == 50.0
    assert source == V_TOT_SOURCE_CSV


def test_resolve_csv_zero_uses_bsr_estimate() -> None:
    """CSV v_tot=0 (default) AND bsr disponibile -> stima MVP."""
    v, source = resolve_v_tot(csv_v_tot=0, bsr_root=10000)
    assert v == pytest.approx(20.0)
    assert source == V_TOT_SOURCE_BSR_ESTIMATE


def test_resolve_csv_zero_no_bsr_returns_default_zero() -> None:
    """Nessun override CSV + nessun BSR -> 0 + flag default."""
    v, source = resolve_v_tot(csv_v_tot=0, bsr_root=None)
    assert v == 0.0
    assert source == V_TOT_SOURCE_DEFAULT_ZERO


def test_resolve_audit_flags_are_distinct() -> None:
    """I 3 flag sono distinti (lock contract anti-collisione)."""
    flags = {V_TOT_SOURCE_CSV, V_TOT_SOURCE_BSR_ESTIMATE, V_TOT_SOURCE_DEFAULT_ZERO}
    assert len(flags) == 3


def test_resolve_csv_one_is_csv_source() -> None:
    """csv_v_tot=1 conta come override esplicito (boundary)."""
    v, source = resolve_v_tot(csv_v_tot=1, bsr_root=10000)
    assert v == 1.0
    assert source == V_TOT_SOURCE_CSV


def test_estimate_doctest_consistency() -> None:
    """Sanity: `math.log10(10000)=4`, `100-20*4=20`. Lock formula MVP."""
    assert estimate_v_tot_from_bsr(10000) == 100.0 - 20.0 * math.log10(10000)
