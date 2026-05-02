"""Test unit per `talos.io_.keepa_client` (CHG-2026-05-01-001, ADR-0017).

Pattern: mock `KeepaApiAdapter` iniettato via `adapter_factory`,
nessun network. Per i test di retry/rate-limit, i wait esponenziali
sono azzerati (`retry_wait_min_s=0.0`, `retry_wait_max_s=0.0`) per
evitare sleep reali.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from talos.io_ import (
    KeepaApiAdapter,
    KeepaClient,
    KeepaMissError,
    KeepaProduct,
    KeepaRateLimitExceededError,
    KeepaTransientError,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock adapter helpers
# ---------------------------------------------------------------------------


class _FixedAdapter:
    """Mock adapter che ritorna sempre lo stesso prodotto."""

    def __init__(self, product: KeepaProduct) -> None:
        self.product = product
        self.calls = 0

    def query(self, asin: str) -> KeepaProduct:  # noqa: ARG002 — mock
        self.calls += 1
        return self.product


class _FlakyAdapter:
    """Mock che fallisce N volte con KeepaTransientError, poi succede."""

    def __init__(self, fail_n: int, product: KeepaProduct) -> None:
        self.fail_n = fail_n
        self.product = product
        self.calls = 0

    def query(self, asin: str) -> KeepaProduct:  # noqa: ARG002 — mock
        self.calls += 1
        if self.calls <= self.fail_n:
            msg = f"transient #{self.calls}"
            raise KeepaTransientError(msg)
        return self.product


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(
    adapter: KeepaApiAdapter,
    *,
    rate_limit_per_minute: int = 60,
    retry_max_attempts: int = 5,
) -> KeepaClient:
    """Helper: KeepaClient con mock adapter + zero-wait retry."""
    return KeepaClient(
        api_key="test-key",
        rate_limit_per_minute=rate_limit_per_minute,
        adapter_factory=lambda _: adapter,
        retry_max_attempts=retry_max_attempts,
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )


def _full_product(asin: str = "B0CN3VDM4G") -> KeepaProduct:
    return KeepaProduct(
        asin=asin,
        buybox_eur=Decimal("199.99"),
        bsr=1234,
        fee_fba_eur=Decimal("4.30"),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_construct_with_default_factory_does_not_raise() -> None:
    """Il default factory wraps `_LiveKeepaAdapter`; non solleva al construct."""
    client = KeepaClient(api_key="x")
    # Verifica indirettamente che il factory di default sia stato invocato.
    assert client is not None


def test_construct_with_empty_api_key_raises() -> None:
    """api_key="" -> ValueError esplicito."""
    with pytest.raises(ValueError, match="api_key"):
        KeepaClient(api_key="")


def test_construct_with_invalid_rate_limit_raises() -> None:
    """rate_limit_per_minute<=0 -> ValueError esplicito."""
    with pytest.raises(ValueError, match="rate_limit_per_minute"):
        KeepaClient(api_key="x", rate_limit_per_minute=0)


def test_construct_with_invalid_retry_attempts_raises() -> None:
    """retry_max_attempts<=0 -> ValueError esplicito."""
    with pytest.raises(ValueError, match="retry_max_attempts"):
        KeepaClient(api_key="x", retry_max_attempts=0)


# `_LiveKeepaAdapter.query` non e' piu' skeleton (CHG-2026-05-01-015 ratifica
# il live mapping con decisioni Leader A2/A/alpha''). La copertura live e' in
# `tests/integration/test_live_keepa.py` (skip module-level se
# `TalosSettings().keepa_api_key is None`).


# ---------------------------------------------------------------------------
# fetch_buybox / fetch_bsr / fetch_fee_fba — happy path
# ---------------------------------------------------------------------------


def test_fetch_buybox_returns_decimal_on_hit() -> None:
    adapter = _FixedAdapter(_full_product())
    client = _make_client(adapter)
    assert client.fetch_buybox("B0CN3VDM4G") == Decimal("199.99")
    assert adapter.calls == 1


def test_fetch_bsr_returns_int_on_hit() -> None:
    adapter = _FixedAdapter(_full_product())
    client = _make_client(adapter)
    assert client.fetch_bsr("B0CN3VDM4G") == 1234


def test_fetch_fee_fba_returns_decimal_on_hit() -> None:
    adapter = _FixedAdapter(_full_product())
    client = _make_client(adapter)
    assert client.fetch_fee_fba("B0CN3VDM4G") == Decimal("4.30")


# ---------------------------------------------------------------------------
# Miss handling — KeepaMissError (R-01)
# ---------------------------------------------------------------------------


def test_fetch_buybox_raises_miss_on_none() -> None:
    adapter = _FixedAdapter(
        KeepaProduct(asin="X", buybox_eur=None, bsr=10, fee_fba_eur=Decimal(1)),
    )
    client = _make_client(adapter)
    with pytest.raises(KeepaMissError) as excinfo:
        client.fetch_buybox("X")
    assert excinfo.value.field == "buybox"
    assert excinfo.value.asin == "X"


def test_fetch_bsr_raises_miss_on_none() -> None:
    adapter = _FixedAdapter(
        KeepaProduct(asin="X", buybox_eur=Decimal(1), bsr=None, fee_fba_eur=Decimal(1)),
    )
    client = _make_client(adapter)
    with pytest.raises(KeepaMissError) as excinfo:
        client.fetch_bsr("X")
    assert excinfo.value.field == "bsr"


def test_fetch_fee_fba_raises_miss_on_none() -> None:
    adapter = _FixedAdapter(
        KeepaProduct(asin="X", buybox_eur=Decimal(1), bsr=10, fee_fba_eur=None),
    )
    client = _make_client(adapter)
    with pytest.raises(KeepaMissError) as excinfo:
        client.fetch_fee_fba("X")
    assert excinfo.value.field == "fee_fba"


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


def test_retry_succeeds_after_n_transient_errors() -> None:
    """Adapter fallisce 2 volte, succede al 3°. Il client maschera i fail."""
    adapter = _FlakyAdapter(fail_n=2, product=_full_product())
    client = _make_client(adapter, retry_max_attempts=5)
    assert client.fetch_buybox("X") == Decimal("199.99")
    assert adapter.calls == 3  # 2 fail + 1 success


def test_retry_exhausted_propagates_transient_error() -> None:
    """Adapter fallisce sempre. Dopo retry_max_attempts -> raise."""
    adapter = _FlakyAdapter(fail_n=999, product=_full_product())
    client = _make_client(adapter, retry_max_attempts=3)
    with pytest.raises(KeepaTransientError):
        client.fetch_buybox("X")
    assert adapter.calls == 3  # esattamente max_attempts


# ---------------------------------------------------------------------------
# Rate limit hard
# ---------------------------------------------------------------------------


def test_rate_limit_exceeded_raises_after_n_calls() -> None:
    """rate_limit=2/min: 3a chiamata in finestra -> KeepaRateLimitExceededError."""
    adapter = _FixedAdapter(_full_product())
    client = _make_client(adapter, rate_limit_per_minute=2)
    # Le prime 2 succedono.
    client.fetch_buybox("A")
    client.fetch_buybox("B")
    # La 3a (entro la stessa finestra) fallisce hard.
    with pytest.raises(KeepaRateLimitExceededError) as excinfo:
        client.fetch_buybox("C")
    assert excinfo.value.rate_limit_per_minute == 2
    assert excinfo.value.asin == "C"


def test_rate_limit_exceeded_does_not_trigger_retry() -> None:
    """KeepaRateLimitExceededError NON e' KeepaTransientError -> no retry (R-01 fail-now)."""
    adapter = _FixedAdapter(_full_product())
    client = _make_client(adapter, rate_limit_per_minute=1, retry_max_attempts=5)
    client.fetch_buybox("A")  # consuma il singolo permit
    with pytest.raises(KeepaRateLimitExceededError):
        client.fetch_buybox("B")
    # adapter chiamato 1 volta (la 2a non e' arrivata all'adapter)
    assert adapter.calls == 1


