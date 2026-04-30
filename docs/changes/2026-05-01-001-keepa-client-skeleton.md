---
id: CHG-2026-05-01-001
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" sessione attivata 2026-04-30 sera, prosegue oltre mezzanotte)
status: Draft
commit: [pending]
adr_ref: ADR-0017, ADR-0014, ADR-0019, ADR-0021
---

## What

Inaugura `src/talos/io_/` con `KeepaClient` skeleton — primo
componente del blocco strategico `io_/extract` Samsung (ADR-0017).
Wrapper isolato della libreria community `keepa` con rate limit
hard (`pyrate-limiter`) + retry esponenziale (`tenacity`) +
errori R-01 espliciti (`KeepaMissError`,
`KeepaRateLimitExceededError`). Adapter pattern: la libreria
community e' isolata dietro `KeepaApiAdapter` (Protocol) per
sostituibilita' futura e per testabilita' senza network.

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | + deps `keepa>=1.4.0,<2`, `tenacity>=8.0.0,<10`, `pyrate-limiter>=3.0.0,<5` (ADR-0017 canale 1). Sostituito commento "Le altre dipendenze applicative entreranno modulo per modulo" con il nuovo blocco Keepa. |
| `src/talos/config/settings.py` | modificato | + `keepa_api_key: str \| None` (env `TALOS_KEEPA_API_KEY`); + `keepa_rate_limit_per_minute: int = 60` (env `TALOS_KEEPA_RATE_LIMIT_PER_MINUTE`); + `field_validator` che impone `> 0`. Pattern coerente con CHG-029/030/031. |
| `src/talos/io_/__init__.py` | nuovo | Re-export `KeepaClient`, `KeepaProduct`, `KeepaApiAdapter`, `KeepaMissError`, `KeepaRateLimitExceededError`, `KeepaTransientError`. Inaugura il package `io_/` (ADR-0013 area consentita). |
| `src/talos/io_/keepa_client.py` | nuovo | `@dataclass(frozen=True) KeepaProduct(asin, buybox_eur, bsr, fee_fba_eur)`; `KeepaApiAdapter(Protocol).query(asin) -> KeepaProduct`; `KeepaClient(api_key, *, rate_limit_per_minute=60, adapter_factory=None)` con `fetch_buybox/fetch_bsr/fetch_fee_fba` (Decimal/int return + `KeepaMissError` su None); rate limit hard via `pyrate_limiter.Limiter` (eccedere -> `KeepaRateLimitExceededError`); retry esponenziale via `tenacity.retry` (max 5 attempts, wait_exponential 1s..60s, retry_if_exception_type `KeepaTransientError`); `_LiveKeepaAdapter` skeleton (NotImplementedError + TODO ADR-0017 mapping CSV indici, ratifica live in CHG dedicato). |
| `tests/unit/test_keepa_client.py` | nuovo | 16 test puri (mock `KeepaApiAdapter`): 5 construct (default factory, empty api_key, invalid rate, invalid retry, NotImplementedError dal LiveAdapter skeleton); 3 happy path fetch_*; 3 miss su ognuno (`KeepaMissError`); 2 retry (success al 3°, exhausted dopo N → propaga `KeepaTransientError`); 2 rate-limit (eccesso → `KeepaRateLimitExceededError`; no retry su rate-limit); adapter_factory injection. Niente network. |
| `tests/unit/test_settings.py` | modificato | + 6 test sui nuovi campi: `keepa_api_key` default None / from env; `keepa_rate_limit_per_minute` default 60 / override; validator zero → ValidationError; validator negativo → ValidationError. |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Aggiornato il record `src/talos/io_/keepa_client.py` con riferimento a CHG-2026-05-01-001 (skeleton + scope). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**516 PASS** (416 unit/governance/golden + 100 integration).
Delta unit: +22 (16 `test_keepa_client.py` + 6 nuovi
`test_settings.py`).

## Why

ADR-0017 designa Keepa come canale 1 (primario) della fallback
chain di acquisizione dati. Senza un wrapper isolato, ogni
modulo che fa lookup esterno ricreerebbe rate limiting / retry
inconsistenti e R-01 NO SILENT DROPS sarebbe violato per default
(la libreria community lancia errori specifici o ritorna `None`
silenziosi a seconda del campo richiesto).

CHG-2026-05-01-001 e' il primo CHG del blocco `io_/extract` Samsung (4-5
CHG attesi, decisioni Leader D1-D5 ratificate "default" il
2026-04-30 sera, memory `project_io_extract_design_decisions.md`).

### Decisioni di design (D1 ratificata)

1. **Cache: D1.a = A** — solo `@st.cache_data(ttl=600)` come ADR-0017
   (no sqlite locale, scope futuro). Il client e' stateless.

2. **Resilience: D1.b = A** — solo `tenacity` retry (max 5
   esponenziale 1s..60s). Niente circuit breaker.

