---
id: CHG-2026-05-01-025
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" estesa round 5+ — telemetria cache `description_resolutions`)
status: Draft
commit: pending
adr_ref: ADR-0021, ADR-0015, ADR-0016, ADR-0014, ADR-0019
---

## What

Errata additiva al catalogo eventi canonici ADR-0021 + emit applicativo
nel caller della cache `description_resolutions` (CHG-019). Chiude il
gap di osservabilità sulla cache: oggi la cache è persistente ma
silente, il rapporto hit/miss è invisibile in produzione.

| Evento | Modulo | Campi obbligatori | Sito di emit |
|---|---|---|---|
| `cache.hit` | `ui/listino_input.py` | `table`, `tenant_id` | `resolve_listino_with_cache` post `find_resolution_by_hash` se hit |
| `cache.miss` | `ui/listino_input.py` | `table`, `tenant_id` | `resolve_listino_with_cache` post `find_resolution_by_hash` se None |

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/observability/events.py` | modificato | + 2 voci `CANONICAL_EVENTS` (`cache.hit`, `cache.miss`) + 2 costanti `EVENT_CACHE_HIT` / `EVENT_CACHE_MISS`. Catalogo passa da **15 a 17 voci**. Header docstring aggiornato (15 → 17 voci). |
| `src/talos/ui/listino_input.py` | modificato | + `import logging` + `_logger = logging.getLogger(__name__)` + costante module-level `_CACHE_TABLE_DESCRIPTION_RESOLUTIONS = "description_resolutions"` + 2 helper puri `_emit_cache_hit(*, table, tenant_id)` / `_emit_cache_miss(*, table, tenant_id)`. Emit inline in `resolve_listino_with_cache`: cache hit → `_emit_cache_hit` post `cached.asin.strip()`; cache miss (`cached is None`) → `_emit_cache_miss` nello stesso `with factory()` block. Caso `factory is None` (cache disabled) → no emit (non è hit né miss applicativo). |
| `docs/decisions/ADR-0021-logging-telemetria.md` | modificato | + voce `## Errata` 2026-05-01 CHG-025 con tabella 2 nuovi eventi cache + razionale (hit rate KPI + decisione cache TTL futura). Coerente con pattern errata CHG-021/024/058 (additivo, no supersessione). |
| `tests/unit/test_listino_input_cache_telemetry.py` | nuovo | 5 test caplog: 2 per `_emit_cache_hit` (happy path table=description_resolutions + edge `table="bsr_cache"` per dimostrare enum-string aperta), 2 per `_emit_cache_miss` (happy path + edge `tenant_id=99` per scenario multi-tenant), 1 governance "catalog contains cache entries". Pattern coerente con `test_dashboard_telemetry_resolve.py` (CHG-021/024). |
| `tests/unit/test_events_catalog.py` | modificato | `_EXPECTED_EVENTS` esteso a 17 voci con commento ancorante CHG-025. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest unit:
**668 PASS** unit/gov/golden (era 663 a CHG-024, +5 nuovi cache telemetry).
Pytest integration: **138 PASS** (incl. live, invariato). **806 PASS**
totali (era 801 a CHG-024).

## Why

CHG-019 ha persistito la cache `description_resolutions` per il flow
descrizione+prezzo (CHG-020). UNIQUE `(tenant_id, description_hash)`
garantisce idempotency, ma **l'efficacia** della cache è oggi
invisibile in produzione:

- **Quanto la cache risparmia in quota Keepa/SERP?** Sconosciuto. Senza
  hit count si naviga al buio sul costo operativo del flow.
- **I CFO ricorrenti hanno listini stabili?** Hit rate alta = sì
  (cache value chiaro). Miss dominanti = no (cache spreco di
  storage).
- **Cache TTL serve davvero?** Out-of-scope CHG-022 lasciava la
  decisione al Leader. Senza dati hit/miss osservati, il Leader
  decide alla cieca.

