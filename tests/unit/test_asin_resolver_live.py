"""Test unit `_LiveAsinResolver` (CHG-2026-05-01-018) — composer mock-only.

Mock di `AmazonSerpAdapter` + `lookup_callable: Callable[[str], ProductData]`.
Pattern coerente con `test_fallback_chain.py` e `test_serp_search.py`:
duck typing pure-Python, no network.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from talos.extract.asin_resolver import (
    DEFAULT_AMBIGUOUS_THRESHOLD_PCT,
    ResolutionResult,
    _LiveAsinResolver,
)
from talos.io_.fallback_chain import ProductData
from talos.io_.serp_search import SerpResult

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class _FixedSerpAdapter:
    """Mock SERP adapter: ritorna sempre la stessa lista di SerpResult."""

    def __init__(self, results: list[SerpResult]) -> None:
        self._results = results
        self.last_query: str | None = None
        self.last_max_results: int | None = None

    def search(self, query: str, *, max_results: int = 5) -> list[SerpResult]:
        self.last_query = query
        self.last_max_results = max_results
        return list(self._results[:max_results])


def _make_lookup(buybox_by_asin: dict[str, Decimal | None]) -> Callable[[str], ProductData]:
    """Mock `lookup_callable`: ritorna ProductData con buybox dal dict.

    Se asin non in dict -> KeyError simula lookup miss/error.
    """

    def lookup(asin: str) -> ProductData:
        if asin not in buybox_by_asin:
            msg = f"asin {asin} not in mock fixture"
            raise KeyError(msg)
        return ProductData(
            asin=asin,
            buybox_eur=buybox_by_asin[asin],
            bsr=None,
            fee_fba_eur=None,
            title=None,
        )

    return lookup


def _serp(asin: str, title: str, position: int = 0) -> SerpResult:
    return SerpResult(
        asin=asin,
        title=title,
        price_displayed=None,
        position=position,
    )


# ---------------------------------------------------------------------------
# Costruzione e validazione
# ---------------------------------------------------------------------------


def test_construct_with_invalid_max_candidates_raises() -> None:
    """`max_candidates <= 0` -> ValueError."""
    serp = _FixedSerpAdapter([])
    with pytest.raises(ValueError, match="max_candidates"):
        _LiveAsinResolver(serp, lambda _: None, max_candidates=0)  # type: ignore[arg-type]


def test_resolve_empty_description_raises() -> None:
    """description vuota / whitespace -> ValueError esplicito."""
    serp = _FixedSerpAdapter([])
    resolver = _LiveAsinResolver(serp, _make_lookup({}))
    with pytest.raises(ValueError, match="description vuota"):
        resolver.resolve_description("", Decimal(100))
    with pytest.raises(ValueError, match="description vuota"):
        resolver.resolve_description("   ", Decimal(100))


def test_resolve_zero_price_raises() -> None:
    """input_price_eur <= 0 -> ValueError esplicito."""
    serp = _FixedSerpAdapter([])
    resolver = _LiveAsinResolver(serp, _make_lookup({}))
    with pytest.raises(ValueError, match="input_price_eur"):
        resolver.resolve_description("desc", Decimal(0))
    with pytest.raises(ValueError, match="input_price_eur"):
        resolver.resolve_description("desc", Decimal(-5))


# ---------------------------------------------------------------------------
# Composizione SERP + lookup
# ---------------------------------------------------------------------------


def test_resolve_zero_serp_results_returns_ambiguous_no_selected() -> None:
    """SERP vuota -> ResolutionResult senza selected, is_ambiguous=True, notes."""
    serp = _FixedSerpAdapter([])
    resolver = _LiveAsinResolver(serp, _make_lookup({}))
    result = resolver.resolve_description("ProdottoIntrovabile", Decimal(100))
    assert isinstance(result, ResolutionResult)
    assert result.selected is None
    assert result.candidates == ()
    assert result.is_ambiguous is True
    assert "zero risultati SERP" in result.notes[0]


def test_resolve_happy_path_top1_strong_match() -> None:
    """Match forte (titolo combacia + prezzo combacia) -> selected top-1, NOT ambiguous."""
    serp = _FixedSerpAdapter(
        [_serp("B0CSTC2RDW", "Samsung Galaxy S24 5G 256GB Onyx Black", position=0)],
    )
    lookup = _make_lookup({"B0CSTC2RDW": Decimal("549.00")})
    resolver = _LiveAsinResolver(serp, lookup)

    result = resolver.resolve_description(
        "Samsung Galaxy S24 256GB Onyx Black",
        Decimal("549.00"),
    )

    assert result.selected is not None
    assert result.selected.asin == "B0CSTC2RDW"
    # Fuzzy alto + delta prezzo 0% -> confidence > 70 -> not ambiguous
    assert result.selected.confidence_pct > DEFAULT_AMBIGUOUS_THRESHOLD_PCT
    assert result.is_ambiguous is False
    assert result.selected.delta_price_pct == pytest.approx(0.0, abs=0.01)
    assert len(result.candidates) == 1


def test_resolve_top_n_picks_max_confidence() -> None:
    """3 candidati: il selected e' quello con max confidence_pct, non sempre il top-1 SERP."""
    serp = _FixedSerpAdapter(
        [
            # Top-1 SERP: titolo poco simile + prezzo lontano -> confidence basso
            _serp("B0WRONG001", "Galaxy A55 5G", position=0),
            # Top-2: titolo perfetto + prezzo perfetto -> alta confidence
            _serp("B0CSTC2RDW", "Samsung Galaxy S24 5G 256GB Onyx", position=1),
            # Top-3: titolo simile ma prezzo distante -> confidence media
            _serp("B0OTHER123", "Samsung Galaxy S24 256GB", position=2),
        ],
    )
    lookup = _make_lookup(
        {
            "B0WRONG001": Decimal("299.00"),  # delta enorme vs 549
            "B0CSTC2RDW": Decimal("549.00"),
            "B0OTHER123": Decimal("799.00"),  # delta moderato
        },
    )
    resolver = _LiveAsinResolver(serp, lookup)

    result = resolver.resolve_description(
        "Samsung Galaxy S24 256GB Onyx",
        Decimal("549.00"),
    )

    # Il candidato selected e' B0CSTC2RDW (top-2 SERP) per max confidence
    assert result.selected is not None
    assert result.selected.asin == "B0CSTC2RDW"
    assert len(result.candidates) == 3


