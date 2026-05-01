"""Test unit per `talos.extract.asin_resolver` skeleton (CHG-2026-05-01-016).

Scope CHG-016: tipi (`ResolutionCandidate`, `ResolutionResult`,
`AsinResolverProtocol`) + helper puri (`compute_confidence`,
`is_ambiguous`). Nessun adapter live, nessun network. CHG-017+
introdurranno il `_AmazonSerpAdapter` live e l'integrazione con
`lookup_product`.

Pattern coerente con `test_keepa_client.py`/`test_samsung.py`:
mock-only via Protocol, fixture pure-Python.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from talos.extract.asin_resolver import (
    CONFIDENCE_WEIGHT_PRICE,
    CONFIDENCE_WEIGHT_TITLE,
    DEFAULT_AMBIGUOUS_THRESHOLD_PCT,
    AsinResolverProtocol,
    ResolutionCandidate,
    ResolutionResult,
    compute_confidence,
    is_ambiguous,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Costanti di design
# ---------------------------------------------------------------------------


def test_confidence_weights_sum_to_one() -> None:
    """Pesi composito title/price devono sommare a 1.0 (sanity contract)."""
    assert pytest.approx(1.0) == CONFIDENCE_WEIGHT_TITLE + CONFIDENCE_WEIGHT_PRICE


def test_default_ambiguous_threshold_in_unit_range() -> None:
    """Threshold ambiguita' (0-100), default 70 (decisione Leader 2-prime/3-prime)."""
    assert 0 <= DEFAULT_AMBIGUOUS_THRESHOLD_PCT <= 100
    assert pytest.approx(70.0) == DEFAULT_AMBIGUOUS_THRESHOLD_PCT


# ---------------------------------------------------------------------------
# `compute_confidence` — pure helper
# ---------------------------------------------------------------------------


def test_compute_confidence_perfect_match() -> None:
    """Title 100 + delta_price 0 -> confidence 100."""
    assert compute_confidence(100.0, 0.0) == pytest.approx(100.0)


def test_compute_confidence_zero_match() -> None:
    """Title 0 + delta_price >= 100 -> confidence 0."""
    assert compute_confidence(0.0, 100.0) == pytest.approx(0.0)
    assert compute_confidence(0.0, 200.0) == pytest.approx(0.0)


def test_compute_confidence_strong_title_close_price() -> None:
    """Title 95 + delta 2% -> 95*0.6 + 98*0.4 = 96.2."""
    assert compute_confidence(95.0, 2.0) == pytest.approx(96.2, abs=0.01)


def test_compute_confidence_lookup_failed_no_price() -> None:
    """delta_price=None penalizza price_score=0 ma non scarta il candidato."""
    # title=80, price=None -> 80*0.6 + 0*0.4 = 48
    assert compute_confidence(80.0, None) == pytest.approx(48.0)


def test_compute_confidence_price_delta_saturates_at_zero() -> None:
    """delta > 100% (es. doppio del prezzo) -> price_score saturato a 0."""
    # title=70, delta=150 -> 70*0.6 + max(0, 100-150)*0.4 = 42 + 0 = 42
    assert compute_confidence(70.0, 150.0) == pytest.approx(42.0)


@pytest.mark.parametrize("invalid_pct", [-1.0, 101.0, -0.01])
def test_compute_confidence_title_out_of_range_raises(invalid_pct: float) -> None:
    """`fuzzy_title_pct` deve essere in [0,100]."""
    with pytest.raises(ValueError, match="fuzzy_title_pct"):
        compute_confidence(invalid_pct, 0.0)


def test_compute_confidence_negative_delta_raises() -> None:
    """`delta_price_pct` negativo invalido (delta e' un valore assoluto)."""
    with pytest.raises(ValueError, match="delta_price_pct"):
        compute_confidence(80.0, -5.0)


