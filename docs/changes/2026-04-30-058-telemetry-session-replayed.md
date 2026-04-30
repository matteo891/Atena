---
id: CHG-2026-04-30-058
date: 2026-04-30
author: Claude (su autorizzazione Leader, modalità "macina" sessione 2026-04-30 sera)
status: Pending
commit: pending
adr_ref: ADR-0021, ADR-0019, ADR-0009, ADR-0014
---

## What

Errata corrige al catalogo eventi canonici di ADR-0021: aggiunge
`session.replayed` come 11° evento (orchestrator.py, campi
`asin_count`, `locked_in_count`, `budget`, `budget_t1`). Emissione
in `replay_session` (CHG-056) come `_logger.debug` post-costruzione
del nuovo `SessionResult`.

| File | Tipo | Cosa |
|---|---|---|
| `docs/decisions/ADR-0021-logging-telemetria.md` | modificato | + riga `session.replayed` nel catalogo eventi (sezione "Eventi strutturati canonici"); + sezione `## Errata` con voce CHG-058 (additivo, non altera semantica eventi esistenti). |
| `src/talos/orchestrator.py` | modificato | + `import logging`; + `_logger = logging.getLogger(__name__)`; + emissione `_logger.debug("session.replayed", extra={...})` in `replay_session` post-costruzione `SessionResult`. |
| `tests/unit/test_replay_session_telemetry.py` | nuovo | 2 test caplog: evento emesso con campi obbligatori del catalogo; `locked_in_count` riflette i locked override applicati. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **489 PASS**
(389 unit/governance/golden + 100 integration).

## Why

CHG-056 ha implementato `replay_session` come scenario "what-if" non
persistito. Senza telemetria, l'audit operativo perde la visibilità su:

- Quante volte il CFO esplora scenari (= rumore vs decisione finale).
- Quali valori di `budget` / `locked_in` vengono testati prima della
  scelta finale (segnale UX preziosi).
- Pattern di replay anomali (es. 100 replay con budget oscillante →
  CFO indeciso o bug UI).

Senza questo CHG il `replay_session` era invisibile post-esecuzione.
Con l'evento canonico, il filtro `grep "session.replayed"` su
`/var/log/talos/talos.jsonl` (ADR-0021 sez. Output) ricostruisce
l'intera attività what-if del CFO.

### Decisioni di design

1. **Errata corrige additiva, non supersessione**: ADR-0001 prescrive
   supersessione per "modifiche di sostanza". Aggiungere un evento al
   catalogo non altera la semantica degli eventi esistenti — è un
   superinsieme. Pattern coerente con ADR-0009 (errata corrige =
   modifica testuale + sezione errata aggiornata).

2. **Campi obbligatori `asin_count`, `locked_in_count`, `budget`,
   `budget_t1`**: scelti per audit "qual era la dimensione del
   problema?" + "quanto ha forzato il CFO?" + "in entrata e uscita
   monetaria". `budget_t1` consente di confrontare l'efficienza
   compounding tra scenari senza joinare DB.

3. **`logger.debug` (non INFO)**: pattern coerente con
   `tetris.skipped_budget` (CHG-046), `vgp.veto_roi_failed` (CHG-049).
   Default INFO+ in produzione → silente; opt-in via handler dedicato
   per audit.

4. **Stringa letterale `"session.replayed"`**: pattern noto (CHG-046
   bug fix governance regex). Importare una costante non lascia
   traccia testuale → `test_log_events_catalog` non la vedrebbe.

5. **Emissione DOPO costruzione `SessionResult`**: il counter
   `len(replayed.enriched_df)` e `len(item.locked)` derivano dal
   risultato finale, non dagli input. Audit fedele al "cosa è stato
   prodotto", non al "cosa è stato chiesto".

6. **Niente bind structlog `(session_id, tenant_id)`** ancora: il
   modulo `replay_session` non ha accesso al `session_id` del
   `SessionResult` ricaricato (`SessionResult` non lo include
   intenzionalmente per coerenza con `run_session` originale che
   non ha id pre-DB). Migrazione `structlog.bind` resta scope
   dedicato.

### Out-of-scope

- **Evento `session.started` / `session.completed`** per `run_session`:
  scope errata catalogo dedicata se utile.