def test_resolve_lookup_failure_keeps_candidate_with_buybox_none() -> None:
    """Lookup fallisce per un candidato -> esposto con buybox=None + notes annotato.

    R-01 NO SILENT DROPS UX-side: il candidato problematico NON viene
    scartato, viene esposto con confidence ridotta.
    """
    serp = _FixedSerpAdapter(
        [
            _serp("B0CSTC2RDW", "Galaxy S24 256GB", position=0),
            _serp("B0FAIL0001", "Galaxy S24 Ultra", position=1),
        ],
    )
    # B0FAIL0001 NON in dict -> KeyError -> lookup fallisce
    lookup = _make_lookup({"B0CSTC2RDW": Decimal("549.00")})
    resolver = _LiveAsinResolver(serp, lookup)

    result = resolver.resolve_description("Galaxy S24 256GB", Decimal("549.00"))

    assert len(result.candidates) == 2
    failed_cand = next(c for c in result.candidates if c.asin == "B0FAIL0001")
    assert failed_cand.buybox_eur is None
    assert failed_cand.delta_price_pct is None
    # Confidence ridotta ma esposto (non scartato)
    assert any("B0FAIL0001 lookup failed" in n for n in result.notes)


def test_resolve_all_lookups_fail_still_returns_candidates() -> None:
    """Tutti i lookup falliti -> tutti i candidates con buybox=None, selected = max fuzzy."""
    serp = _FixedSerpAdapter(
        [
            _serp("B0OTHER001", "Galaxy A55 4G", position=0),
            _serp("B0CSTC2RDW", "Samsung Galaxy S24 5G 256GB Onyx", position=1),
        ],
    )
    # Dict vuoto -> tutti i lookup falliscono
    resolver = _LiveAsinResolver(serp, _make_lookup({}))

    result = resolver.resolve_description(
        "Samsung Galaxy S24 256GB Onyx",
        Decimal("549.00"),
    )

    assert all(c.buybox_eur is None for c in result.candidates)
    assert all(c.delta_price_pct is None for c in result.candidates)
    # Selected = quello con fuzzy_title piu' alto = B0CSTC2RDW (titolo combacia perfetto)
    assert result.selected is not None
    assert result.selected.asin == "B0CSTC2RDW"
    # is_ambiguous=True perche' senza prezzo, confidence al massimo = 100*0.6 = 60 < 70
    assert result.is_ambiguous is True
    assert len(result.notes) == 2


def test_resolve_passes_max_candidates_to_serp() -> None:
    """`max_candidates` del resolver propagato a `serp.search(max_results=...)`."""
    serp = _FixedSerpAdapter([])
    resolver = _LiveAsinResolver(serp, _make_lookup({}), max_candidates=3)
    resolver.resolve_description("any", Decimal(100))
    assert serp.last_max_results == 3


def test_resolve_low_fuzzy_low_price_still_exposes_candidate() -> None:
    """Anche match scadente NON viene scartato (R-01 UX-side)."""
    serp = _FixedSerpAdapter(
        [_serp("B0RANDOM01", "Pentola Casa Cucina Inox", position=0)],
    )
    lookup = _make_lookup({"B0RANDOM01": Decimal("999.00")})
    resolver = _LiveAsinResolver(serp, lookup)

    result = resolver.resolve_description(
        "Samsung Galaxy S24 256GB",
        Decimal("549.00"),
    )

    assert result.selected is not None
    assert result.selected.asin == "B0RANDOM01"
    # Fuzzy bassissimo + prezzo lontano -> confidence sotto 70 ma candidato esposto
    assert result.is_ambiguous is True
    assert len(result.candidates) == 1


def test_resolve_perfect_fuzzy_no_price_lookup_marks_ambiguous() -> None:
    """Fuzzy 100 ma lookup fallito -> confidence = 60 -> ambiguous (R-01 UX)."""
    serp = _FixedSerpAdapter(
        [_serp("B0CSTC2RDW", "Galaxy S24 5G 256GB", position=0)],
    )
    resolver = _LiveAsinResolver(serp, _make_lookup({}))  # vuoto -> sempre fail

    result = resolver.resolve_description("Galaxy S24 5G 256GB", Decimal("549.00"))

    assert result.selected is not None
    # Fuzzy 100 + price=None -> compute_confidence(100, None) = 60
    assert result.selected.fuzzy_title_pct == pytest.approx(100.0)
    assert result.selected.confidence_pct == pytest.approx(60.0)
    # 60 < 70 -> ambiguous
    assert result.is_ambiguous is True


def test_resolve_propagates_description_to_serp() -> None:
    """La descrizione viene passata as-is alla SERP."""
    serp = _FixedSerpAdapter([])
    resolver = _LiveAsinResolver(serp, _make_lookup({}))
    resolver.resolve_description("Galaxy S24 256GB Onyx", Decimal(549))
    assert serp.last_query == "Galaxy S24 256GB Onyx"
