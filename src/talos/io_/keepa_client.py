"""KeepaClient — wrapper isolato libreria community `keepa` (ADR-0017).

CHG-2026-05-01-001 inaugura `src/talos/io_/`. Adapter pattern:
`KeepaApiAdapter` Protocol isola la libreria community per
sostituibilita' futura e testabilita' senza network.

CHG-2026-05-01-005 attiva la telemetria: emette `keepa.miss`
(catalogo ADR-0021) prima di sollevare `KeepaMissError`, e
`keepa.rate_limit_hit` prima di `KeepaRateLimitExceededError`.

Decisioni di design (D1 ratificata Leader 2026-04-30 sera, "default"):
- D1.a Cache: solo `@st.cache_data(ttl=600)` lato Streamlit
  (ADR-0016), no sqlite locale qui dentro.
- D1.b Resilience: solo `tenacity` retry esponenziale (default
  max 5 attempts, wait 1s..60s). NO circuit breaker.
- D1.c Rate limit: configurabile via
  `TalosSettings.keepa_rate_limit_per_minute`
  (env `TALOS_KEEPA_RATE_LIMIT_PER_MINUTE`, default 60).
  `pyrate_limiter.Limiter` con `Rate(N, Duration.MINUTE)`.
  Eccedere -> `KeepaRateLimitExceededError` (R-01 NO SILENT DROPS).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Protocol

from pyrate_limiter import Duration, Limiter, Rate
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_logger = logging.getLogger(__name__)

DEFAULT_RETRY_MAX_ATTEMPTS = 5
DEFAULT_RETRY_WAIT_MIN_S = 1.0
DEFAULT_RETRY_WAIT_MAX_S = 60.0
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
DEFAULT_KEEPA_DOMAIN = "IT"

# Hierarchy decisione Leader 2026-05-01 round 4 (A2): se il piano subscription
# non espone `BUY_BOX_SHIPPING`, il prossimo source ragionevole e' `NEW`
# (prezzo offerta nuova piu' bassa), poi `AMAZON` (Amazon-as-seller). Caller
# riceve il primo valore valido o `KeepaMissError` se nessuno disponibile.
_BUYBOX_SOURCE_HIERARCHY = ("BUY_BOX_SHIPPING", "NEW", "AMAZON")

# Decisione Leader 2026-05-01 round 4 (alpha''): l'adapter NON popola mai
# `fee_fba_eur` da Keepa. Il `pickAndPackFee` di Keepa misura solo la quota
# logistica atomica (~10x piu' piccola della formula L11b Frozen del Leader,
# che stima la "Fee FBA totale"). Per preservare la semantica di L11b senza
# inquinare Cash_Profit/ROI/VGP, l'adapter ritorna sempre `None` su
# `fee_fba_eur` -> caller riceve `KeepaMissError` -> fallback `fee_fba_manual`
# (CHG-2026-04-30-022). Documentato in change CHG-2026-05-01-015.


@dataclass(frozen=True)
class KeepaProduct:
    """Risposta normalizzata Keepa per un singolo ASIN.

    Un campo `None` significa miss del piano subscription corrente
    o del provider. Il client mappa `None` -> `KeepaMissError`
    (R-01 NO SILENT DROPS).
    """

    asin: str
    buybox_eur: Decimal | None
    bsr: int | None
    fee_fba_eur: Decimal | None


class KeepaApiAdapter(Protocol):
    """Interfaccia minimal per provider Keepa.

    L'adapter pattern isola la libreria community `keepa` dietro
    un'interfaccia stabile. Test: implementazioni mock iniettate
    via `adapter_factory`. Runtime: `_LiveKeepaAdapter`.
    """

    def query(self, asin: str) -> KeepaProduct:
        """Ritorna il prodotto normalizzato per `asin`."""
        ...


class KeepaMissError(Exception):
    """Field richiesto non disponibile dal provider corrente.

    R-01 NO SILENT DROPS: il caller (fallback chain, CHG futuro)
    cattura e attiva il fallback (formula manuale L11b CHG-022
    per `fee_fba`, scraping per `buybox`, AMBIGUO per `bsr`).
    """

    def __init__(self, asin: str, *, field: str) -> None:
        super().__init__(f"Keepa miss su {field} per ASIN {asin}")
        self.asin = asin
        self.field = field


class KeepaRateLimitExceededError(Exception):
    """Rate limit hard locale ecceduto (pyrate-limiter).

    R-01: NON viene fatto retry su questo errore (fail-now
    esplicito). Il caller decide se aspettare e/o rivedere il
    limite via `TALOS_KEEPA_RATE_LIMIT_PER_MINUTE`.
    """

    def __init__(self, asin: str, *, rate_limit_per_minute: int) -> None:
        super().__init__(
            f"Rate limit Keepa ecceduto ({rate_limit_per_minute}/min) durante fetch ASIN {asin}",
        )
        self.asin = asin
        self.rate_limit_per_minute = rate_limit_per_minute


class KeepaTransientError(Exception):
    """Errore transitorio (rete/5xx/429 server-side).

    Triggera retry esponenziale. Dopo `retry_max_attempts` tentativi
    falliti -> propagato al caller con `reraise=True`.
    """


def _last_valid_value(arr: Iterable[Any] | None) -> float | None:
    """Ultimo valore time-series valido (non `None`/NaN/-1/negativo).

    Keepa CSV / data-arrays sono serie temporali con sentinel `-1` per
    "out of stock" e possibilmente NaN. Iteriamo a ritroso e ritorniamo
    il primo numero finito >= 0. R-01 NO SILENT DROPS: assenza di
    valori validi -> `None` (caller solleva `KeepaMissError`).
    """
    if arr is None:
        return None
    for v in reversed(list(arr)):
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f) or f < 0:
            continue
        return f
    return None


class _LiveKeepaAdapter:
    """Adapter live su libreria community `keepa`.

    Implementato in CHG-2026-05-01-015 con decisioni Leader ratificate:

    - **buybox source A2 hierarchy**: `data['BUY_BOX_SHIPPING']` ->
      `data['NEW']` -> `data['AMAZON']`. Il piano subscription corrente
      non espone `BUY_BOX_SHIPPING`; `NEW` coincide empiricamente col
      Buy Box reale (validato live su B0CSTC2RDW Galaxy S24: scraper
      €549.00 == Keepa NEW €549.00).
    - **bsr source A**: `data['SALES']` (BSR root categoria).
    - **fee_fba policy alpha''**: SEMPRE `fee_fba_eur=None`. Il
      `pickAndPackFee` Keepa NON e' equivalente alla formula L11b
      Frozen del Leader (ordine di grandezza ~10x diverso). Caller
      riceve `KeepaMissError` -> fallback `fee_fba_manual` CHG-022.

    Lazy init: `keepa.Keepa(api_key)` istanzia al primo `query()` per
    evitare network al boot del client (test unit non devono pagare
    overhead). `domain="IT"` per Amazon.it.

    Errori network/transient (`requests.exceptions.RequestException`,
    timeouts) sono rimappati a `KeepaTransientError` -> retry
    esponenziale del `KeepaClient`. Errori di shape (response vuoto,
    asin mismatch) -> `KeepaTransientError` (potrebbero essere flap
    temporanei API Keepa).
    """

    def __init__(self, api_key: str, *, domain: str = DEFAULT_KEEPA_DOMAIN) -> None:
        self._api_key = api_key
        self._domain = domain
        self._api: Any = None  # lazy: keepa.Keepa istanziata al primo query()

    def _ensure_api(self) -> Any:
        if self._api is None:
            import keepa  # noqa: PLC0415 — lazy import per non pagare boot in test mock-only

            self._api = keepa.Keepa(self._api_key)
        return self._api

    def query(self, asin: str) -> KeepaProduct:
        api = self._ensure_api()
        try:
            products = api.query([asin], domain=self._domain)
        except Exception as exc:
            msg = f"Keepa API call failed for {asin}: {type(exc).__name__}: {exc}"
            raise KeepaTransientError(msg) from exc

        if not products:
            msg = f"Keepa returned empty product list for {asin}"
            raise KeepaTransientError(msg)
        product = products[0]
        if product.get("asin") != asin:
            msg = f"Keepa returned ASIN mismatch: requested {asin}, got {product.get('asin')!r}"
            raise KeepaTransientError(msg)

        data = product.get("data") or {}
        buybox_eur: Decimal | None = None
        for source in _BUYBOX_SOURCE_HIERARCHY:
            value = _last_valid_value(data.get(source))
            if value is not None:
                buybox_eur = Decimal(str(value))
                break

        bsr_value = _last_valid_value(data.get("SALES"))
        bsr: int | None = int(bsr_value) if bsr_value is not None else None

        # Decisione alpha'': fee_fba_eur sempre None (caller usa fee_fba_manual).
        return KeepaProduct(
            asin=asin,
            buybox_eur=buybox_eur,
            bsr=bsr,
            fee_fba_eur=None,
        )


def _default_adapter_factory(api_key: str) -> KeepaApiAdapter:
    return _LiveKeepaAdapter(api_key)


class KeepaClient:
    """Wrapper isolato per Keepa con rate limit hard + retry + R-01.

    Uso runtime:

        client = KeepaClient(api_key="...", rate_limit_per_minute=60)
        try:
            buybox = client.fetch_buybox("B0CN3VDM4G")
        except KeepaMissError:
            # fallback a scraping / formula manuale
            ...
        except KeepaRateLimitExceededError:
            # caller decide se aspettare
            ...

    Uso test (mock adapter, no network, no sleep):

        client = KeepaClient(
            api_key="x",
            adapter_factory=lambda _: my_mock_adapter,
            retry_wait_min_s=0.0,
            retry_wait_max_s=0.0,
        )
    """

    def __init__(  # noqa: PLR0913 — adapter pattern + retry/rate config inietta tutto via init
        self,
        api_key: str,
        *,
        rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
        adapter_factory: Callable[[str], KeepaApiAdapter] | None = None,
        retry_max_attempts: int = DEFAULT_RETRY_MAX_ATTEMPTS,
        retry_wait_min_s: float = DEFAULT_RETRY_WAIT_MIN_S,
        retry_wait_max_s: float = DEFAULT_RETRY_WAIT_MAX_S,
    ) -> None:
        if not api_key:
            msg = "KeepaClient richiede api_key non vuota"
            raise ValueError(msg)
        if rate_limit_per_minute <= 0:
            msg = f"rate_limit_per_minute deve essere intero > 0 (ricevuto {rate_limit_per_minute})"
            raise ValueError(msg)
        if retry_max_attempts <= 0:
            msg = f"retry_max_attempts deve essere > 0 (ricevuto {retry_max_attempts})"
            raise ValueError(msg)
        self._api_key = api_key
        self._rate_limit_per_minute = rate_limit_per_minute
        self._limiter = Limiter(Rate(rate_limit_per_minute, Duration.MINUTE))
        factory = adapter_factory or _default_adapter_factory
        self._adapter = factory(api_key)
        self._retry_max_attempts = retry_max_attempts
        self._retry_wait_min_s = retry_wait_min_s
        self._retry_wait_max_s = retry_wait_max_s

    def fetch_buybox(self, asin: str) -> Decimal:
        """Ritorna il prezzo BuyBox in EUR. Solleva su miss/limit/transient.

        Raises:
            KeepaMissError: il provider non espone BuyBox per `asin`.
            KeepaRateLimitExceededError: rate limit locale ecceduto.
            KeepaTransientError: errore transitorio dopo retry esauriti.
        """
        product = self._fetch_with_retry(asin)
        if product.buybox_eur is None:
            self._emit_miss(asin, field="buybox")
            raise KeepaMissError(asin, field="buybox")
        return product.buybox_eur

    def fetch_bsr(self, asin: str) -> int:
        """Ritorna il Best Sellers Rank intero. Solleva su miss/limit/transient."""
        product = self._fetch_with_retry(asin)
        if product.bsr is None:
            self._emit_miss(asin, field="bsr")
            raise KeepaMissError(asin, field="bsr")
        return product.bsr

    def fetch_fee_fba(self, asin: str) -> Decimal:
        """Ritorna la Fee FBA in EUR. Solleva su miss/limit/transient.

        Su miss, il caller deve attivare il fallback `fee_fba_manual`
        (L11b, CHG-2026-04-30-022).
        """
        product = self._fetch_with_retry(asin)
        if product.fee_fba_eur is None:
            self._emit_miss(asin, field="fee_fba")
            raise KeepaMissError(asin, field="fee_fba")
        return product.fee_fba_eur

    @staticmethod
    def _emit_miss(asin: str, *, field: str) -> None:
        """Emette evento canonico `keepa.miss` (catalogo ADR-0021).

        Attivato in CHG-2026-05-01-005. Campi: asin, error_type
        (= il `field` mancante), retry_count (=0 perche' miss e'
        deterministico, non transient).
        """
        _logger.debug(
            "keepa.miss",
            extra={"asin": asin, "error_type": field, "retry_count": 0},
        )

    def _fetch_with_retry(self, asin: str) -> KeepaProduct:
        """Applica retry esponenziale solo su KeepaTransientError.

        `KeepaRateLimitExceededError` NON triggera retry (R-01 fail-now).
        `KeepaMissError` non e' sollevato qui (e' deciso a livello
        `fetch_*` dopo aver letto i campi del prodotto).
        """
        retrying = Retrying(
            stop=stop_after_attempt(self._retry_max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self._retry_wait_min_s,
                max=self._retry_wait_max_s,
            ),
            retry=retry_if_exception_type(KeepaTransientError),
            reraise=True,
        )
        return retrying(self._fetch_one, asin)

    def _fetch_one(self, asin: str) -> KeepaProduct:
        """Singola query: rate-limit check + adapter dispatch."""
        acquired = self._limiter.try_acquire("keepa", blocking=False)
        if not acquired:
            # Telemetria CHG-2026-05-01-005: evento canonico ADR-0021.
            _logger.debug(
                "keepa.rate_limit_hit",
                extra={
                    "requests_in_window": self._rate_limit_per_minute,
                    "limit": self._rate_limit_per_minute,
                },
            )
            raise KeepaRateLimitExceededError(
                asin,
                rate_limit_per_minute=self._rate_limit_per_minute,
            )
        return self._adapter.query(asin)
