---
id: CHG-2026-05-01-038
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 7 — bug fix MVP CFO Path B' bloccante)
status: Draft
commit: e4290cf
adr_ref: ADR-0014, ADR-0019, ADR-0017, ADR-0018
---

## What

**Fix unit drift `DEFAULT_REFERRAL_FEE_PCT`**: il default era `8.0`
(interpretato come "8 percent") ma il consumer `cash_inflow_eur`
valida `referral_fee_rate` in `[0, 1]` (frazione decimale). Risultato:
qualsiasi run del flow Path B' (descrizione+prezzo) con il default
falliva con `ValueError("referral_fee_rate invalido: 8.0. Atteso
valore in [0, 1] (frazione decimale, 0.08 = 8%).")` durante
`run_session`. **Bug bloccante MVP CFO** Path B' rilevato live in
browser dal Leader (TEST-DEBT-003 in azione).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | Riga 108: `DEFAULT_REFERRAL_FEE_PCT: float = 8.0` → `0.08`. Docstring module-level (riga 23) e docstring `build_listino_raw_from_resolved` (riga 413) aggiornati con riferimento esplicito a "frazione decimale [0, 1]" + nota CHG-038. |
| `tests/unit/test_listino_input.py` | modificato | + 1 test sentinel `test_default_referral_fee_pct_is_decimal_fraction`: `assert 0.0 <= DEFAULT_REFERRAL_FEE_PCT <= 1.0` (lock contract anti-regressione). |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **706 PASS** unit/gov/golden (era 705, +1 sentinel).
- **138 PASS** integration (invariato).
- **844 PASS** totali.

Detect_changes: 5 simboli touched, 2 file, **0 processi affetti**,
**risk LOW**.

## Why

Drift introdotto in CHG-2026-05-01-020 (UI rifondata flow
descrizione+prezzo). Tutti gli altri callsite del campo
`referral_fee_pct` nel codebase usano la **frazione decimale**:

- `tests/integration/test_referral_fee_lookup.py:158`: `0.12`
- `tests/integration/test_delete_config_override.py:226`: `0.07`
- `tests/unit/test_orchestrator_referral_fee_override.py`: `0.10`,
  `0.12` ripetuti
- `cash_inflow_eur` valida `[0, 1]` (`formulas/cash_inflow.py:53-54`)

Il singolo punto sbagliato era il **valore** del default in
`listino_input.py:108`. Il **nome** del campo (`_pct`) è ambiguo
ma cambiarlo a `_rate` ha blast radius enorme (config_repository
key `KEY_REFERRAL_FEE_PCT`, schema DB `config_overrides.key`,
form sidebar CFO con CHG-051, orchestrator `_resolve_referral_fee`,
6 file src + 5 test): scope CHG futuro, non oggi.

### Decisioni di design

1. **Fix valore, NON rinomina campo** (CHG-038): minimizzare blast
   radius. Il nome `_pct` resta semantically misleading ma è
   stabile in tutto il codebase. Rinomina a `_rate` → CHG futuro
   con migration alembic + UI form CFO update.

2. **Test sentinel `0.0 <= x <= 1.0`** invece di `== 0.08`:
   il valore esatto del default è una decisione di product (8% è
   convenzione marketplace; il Leader può ratificare 0.10 o 0.15
   con un nuovo CHG senza rompere il test). Il sentinel blinda il
   **contratto** (range), non il valore.

3. **Docstring rafforzato sul modulo + sulla funzione**: i 2 punti
   che erano stale referenziano ora esplicitamente "frazione
   decimale [0, 1]" + nota CHG-038. Pattern errata corrige
   minimale.

4. **Nessuna modifica a `cash_inflow_eur`**: è già il consumer
   formalmente corretto (range check esplicito + messaggio di
   errore esemplificativo). Il fix andava nel produttore, non nel
   consumatore.

5. **Test esistente `test_build_listino_raw_*` invariato**: la
   sua asserzione era `df.iloc[0]["referral_fee_pct"] ==
   DEFAULT_REFERRAL_FEE_PCT` (riferimento alla costante, non
   hardcoded a `8.0`). Resta verde post-fix senza modifiche.

### Out-of-scope

- **Rinomina `referral_fee_pct` → `referral_fee_rate`** in tutto
  il codebase + DB key. Scope CHG futuro (sessione dedicata,
  blast radius alto).
- **Validazione UI sidebar form CFO**: il form di CHG-051 accetta
  qualsiasi `float` come `referral_fee_pct`; un CFO che inserisce
  `8.0` invece di `0.08` ricadrebbe nello stesso errore.
  Mitigazione: scope CHG futuro (validation client-side
  Streamlit `min_value=0.0, max_value=1.0` sul `number_input`).
- **Migration default DB**: nessun valore `8.0` salvato a DB
  (il default è solo in-memory, non in `config_overrides`).
  Nessuna migration richiesta.

## How

### `listino_input.py` (highlight diff)

