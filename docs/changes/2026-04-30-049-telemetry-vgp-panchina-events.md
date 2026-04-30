---
id: CHG-2026-04-30-049
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0021, ADR-0019, ADR-0018, ADR-0014
---

## What

Aggiunge **3 eventi canonici viventi** al cluster vgp/tetris (passa da 1
a 4 eventi attivi del catalogo ADR-0021):

- `vgp.veto_roi_failed` (asin, roi_pct, threshold) — emesso da
  `compute_vgp_score` per riga vetata da R-08 (sotto soglia ROI ma non
  killed).
- `vgp.kill_switch_zero` (asin, match_status) — emesso da
  `compute_vgp_score` per riga killed (R-05).
- `panchina.archived` (asin, vgp_score) — emesso da `build_panchina` per
  riga archiviata (idonei scartati per cassa, R-09).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/vgp/score.py` | modificato | +`import logging`/`_logger` + emissione per-asin di `vgp.veto_roi_failed` (loop `out.loc[veto_only_mask]`) e `vgp.kill_switch_zero` (loop `out.loc[kill_mask]`); +kwargs `asin_col="asin"` e `match_status_col="match_status"` opzionali (graceful skip se assenti) |
| `src/talos/tetris/panchina.py` | modificato | +`import logging`/`_logger` + emissione per-asin `panchina.archived` su `out.iterrows()` post-sort |
| `tests/unit/test_vgp_telemetry.py` | nuovo | 5 test `caplog` (veto event, kill event, no event quando tutti passano, skip senza asin_col, fallback match_status assente) |
| `tests/unit/test_panchina_telemetry.py` | nuovo | 3 test `caplog` (event per riga, vgp_score campo, no event se panchina vuota) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | entry `score.py` e `panchina.py` aggiornate con CHG-049 |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **438 PASS**
(380 unit/governance/golden + 58 integration).

## Why

CHG-046 ha aperto il pattern di emissione canonica con
`tetris.skipped_budget`. Il catalogo ADR-0021 ha 10 eventi dichiarati;
post CHG-046 solo 1 era vivente. Tre erano gia' definiti (`vgp.veto_*`,
`vgp.kill_*`, `panchina.archived`) ma mai emessi. Questo CHG li attiva.

Senza i 3 eventi:
- Audit: niente trace di **quanti** ASIN sono stati vetati / killed /
  archiviati. CFO sa solo "questi sono nel cart"; non sa "questi sono
  stati esclusi e perche'".
- Debug: profiler operativo cieco su scarti VGP. Se la pipeline
  decisionale "non vede" un ASIN, niente diagnostica.
- Compliance: storico decisione completo richiede log strutturato di
  ogni esclusione (R-01 NO SILENT DROPS dinamico).

### Decisioni di design

1. **Emissione per-asin (non summary)**: il catalogo ADR-0021 dichiara
   `("asin", ...)` come **campi obbligatori** dell'evento. Una summary
   `count` sarebbe un evento DIVERSO (`vgp.veto_summary`?), non
   coperto dal catalogo. Per non aggiungere eventi nuovi (ADR errata
   richiesta), emettiamo per-asin. Volume mitigato dal level DEBUG.
2. **Loop esplicito sulle righe filtered (`out.loc[mask]`)**: niente
   `.apply()` (lento), niente `iterrows()` su tutto il df (potrebbe
   essere 10k righe). Loop solo sulle righe da loggare → tipicamente
   1-5% del listino per veto + 1-3% per kill.
3. **`asin_col` come kwarg opzionale (default `"asin"`)**: caller-friendly.
   Se la colonna manca, niente emissione (graceful). Il modulo non
   forza il contratto, lo verifica.
4. **`match_status_col` opzionale, fallback `""`**: per kill events
   senza `match_status` nel df. Il catalogo dichiara `match_status`
   obbligatorio; emettiamo `""` come placeholder esplicito. Pattern
   coerente con stdlib logging (no `None` nei campi struct).
5. **`logger.debug`**: stesso livello di CHG-046. Default INFO+ in
   produzione → silente; `caplog.at_level(DEBUG, logger="talos.vgp.score")`
   nei test.
6. **`extra=` (stdlib logging)**: sempre per consistency con CHG-046.
   Migrazione a `structlog` con context binding (`session_id`, `tenant_id`)
   e' scope CHG futuro.
7. **Niente attivazione di `extract.kill_switch`** (catalogo): l'evento
   viene emesso dall'extractor (CHG futuro `io_/extract`), non dal
   `compute_vgp_score`. La distinzione semantica e' importante:
   `vgp.kill_switch_zero` = "VGP ha azzerato perche' kill_mask=True";
   `extract.kill_switch` = "estrattore ha messo kill_mask=True a monte".
8. **Stringa letterale `"vgp.veto_roi_failed"` etc**: il governance
   test (CHG-046 fix) cerca queste stringhe nei file. Importare la
   costante non lascerebbe traccia testuale → test fallirebbe.

### Out-of-scope

- **Eventi `extract.kill_switch`, `keepa.miss`, `keepa.rate_limit_hit`,
  `scrape.selector_fail`, `ocr.below_confidence`**: scope CHG `io_/extract`.
- **Evento `db.audit_log_write`**: scope CHG persistence audit hook.
- **Migrazione completa a `structlog.bind(session_id, tenant_id)`** con
  context tracing: scope CHG dedicato (richiede modifica
  `observability/logging_config.py`).
- **Aggregazione summary** (`{"event": "vgp.veto_summary", "count": N}`):
  scope futuro, richiede aggiunta nuovo evento al catalogo.
- **Telemetria volume reduction** (sampling, dedup) per listini
  >>10k: scope errata corrige post-MVP se profiler richiede.

## How

### `vgp/score.py` (highlight)

```python
# Dopo aver calcolato vgp_score:
if asin_col in out.columns:
    veto_only_mask = ~out["veto_roi_passed"] & ~kill_mask
    for asin, roi_value in zip(
        out.loc[veto_only_mask, asin_col],
        out.loc[veto_only_mask, roi_col],
        strict=False,
    ):
        _logger.debug(
            "vgp.veto_roi_failed",
            extra={"asin": str(asin), "roi_pct": float(roi_value), "threshold": veto_roi_threshold},
        )

    if kill_mask.any():
        # match_status fallback "" se colonna assente
        for asin, match_status in zip(...):
            _logger.debug("vgp.kill_switch_zero", extra={...})
