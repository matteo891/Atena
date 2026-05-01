---
id: CHG-2026-05-01-009
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 2 attiva, Path B target — chiusura Fase 1)
status: Draft
commit: 1a9369d
adr_ref: ADR-0017, ADR-0014, ADR-0019
---

## What

Aggiunge `lookup_products(asin_list, *, keepa, scraper=None,
page=None, ocr=None) -> list[ProductData]` in
`src/talos/io_/fallback_chain.py`. Bulk wrapper su `lookup_product`
(CHG-006): itera in ordine e accumula i risultati. Eccezioni
"tecniche" (`KeepaRateLimitExceededError`, `KeepaTransientError`,
errori live di `page.goto`) propagano al primo ASIN che le
incontra (R-01 fail-fast).

`lookup_products([])` ritorna `[]` senza chiamare nessun canale
(no-op verificato: il mock `keepa` configurato per sollevare non
viene invocato).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/io_/fallback_chain.py` | modificato | + `lookup_products(asin_list, *, keepa, scraper=None, page=None, ocr=None) -> list[ProductData]` come list-comprehension su `lookup_product`. Docstring esteso (R-01 fail-fast, ordine preservato, scraper+page condivisi fra le chiamate). |
| `src/talos/io_/__init__.py` | modificato | + re-export `lookup_products` in `__all__`. |
| `tests/unit/test_fallback_chain.py` | modificato | + 4 test su `lookup_products`: empty list -> [], ordine + cardinalita' preservati, RateLimit fail-fast, scraper+page condivisi (goto chiamato per ogni ASIN, in ordine). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**655 PASS** (548 unit/governance/golden + 107 integration; era
651, +4 nuovi test).

## Why

L'integratore Fase 1 (`acquire_and_persist`, CHG-010 atteso)
necessita di una primitiva bulk per evitare il loop in linea
ripetuto. Inoltre, esplicitare la primitiva bulk nel package
public API rende chiaro al caller che lo scraper e la page
sono condivisibili fra le chiamate (riuso di context Chromium
in Fase 3, evitando overhead ~150 ms per ASIN).

Pattern fail-fast ratificato: `KeepaRateLimitExceededError` non
ha senso continuare il batch (ogni ASIN successivo lo trigger
di nuovo); `KeepaTransientError` post-retry e' irrecuperabile
applicativamente. `KeepaMissError` e `SelectorMissError`
restano gestiti da `lookup_product` come `field=None` + entry
in `notes`, **non** propagano.

Out-of-scope:
- **Concurrency** (asyncio / threading): scope futuro (es.
  `await asyncio.gather` su `lookup_product` async). Oggi
  sequenziale per semplicita' + rispetto rate-limit Keepa.
- **Partial recovery on rate-limit**: oggi propaga al primo
  hit. Pattern alternativo "skip e accumula" e' decisione
  Leader (cambia semantica del batch).

## How

### `lookup_products` (highlight)

```python
def lookup_products(
    asin_list: list[str],
    *,
    keepa: KeepaClient,
    scraper: AmazonScraper | None = None,
    page: BrowserPageProtocol | None = None,
    ocr: OcrPipeline | None = None,
) -> list[ProductData]:
    return [
        lookup_product(asin, keepa=keepa, scraper=scraper, page=page, ocr=ocr)
        for asin in asin_list
    ]
```

### Test plan eseguito

4 test unit in `tests/unit/test_fallback_chain.py`:

- `test_lookup_products_empty_list_returns_empty`: no-op verificato (mock keepa configurato per `KeepaTransientError` non chiamato).
- `test_lookup_products_preserves_order_and_cardinality`: 3 ASIN, ordine e dati corrispondenti.
- `test_lookup_products_propagates_rate_limit_at_first_failure`: `KeepaRateLimitExceededError` raise al primo ASIN.
- `test_lookup_products_threads_scraper_and_page_through`: `goto` chiamato per ogni ASIN in sequenza, page condivisa.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/fallback_chain.py src/talos/io_/__init__.py tests/unit/test_fallback_chain.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_fallback_chain.py` | 0 issues (49 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **548 PASS** (era 544, +4) |
| Integration | non richiesto (helper puro, no DB) | skip |

**Rischi residui:**
- **Sequenziale**: per N grandi, la latenza si accumula. Caller batch
  deve dimensionare `rate_limit_per_minute` di conseguenza (es.
  500 ASIN @ 60/min = ~8 min minimo).
- **Page condivisa = stato persistente Chromium**: in Fase 3 il
  context Chromium (cookies, viewport) accumula stato tra le
  chiamate. Se Amazon serve contenuto diverso in base a sessione,
  il primo ASIN puo' influenzare i successivi. Caller che vuole
  isolamento massimo passa una page fresh per ogni ASIN.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/fallback_chain.py` ✓
  (area `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:** wrapper sequenziale su
  `lookup_product` esistente; nessuna nuova dipendenza, nessun
  nuovo Protocol.
- **R-01 NO SILENT DROPS (governance test):** ✓ (eccezioni
  tecniche propagano fail-fast).
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `lookup_products` ->
  ADR-0017.
- **Backward compat:** wrapper additivo, niente break.
- **Impact analysis pre-edit:** primitiva nuova, zero caller
  esistenti.

## Impact

- **Fase 1 Path B avanzamento**: 4/N CHG (CHG-006..009).
- **`pyproject.toml` invariato**.
- **Pronto per CHG-010** (orchestratore Fase 1
  `acquire_and_persist` che chiama `lookup_products` per N ASIN).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11
  viventi).

## Refs

- ADR: ADR-0017 (canale io_/extract), ADR-0014, ADR-0019.
- Predecessore: CHG-2026-05-01-006 (`lookup_product`).
- Successore atteso: CHG-2026-05-01-010 (orchestratore
  `acquire_and_persist` che usa `lookup_products` per N ASIN).
- Commit: `1a9369d`.