3. **Rate limit: D1.c = B** — `keepa_rate_limit_per_minute`
   configurabile via env `TALOS_KEEPA_RATE_LIMIT_PER_MINUTE`.
   Default 60 (esempio ADR-0017). `pyrate_limiter.Limiter` con
   `Rate(N, Duration.MINUTE)`. Eccedere -> `KeepaRateLimitExceededError`
   (R-01: NO SILENT DROPS).

4. **Adapter Pattern**: `KeepaApiAdapter(Protocol)` isola la
   libreria community. `_LiveKeepaAdapter` e' lo wrapper su
   `keepa.Keepa`; in CHG-2026-05-01-001 e' uno **skeleton** (raise
   NotImplementedError + TODO sui CSV indici) — la mappatura
   live richiede sandbox con API key reale (scope CHG futuro
   o integrato con CHG-2026-05-01-005 fallback chain). I test unit
   mockano l'adapter, scollegando logica cross-cutting da
   network.

5. **`KeepaProduct` immutabile**: `@dataclass(frozen=True)`,
   3 campi (`buybox_eur: Decimal | None`, `bsr: int | None`,
   `fee_fba_eur: Decimal | None`). `None` = miss → mappato a
   `KeepaMissError` dal client (R-01).

6. **Errore esplicito su miss campo**: ADR-0017 vincola lookup
   primario Keepa con fallback formula manuale (L11b CHG-022).
   Il client lancia `KeepaMissError(asin, field)`; il caller
   (fallback chain, CHG futuro) cattura e attiva fallback.
   Niente `Optional[Decimal]` nel return type (eviterebbe la
   discriminazione esplicita).

7. **`adapter_factory` opzionale**: se `None`, `_LiveKeepaAdapter`
   e' usato come default. I test passano `mock_adapter_factory`
   per iniettare un mock — pattern coerente con altri moduli
   (es. `engine.py` accetta override URL).

### Out-of-scope

- **Live mapping CSV indici Keepa** (BUY_BOX_SHIPPING idx 18,
  SALES idx 3, fee_fba via `data` campo): scope CHG dedicato
  (richiede API key sandbox).
- **Cache sqlite/parquet locale**: D1.a = A (solo Streamlit cache).
- **Circuit breaker**: D1.b = A (solo retry).
- **Async client**: la libreria community ha anche AsyncKeepa,
  fuori scope (ADR-0017 + CHG-007 SQLAlchemy 2.0 sync).
- **Telemetria evento `keepa.miss` / `keepa.rate_limit_hit`**:
  catalogo ADR-0021 contiene gia' i 2 eventi (dormienti). Verranno
  attivati nell'integratore fallback chain (CHG-2026-05-01-005 atteso). In
  CHG-2026-05-01-001 niente emissione: il client e' API-pura (stateless,
  no logger import) — la telemetria sta nel caller (orchestrator
  o fallback chain).

## How

### `KeepaClient` (highlight)

```python
@dataclass(frozen=True)
class KeepaProduct:
    asin: str
    buybox_eur: Decimal | None
    bsr: int | None
    fee_fba_eur: Decimal | None


class KeepaApiAdapter(Protocol):
    def query(self, asin: str) -> KeepaProduct: ...


class KeepaClient:
    def __init__(
        self,
        api_key: str,
        *,
        rate_limit_per_minute: int = 60,
        adapter_factory: Callable[[str], KeepaApiAdapter] | None = None,
    ) -> None:
        self._rate = Limiter(Rate(rate_limit_per_minute, Duration.MINUTE))
        factory = adapter_factory or _default_adapter_factory
        self._adapter = factory(api_key)

    def fetch_buybox(self, asin: str) -> Decimal:
        product = self._fetch_with_retry(asin)
        if product.buybox_eur is None:
            raise KeepaMissError(asin, field="buybox")
        return product.buybox_eur

    # fetch_bsr / fetch_fee_fba simili.

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type(KeepaTransientError),
        reraise=True,
    )
    def _fetch_with_retry(self, asin: str) -> KeepaProduct:
        try:
            self._rate.try_acquire("keepa")
        except BucketFullException as exc:
            raise KeepaRateLimitExceededError(asin, ...) from exc
        return self._adapter.query(asin)
```

### Test plan eseguito

16 unit test su `keepa_client` (mock adapter, no network, no sleep):

1. `test_construct_with_default_factory_does_not_raise`
2. `test_construct_with_empty_api_key_raises`
3. `test_construct_with_invalid_rate_limit_raises`
4. `test_construct_with_invalid_retry_attempts_raises`
5. `test_default_factory_query_raises_not_implemented`
6-8. `test_fetch_buybox/bsr/fee_fba_returns_*_on_hit`
9-11. `test_fetch_buybox/bsr/fee_fba_raises_miss_on_none`
12. `test_retry_succeeds_after_n_transient_errors`
13. `test_retry_exhausted_propagates_transient_error`
14. `test_rate_limit_exceeded_raises_after_n_calls`
15. `test_rate_limit_exceeded_does_not_trigger_retry`
16. `test_adapter_factory_receives_api_key`