- **`session_id` nei campi**: il `SessionResult` non porta l'id; per
  averlo serve passarlo al `replay_session` come kwarg, errata futura.
- **Migrazione structlog**: scope dedicato (eccezione 5 — caplog
  test pattern).
- **Aggregazione "session.replayed.summary"**: scope futuro se i log
  diventano troppo voluminosi.

## How

### ADR-0021 errata (highlight)

```markdown
| `session.replayed` | `orchestrator.py` | `asin_count`, `locked_in_count`, `budget`, `budget_t1` |

## Errata
**2026-04-30 (CHG-058) — additivo catalogo eventi.** Aggiunto evento
`session.replayed` ... Modifica additiva, non altera la semantica
degli eventi esistenti — non richiede supersessione.
```

### `replay_session` emissione (highlight)

```python
_logger = logging.getLogger(__name__)

def replay_session(loaded, *, locked_in_override=None, budget_override=None):
    # ... (stesso flusso CHG-056)
    replayed = SessionResult(cart=cart, panchina=panchina, budget_t1=budget_t1,
                             enriched_df=sorted_df)
    _logger.debug(
        "session.replayed",
        extra={
            "asin_count": len(replayed.enriched_df),
            "locked_in_count": sum(1 for item in replayed.cart.items if item.locked),
            "budget": float(new_budget),
            "budget_t1": float(replayed.budget_t1),
        },
    )
    return replayed
```

### Test plan (2 unit caplog)

1. `test_replay_emits_session_replayed_event` — campi obbligatori del
   catalogo presenti nel record; `asin_count == len(enriched_df)`,
   `budget == budget_override`.
2. `test_replay_event_locked_in_count` — locked_in_override=["RT02"]
   → `locked_in_count == 1`.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 100 files already formatted |
| Type | `uv run mypy src/` | 40 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **389 PASS** (387 + 2) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **100 PASS** (invariato) |

**Rischi residui:**
- **Volume log su `replay_session` chiamato in loop**: il what-if UI
  emette 1 evento per click. Volume trascurabile (CFO clicca
  manualmente). Se profilo automatizzato dovesse spammare replay,
  errata futura per sampling.
- **Niente `session_id`**: il match log ↔ DB session richiede
  manualmente correlare timestamp + `budget`. Errata futura se
  necessario.
- **caplog su `talos.orchestrator` cattura anche altri eventi**: i
  test filtrano per `record.message == "session.replayed"` per
  isolare. Pattern coerente con altri test telemetria.

## Test di Conformità

- **Path codice applicativo:** `src/talos/orchestrator.py` ✓ (top-level
  consentito).
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** modifica esistente (`replay_session`)
  + emissione evento del catalogo aggiornato.
- **Errata corrige conforme ADR-0009:** sezione `## Errata` aggiornata
  con voce CHG-058 + razionale "additivo, non altera semantica".
- **Stringa letterale rilevabile da governance test:** `"session.replayed"`
  visibile a `grep` (CHG-046 fix MULTILINE).

## Impact

**Catalogo ADR-0021 ora 5/11 eventi viventi**: `tetris.skipped_budget`
(CHG-046), `vgp.veto_roi_failed` (CHG-049), `vgp.kill_switch_zero`
(CHG-049), `panchina.archived` (CHG-049), `session.replayed`
(CHG-058). 6 dormienti (`extract.*`, `keepa.*`, `scrape.*`, `ocr.*`,
`db.audit_log_write`) si attiveranno con i rispettivi moduli.

What-if del CFO ora tracciabile via `grep "session.replayed"` sui log
strutturati.

## Refs

- ADR: ADR-0021 (logging/telemetria + catalogo), ADR-0019 (test
  pattern caplog), ADR-0009 (errata corrige), ADR-0014 (quality gate).
- Predecessori: CHG-2026-04-30-046 (primo evento canonico vivente),
  CHG-2026-04-30-049 (3 eventi vgp/panchina), CHG-2026-04-30-056
  (`replay_session`), CHG-2026-04-30-057 (UI consumer).
- Successore atteso: `session.started` / `session.completed`;
  `session_id` nei campi (richiede signature change `replay_session`);
  migrazione `structlog.bind`.
- Commit: pending (backfill).