```

### `tetris/panchina.py` (highlight)

```python
out = eligible.sort_values(score_col, ascending=False)
for asin, score in zip(out[asin_col], out[score_col], strict=False):
    _logger.debug(
        "panchina.archived",
        extra={"asin": str(asin), "vgp_score": float(score)},
    )
return out
```

### Test plan

- **vgp** (5):
  1. `test_veto_roi_failed_event_emitted` — 1 vetato → 1 record
  2. `test_kill_switch_zero_event_emitted` — 1 killed → 1 record con match_status
  3. `test_no_telemetry_when_all_pass` — niente record se tutti OK
  4. `test_telemetry_skipped_when_asin_col_absent` — graceful skip
  5. `test_kill_event_uses_empty_string_when_match_status_absent` — fallback
- **panchina** (3):
  1. `test_panchina_archived_event_per_row` — 3 in panchina → 3 record
  2. `test_panchina_archived_event_carries_vgp_score`
  3. `test_no_panchina_event_when_panchina_empty`

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 90 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **380 PASS** (372 + 8) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **58 PASS** (invariato) |

**Rischi residui:**
- **Volume log su listini >>1k**: 3 nuovi eventi per-asin si aggiungono
  a `tetris.skipped_budget`. Con 10k ASIN potenzialmente migliaia di
  emissioni per sessione. Default INFO+ filtra; in produzione handler
  DEBUG e' opt-in per audit. Aggregazione summary errata futura.
- **`zip(strict=False)`**: se le maschere divergono in lunghezza
  (impossibile per costruzione, ma defensive), `zip` salta la coda.
  Non emettere e' meglio che crash. Documentato.
- **Stdlib logging vs structlog**: il context binding (session_id,
  tenant_id) e' scope futuro. L'estrazione dei campi via `getattr(record,
  "asin", None)` funziona ma e' manuale. Migration scope dedicato.

## Impact

**Catalogo ADR-0021 ora 4/10 eventi viventi**: `tetris.skipped_budget`
(CHG-046), `vgp.veto_roi_failed`, `vgp.kill_switch_zero`,
`panchina.archived` (CHG-049). 5 dormienti (`extract.*`, `keepa.*`,
`scrape.*`, `ocr.*`, `db.audit_log_write`) si attiveranno con i
rispettivi moduli (CHG futuri).

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze` le
modifiche di body in `compute_vgp_score` e `build_panchina` (signature
invariata di `build_panchina`; `compute_vgp_score` ha 2 kwargs nuovi
opzionali).

## Refs

- ADR: ADR-0021 (logging/telemetria + catalogo eventi), ADR-0019 (test
  pattern caplog), ADR-0018 (R-05/R-08/R-09 verbatim), ADR-0014
  (mypy/ruff strict)
- Predecessori: CHG-2026-04-30-006 (osservability bootstrap),
  CHG-2026-04-30-035 (`compute_vgp_score`), CHG-2026-04-30-037
  (`build_panchina`), CHG-2026-04-30-046 (primo evento vivente)
- Successore atteso: migrazione `structlog.bind(session_id, tenant_id)`;
  attivazione eventi `extract.*` con `io_/extract`; aggregazione
  summary se profiler richiede; `db.audit_log_write` con persistence audit
- Commit: `[pending]`
