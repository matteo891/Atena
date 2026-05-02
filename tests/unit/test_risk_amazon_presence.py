"""Test unit Amazon Presence Filter (ADR-0024 / CHG-2026-05-02-031)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from talos.risk import (
    AMAZON_PRESENCE_MAX_SHARE,
    is_amazon_dominant_mask,
    passes_amazon_presence,
)
from talos.vgp import compute_vgp_score

if TYPE_CHECKING:
    from structlog.testing import LogCapture

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Costante threshold (Arsenale 180k default ratificato Leader)
# ---------------------------------------------------------------------------


def test_amazon_presence_max_share_constant() -> None:
    """Threshold 25% (Arsenale 180k default ratificato CHG-030)."""
    assert AMAZON_PRESENCE_MAX_SHARE == 0.25


# ---------------------------------------------------------------------------
# `passes_amazon_presence` scalare (R-01 boundary inclusive)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("share", "expected"),
    [
        (0.0, True),  # Amazon mai BuyBox
        (0.10, True),
        (0.25, True),  # boundary inclusivo (passa)
        (0.2501, False),  # primo valore vetato
        (0.50, False),
        (0.99, False),  # AmazonBasics-like
        (1.0, False),
        (None, True),  # ASIN nuovi senza dati → pass (decisione Leader default)
    ],
)
def test_passes_amazon_presence_boundary(
    share: float | None,
    expected: bool,  # noqa: FBT001 — `expected` è bool by parametrize design
) -> None:
    """Boundary inclusivo: ≤25% pass, >25% fail. None → True (default più liberale)."""
    assert passes_amazon_presence(share) is expected


# ---------------------------------------------------------------------------
# `is_amazon_dominant_mask` vettoriale
# ---------------------------------------------------------------------------


def test_is_amazon_dominant_mask_basic() -> None:
    """Mask vettoriale: True dove dominant (FAIL filter), False altrove."""
    series = pd.Series([0.0, 0.10, 0.25, 0.30, 0.99])
    mask = is_amazon_dominant_mask(series)
    assert mask.tolist() == [False, False, False, True, True]


def test_is_amazon_dominant_mask_nan_handling() -> None:
    """NaN → False (= NOT dominant = pass), coerente con `passes_amazon_presence(None)`."""
    series = pd.Series([0.10, float("nan"), 0.99, float("nan")])
    mask = is_amazon_dominant_mask(series)
    assert mask.tolist() == [False, False, True, False]


# ---------------------------------------------------------------------------
# Integrazione `compute_vgp_score` (graceful skip se colonna assente)
# ---------------------------------------------------------------------------


def _build_base_listino(amazon_shares: list[float | None] | None = None) -> pd.DataFrame:
    """DataFrame minimale con tutte le colonne richieste da `compute_vgp_score`.

    4 righe (non 3): la min-max normalize azzera la riga col valore minimo,
    quindi servono 4+ ASIN con valori diversificati per garantire vgp_score>0
    su tutti gli ASIN che passano i filtri.
    """
    df = pd.DataFrame(
        {
            "asin": ["B0AAA", "B0BBB", "B0CCC", "B0DDD"],
            "roi": [0.30, 0.30, 0.30, 0.30],  # tutti sopra veto 8%
            "velocity_monthly": [10.0, 20.0, 30.0, 40.0],
            "cash_profit_eur": [50.0, 60.0, 70.0, 80.0],
            "kill_mask": [False, False, False, False],
            "match_status": ["SICURO", "SICURO", "SICURO", "SICURO"],
        },
    )
    if amazon_shares is not None:
        df["amazon_buybox_share"] = amazon_shares
    return df


def test_compute_vgp_score_backwards_compat_no_amazon_col() -> None:
    """CHG-031 backwards-compat sentinel: dataframe senza `amazon_buybox_share`
    → behavior invariato (953 test esistenti devono passare).

    Min-max normalize azzera la riga con il valore minimo: serve almeno
    1 ASIN con vgp_score > 0 (quelli con valori intermedi/max).
    """
    df = _build_base_listino(amazon_shares=None)
    result = compute_vgp_score(df)
    # Almeno gli ASIN con valori intermedi/max devono avere vgp_score > 0.
    # B0DDD (max velocity + max cash_profit) dovrebbe avere score massimo.
    assert result.loc[result["asin"] == "B0DDD", "vgp_score"].iloc[0] > 0
    assert result.loc[result["asin"] == "B0CCC", "vgp_score"].iloc[0] > 0


def test_compute_vgp_score_amazon_dominant_vetoed() -> None:
    """ASIN con amazon_share > 25% → vgp_score = 0 (hard veto)."""
    df = _build_base_listino(amazon_shares=[0.10, 0.50, 0.20, 0.05])
    result = compute_vgp_score(df)
    # B0BBB (share=0.50) deve essere vetato.
    assert result.loc[result["asin"] == "B0BBB", "vgp_score"].iloc[0] == 0
    # B0DDD (max velocity + max cash_profit, share=0.05) deve passare.
    assert result.loc[result["asin"] == "B0DDD", "vgp_score"].iloc[0] > 0


def test_compute_vgp_score_amazon_boundary_inclusive() -> None:
    """Boundary inclusivo: amazon_share = 0.25 esattamente → pass."""
    df = _build_base_listino(amazon_shares=[0.25, 0.2501, 0.249, 0.10])
    result = compute_vgp_score(df)
    assert result.loc[result["asin"] == "B0BBB", "vgp_score"].iloc[0] == 0  # 0.2501 fail
    assert result.loc[result["asin"] == "B0DDD", "vgp_score"].iloc[0] > 0  # 0.10 ok


def test_compute_vgp_score_amazon_nan_passes() -> None:
    """ASIN con amazon_share NaN/None → pass (decisione Leader default)."""
    df = _build_base_listino(amazon_shares=[float("nan"), 0.50, 0.10, 0.05])
    result = compute_vgp_score(df)
    assert result.loc[result["asin"] == "B0BBB", "vgp_score"].iloc[0] == 0  # vetato 0.50
    # B0DDD (max valori + share 0.05) deve passare; B0CCC (share 0.10) anche.
    assert result.loc[result["asin"] == "B0DDD", "vgp_score"].iloc[0] > 0
    assert result.loc[result["asin"] == "B0CCC", "vgp_score"].iloc[0] > 0


# ---------------------------------------------------------------------------
# Telemetria `vgp.amazon_dominant_seller` (ADR-0021)
# ---------------------------------------------------------------------------


def test_telemetry_amazon_dominant_seller_emitted(log_capture: LogCapture) -> None:
    """Evento canonico emesso per ogni ASIN dominato da Amazon (ADR-0021).

    Pattern conforme `test_vgp_telemetry.py` (CHG-2026-04-30-049):
    fixture `log_capture` da `tests/conftest.py` (CHG-2026-05-01-031).
    """
    df = _build_base_listino(amazon_shares=[0.10, 0.50, 0.30, 0.05])
    compute_vgp_score(df)
    amazon_events = [e for e in log_capture.entries if e["event"] == "vgp.amazon_dominant_seller"]
    # 2 ASIN devono triggerare (B0BBB share=0.50 + B0CCC share=0.30).
    assert len(amazon_events) == 2
    asins = {e["asin"] for e in amazon_events}
    assert asins == {"B0BBB", "B0CCC"}
    # Tutti gli eventi devono includere threshold (extra contract).
    for event in amazon_events:
        assert event["threshold"] == AMAZON_PRESENCE_MAX_SHARE


def test_telemetry_no_amazon_event_if_all_pass(log_capture: LogCapture) -> None:
    """Nessun evento se tutti gli ASIN passano (share <= 0.25)."""
    df = _build_base_listino(amazon_shares=[0.10, 0.20, 0.05, 0.15])
    compute_vgp_score(df)
    amazon_events = [e for e in log_capture.entries if e["event"] == "vgp.amazon_dominant_seller"]
    assert amazon_events == []