# ---------------------------------------------------------------------------
# Adapter factory injection
# ---------------------------------------------------------------------------


def test_adapter_factory_receives_api_key() -> None:
    """La factory custom riceve la api_key passata al construct."""
    captured: list[str] = []

    def factory(api_key: str) -> KeepaApiAdapter:
        captured.append(api_key)
        return _FixedAdapter(_full_product())

    KeepaClient(api_key="real-key", adapter_factory=factory)
    assert captured == ["real-key"]


# ---------------------------------------------------------------------------
# CHG-2026-05-02-035: campi ancillari Arsenale (drops_30/avg90/amazon_share)
# ---------------------------------------------------------------------------


def _arsenale_product(
    *,
    drops_30: int | None = 100,
    buy_box_avg90: Decimal | None = Decimal("180.50"),
    amazon_buybox_share: float | None = 0.10,
) -> KeepaProduct:
    """Mock product con campi ancillari popolati."""
    return KeepaProduct(
        asin="B0CN3VDM4G",
        buybox_eur=Decimal("199.99"),
        bsr=1234,
        fee_fba_eur=Decimal("4.30"),
        drops_30=drops_30,
        buy_box_avg90=buy_box_avg90,
        amazon_buybox_share=amazon_buybox_share,
    )


def test_fetch_drops_30_returns_value() -> None:
    """`fetch_drops_30` ritorna il valore parsato dal response."""
    adapter = _FixedAdapter(_arsenale_product(drops_30=42))
    client = _make_client(adapter)
    assert client.fetch_drops_30("B0CN3VDM4G") == 42


