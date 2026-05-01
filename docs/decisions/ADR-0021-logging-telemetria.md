---
id: ADR-0021
title: Logging & Telemetria — structlog + R-01 enforcement
date: 2026-04-29
status: Active
deciders: Leader
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

R-01 (NO SILENT DROPS) impone che ogni scarto venga loggato. ADR-0008 (Anti-Allucinazione) impone tracciabilità di ogni claim. ADR-0017 (Acquisizione Dati) prevede log strutturato dei mismatch dei selettori scraping. ADR-0018 (Algoritmo) prevede log dei kill-switch e veto.

Senza un ADR dedicato:
- ogni modulo userebbe il suo logger ad-hoc (`print`, `logging.getLogger`, etc.) → log inutilizzabili;
- R-01 sarebbe verificabile solo a livello di codice statico (grep), non a runtime (effettivo evento di log);
- il drift dati Keepa (rischio L24) non sarebbe osservabile in produzione.

## Decisione

### Libreria: `structlog`

JSON output, livello configurabile, integrazione con stdlib `logging`.

Scelta vs alternative:
- `structlog` >> `loguru` (loguru è meno strutturato, output non JSON nativo)
- `structlog` >> stdlib `logging.JSONFormatter` (structlog ha context immutabile, processor pipeline configurabile)

### Configurazione

`src/talos/observability/logging_config.py`:

```python
import structlog
import logging

def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        cache_logger_on_first_use=True,
    )
```

Bootstrap in `src/talos/__init__.py` o in entrypoint Streamlit/CLI.

### Eventi strutturati canonici (R-01 enforcement)

Ogni dato non-banale che viene scartato/escluso/modificato deve produrre un evento strutturato:

| Evento | Modulo | Campi obbligatori |
|---|---|---|
| `extract.kill_switch` | `extract/samsung.py` | `asin`, `reason`, `mismatch_field`, `expected`, `actual` |
| `vgp.veto_roi_failed` | `vgp/veto.py` | `asin`, `roi_pct`, `threshold` |
| `vgp.kill_switch_zero` | `vgp/score.py` | `asin`, `match_status` |
| `tetris.skipped_budget` | `tetris/allocator.py` | `asin`, `cost`, `budget_remaining` |
| `panchina.archived` | `tetris/panchina.py` | `asin`, `vgp_score` |
| `keepa.miss` | `io_/keepa_client.py` | `asin`, `error_type`, `retry_count` |
| `keepa.rate_limit_hit` | `io_/keepa_client.py` | `requests_in_window`, `limit` |
| `scrape.selector_fail` | `io_/scraper.py` | `asin`, `selector_name`, `html_snippet_hash` |
| `ocr.below_confidence` | `io_/ocr.py` | `file`, `confidence`, `threshold`, `text_extracted` |
| `db.audit_log_write` | `persistence/audit.py` | `actor`, `table`, `op`, `row_id` |
| `session.replayed` | `orchestrator.py` | `asin_count`, `locked_in_count`, `budget`, `budget_t1` |

**Vincolo:** ogni `.drop()`, `.skip()`, `continue` su listino o pipeline VGP deve essere preceduto o seguito da un evento di log strutturato. Test `tests/governance/test_log_on_drop.py` verifica empiricamente: dato un input con scarto noto, controlla che l'evento di log corrispondente sia stato emesso.

### Output

| Ambiente | Output | Razionale |
|---|---|---|
| Sviluppo locale | Console colorata (`structlog.dev.ConsoleRenderer`) | Leggibilità |
| CI | JSON su stderr | Parsable per debug failure |
| Produzione (MVP locale) | JSON su file rotato (`/var/log/talos/talos.jsonl`) | Audit + grep |
| Streamlit | Console + file (override via env) | Debug in tempo reale |

Rotazione: `RotatingFileHandler` 10MB × 7 file (configurabile).

### Livelli di log

