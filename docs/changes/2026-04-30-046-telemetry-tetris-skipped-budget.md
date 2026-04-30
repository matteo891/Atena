---
id: CHG-2026-04-30-046
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0021, ADR-0019, ADR-0018, ADR-0014
---

## What

Doppio risultato:

1. **Bug fix governance** in `tests/governance/test_log_events_catalog.py`:
   il regex `^\s*continue\b` mancava di `re.MULTILINE`. `re.search` con
   `^` matcha solo l'inizio dell'intero file → il test era de facto un
   no-op per il pattern `continue` (false positive dei moduli `tetris/`,
   `vgp/`, `orchestrator.py`).
2. **Telemetria** `tetris.skipped_budget` (ADR-0021 catalogo):
   `allocate_tetris` ora emette evento canonico quando una riga viene
   skippata in Pass 2 per `cost_total > cart.remaining` (R-06 letterale).
3. **Orchestrator hardening**: `continue` defensive nel loop
   `cart_profits` sostituito con `raise RuntimeError(...)` (branch
   impossibile per costruzione; raise > silent skip, R-01).

| File | Tipo | Cosa |
|---|---|---|
| `tests/governance/test_log_events_catalog.py` | modificato | +`re.MULTILINE` flag su pattern `^\s*continue\b` con commento esplicito che documenta il fix di CHG-046 |
| `src/talos/tetris/allocator.py` | modificato | +`import logging` + `_logger` modulo + `_logger.debug("tetris.skipped_budget", ...)` con `extra={asin, cost, budget_remaining}` (campi da catalogo events.py) |
| `src/talos/orchestrator.py` | modificato | `continue` nel loop `cart_profits` → `raise RuntimeError(...)` con messaggio diagnostico ("BUG interno: ASIN '...' nel cart ma assente da scored_sorted") |
| `tests/unit/test_tetris_telemetry.py` | nuovo | 3 test `caplog` (emissione su skip over-budget, no emissione se tutti entrano, no emissione su score=0) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | entry `allocator.py` aggiornata con ADR-0021 secondario |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **420 PASS**
(372 unit/governance/golden + 48 integration).

## Why

ADR-0021 specifica un catalogo eventi canonici (CHG-2026-04-30-006) che
governa R-01 NO SILENT DROPS dinamico. Il governance test era stato
introdotto come sentinella ma il regex aveva un bug silente: `re.search(
r"^\s*continue\b", content)` matcha **solo** se la prima riga del file
inizia con `continue` — impossibile per Python. Questo ha esentato a
torto i moduli con loop di scarto (`tetris/allocator`, `orchestrator`).

Senza il fix, il test resterebbe falsamente verde anche con scarti
silenziosi. Senza la telemetria, il CFO non vede dove il Tetris perde
ASIN per cassa insufficiente: niente debug, niente aggregati.

### Decisioni di design

1. **`re.MULTILINE` invece di `re.findall` riga-per-riga**: minimizza il
   diff. La semantica e' identica (match `^` su ogni riga).
2. **`_logger.debug` (non info)**: l'evento e' frequente in listini
   grandi (10k ASIN → potenzialmente migliaia di skip per saturazione).
   Default level INFO non li mostra; `caplog.at_level(DEBUG)` li
   cattura nei test. In produzione un toggle `DEBUG=1` per audit.
3. **`extra=` per campi strutturati**: stdlib `logging` non e' structlog
   nativo, ma `extra` espone i campi come attributi del LogRecord
   accessibili via `getattr(record, "asin", None)`. Il test usa questo
   pattern. Migrazione completa a `structlog.bind(...)` e' scope CHG
   futuro (richiede `bind_session_context` / `clear_session_context`
   helper di `observability.logging_config`).
4. **Stringa letterale `"tetris.skipped_budget"`** (non
   `EVENT_TETRIS_SKIPPED_BUDGET` costante): il governance test fa
   sostanzialmente `grep` della stringa, e una costante con `Final[str]`
   non comparirebbe come stringa nel modulo che la importa. Stringa
   letterale = test passa + leggibilita' immediata.
5. **`continue` defensive in orchestrator → `raise`**: la condizione
   `match.empty` e' un caso "non dovrebbe mai accadere" (allocate_tetris
   valida che ogni ASIN esista in vgp_df). Silenziarlo nascondeva un
   eventuale BUG futuro di mapping. Il raise e' R-01 puro.