CHG-025 espone il dato. Il pattern è simmetrico a CHG-024
(`ui.override_applied` per A3): aggiungiamo l'osservabilità DOPO che
la feature è in produzione, una volta che esiste un consumatore reale
del segnale.

### Decisioni di design

1. **Sito di emit = caller, non repository**: il repository
   `asin_resolver_repository.py` resta puro persistence (no `logging`
   import), pattern coerente con `save_session_result` /
   `set_config_override_*`. Il caller `resolve_listino_with_cache` ha
   più contesto (`tenant_id` deciso a livello applicativo), e simmetria
   con `_emit_ui_*` di `dashboard.py` (helper puri inline).

2. **Campo `table` invece di evento dedicato per cache**: pattern
   estendibile. Future cache (es. `bsr_cache`, `category_cache`) si
   aggiungono additivamente cambiando solo il valore di `table`,
   senza nuove voci di catalogo. Coerente con `reason` di
   `ui.resolve_failed` (CHG-024).

3. **`factory is None` → NO emit**: il caso "cache disabled" non è
   né hit né miss applicativo. Emettere `cache.miss` su factory None
   distorcerebbe il KPI (`hit_rate = n_hits / (n_hits + n_misses)`):
   il denominatore includerebbe casi in cui la cache non è proprio
   stata consultata. Decisione esplicita: KPI = hit rate sui lookup
   effettuati.

4. **Helper puri (no inline `_logger.debug`)**: pattern consolidato
   CHG-021/024. Permette test caplog senza Streamlit / DB context.

