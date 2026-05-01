---
id: CHG-2026-05-01-033
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 6 — blocco B1 sessione dedicata 4/8)
status: Draft
commit: 0d748f2
adr_ref: ADR-0021, ADR-0017, ADR-0018, ADR-0014, ADR-0019
---

## What

**Bridge stdlib→structlog del cluster `extract/`** (4/5 fase B1.1).
Migra `extract/samsung.py` (1 emit `extract.kill_switch` R-05
HARDWARE) e `extract/asin_resolver.py` (logger init solo, 0 emit
attivi: anticipa B1.2 senza dead code residuo). **Rinomina** via
`git mv` il file test ibrido `test_io_extract_telemetry.py` →
`test_extract_telemetry.py`, completa la migrazione caplog →
`LogCapture` per i 4 test `extract.kill_switch`. Pattern uniforme
post-bridge **completato sui cluster `vgp/`/`tetris/`/`io_/`/`extract/`**;
manca solo `ui/` (B1.1.e) per chiudere la fase B1.1.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/samsung.py` | modificato | `import logging` → `import structlog`. `_logger = logging.getLogger(__name__)` → `_logger = structlog.get_logger(__name__)`. 1 emit `extract.kill_switch`: `extra={...}` → `**kwargs` native (5 campi: `asin`/`reason`/`mismatch_field`/`expected`/`actual`). |
| `src/talos/extract/asin_resolver.py` | modificato | Stesso pattern. 0 emit attivi → solo init logger. Anticipa B1.2 (potenziale emit telemetria su asin_resolver in CHG futuro) evitando dead code stdlib persistente. |
| `tests/unit/test_io_extract_telemetry.py` → `tests/unit/test_extract_telemetry.py` | rinominato + riscritto | `git mv` preserva history. Migrato pytest `caplog` → `LogCapture` (consumer fixture conftest CHG-031). Header docstring aggiornato: ora simmetrico ai fratelli `test_*_telemetry.py` post-bridge. 4 test invariati semanticamente. Type-ignore `attr-defined` rimossi. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **700 PASS** unit/gov/golden (invariato).
- **138 PASS** integration (invariato).
- **838 PASS** totali.

Detect_changes: 3 file, 2 simboli touched (`SamsungExtractor` +
`SamsungExtractor.match`), 0 processi affetti, **risk LOW**.

Comportamento applicativo invariato 100%: stesso evento canonico,
stessi 5 campi.

## Why

Cluster `extract/` è il 4° dei 5 cluster applicativi (vgp, tetris,
io_, extract, ui). Solo `ui/` resta per chiudere B1.1. L'ordine
scelto (extract dopo io_) riflette il flusso architetturale di
acquisizione dati: io_ acquisisce raw → extract normalizza → vgp
score → tetris alloca. Migrare in quest'ordine permette ad ogni
CHG di trovare i suoi caller già migrati (vgp aveva 0 caller in
test, tetris dipendeva da vgp, io_ è autonomo, extract dipende da
io_, ui dipenderà da tutto).

`asin_resolver.py` ha `_logger` ma 0 emit attivi (verificato
empiricamente con `grep`). Migrarlo comunque evita lasciare un
logger stdlib orfano nel cluster già migrato — quando B1.2/B1.3
introdurrà `bind_session_context` adoption, qualunque emit futuro
in asin_resolver sarà già coerente.

La rinomina `test_io_extract_telemetry.py` → `test_extract_telemetry.py`
era pianificata in CHG-032 ("scope CHG-B1.1.d, rinomina con git
mv contestuale alla migrazione fixture"). Eseguita ora con `git
mv` (preserva history `git log --follow`) seguito da riscrittura
completa del contenuto (caplog → LogCapture).

### Decisioni di design

1. **`asin_resolver.py` migrato anche con 0 emit**: zero costo
   (1 import + 1 init logger). Evita stato "orfano" stdlib in un
   cluster altrimenti migrato. Eventuali emit futuri (B1.2 può
   aggiungere telemetria su `_LiveAsinResolver` per correlazione
   SERP→Keepa→Resolver) entrano già nel pipeline corretto.

2. **`git mv` preserva history**: `git log --follow tests/unit/test_extract_telemetry.py`
   risale fino al primo commit del file ibrido (CHG-005). Pattern
   pytest non cambia — i 4 test sono semanticamente identici.

3. **`reason` field con valore string `"model_mismatch"`**:
   preservato verbatim. È enum-string aperta nel catalogo (futuro
   `low_confidence` potrebbe aggiungersi). Coerente con pattern
   `field`/`table` enum-string aperti dal round 5+ (CHG-024/025).

4. **Test fixture e helpers spostati 1:1**: `_StaticTesseractAdapter`
   non era nel file extract, restano gli helpers ad-hoc per il
   test (tipo `SamsungEntities` constructor inline). Nessuna
   estrazione cross-test (premature).

5. **Import structlog dopo `from rapidfuzz import fuzz`**: ordine
   alfabetico ruff isort `import structlog` prima di
   `from rapidfuzz...`. Coerente con CHG-031/032.

6. **`ruff TC002`**: `LogCapture` import in TYPE_CHECKING block,
   pattern consolidato.

7. **Docstring file aggiornato con storia rinomina**: serve come
   ancora narrativa per chi legge il file dopo CHG-033 senza
   `git log`. Sezione "Predecessor" puntuale, nessun rumore.

8. **Detect_changes risk LOW** (vs CHG-032 MEDIUM): `samsung.py`
   ha solo 1 emit, `SamsungExtractor.match` non è nodo di
   processi GitNexus (vs `_resolve_field`/`process_image` di
   CHG-032). Refactor più "isolato" architetturalmente.

### Out-of-scope

- **Bridge `ui/`**: scope CHG-B1.1.e (5° e ultimo CHG B1.1 —
  chiude fase di refactor mass).
- **Adoption `bind_session_context`**: scope CHG-B1.2 (orchestrator)
  e CHG-B1.3 (UI).
- **Errata catalogo ADR-0021**: scope CHG-B1.4 (drift
  `serp_search.scrape.selector_fail` field names + pulizia
  `tenant_id` context-bound).
- **Telemetria attiva su `asin_resolver`**: scope decisione Leader
  futura. Oggi 0 emit, probabilmente `extract.resolution_started/
  /completed/ambiguous` aggiunti in CHG-B1.2 con bind context
  attivo.

## How

### `extract/samsung.py` (highlight diff)

```diff
-import logging
+import structlog
 ...
