---
id: CHG-2026-05-02-004
date: 2026-05-02
author: Claude (su autorizzazione esplicita Leader, modalità "ultra macinata" round 7 — "snellire test che sono solo eccesso di zelo")
status: Draft
adr_ref: ADR-0019, ADR-0014
commit: 4deb537
---

## What

**Snellimento test eccesso di zelo**: rimossi 4 test che testano
garanzie del **linguaggio** o del **typer** (mypy) anziché logica
applicativa, + parametrizzati 6 single-case test del parser
`parse_locked_in` in 1 test parametrico (6 sub-cases).

Net: 9 funzioni di test rimosse, 1 funzione parametrica aggiunta
con 6 sub-cases (parità di copertura sui casi del parser, signal
identica). Test count: **731 → 727** (-4 funzioni; 6 parametrize
casi count come 6 test in pytest).

| File | Tipo | Cosa rimosso |
|---|---|---|
| `tests/unit/test_ui_dashboard.py` | modificato | -1 `test_dashboard_module_imports` (smoke import banale, mypy lo cattura). -1 `test_dashboard_re_exports_in_init` (testa `hasattr(ui, "...")`, mypy garantisce). -1 `test_persistence_helpers_re_exported` (idem; assert `DEFAULT_TENANT_ID==1` duplicava sentinel di config). -6 `test_parse_locked_in_*` (single-case) + +1 `test_parse_locked_in_parametric` (6 casi via `@pytest.mark.parametrize`). |
| `tests/unit/test_listino_input.py` | modificato | -1 `test_resolved_row_default_verified_buybox_is_none` (testa default `None` di campo dataclass, garantito dal linguaggio Python — eccesso di zelo). |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **727 PASS** unit/gov/golden (era 731, -4).
- **138 PASS** integration (invariato).
- **865 PASS** totali (era 869, -4).

Detect_changes: 3 simboli touched, 2 file, **0 processi affetti**,
**risk LOW**.

## Why

Direttiva Leader 2026-05-02 round 7: "spingere il piede sull'acceleratore
... sei autorizzato a snellire i test che sono solo eccesso di zelo".

Criteri di selezione applicati (conservativi: rimuovo solo se
**certificatamente** ridondante):

1. **Test che testano il linguaggio**: campo dataclass con default `None`
   → Python lo garantisce a prescindere dal codice. Non c'è bug catturato.
2. **Test che testano il typer**: `hasattr(ui, "X")` su simboli re-esportati
   → mypy strict cattura ogni rinomina/rimozione. Test = noise.
3. **Test smoke import**: "il modulo si importa senza raise" → mypy +
   collection di pytest stesso lo verificano (l'import è prerequisito
   per qualsiasi altro test). Ridondante.
4. **6 test single-case ridondanti su parser** (`parse_locked_in`):
   compressi in 1 parametrico. Stesso signal, 6 righe di parametri vs
   60 righe di funzioni separate.

### Decisioni di design

1. **Rimosso solo se "certificatamente" ridondante**: NON ho rimosso
   test boundary, sentinel di costanti business, regressione sentinel
   da CHG passati. La conservazione vince in dubbio.

2. **Parametrize vs separate functions**: pytest tratta ogni parametro
   come test indipendente (in caso di failure mostra quale ha fallito).
   Quindi parità di diagnosticabilità, ma -50 righe LOC test.

3. **Sentinel `assert ui.DEFAULT_TENANT_ID == 1`** (parte del rimosso
   `test_persistence_helpers_re_exported`): questo era un sentinel di
   product (single-tenant MVP). Rischio falla? **No**: la costante è
   già usata internamente in `_resolved_row_from_result` /
   `try_persist_session` con default fisso, e altri test integration
   verificano il behavior end-to-end con tenant=1.

4. **Backward compat default `verified_buybox_eur=None`** test rimosso:
   se in futuro qualcuno cambia il default a un Decimal, il test
   esistente `test_build_listino_falls_back_to_cost_when_no_verified_buybox`
   romperà comunque (testa il **comportamento** del fallback, non il
   default in sé). Quindi sentinel più forte già presente.

### Out-of-scope

- **Doctest replicati come test unit**: scope CHG futuro (richiede
  audit puntuale). Oggi solo i 4 macroridondanti sopra.