def test_compute_confidence_delta_zero_is_max_price_score() -> None:
    """delta_price=0 -> price_score=100, non penalizza."""
    # title=80, delta=0 -> 80*0.6 + 100*0.4 = 88
    assert compute_confidence(80.0, 0.0) == pytest.approx(88.0)


# ---------------------------------------------------------------------------
# `is_ambiguous`
# ---------------------------------------------------------------------------


def test_is_ambiguous_below_default_threshold() -> None:
    """confidence 50 < 70 -> ambiguo."""
    assert is_ambiguous(50.0) is True


def test_is_ambiguous_at_default_threshold() -> None:
    """confidence 70 == soglia -> NON ambiguo (sotto, strict)."""
    assert is_ambiguous(70.0) is False


def test_is_ambiguous_above_default_threshold() -> None:
    """confidence 95 > 70 -> NON ambiguo."""
    assert is_ambiguous(95.0) is False


def test_is_ambiguous_custom_threshold() -> None:
    """Caller puo' override il threshold (es. config_overrides L10-style)."""
    assert is_ambiguous(85.0, threshold=90.0) is True
    assert is_ambiguous(85.0, threshold=80.0) is False


# ---------------------------------------------------------------------------
# Dataclass shape (frozen, defaults)
# ---------------------------------------------------------------------------


def test_resolution_candidate_is_frozen() -> None:
    """`ResolutionCandidate` immutable (errore assegnando dopo costruzione)."""
    cand = ResolutionCandidate(
        asin="B0CSTC2RDW",
        title="Galaxy S24 5G",
        buybox_eur=Decimal("549.00"),
        fuzzy_title_pct=92.0,
        delta_price_pct=2.0,
        confidence_pct=95.0,
    )
    with pytest.raises(AttributeError):
        cand.asin = "X"  # type: ignore[misc]


def test_resolution_result_default_ambiguous_true_and_no_candidates() -> None:
    """Default conservativo: senza selected/candidates -> ambiguo + tuple vuote."""
    result = ResolutionResult(
        description="Galaxy S24 256GB Onyx Black",
        input_price_eur=Decimal("549.00"),
        selected=None,
    )
    assert result.is_ambiguous is True
    assert result.candidates == ()
    assert result.notes == ()
    assert result.selected is None


def test_resolution_result_with_selected_and_candidates() -> None:
    """Caller costruisce result con candidato top-1 + lista candidati."""
    cand = ResolutionCandidate(
        asin="B0CSTC2RDW",
        title="Samsung Galaxy S24 5G 256GB",
        buybox_eur=Decimal("549.00"),
        fuzzy_title_pct=92.0,
        delta_price_pct=2.0,
        confidence_pct=95.0,
    )
    result = ResolutionResult(
        description="Galaxy S24 256GB",
        input_price_eur=Decimal("539.00"),
        selected=cand,
        candidates=(cand,),
        is_ambiguous=False,
        notes=("top-1 SERP, price delta 1.85%",),
    )
    assert result.selected is not None
    assert result.selected.asin == "B0CSTC2RDW"
    assert len(result.candidates) == 1
    assert result.is_ambiguous is False


# ---------------------------------------------------------------------------
# Protocol shape (verifica struttura, no live)
# ---------------------------------------------------------------------------


class _MockResolver:
    """Mock implementation per test del Protocol shape."""

    def resolve_description(
        self,
        description: str,
        input_price_eur: Decimal,
    ) -> ResolutionResult:
        return ResolutionResult(
            description=description,
            input_price_eur=input_price_eur,
            selected=None,
            notes=("mock no-op",),
        )


def test_mock_resolver_satisfies_protocol() -> None:
    """Verifica che un mock duck-typato sia accettato dal Protocol."""
    resolver: AsinResolverProtocol = _MockResolver()
    result = resolver.resolve_description("desc", Decimal(100))
    assert isinstance(result, ResolutionResult)
    assert result.selected is None
    assert result.is_ambiguous is True
    assert result.notes == ("mock no-op",)