6 test settings (test_settings.py esistente esteso):

1. `test_keepa_api_key_default_none`
2. `test_keepa_api_key_from_env`
3. `test_keepa_rate_limit_default_60`
4. `test_keepa_rate_limit_override_from_env`
5. `test_keepa_rate_limit_zero_rejected`
6. `test_keepa_rate_limit_negative_rejected`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/ src/talos/config/settings.py tests/unit/test_keepa_client.py tests/unit/test_settings.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_keepa_client.py tests/unit/test_settings.py` | 0 issues (44 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **416 PASS** (era 394, +22) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **100 PASS** (invariato) |

**Rischi residui:**
- **`_LiveKeepaAdapter` raise NotImplementedError**: chi tenta
  `KeepaClient(api_key="real").fetch_buybox(...)` SENZA passare
  un adapter custom riceve immediatamente `NotImplementedError`
  con messaggio esplicito che dichiara il TODO ADR-0017. R-01
  rispettato (no silent fallback).
- **`pyrate-limiter` v4 vs v3 API**: l'esempio ADR-0017
  menziona `aiolimiter` (sync via `pyrate-limiter`). v4 richiama
  `try_acquire(name, weight)` che lancia `BucketFullException`
  in caso di limite ecceduto. La nostra implementazione cattura
  l'eccezione e mappa a `KeepaRateLimitExceededError`.
- **Retry su `KeepaRateLimitExceededError`**: il client NON fa
  retry su questo errore (e' deterministicamente fail-now per
  R-01). Solo `KeepaTransientError` triggera retry.
- **Test rate limit boundary**: il test usa un `rate_limit_per_minute=2`
  + 3 chiamate consecutive per forzare il 3° fail. La finestra
  di pyrate-limiter e' rolling — il test deve eseguire le 3
  chiamate entro la finestra senza sleep.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/keepa_client.py`,
  `src/talos/io_/__init__.py` ✓ (area `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Wrapper isolato ✓
  - Backoff esponenziale via tenacity ✓ (base 1s, max 60s, max 5 retry)
  - Rate limit hard ✓ (R-01 NO SILENT DROPS)
  - `fetch_buybox/fetch_bsr/fetch_fee_fba` ✓ (interfaccia ratificata)
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019 + ADR-0011: codice
  applicativo richiede test automatici).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `KeepaClient` mappa
  ad ADR-0017; `KeepaProduct`, `KeepaApiAdapter`, errori → ADR-0017.
- **Backward compat:** modulo nuovo, niente break.
- **Impact analysis pre-edit:** primo file in `io_/` (zero caller).
  Settings esteso retrocompat (default values).

## Impact

- **Inaugura `src/talos/io_/`** — primo componente operativo del
  blocco acquisizione dati. ADR-0017 attivato.
- **5 eventi dormienti ADR-0021** (`keepa.miss`, `keepa.rate_limit_hit`,
  `scrape.selector_fail`, `ocr.below_confidence`, `extract.kill_switch`)
  attendono i CHG successivi (CHG-2026-05-01-002 scraper, CHG-2026-05-01-003 OCR,
  CHG-2026-05-01-004 SamsungExtractor, CHG-2026-05-01-005 integratore).
- **TalosSettings cresce a 8 campi** (era 6 — aggiunti 2 Keepa).
- **`pyproject.toml` cresce di 3 deps applicative**: `keepa`,
  `tenacity` (gia' transitive da streamlit, ora esplicita per
  tracciabilita'), `pyrate-limiter`. Trascina `aiohttp`,
  `requests`, `tqdm` (transitive di `keepa`).
- **Nessun caller**: `KeepaClient` e' il primitive; integrazione
  con orchestrator/fallback chain in CHG futuro.

## Refs

- ADR: ADR-0017 (Keepa canale 1), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test unit pattern), ADR-0021 (catalogo eventi
  dormienti — attivazione futura).
- Predecessori: CHG-2026-04-30-001 (promulgazione cluster ADR
  stack 0013-0021), CHG-2026-04-30-029 (config layer
  pydantic-settings), CHG-2026-04-30-030 (engine via TalosSettings).
- Successori attesi: CHG-2026-05-01-002 `scraper.py` Playwright;
  CHG-2026-05-01-003 `ocr.py` Tesseract; CHG-2026-05-01-004 `extract/samsung.py`
  SamsungExtractor + R-05; CHG-2026-05-01-005 integratore fallback chain
  + `_LiveKeepaAdapter` mapping ratificato + telemetria 5
  eventi.
- Memory: `project_io_extract_design_decisions.md` (D1-D5 default
  ratificate Leader 2026-04-30 sera).
- Commit: `[pending]`.