6. **Niente telemetria per `vgp.veto_roi_failed` e `vgp.kill_switch_zero`
   (vettoriali in `compute_vgp_score`)**: scope CHG futuro (`compute_vgp_score`
   non ha loop, vorrebbe summary aggregato). Il governance test non
   flagga `score.py` (no `continue`/`drop`/`skip`).
7. **Niente telemetria per `panchina.archived`** (modulo no `continue`):
   stesso ragionamento. Scope futuro.

### Out-of-scope

- **Migrazione completa a `structlog`** con context binding: scope
  CHG dedicato.
- **Telemetria aggregata in `compute_vgp_score`** (`vgp.veto_roi_failed`
  count, `vgp.kill_switch_zero` count, `panchina.archived` count):
  scope CHG-047 o successivo.
- **Nuovi eventi canonici** (`session.started`, `session.persisted`,
  `session.failed`): richiede nuovo CHG con aggiornamento
  `events.py` + ADR-0021 errata corrige. Il catalogo attuale copre
  scarti operativi, non lifecycle di sessione.

## How

### `tests/governance/test_log_events_catalog.py` (highlight)

```python
_DROP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.drop\("),
    re.compile(r"\.skip\("),
    re.compile(r"^\s*continue\b", re.MULTILINE),  # CHG-046 fix
)
```

### `src/talos/tetris/allocator.py` (highlight)

```python
import logging
_logger = logging.getLogger(__name__)

# Pass 2 (R-06):
if cost_total > cart.remaining:
    _logger.debug(
        "tetris.skipped_budget",
        extra={
            "asin": str(row[asin_col]),
            "cost": cost_total,
            "budget_remaining": cart.remaining,
        },
    )
    continue
```

### `src/talos/orchestrator.py` (highlight)

```python
for item in cart.items:
    match = scored_sorted[scored_sorted["asin"] == item.asin]
    if match.empty:
        msg = (
            f"BUG interno: ASIN '{item.asin}' nel cart ma assente da "
            "scored_sorted; mapping VgpResult/Cart corrotto."
        )
        raise RuntimeError(msg)
    ...
```

### Test plan

3 unit (caplog):
1. `test_skipped_budget_emits_canonical_event` — riga over-budget → 1
   record con asin/cost/budget_remaining corretti.
2. `test_no_skipped_budget_event_when_all_fit` — niente record se nessuna
   riga supera il budget.
3. `test_skipped_budget_event_does_not_trigger_for_score_zero` — skip per
   `vgp_score==0` NON emette `tetris.skipped_budget` (motivo diverso,
   gia' a monte da R-05/R-08).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 86 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **372 PASS** (369 + 3) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **48 PASS** |

**Rischi residui:**
- **Volume log su listini >>1k**: `tetris.skipped_budget` emesso per ogni
  riga skippata. Default level DEBUG mitiga in produzione (handler INFO+
  filtra). Aggregare a fine sessione in summary log e' errata futura.
- **Stdlib `logging` invece di `structlog`**: il binding di context
  (session_id, tenant_id) richiede structlog. Migrazione scope CHG
  successivo.
- **`raise RuntimeError` in orchestrator**: se mai si attivasse, il
  Streamlit mostra `st.error`. Ottimo per debug; in produzione un BUG
  di mapping interno e' raro ma il fail-fast lo fa emergere.

## Impact

**Sentinella governance R-01 ripristinata**: il test ora cattura
realmente i pattern `continue` con grep nei moduli applicativi. Future
PR che introducono scarti silenziosi falliranno il gate.

`tetris.skipped_budget` e' il primo evento canonico vivente (gli altri
9 sono catalogo dormiente in attesa dei rispettivi moduli — `extract.*`,
`keepa.*`, `scrape.*`, `ocr.*`, `db.audit_log_write`, `panchina.archived`,
`vgp.veto_roi_failed`, `vgp.kill_switch_zero`). Pattern di emissione
documentato e replicabile per i prossimi.

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze` la
modifica del body di `allocate_tetris` (signature invariata, body
modificato).

## Refs

- ADR: ADR-0021 (logging/telemetria + catalogo eventi), ADR-0019 (test
  governance), ADR-0018 (R-06 letterale), ADR-0014 (mypy/ruff strict)
- Predecessori: CHG-2026-04-30-006 (osservability bootstrap),
  CHG-2026-04-30-036 (`allocate_tetris` originale)
- Successore atteso: CHG futuro per emissione aggregata in
  `compute_vgp_score` (`vgp.veto_roi_failed` count, `vgp.kill_switch_zero`
  count) + `panchina.archived` per panchina; migrazione a
  `structlog.bind(session_id, tenant_id, asin)` per context tracing
- Commit: `[pending]`