def test_fetch_drops_30_returns_none_on_miss() -> None:
    """`fetch_drops_30` NON solleva su miss (dato ancillare): ritorna None."""
    adapter = _FixedAdapter(_arsenale_product(drops_30=None))
    client = _make_client(adapter)
    assert client.fetch_drops_30("B0CN3VDM4G") is None


def test_fetch_avg_price_90d_returns_value() -> None:
    """`fetch_avg_price_90d` ritorna Decimal."""
    adapter = _FixedAdapter(_arsenale_product(buy_box_avg90=Decimal("150.00")))
    client = _make_client(adapter)
    assert client.fetch_avg_price_90d("B0CN3VDM4G") == Decimal("150.00")


def test_fetch_avg_price_90d_returns_none_on_miss() -> None:
    """`fetch_avg_price_90d` NON solleva: None su miss."""
    adapter = _FixedAdapter(_arsenale_product(buy_box_avg90=None))
    client = _make_client(adapter)
    assert client.fetch_avg_price_90d("B0CN3VDM4G") is None


def test_fetch_buybox_amazon_share_returns_value() -> None:
    """`fetch_buybox_amazon_share` ritorna float in [0, 1]."""
    adapter = _FixedAdapter(_arsenale_product(amazon_buybox_share=0.30))
    client = _make_client(adapter)
    assert client.fetch_buybox_amazon_share("B0CN3VDM4G") == 0.30


def test_fetch_buybox_amazon_share_returns_none_on_miss() -> None:
    """`fetch_buybox_amazon_share` NON solleva: None su miss."""
    adapter = _FixedAdapter(_arsenale_product(amazon_buybox_share=None))
    client = _make_client(adapter)
    assert client.fetch_buybox_amazon_share("B0CN3VDM4G") is None


def test_keepa_product_default_arsenale_fields_none() -> None:
    """KeepaProduct senza i nuovi kwarg → campi default None (backwards-compat)."""
    p = KeepaProduct(
        asin="B0AAA",
        buybox_eur=Decimal(100),
        bsr=10,
        fee_fba_eur=Decimal(5),
    )
    assert p.drops_30 is None
    assert p.buy_box_avg90 is None
    assert p.amazon_buybox_share is None


def test_arsenale_fields_dont_trigger_retry_when_none() -> None:
    """Miss campi ancillari NON triggera retry (sono `None` graceful)."""
    adapter = _FixedAdapter(_arsenale_product(drops_30=None, buy_box_avg90=None))
    client = _make_client(adapter, retry_max_attempts=5)
    client.fetch_drops_30("X")
    client.fetch_avg_price_90d("X")
    # adapter chiamato solo 2 volte (no retry).
    assert adapter.calls == 2


def test_arsenale_share_clamped_validity() -> None:
    """`amazon_buybox_share` in [0.0, 1.0]: il client espone valori reali."""
    adapter = _FixedAdapter(_arsenale_product(amazon_buybox_share=0.99))
    client = _make_client(adapter)
    share = client.fetch_buybox_amazon_share("X")
    assert share is not None
    assert 0.0 <= share <= 1.0


# ---------------------------------------------------------------------------
# CHG-2026-05-02-040: errata alpha-prime invertita - fee_fba atomica Keepa preferred
# ---------------------------------------------------------------------------


def test_arsenale_product_fee_fba_eur_field_optional() -> None:
    """KeepaProduct accetta `fee_fba_eur` Decimal valida (post-CHG-040 errata)."""
    p = KeepaProduct(
        asin="B0AAA",
        buybox_eur=Decimal(199),
        bsr=10,
        fee_fba_eur=Decimal("3.05"),  # atomica Keepa pickAndPackFee
        drops_30=42,
        buy_box_avg90=Decimal("180.50"),
        amazon_buybox_share=0.10,
    )
    assert p.fee_fba_eur == Decimal("3.05")


def test_fetch_fee_fba_returns_atomic_when_present() -> None:
    """Post-CHG-040: `fetch_fee_fba` ritorna pickAndPackFee atomica Keepa."""
    adapter = _FixedAdapter(
        KeepaProduct(
            asin="B0CN3VDM4G",
            buybox_eur=Decimal("199.99"),
            bsr=1234,
            fee_fba_eur=Decimal("3.10"),  # ~atomica Samsung
        ),
    )
    client = _make_client(adapter)
    fee = client.fetch_fee_fba("B0CN3VDM4G")
    assert fee == Decimal("3.10")


def test_fetch_fee_fba_raises_miss_when_keepa_none() -> None:
    """Backwards-compat: KeepaProduct.fee_fba_eur=None → KeepaMissError (caller fallback L11b)."""
    adapter = _FixedAdapter(
        KeepaProduct(
            asin="B0CN3VDM4G",
            buybox_eur=Decimal("199.99"),
            bsr=1234,
            fee_fba_eur=None,
        ),
    )
    client = _make_client(adapter)
    with pytest.raises(KeepaMissError):
        client.fetch_fee_fba("B0CN3VDM4G")
