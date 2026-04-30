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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from pyrate_limiter import Duration, Limiter, Rate
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from decimal import Decimal

_logger = logging.getLogger(__name__)

DEFAULT_RETRY_MAX_ATTEMPTS = 5
DEFAULT_RETRY_WAIT_MIN_S = 1.0
DEFAULT_RETRY_WAIT_MAX_S = 60.0
DEFAULT_RATE_LIMIT_PER_MINUTE = 60


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


class _LiveKeepaAdapter:
    """Adapter live su libreria community `keepa`.

    Skeleton CHG-2026-05-01-001: il mapping CSV indici Keepa
    (BUY_BOX_SHIPPING idx 18, SALES idx 3) e il parsing del campo
    fee_fba richiedono sandbox con API key reale, rinviato a CHG
    dedicato (probabile CHG-2026-05-01-005 fallback chain
    integratore, o CHG separato `keepa-live-mapping`).

    Finche' non implementato, `query()` lancia `NotImplementedError`
    esplicito (R-01 NO SILENT DROPS rispettato: nessun fallback
    silenzioso). I test devono iniettare un mock via
    `adapter_factory`.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def query(self, asin: str) -> KeepaProduct:
        msg = (
            f"_LiveKeepaAdapter.query({asin!r}) non implementato in "
            "CHG-2026-05-01-001. Mapping CSV indici Keepa "
            "(BUY_BOX_SHIPPING idx 18, SALES idx 3) e fee_fba richiedono "
            "sandbox + API key reale; ratifica in CHG dedicato. "
            "Test devono iniettare un mock via adapter_factory."
        )
        raise NotImplementedError(msg)


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