-_logger = logging.getLogger(__name__)
+_logger = structlog.get_logger(__name__)
 ...
-_logger.debug(
-    "extract.kill_switch",
-    extra={
-        "asin": asin if asin is not None else "<n/a>",
-        "reason": "model_mismatch",
-        "mismatch_field": "model",
-        "expected": supplier.model,
-        "actual": amazon.model,
-    },
-)
+_logger.debug(
+    "extract.kill_switch",
+    asin=asin if asin is not None else "<n/a>",
+    reason="model_mismatch",
+    mismatch_field="model",
+    expected=supplier.model,
+    actual=amazon.model,
+)
```

### `extract/asin_resolver.py` (highlight diff)

```diff
-import logging
 ...
+import structlog
 ...
-_logger = logging.getLogger(__name__)
+_logger = structlog.get_logger(__name__)
```

### Test rinominato (highlight)

```python
def test_extract_kill_switch_event_emitted_on_model_mismatch(
    log_capture: LogCapture,
) -> None:
    extractor = SamsungExtractor()
    sup = SamsungEntities(model="Galaxy S24", ram_gb=12, rom_gb=256)
    amz = SamsungEntities(model="Galaxy S23", ram_gb=12, rom_gb=256)
    result = extractor.match(supplier=sup, amazon=amz)

    kill = [e for e in log_capture.entries if e["event"] == "extract.kill_switch"]
    assert len(kill) == 1
    entry = kill[0]
    assert entry["reason"] == "model_mismatch"
    assert entry["expected"] == "Galaxy S24"
    assert entry["actual"] == "Galaxy S23"
    assert entry["asin"] == "<n/a>"
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 138 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Telemetria mirata | `uv run pytest tests/unit/test_extract_telemetry.py -v` | **4 PASS** |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **700 PASS** (invariato) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | `gitnexus_impact("SamsungExtractor", "upstream")` | risk LOW, 0 upstream, 0 processes |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 2 symbols / 3 files (1 rename), 0 processes affected, risk LOW |