5. **DEBUG level**: coerente con il catalogo. INFO sarebbe
   semanticamente più corretto per `cache.hit` (è un evento "normale
   del business"), ma il catalogo ha già stabilito DEBUG come livello
   uniforme — coerenza batte semantica granulare per ora.

6. **`_CACHE_TABLE_DESCRIPTION_RESOLUTIONS` costante module-level vs
   stringa letterale**: typo-safety + grep-friendliness. Future
   estensioni cache useranno costanti analoghe (es.
   `_CACHE_TABLE_BSR`).

7. **Catalogo passa 15 → 17 voci**: errata additiva (pattern
   CHG-021/024/058), non supersessione. Regola ADR-0001 non si applica
   a modifiche additive di cataloghi.

8. **File test dedicato `test_listino_input_cache_telemetry.py`**:
   separation-of-concern. Pattern coerente con
   `test_dashboard_telemetry_resolve.py` (telemetry helper di
   `dashboard.py`). Il file `test_listino_input.py` esistente copre
   helper non-telemetry (parser, builder, override).

### Out-of-scope

- **Telemetria dal repository (`db.cache_hit/miss`)**: pattern
  alternativo se in futuro la cache verrà consultata da molti caller
  (oggi solo `resolve_listino_with_cache`). Decisione Leader pendente
  se serve.
- **Cache TTL `description_resolutions` + `expires_at` column**:
  out-of-scope CHG-022 esplicito. Decisione Leader pendente, ora
  finalmente DECIDIBILE su dati osservati post-CHG-025.
- **`cache.bypass` per `factory is None`**: scope futuro se
  l'osservabilità "cache disabilitata" diventa rilevante.
- **Telemetria `cache.upsert` post-resolve**: oggi `upsert_resolution`
  è invisibile. Scope futuro errata se serve tracking write rate.
- **Dashboard observability cache hit rate**: scope futuro multi-page B2.
- **Refactor a `EVENT_CACHE_*` costanti nei caller**: scope futuro
  (out-of-scope CHG-021 dec. 6). Pattern governance test grep richiede
  stringhe letterali.

## How

### `events.py` (highlight 2 nuove voci)

```python
CANONICAL_EVENTS: Final[dict[str, tuple[str, ...]]] = {
    # ... 15 voci esistenti ...
    # Cache `description_resolutions` (ADR-0015) — errata CHG-2026-05-01-025
    "cache.hit": ("table", "tenant_id"),
    "cache.miss": ("table", "tenant_id"),
}

EVENT_CACHE_HIT: Final[str] = "cache.hit"
EVENT_CACHE_MISS: Final[str] = "cache.miss"
```

### `listino_input.py` (highlight)

```python
import logging

_logger = logging.getLogger(__name__)

_CACHE_TABLE_DESCRIPTION_RESOLUTIONS: str = "description_resolutions"


def _emit_cache_hit(*, table: str, tenant_id: int) -> None:
    _logger.debug("cache.hit", extra={"table": table, "tenant_id": tenant_id})


def _emit_cache_miss(*, table: str, tenant_id: int) -> None:
    _logger.debug("cache.miss", extra={"table": table, "tenant_id": tenant_id})


# In resolve_listino_with_cache:
if factory is not None:
    with factory() as db_session:
        cached = find_resolution_by_hash(...)
        if cached is not None:
            cached_asin = cached.asin.strip()
            cached_confidence = float(cached.confidence_pct)
            _emit_cache_hit(
                table=_CACHE_TABLE_DESCRIPTION_RESOLUTIONS,
                tenant_id=tenant_id,
            )
        else:
            _emit_cache_miss(
                table=_CACHE_TABLE_DESCRIPTION_RESOLUTIONS,
                tenant_id=tenant_id,
            )
```

### Test caplog (highlight pattern enum-string aperta)

```python
def test_cache_hit_open_table_enum(caplog):
    """`table` è enum-string aperta: future cache (es. bsr.cache) additive."""
    with caplog.at_level(logging.DEBUG, logger="talos.ui.listino_input"):
        _emit_cache_hit(table="bsr_cache", tenant_id=42)
    records = [r for r in caplog.records if r.message == EVENT_CACHE_HIT]
    assert records[0].table == "bsr_cache"
    assert records[0].tenant_id == 42
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 137 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria + governance | `uv run pytest tests/unit/test_listino_input_cache_telemetry.py tests/unit/test_events_catalog.py tests/governance -v` | **9 PASS** (5 cache telemetry + 2 catalog + 2 governance) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **668 PASS** (era 663, +5 nuovi cache telemetry) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |

**Rischi residui:**
- **Test caplog non esercita il caller reale**: i 5 test invocano gli
  helper direttamente. La validazione "find_resolution_by_hash → emit"
  end-to-end è coperta dai test integration `test_asin_resolver_repository.py`
  + i test esistenti del flow descrizione+prezzo, ma nessuno asserisce
  esplicitamente l'emit. Mitigazione: il pattern è semplice (1 if/else),
  diff = 11 righe; rivedibile in code review.
- **Doppio emit per riga su `factory is None` non emette**: se in futuro
  un caller dimentica di passare `factory`, la cache resta silente
  invece di emettere `cache.miss`. Decisione esplicita per evitare
  KPI distorto (out-of-scope decisione 3). Mitigazione: documentazione
  nei docstring degli helper.
- **DEBUG level masking in produzione**: come CHG-021 — il container
  produzione MVP usa DEBUG default. Mitigazione: idem CHG-021.
- **Drift dict ↔ ADR**: il governance snapshot `_EXPECTED_EVENTS`
  protegge da drift, ma il test non verifica meccanicamente che ogni
  evento del dict sia anche nell'ADR. Disciplina umana.
- **`table` enum-string non type-checked**: il pattern accetta
  qualsiasi stringa. Future cache senza errata catalogo possono
  emettere valori non documentati. Mitigazione: pattern coerente con
  `reason` di CHG-024; se diventa problema, scope futuro Enum tipizzato.

## Test di Conformità

- **Path codice applicativo:** `src/talos/observability/`,
  `src/talos/ui/` ✓ (aree ADR-0013 consentite).
- **ADR-0021 vincoli rispettati:**
  - Catalogo eventi canonici esteso via errata additiva (pattern
    CHG-021/024/058) — no supersessione necessaria.
  - Campi obbligatori esposti come `tuple`.
  - Modulo emittente documentato in errata.
  - DEBUG level coerente.
  - R-01 NO SILENT DROPS dinamico verde post-modifica
    (governance test grep verde).
- **ADR-0015 vincoli rispettati:** repository invariato (pattern
  Unit-of-Work preservato, no `logging` import in `persistence/`).
  Il caller emette dal layer applicativo.
- **ADR-0016 vincoli rispettati:** helper puri testabili senza
  Streamlit (pattern CHG-021/024). Il modulo `listino_input.py`
  resta zero-Streamlit (esistente da CHG-020).
- **Test unit puri:** ✓ (ADR-0019). 5 test caplog senza dipendenza
  Streamlit / DB.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:**
  `_emit_cache_hit` / `_emit_cache_miss` → ADR-0021 (telemetria) +
  ADR-0015 (cache layer). Costanti `EVENT_CACHE_*` → ADR-0021.
- **Backward compat:** modifica additiva 100%; `find_resolution_by_hash`
  / `upsert_resolution` invariati. Caller `resolve_listino_with_cache`
  signature invariata. Nessun caller esterno rompe.
- **Sicurezza:** zero secrets nei campi log; `table` (string fissa) +
  `tenant_id` (intero) sono dati operativi non sensibili.
- **Impact analysis pre-edit:** `find_resolution_by_hash` zero caller
  upstream esterni nell'indice. `resolve_listino_with_cache` zero
  caller upstream esterni. Risk LOW.
- **Detect changes pre-commit:** `gitnexus_detect_changes` risk
  **LOW** (35 simboli touched principalmente module-level constants
  refresh, 0 processi affetti, 4 file).

## Impact

- **Catalogo ADR-0021: 17/17 viventi** (era 15/15). +2 voci cache.
- **Cache `description_resolutions` osservabile**: `n_hits / (n_hits +
  n_misses)` ora misurabile in produzione. KPI attivabile in
  dashboard observability futura.
- **Decisione cache TTL ora supportata da dati**: Leader può decidere
  TTL su evidenza, non più alla cieca (out-of-scope CHG-022 sblocca).
- **`pyproject.toml` invariato** (no nuove deps).
- **Test suite +5 unit**: 668 unit/gov/golden (era 663).
- **MVP CFO target**: hardening incrementale; il flow descrizione+prezzo
  resta production-ready, ora con copertura osservabilità completa
  (UI → cache → resolver → DB).
- **Pattern `_emit_cache_*` puro**: replicabile per future cache (es.
  `bsr_cache` quando il blocco BSR si stratifica).

## Refs

- ADR: ADR-0021 (catalogo eventi canonici, errata additiva pattern
  CHG-021/024/058), ADR-0015 (cache `description_resolutions` da
  CHG-019), ADR-0016 (helper puri, modulo zero-Streamlit), ADR-0014
  (mypy/ruff strict), ADR-0019 (test unit caplog).
- Predecessori:
  - CHG-2026-05-01-019 (cache `description_resolutions` schema +
    repository): producer del segnale tracciato in CHG-025.
  - CHG-2026-05-01-020 (UI flow descrizione+prezzo): caller della cache.
  - CHG-2026-05-01-024 (telemetria UI override + resolve_failed):
    pattern errata additiva cataloghi ereditato.
  - CHG-2026-04-30-058 (drift `session.replayed`): pattern errata
    additiva.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato (errata snella + 5 test mirati + change doc auto-contenuto).
- Successore atteso: nessuno specifico in scope hardening telemetria.
  Possibili rotte (decisione Leader): cache TTL `description_resolutions`
  ora decidibile su dati, (B1) `structlog.bind` context tracing,
  (B2) refactor UI multi-page ADR-0016, (β) `upsert_session` semantica,
  (POLICY-001) Velocity bsr_chain.
- Commit: pending.
