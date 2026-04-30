---
id: CHG-2026-04-30-006
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 9298e70
adr_ref: ADR-0021, ADR-0019, ADR-0014
---

## What

Primo modulo applicativo di sostanza: **`src/talos/observability/`** con `configure_logging` reale + catalogo eventi canonici (10 voci ADR-0021). Sostituisce lo stub `__init__.py` introdotto in CHG-2026-04-30-004. Aggiunge `structlog>=24.4.0` come **prima dipendenza runtime** del progetto.

| File | Tipo | LOC | Cosa |
|---|---|---:|---|
| `src/talos/observability/events.py` | nuovo | 50 | `CANONICAL_EVENTS` dict[str, tuple[str, ...]] (10 voci, fonte di verità) + 10 costanti `Final[str]` per autocompletamento |
| `src/talos/observability/logging_config.py` | nuovo | 78 | `configure_logging(level, json_output)` + `bind_session_context(...)` + `clear_session_context()`. Pipeline structlog: contextvars merge → add_log_level → TimeStamper(iso) → StackInfoRenderer → format_exc_info → JSONRenderer/ConsoleRenderer |
| `src/talos/observability/__init__.py` | modificato | 17 | Re-export delle API pubbliche (CANONICAL_EVENTS, configure_logging, bind/clear_session_context) |
| `tests/unit/test_logging_config.py` | nuovo | 86 | 6 test unit con `LogCapture`: default OK, console renderer OK, invalid level raises, evento con kwargs propagato, session context propagato, clear rimuove binding |
| `tests/unit/test_events_catalog.py` | nuovo | 35 | 2 test: catalogo ha esattamente le 10 voci attese; ogni voce ha tupla campi non vuota di stringhe |
| `tests/governance/test_log_events_catalog.py` | nuovo | 51 | R-01 NO SILENT DROPS dinamico: scansiona `src/talos/`, fallisce se trova `.drop(`/`.skip(`/`continue` in file che non usano costanti canoniche del catalogo |
| `pyproject.toml` | modificato | +5 | `[project].dependencies` ora ha `structlog>=24.4.0` (commento spiega che è la prima dep runtime e che le altre entreranno modulo per modulo) |
| `uv.lock` | modificato | rigenerato | `structlog==25.5.0` lockato |

Quality gate locale: **12 test PASS**, ruff/format/mypy puliti su 4 source file.

## Why

ADR-0021 prescrive structlog + catalogo eventi canonici come componente fundamentale per R-01 NO SILENT DROPS. Il bootstrap di CHG-004 aveva volutamente lasciato `observability/__init__.py` come stub: ora che la pipeline locale + CI è verde, conviene introdurre il primo modulo concreto, **leggero ma cardine**, prima di qualunque modulo che generi log (vgp/tetris/io_/persistence).

Beneficio strutturale:
1. Ogni modulo successivo può importare `from talos.observability import configure_logging` e usare le costanti `EVENT_*` senza re-inventare il logging.
2. `tests/governance/test_log_events_catalog.py` è già attivo: appena uno dei prossimi CHG introdurrà un `.drop(` o `continue` in `src/talos/`, il test fallirà se manca la chiamata canonica. Disciplina R-01 enforced **dal giorno 1** del primo modulo.
3. `bind_session_context` è la base per rendere ogni evento di una sessione di analisi correlabile via `session_id` + `listino_hash` (utilizzo previsto da Streamlit dashboard di ADR-0016).

## How

### `events.py` — catalogo canonico

`CANONICAL_EVENTS: Final[dict[str, tuple[str, ...]]]` come fonte di verità: nome evento → tupla di campi obbligatori del kwargs. Le 10 voci coprono esattamente la tabella di ADR-0021:

```
extract.kill_switch     (asin, reason, mismatch_field, expected, actual)
vgp.veto_roi_failed     (asin, roi_pct, threshold)
vgp.kill_switch_zero    (asin, match_status)
tetris.skipped_budget   (asin, cost, budget_remaining)
panchina.archived       (asin, vgp_score)
keepa.miss              (asin, error_type, retry_count)
keepa.rate_limit_hit    (requests_in_window, limit)
scrape.selector_fail    (asin, selector_name, html_snippet_hash)
ocr.below_confidence    (file, confidence, threshold, text_extracted)
db.audit_log_write      (actor, table, op, row_id)
```

Per ogni evento c'è anche una costante `EVENT_<UPPER_SNAKE>: Final[str]` per uso applicativo (autocompletamento + refactor-safe via mypy strict).

### `logging_config.py` — API pubblica

Tre funzioni:

- `configure_logging(*, level="INFO", json_output=True) -> None` — kwargs-only per non sbagliare ordine. Validazione livello esplicita (ValueError se sconosciuto). Pipeline aderente alla decisione cardine di ADR-0021: `merge_contextvars → add_log_level → TimeStamper(iso) → StackInfoRenderer → format_exc_info → renderer`. Default `JSONRenderer` (ADR-0021: "JSON output default in CI/prod"); `ConsoleRenderer` solo per dev locale.
- `bind_session_context(*, session_id, listino_hash, velocity_target, budget_eur)` — wrapper su `structlog.contextvars.bind_contextvars` con i 4 campi prescritti da ADR-0021 nella sezione "Context binding".
- `clear_session_context()` — pulisce a fine sessione (necessario tra sessioni di test consecutive per evitare leak di binding).

Decisione: nessun bootstrap automatico in `talos.__init__`. Il caller (Streamlit/CLI/test) chiama `configure_logging()` esplicitamente. Questo evita che import `talos` per un test puro forzi configurazione globale del logger, lasciando il default stdlib.

### `__init__.py` — re-export

API pubbliche promosse a top-level del package: `from talos.observability import configure_logging`. Sezione `__all__` esplicita per `pyflakes`/mypy/ruff.

### Test unit (6 + 2)

`test_logging_config.py`:
- `test_configure_logging_default_no_raise` — sanity (kwargs di default OK)
- `test_configure_logging_console_renderer_no_raise` — sanity DEBUG + console renderer
- `test_configure_logging_invalid_level_raises` — `ValueError` su livello non valido
- `test_logger_emits_event_with_kwargs` — `LogCapture` cattura un evento canonico con i suoi campi
- `test_session_context_propagates` — i 4 campi di sessione finiscono in ogni evento successivo
- `test_clear_session_context_removes_bindings` — dopo clear, gli eventi non hanno più i campi di sessione

`test_events_catalog.py`:
- `test_catalog_has_ten_canonical_events` — esattamente le 10 voci attese (no drift)
- `test_catalog_each_event_has_non_empty_field_tuple` — invariante strutturale

### Test governance R-01 (1)

`test_log_events_catalog.py`:
- Scansiona ogni `src/talos/**/*.py`
- Pattern di "scarto": `\.drop\(`, `\.skip\(`, `^\s*continue\b`
- Fallisce se trova un file con almeno un pattern ma **nessuna costante canonica** del catalogo
- In bootstrap (oggi): zero file con quei pattern → test PASS banalmente
- Diventa significativo non appena arriva un modulo applicativo

### Decisioni di config

- **`structlog>=24.4.0`** in `[project].dependencies`. Versione minima moderna con type hints inline; l'attuale è 25.5.0.
- **No `cache_logger_on_first_use=False` di default in produzione:** il default è `True` come da ADR-0021 (performance). I test usano `structlog.testing.LogCapture` con `cache_logger_on_first_use=False` esplicito per re-config tra test.
- **`from __future__ import annotations`** su tutti i moduli nuovi: postpone evaluation dei type hints (PEP 563), riduce import overhead.

## Tests

Test automatici eseguiti localmente (Test Gate ADR-0002). Tutti **PASS**.

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 10 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 4 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 12 passed in 0.17s |
| Pre-commit-app E2E | (verificato in commit reale dal hook governance) | atteso PASS |

**Validazione semantica:**
- `LogCapture` cattura eventi con tutti i kwargs come dict piatto (verificato in `test_logger_emits_event_with_kwargs`).
- `bind_contextvars` propaga i 4 campi `session_id/listino_hash/velocity_target/budget_eur` a ogni evento successivo (verificato in `test_session_context_propagates`).
- `clear_contextvars` rimuove i binding (verificato in `test_clear_session_context_removes_bindings`).

**Rischi residui:**
- `structlog` 25.x potrebbe deprecare API minori (`structlog.types.Processor`, `make_filtering_bound_logger`). Pinning `>=24.4.0` accetta drift; in caso di breaking change → errata corrige di `logging_config.py` con commit dedicato.
- Il pattern `^\s*continue\b` di `test_log_events_catalog.py` è euristico: in futuro potrebbe servire una whitelist di moduli (`_EXEMPT_FILES`) per `continue` benigni in loop di parsing. Disciplina: aggiungere a `_EXEMPT_FILES` solo dopo discussione esplicita.
- Il catalogo è "fonte di verità" ma non è ancora collegato a verifica statica dei kwargs (mypy non sa che `keepa.miss` richiede `asin/error_type/retry_count`). Estensione futura: TypedDict o mypy plugin custom — non in scope MVP.
- Plugin `sqlalchemy[mypy]` ancora non attivato (entrerà col primo modulo `persistence/`).

## Refs

- ADR: ADR-0021 (decisione cardine), ADR-0019 (test strategy — governance test attivato), ADR-0014 (mypy strict + ruff strict applicati)
- Predecessore: CHG-2026-04-30-005 (CI base)
- Successore atteso: probabilmente primo modulo `persistence/` (ADR-0015) — ora il logging è disponibile per istrumentare le query
- Commit: `9298e70`