**Rischi residui:**

- **`asin_resolver.py` con `_logger` non usato**: ruff potrebbe
  segnalare `F401` (unused) in futuro. Verificato: `_logger` è
  variabile module-level, ruff non la flagga (non è import).
  Nessun issue al momento. Se in futuro la verifica strict tagga
  l'init come dead code, si può rimuovere o aggiungere `# noqa`
  con TODO B1.2.

- **`reason="model_mismatch"` enum-string aperta**: catalogo
  `extract.kill_switch` ha tupla obbligatoria (`asin`, `reason`,
  `mismatch_field`, `expected`, `actual`). Il valore `reason`
  resta string libera. Future estensioni (es. `low_confidence`)
  saranno compatibili.

- **Detect_changes risk LOW**: limitato refactor su 2 file applicativi
  (1 con emit, 1 init-only) + 1 file test rinominato. Nessun
  processo cross-community impattato.

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/` ✓ (area
  ADR-0013 consentita; ADR-0017 governa).
- **ADR-0017 vincoli rispettati**: protocollo `BrandExtractor` /
  `SamsungExtractor` / `AsinResolverProtocol` invariati.
- **ADR-0018 vincoli rispettati**: R-05 KILL-SWITCH HARDWARE
  preservato verbatim (logica + telemetria + comportamento).
- **ADR-0019 (test strategy)**: unit puri ✓, mock-only.
- **Quality gate verde**: ruff/format/mypy/pytest tutti pass
  (ADR-0014).
- **No nuovi simboli applicativi**: solo refactor.
- **Backward compat semantica**: invariata 100%.
- **Sicurezza**: zero secrets/PII; no nuove deps.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 2 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**: refactor
  mirato + 0 test nuovi (riusati gli esistenti via rinomina) +
  change doc snello.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite invariata in conteggio**: 838 PASS. I 4 test
  extract migrati con `git mv` + riscrittura.
- **Sblocca CHG-B1.1.e**: ultimo cluster (`ui/`) per chiudere
  B1.1. Dopo CHG-034 tutti i 12 siti applicativi consumeranno
  `merge_contextvars`.
- **Sblocca CHG-B1.2** (orchestrator adoption): post B1.1.e ogni
  emit downstream eredita il bind senza eccezioni residue.
- **Code health**: -4 type-ignore `attr-defined` (test dict-style).
  Nome file simmetrico ai fratelli (`test_extract_telemetry.py`).
  History preservata via `git mv`.

## Refs

- ADR: ADR-0021 (logging/telemetria), ADR-0017 (extract/), ADR-0018
  (R-05 KILL-SWITCH), ADR-0014 (mypy/ruff strict), ADR-0019 (test
  strategy).
- Predecessori:
  - CHG-2026-04-30-006 (configure_logging structlog).
  - CHG-2026-05-01-004 (SamsungExtractor R-05 KILL-SWITCH).
  - CHG-2026-05-01-005 (telemetria 5 eventi io_/extract attivati).
  - CHG-2026-05-01-007 (asin kwarg propagation).
  - CHG-2026-05-01-016 (asin_resolver skeleton).
  - CHG-2026-05-01-030..032 (B1.1.a vgp / B1.1.b tetris / B1.1.c
    io_).
- Decisioni Leader 2026-05-01 round 6 (pre-flight B1).
- Successore atteso: **CHG-B1.1.e** (bridge structlog su `ui/` —
  ultimo cluster, chiude B1.1).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: `0d748f2`.