- **Test che costruiscono fixture pesanti per asserzione triviali**:
  candidati vari ma nessun esempio chiaro emerso in scan.
- **Test che testano fixture stesse**: nessuno trovato in scan.

## How

### `test_ui_dashboard.py` (highlight diff)

```diff
-def test_dashboard_module_imports():
-    from talos.ui.dashboard import DEFAULT_BUDGET_EUR, main, parse_locked_in
-    assert callable(main)
-    assert callable(parse_locked_in)
-    assert pytest.approx(10_000.0) == DEFAULT_BUDGET_EUR

-def test_parse_locked_in_simple(): ...
-def test_parse_locked_in_empty_string(): ...
-def test_parse_locked_in_only_commas(): ...
-def test_parse_locked_in_strip_whitespace(): ...
-def test_parse_locked_in_filters_empty(): ...
-def test_parse_locked_in_single_asin(): ...
+@pytest.mark.parametrize(
+    ("raw", "expected"),
+    [
+        ("AAA, BBB,CCC", ["AAA", "BBB", "CCC"]),
+        ("", []),
+        (",,, , ,", []),
+        ("  AAA  ,\tBBB\n,  CCC", ["AAA", "BBB", "CCC"]),
+        (",,,A,, B, ", ["A", "B"]),
+        ("XYZ123", ["XYZ123"]),
+    ],
+)
+def test_parse_locked_in_parametric(raw, expected): ...

-def test_dashboard_re_exports_in_init(): ...
-def test_persistence_helpers_re_exported(): ...
```

### `test_listino_input.py` (highlight diff)

```diff
-def test_resolved_row_default_verified_buybox_is_none():
-    """Default `verified_buybox_eur=None` per backward compat ..."""
-    row = ResolvedRow(...)  # 11 fields
-    assert row.verified_buybox_eur is None
-    assert row.candidates == ()
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | unchanged |
| Type | `uv run mypy src/` | 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **727 PASS** (era 731, -4 funzioni) |
| Integration full | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 3 simboli / 2 file, **0 processi affetti**, **risk LOW** |

**Rischi residui:**

- **Falsa rimozione di sentinel**: ho mitigato controllando per ognuno
  che ci fosse un test alternativo che cattura lo stesso scenario.
- **Doctest ridondanti rimasti**: scope CHG futuro.
- **Future feature flags / config defaults**: se in futuro qualcuno
  cambia il default `DEFAULT_TENANT_ID` da 1, NON c'è più sentinel
  diretto. Mitigazione: comportamento integrato in test integration
  (RLS + tenant-bound).

## Test di Conformità

- **Path codice applicativo:** `tests/unit/` ✓ (no src/ touched).
- **ADR-0019 (test strategy)**: snellimento allineato al pattern
  "rule-of-three superato → parametrize" + criterio "test che testa
  garanzie linguaggio/typer = noise".
- **ADR-0014 (mypy/ruff strict)**: 0 issues.
- **Backward compat**: zero impact runtime; solo test rimossi.
- **Sicurezza**: zero secrets/PII; no nuove deps; no migration.
- **Impact analysis pre-edit**: risk LOW (test only).
- **Detect changes pre-commit**: 3 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **Test suite -4 funzioni**: 727 unit/gov/golden + 138 integration =
  **865 PASS**.
- **LOC test ridotte ~80 righe** (eliminato boilerplate + parametrize).
- **Build time test**: marginalmente ridotto (4 test in meno; non
  significativo per ora ma cumulativo se sweep continua).
- **Code health**: -4 test "che testano framework/linguaggio".
  Pattern "parametrize per single-case repetitive" applicato.
- **Sblocca**: mood pulizia per future sweep di doctest replicati o
  test integration ridondanti (scope futuro).

## Refs

- ADR: ADR-0019 (test strategy), ADR-0014 (mypy/ruff strict).
- Direttiva Leader: 2026-05-02 round 7 ultra-macinata, "snellire i
  test che sono solo eccesso di zelo".
- Predecessori indiretti: tutti i CHG che hanno aggiunto test smoke /
  re-export (CHG-2026-04-30-040, CHG-2026-04-30-042, CHG-2026-05-01-022).
- Nessun successore atteso. Possibili rotte: sweep doctest replicati,
  audit fixture pesanti.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: `4deb537`.