| Livello | Quando usarlo |
|---|---|
| `DEBUG` | Dettagli granulari per debug (es. shape DataFrame, intermediate values) |
| `INFO` | Eventi normali del business (sessione iniziata, ordine effettuato, listino caricato) |
| `WARNING` | Anomalie recoverable (Keepa miss → fallback scraping; selector mismatch → fallback selector) |
| `ERROR` | Errori non-fatal (rate limit hit; OCR sotto soglia; ASIN AMBIGUO bloccante) |
| `CRITICAL` | Stato inconsistente (DB inaccessibile; kill_switch su tutto il listino; veto_roi su tutto il listino) |

Default ambiente:
- Dev: `DEBUG`
- CI: `INFO`
- Prod: `INFO`

### Context binding

Ogni sessione di analisi imposta context globale:

```python
structlog.contextvars.bind_contextvars(
    session_id=session.id,
    listino_hash=session.listino_hash,
    velocity_target=session.velocity_target,
    budget_eur=float(session.budget_eur),
)
```

Tutti gli eventi successivi nella stessa task ereditano questi campi automaticamente.

### Metriche (post-MVP, non-decisione qui)

Prometheus / OpenTelemetry esclusi dall'MVP. Eventuale ADR-NNNN futuro post-MVP.

### Audit log DB ↔ structlog

Ogni `INSERT` in `audit_log` (ADR-0015) deve essere replicato come evento `db.audit_log_write` in structlog. Doppia tracciabilità: DB per audit storico, structlog per debug/correlation.

## Conseguenze

**Positive:**
- R-01 verificabile sia staticamente (grep `\.drop\(`) sia dinamicamente (presenza eventi log canonici).
- Debug post-failure: `cat talos.jsonl | jq 'select(.session_id=="123")'` ricostruisce il flusso completo.
- Drift dati Keepa monitorabile: analisi periodica eventi `keepa.miss` + `scrape.selector_fail`.

**Negative / costi:**
- Disciplina richiesta: ogni nuovo modulo deve aderire al catalogo eventi canonici.
- Volume log su 10k righe × N sessioni può crescere rapido. Rotazione 10MB×7 = ~70MB max, accettabile.
- JSON output meno leggibile in console (mitigato dal renderer dev).

**Effetti collaterali noti:**
- Modificare la lista degli eventi canonici è un cambio non-banale (impatta test governance) → richiede change document.
- Performance: structlog è lazy + cache: <5% overhead vs logging stdlib. Trascurabile.

## Test di Conformità

1. **Test catalogo eventi:** `tests/governance/test_log_events_catalog.py` verifica che ogni modulo che ha `.drop`/`.skip`/`continue` abbia almeno una chiamata a un evento del catalogo.
2. **Test R-01 dinamico:** `tests/governance/test_r01_log_emission.py` simula un input con scarto noto (es. ASIN con KILL-SWITCH) e verifica che l'evento `extract.kill_switch` sia stato emesso (capture handler).
3. **JSON validity:** ogni evento di log in CI è validato come JSON parsable (`jq -e .`).
4. **Context binding:** test verifica che eventi nella stessa sessione abbiano stesso `session_id`.
5. **Coverage observability:** modulo `observability/` ≥ 80% (ADR-0019).

## Cross-References

- ADR correlati: ADR-0008 (anti-allucinazione: tracciabilità), ADR-0013 (struttura `observability/`), ADR-0014 (stack), ADR-0015 (audit_log DB), ADR-0017 (eventi acquisizione), ADR-0018 (eventi algoritmo), ADR-0019 (test governance log events)
- Governa: `src/talos/observability/`
- Impatta: ogni modulo che produce log; ogni operazione che scarta/modifica dati
- Test: `tests/governance/test_log_events_catalog.py`, `test_r01_log_emission.py`, `test_log_context.py`
- Commits: `<pending>`

## Rollback