```diff
-DEFAULT_REFERRAL_FEE_PCT: float = 8.0
+# CHG-2026-05-01-038: corretto da 8.0 a 0.08 (fix unit drift —
+# `cash_inflow_eur` valida `referral_fee_rate` in [0, 1] frazione decimale).
+DEFAULT_REFERRAL_FEE_PCT: float = 0.08
```

### `test_listino_input.py` (highlight)

```python
def test_default_referral_fee_pct_is_decimal_fraction() -> None:
    """Lock contract: `DEFAULT_REFERRAL_FEE_PCT` deve essere frazione [0, 1].

    Coerente con `cash_inflow_eur(referral_fee_rate)` che valida lo
    stesso range. Sentinel per prevenire la regressione fixata in
    CHG-2026-05-01-038 (era 8.0 = "8 percent" → rotta pipeline su default).
    """
    assert 0.0 <= DEFAULT_REFERRAL_FEE_PCT <= 1.0
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 138 files already formatted |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Listino input dedicated | `uv run pytest tests/unit/test_listino_input.py -q` | **71 PASS** (era 70, +1 sentinel) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **706 PASS** (era 705, +1 sentinel) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | `gitnexus_impact("DEFAULT_REFERRAL_FEE_PCT", "upstream")` | risk LOW (1 callsite test) |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 5 simboli / 2 file, **0 processi affetti**, **risk LOW** |
| **Validazione bug fix end-to-end** | Streamlit live in browser, CSV `descrizione,prezzo` Samsung Galaxy | scope post-commit (Leader) |

**Rischi residui:**

- **Form CFO sidebar (CHG-051)** accetta qualsiasi float per
  `referral_fee_pct` (no range validation). Stesso scenario error
  se il CFO inserisce `8.0`. Mitigation: scope CHG futuro.
- **Naming `_pct` ambiguo**: documentato esplicitamente nel
  docstring CHG-038 ma il nome resta. Rinomina = scope CHG futuro
  (blast radius DB + UI).
- **Test esistente `test_build_listino_raw_with_default_columns`**
  passa la costante (non hardcoded `8.0`): sentinel del **contratto
  costante**, non del valore. Verde post-fix automatico.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/listino_input.py` ✓
  (area `ui/` ADR-0013 + ADR-0016).
- **ADR-0017 (Path B')**: contratto `referral_fee_pct` frazione
  ratificato in `cash_inflow_eur` (CHG-2026-04-30-025).
- **ADR-0018 (algoritmo VGP)**: formula `cash_inflow_eur` invariata.
  Bug era nel produttore (default UI), non nel consumatore.
- **ADR-0019 (test strategy)**: unit puro ✓ + sentinel mock-only.
- **Quality gate verde** (ADR-0014 mypy/ruff strict).
- **Backward compat**: tutti i caller esistenti che passano
  esplicitamente `referral_fee_pct=...` (test orchestrator,
  test pipeline samsung mini) usano già frazione → invariati.
- **Sicurezza**: zero secrets/PII; nessuna nuova dep; nessuna
  migration DB.
- **Impact analysis pre-edit**: risk LOW (1 callsite test).
- **Detect changes pre-commit**: 5 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +1**: 706 unit/gov/golden + 138 integration = **844
  PASS**.
- **🎯 Path B' MVP CFO sbloccato live**: `run_session` su listino
  costruito con `build_listino_raw_from_resolved` ora completa
  end-to-end senza `ValueError`. Bug bloccante chiuso.
- **TEST-DEBT-003 (smoke browser CFO-side)** ha pagato il primo
  dividendo: il Leader ha aperto Streamlit per la prima volta in
  questa sessione e ha rilevato il bug entro 30 secondi.
  Pattern: smoke browser = test-debt critico, non opzionale.
- **Code health**: -1 unit drift; +1 sentinel anti-regressione.

## Refs

- ADR: ADR-0014 (mypy/ruff strict), ADR-0019 (test strategy),
  ADR-0017 (Path B' io_/extract), ADR-0018 (formula `cash_inflow`
  contratto canonico).
- Predecessori:
  - CHG-2026-04-30-025 (`cash_inflow_eur` contratto `referral_fee_rate`
    in [0, 1]).
  - CHG-2026-05-01-020 (UI rifondata flow descrizione+prezzo —
    introduzione del default `8.0` che ha causato il drift).
  - CHG-2026-04-30-051 (form sidebar CFO `referral_fee_pct` per
    categoria — accetta float senza range validation).
  - CHG-2026-04-30-053 (orchestrator `referral_fee_overrides` lookup
    hierarchy — assume frazione coerentemente).
- Bug rilevato live in browser dal Leader durante validazione
  smoke Path B' MVP CFO (sessione 2026-05-01 round 7).
- Successore atteso: nessuno specifico. Possibili rotte (decisione
  Leader): rinomina `referral_fee_pct` → `referral_fee_rate` (scope
  sessione dedicata) oppure validation UI sidebar form CFO
  `min_value=0.0, max_value=1.0`.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: `e4290cf`.
