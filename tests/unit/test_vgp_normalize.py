"""Unit test per `talos.vgp.normalize` (CHG-2026-04-30-034, ADR-0018).

L04b verbatim Round 4: *"normalizzazione min-max [0,1] sul listino di
sessione, escludendo righe KILLED dal calcolo di min/max"*.

Comprende test deterministici (snapshot + edge case) e property-based
via Hypothesis (ADR-0018 sez. "Property-based tests" + ADR-0019).
"""

from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from talos.vgp.normalize import min_max_normalize

pytestmark = pytest.mark.unit


# Snapshot deterministici


def test_no_kill_simple_series() -> None:
    """Serie [10, 20, 30], no kill -> [0.0, 0.5, 1.0]."""
    s = pd.Series([10.0, 20.0, 30.0])
    k = pd.Series([False, False, False])
    result = min_max_normalize(s, k)
    assert list(result) == pytest.approx([0.0, 0.5, 1.0])


def test_kill_excluded_from_min_max() -> None:
    """Riga killed esclusa dal calcolo di min/max; valori eligible normalizzati su [1,4]."""
    # eligible = [1, 2, 3, 4]; min=1, max=4. La riga killed (100) NON entra in min/max.
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])
    k = pd.Series([False, False, False, False, True])
    result = min_max_normalize(s, k)
    assert result.iloc[0] == pytest.approx(0.0)
    assert result.iloc[1] == pytest.approx(1.0 / 3.0)
    assert result.iloc[2] == pytest.approx(2.0 / 3.0)
    assert result.iloc[3] == pytest.approx(1.0)
    # La riga killed riceve la formula applicata: (100-1)/(4-1) = 33.0
    # Out-of-range by design - sara' azzerata downstream da R-05.
    assert result.iloc[4] == pytest.approx(33.0)


def test_all_killed_returns_zero_series() -> None:
    """Eligible vuoto (tutte killed) -> serie di 0.0 (edge case ADR-0018)."""
    s = pd.Series([10.0, 20.0, 30.0])
    k = pd.Series([True, True, True])
    result = min_max_normalize(s, k)
    assert list(result) == [0.0, 0.0, 0.0]


def test_max_equals_min_returns_zero_series() -> None:
    """Tutti i valori eligible identici -> serie di 0.0 (convenzione L04b)."""
    s = pd.Series([5.0, 5.0, 5.0])
    k = pd.Series([False, False, False])
    result = min_max_normalize(s, k)
    assert list(result) == [0.0, 0.0, 0.0]


def test_single_eligible_returns_zero_series() -> None:
    """Una sola riga eligible -> max==min -> 0.0."""
    s = pd.Series([10.0, 20.0])
    k = pd.Series([False, True])
    result = min_max_normalize(s, k)
    # eligible = [10], min=max=10 -> tutto 0.0 (anche la riga killed e' 0 by formula)
    assert list(result) == [0.0, 0.0]


def test_negative_values_supported() -> None:
    """Cash_Profit puo' essere negativo (loss); min-max funziona comunque."""
    s = pd.Series([-100.0, 0.0, 100.0])
    k = pd.Series([False, False, False])
    result = min_max_normalize(s, k)
    assert list(result) == pytest.approx([0.0, 0.5, 1.0])


def test_preserves_index() -> None:
    """Index originale preservato (importante per join downstream con vgp_df)."""
    s = pd.Series([1.0, 2.0, 3.0], index=["a", "b", "c"])
    k = pd.Series([False, False, False], index=["a", "b", "c"])
    result = min_max_normalize(s, k)
    assert list(result.index) == ["a", "b", "c"]


def test_mismatched_index_raises_value_error() -> None:
    """Index disallineato -> ValueError esplicito (R-01 NO SILENT DROPS)."""
    s = pd.Series([1.0, 2.0], index=[0, 1])
    k = pd.Series([False, False], index=[2, 3])
    with pytest.raises(ValueError, match="indici"):
        min_max_normalize(s, k)


def test_empty_series() -> None:
    """Serie vuota -> output vuoto (eligible vuoto -> serie 0.0 di lunghezza 0)."""
    s = pd.Series([], dtype=float)
    k = pd.Series([], dtype=bool)
    result = min_max_normalize(s, k)
    assert len(result) == 0


def test_two_distinct_values() -> None:
    """Caso minimo con discriminazione: 2 eligible distinti -> [0.0, 1.0]."""
    s = pd.Series([3.0, 7.0])
    k = pd.Series([False, False])
    result = min_max_normalize(s, k)
    assert list(result) == pytest.approx([0.0, 1.0])


# Property-based (Hypothesis - ADR-0018 + ADR-0019)


@given(
    values=st.lists(
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        min_size=2,
        max_size=50,
    ),
)
def test_property_no_kill_normalized_in_unit_range(values: list[float]) -> None:
    """Property: con kill_mask tutto False, output ∈ [0, 1] per ogni elemento."""
    s = pd.Series(values)
    k = pd.Series([False] * len(values))
    assume(s.min() != s.max())  # max==min e' edge case separato (ritorna 0.0)
    result = min_max_normalize(s, k)
    assert (result >= 0.0).all()
    assert (result <= 1.0).all()


@given(
    values=st.lists(
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        min_size=2,
        max_size=50,
    ),
)
def test_property_min_maps_to_zero(values: list[float]) -> None:
    """Property: il valore min (eligible) mappa a 0.0."""
    s = pd.Series(values)
    k = pd.Series([False] * len(values))
    assume(s.min() != s.max())
    result = min_max_normalize(s, k)
    min_indices = s[s == s.min()].index
    for idx in min_indices:
        assert result.loc[idx] == pytest.approx(0.0)


@given(
    values=st.lists(
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        min_size=2,
        max_size=50,
    ),
)
def test_property_max_maps_to_one(values: list[float]) -> None:
    """Property: il valore max (eligible) mappa a 1.0."""
    s = pd.Series(values)
    k = pd.Series([False] * len(values))
    assume(s.min() != s.max())
    result = min_max_normalize(s, k)
    max_indices = s[s == s.max()].index
    for idx in max_indices:
        assert result.loc[idx] == pytest.approx(1.0)