Se structlog risulta inadeguato (es. esigenza OpenTelemetry):
1. Promulgare ADR-NNNN per migrare a OpenTelemetry SDK + structlog come transport.
2. Mantenere catalogo eventi canonici (è il contratto, non l'implementazione).
3. Adapter: `observability/logging_config.py` riconfigurato.

Se R-01 enforcement dinamico è troppo invasivo:
1. Errata Corrige a ADR-0021: degradare a enforcement statico (grep) only.
2. Mantenere comunque structlog come libreria.

## Errata

**2026-04-30 (CHG-2026-04-30-058) — additivo catalogo eventi.**
Aggiunto evento canonico `session.replayed` per tracciare le esecuzioni
di `replay_session` (CHG-2026-04-30-056). Campi obbligatori:
`asin_count`, `locked_in_count`, `budget`, `budget_t1`. Modulo emittente:
`orchestrator.py`. Razionale: il what-if non e' persistito in DB, ma
deve restare tracciabile per audit ("quanti scenari ha esplorato il
CFO?"). Modifica additiva, non altera la semantica degli eventi
esistenti — non richiede supersessione (regola ADR-0001 non si applica).

**2026-05-01 (CHG-2026-05-01-021) — additivo catalogo eventi UI + bonus correttivo.**
Aggiunti due eventi canonici per il flow descrizione+prezzo (CHG-020):

| Evento | Modulo | Campi obbligatori |
|---|---|---|
| `ui.resolve_started` | `ui/dashboard.py` | `n_rows`, `has_factory` |
| `ui.resolve_confirmed` | `ui/dashboard.py` | `n_total`, `n_resolved`, `n_ambiguous` |

Razionale: il flow `(descrizione, prezzo) → ASIN` consuma quota
SERP/Keepa al primo click ("Risolvi descrizioni"); senza `ui.resolve_started`
il costo e' invisibile in produzione. `ui.resolve_confirmed` traccia il
conversion rate (quanti listini umani caricati arrivano effettivamente
a `run_session`) — KPI prodotto per misurare se il MVP CFO regge
nell'uso reale. Catalogo ora **13 voci totali**.

**Bonus correttivo:** la voce `session.replayed` (errata CHG-058) era
stata aggiunta ad ADR-0021 ma non a `src/talos/observability/events.py`
(`CANONICAL_EVENTS` rimasto a 10 voci). Drift sanato in CHG-021: il dict
ora contiene tutte le 13 voci. Modifica additiva, non altera la
semantica degli eventi esistenti — non richiede supersessione.

**2026-05-01 (CHG-2026-05-01-024) — additivo catalogo eventi UI (round 5+).**
Aggiunti due eventi canonici per chiudere la copertura del flow
descrizione+prezzo (CHG-020 + hardening A1+A2+A3 CHG-021/022/023):

| Evento | Modulo | Campi obbligatori |
|---|---|---|
| `ui.override_applied` | `ui/dashboard.py` | `n_overrides`, `n_eligible` |
| `ui.resolve_failed` | `ui/dashboard.py` | `reason`, `n_rows` |

Razionale: `ui.override_applied` traccia l'**adoption rate** della
feature override candidato manuale (A3 CHG-023): `n_overrides / n_eligible`
misura la % di righe ambigue su cui il CFO sostituisce il top-1
automatico del resolver. KPI prodotto per validare se l'A3 è
effettivamente usato nell'uso reale o se il top-1 è già "abbastanza
buono". `ui.resolve_failed` traccia i fail-mode pre-resolve (oggi solo
`reason="keepa_key_missing"`, in futuro `"exception"` se il resolver
crash) — chiude il gap di osservabilità tra `ui.resolve_started` e
`ui.resolve_confirmed` (un fail manca da entrambi).

`reason` è enum-string aperta: il primo valore in produzione è
`"keepa_key_missing"`. Nuovi valori si aggiungono additivamente senza
rompere il contratto. Catalogo ora **15 voci totali**. Modifica
additiva, non altera la semantica degli eventi esistenti — non
richiede supersessione (regola ADR-0001 non si applica).
