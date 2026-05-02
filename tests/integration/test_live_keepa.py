"""Test integration live `_LiveKeepaAdapter` (CHG-2026-05-01-015, ADR-0017).

Pattern coerente con `test_live_tesseract.py` (CHG-011) e
`test_live_playwright.py` (CHG-012): skip module-level se la chiave
Keepa non e' disponibile (`TalosSettings().keepa_api_key is None`).
In CI senza secrets -> skip silenzioso.

Decisioni Leader ratificate 2026-05-01 round 4:

- **A2** buybox source hierarchy (BUY_BOX_SHIPPING -> NEW -> AMAZON)
- **A** bsr source `data['SALES']`
- **alpha''** fee_fba SEMPRE `KeepaMissError` -> caller usa
  `fee_fba_manual` (L11b Frozen)

ASIN di riferimento: B0CSTC2RDW (Samsung Galaxy S24 5G), gia' usato
nei test live scraping (CHG-013). Quota Keepa consumata: ~3-5
token (1 per `query()` test + 1 per `fetch_buybox` + 1 per
`fetch_bsr` + 1 per `fetch_fee_fba`). I `fetch_*` riutilizzano
internamente la stessa query Keepa per ASIN nello stesso processo
solo se cached server-side; pessimisticamente si paga 1 token per
chiamata.
"""

from __future__ import annotations

import pytest

from talos.config.settings import TalosSettings
from talos.io_.keepa_client import (
    KeepaClient,
    KeepaMissError,
    _LiveKeepaAdapter,
)

_settings = TalosSettings()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        _settings.keepa_api_key is None,
        reason="TALOS_KEEPA_API_KEY non impostata; live Keepa skipped (CI senza secrets).",
    ),
]


_GALAXY_S24_ASIN = "B0CSTC2RDW"


@pytest.fixture
def live_adapter() -> _LiveKeepaAdapter:
    """Adapter live con la key reale; domain Amazon.it."""
    api_key = _settings.keepa_api_key
    assert api_key is not None  # narrow per mypy (verificato dal pytestmark.skipif)
    return _LiveKeepaAdapter(api_key=api_key)


@pytest.fixture
def live_client() -> KeepaClient:
    """Client live con rate limit conservativo per non sforare in test."""
    api_key = _settings.keepa_api_key
    assert api_key is not None
    return KeepaClient(api_key=api_key, rate_limit_per_minute=20)


def test_live_query_returns_buybox_bsr_and_fee_atomic(
    live_adapter: _LiveKeepaAdapter,
) -> None:
    """`query()` su ASIN reale -> buybox/bsr popolati. Post-CHG-040 errata
    alpha-prime invertita: `fee_fba_eur` ora puo' essere popolato dal
    `pickAndPackFee` Keepa (atomica, ~€3 per Samsung). Caller fallback a
    `fee_fba_manual` L11b solo se Keepa non espone il campo.
    """
    product = live_adapter.query(_GALAXY_S24_ASIN)
    assert product.asin == _GALAXY_S24_ASIN
    assert product.buybox_eur is not None
    assert product.buybox_eur > 0
    # Range plausibile per Galaxy S24 (~€500-800 in Italia 2024-2025).
    assert 400 <= float(product.buybox_eur) <= 1500
    assert product.bsr is not None
    assert product.bsr > 0
    # Post-CHG-040: fee_fba_eur puo' essere None (Keepa miss) o atomica.
    # Test live tollerante a entrambi gli stati.
    if product.fee_fba_eur is not None:
        assert 0 < float(product.fee_fba_eur) < 50  # atomica plausibile <€50


def test_live_fetch_buybox_returns_decimal(live_client: KeepaClient) -> None:
    """`KeepaClient.fetch_buybox` ritorna `Decimal` > 0 per ASIN reale."""
    buybox = live_client.fetch_buybox(_GALAXY_S24_ASIN)
    assert buybox > 0


def test_live_fetch_bsr_returns_int(live_client: KeepaClient) -> None:
    """`KeepaClient.fetch_bsr` ritorna `int` > 0 per ASIN reale."""
    bsr = live_client.fetch_bsr(_GALAXY_S24_ASIN)
    assert isinstance(bsr, int)
    assert bsr > 0


def test_live_fetch_fee_fba_atomic_or_miss(live_client: KeepaClient) -> None:
    """`fetch_fee_fba` post-CHG-040: ritorna pickAndPackFee atomica se disponibile,
    altrimenti `KeepaMissError` (caller fallback `fee_fba_manual` L11b).

    Errata alpha-prime invertita 2026-05-02 (CHG-2026-05-02-040).
    Test live tollerante a entrambi gli esiti (dipende da quale dato
    Keepa espone per l'ASIN test).
    """
    try:
        fee = live_client.fetch_fee_fba(_GALAXY_S24_ASIN)
    except KeepaMissError as exc:
        # Branch legacy alpha-prime: Keepa non espone pickAndPackFee per ASIN.
        miss_exc = exc
    else:
        miss_exc = None
        assert 0 < float(fee) < 50  # atomica plausibile range
    if miss_exc is not None:
        assert miss_exc.asin == _GALAXY_S24_ASIN
        assert miss_exc.field == "fee_fba"
