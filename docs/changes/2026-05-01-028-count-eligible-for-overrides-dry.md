---
id: CHG-2026-05-01-028
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" estesa round 5+ — refactor DRY helper count_eligible_for_overrides)
status: Draft
commit: 57ab540
adr_ref: ADR-0016, ADR-0014, ADR-0019
---

## What

Refactor minor: estraggo `count_eligible_for_overrides(resolved) -> int`
helper puro in `listino_input.py` per eliminare il **ricalcolo
duplicato** di `n_eligible` fra `dashboard.py` (telemetria
`ui.override_applied` di CHG-024) e `_render_ambiguous_candidate_overrides`
(render Streamlit di CHG-023). Single source of truth per la
condizione di eligibilità override CFO.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + helper puro `count_eligible_for_overrides(resolved: list[ResolvedRow]) -> int`. Logica unica: `r.is_ambiguous AND r.asin AND len(r.candidates) > 1`. |
| `src/talos/ui/dashboard.py` | modificato | Sostituita la list-comp inline `sum(1 for r in resolved if r.is_ambiguous and r.asin and len(r.candidates) > 1)` (CHG-024) con chiamata a `count_eligible_for_overrides(resolved)`. Import esteso. |
| `tests/unit/test_listino_input.py` | modificato | + helper `_resolved_eligibility(*, is_ambiguous, asin, n_candidates)` + 6 test mock-only: empty / no ambigui / unresolved esclusa / 1 candidate esclusa / 0 candidates esclusa (cache hit) / mixed con tutte le combinazioni. + import `count_eligible_for_overrides`. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest unit:
**688 PASS** unit/gov/golden (era 682 a CHG-027, +6 nuovi count_eligible).
Pytest integration: **138 PASS** invariato. **826 PASS** totali (era
820 a CHG-027).

## Why

CHG-024 ha emesso `ui.override_applied` con `n_eligible` calcolato
inline in `dashboard.py`. CHG-023 aveva già la stessa logica
internamente in `_render_ambiguous_candidate_overrides` (per popolare
`eligible_rows`). Da CHG-024 in poi la condizione `r.is_ambiguous AND
r.asin AND len(r.candidates) > 1` è duplicata in 2 punti — drift
silente se uno dei due cambia.

CHG-028 chiude il duplicato:
- Single source of truth: il caller `dashboard.py` e il render
  `_render_ambiguous_candidate_overrides` dipenderanno entrambi
  dall'helper centralizzato.
- Testabilità: helper puro mock-only, 6 casi coperti compresa
  l'edge case "cache hit con candidates=()".
- Documentazione esplicita della **definizione** di "eligible per
  override" come concetto di prodotto, non più solo come predicato
  comprehension.

> Nota di scope: il render `_render_ambiguous_candidate_overrides`
> NON viene refactored in questo CHG perché ha bisogno della tupla
> `(idx, row)` per popolare il selectbox (non solo del count).
> L'helper attuale (`count_*`) è single-purpose. Refactor del render
> a usare un'estrazione condivisa (es. `eligible_for_override_indices`)
> = scope futuro se serve.

### Decisioni di design

1. **Helper PUBBLICO `count_eligible_for_overrides`** (no `_`-prefisso):
   pattern coerente con `apply_candidate_overrides`,
   `format_cache_hit_caption`, `format_buybox_verified_caption`
   (CHG-023/026/027). Importabile da `dashboard.py` per
   `_emit_ui_override_applied.n_eligible`.

2. **Single-purpose `count`**: il caller dashboard ha bisogno solo
   del numero. Restituire `list[tuple[int, ResolvedRow]]` (come fa
   `_render_ambiguous_candidate_overrides` internamente) sarebbe
   over-fetching per il caller telemetria. Decisione: 2 helper
   separati per 2 use case (count vs list di coppie).

3. **`_render_ambiguous_candidate_overrides` invariato**: lascia
   la sua list-comp `eligible_rows = [(idx, r) for ...]` perché ha
   bisogno della coppia per il render. Il fatto che usi la stessa
   condizione del nuovo helper non aggiunge drift (solo ridondanza
   testuale): se in futuro la condizione cambia, sia `count_*` che
   `_render_*` vanno aggiornati.

4. **Test `_resolved_eligibility` helper locale, NOT esportato**:
   pattern coerente con `_resolved_with_cache_hit` (CHG-026) e
   `_resolved_with_buybox` (CHG-027). 1 fixture per test verticale.

5. **`ResolutionCandidate` test fixture include 6 fields obbligatori**:
   bug-fix latente — l'inizializzazione non triviale richiede
   `fuzzy_title_pct` + `delta_price_pct` (CHG-018). I test ora
   coprono la signature reale.

6. **Test `zero_candidates_excluded` (cache hit branch)**: importante
   — la cache hit non popola `candidates` (CHG-022 dec. 2 / CHG-023
   propagation). Quel branch è eligible=False per definizione.

### Out-of-scope

- **Refactor `_render_ambiguous_candidate_overrides` per usare
  helper condiviso**: serve `list[tuple[int, ResolvedRow]]`, single-CHG
  futuro (es. `eligible_for_override_indices`).
- **Caching del count su `ResolvedRow.eligibility_for_override`**:
  premature optimization, oggi il count è O(N) su listino piccolo
  (<100 righe).
- **Pattern simile per `n_resolved` / `n_total` / `n_ambiguous`**:
  questi sono già single-line list-comp non drogo. Refactor non vale.

## How

### `listino_input.py` (highlight)

```python
def count_eligible_for_overrides(resolved: list[ResolvedRow]) -> int:
    """Single source of truth per condizione override eligibility CHG-023."""
    return sum(1 for r in resolved if r.is_ambiguous and r.asin and len(r.candidates) > 1)
```

### `dashboard.py` (highlight diff)

```diff
 if overrides:
-    n_eligible = sum(1 for r in resolved if r.is_ambiguous and r.asin and len(r.candidates) > 1)
+    n_eligible = count_eligible_for_overrides(resolved)
     _emit_ui_override_applied(n_overrides=len(overrides), n_eligible=n_eligible)
```

### Test pattern (highlight mixed)

```python
def test_count_eligible_mixed() -> None:
    """3 eligible + 2 ambigui-con-1-cand + 1 sicura + 1 unresolved -> 3."""
    rows = [
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD0", n_candidates=3),  # eligible
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD1", n_candidates=2),  # eligible
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD2", n_candidates=4),  # eligible
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD3", n_candidates=1),  # 1 cand: NO
        _resolved_eligibility(is_ambiguous=True, asin="B0CSTC2RD4", n_candidates=1),  # idem
        _resolved_eligibility(is_ambiguous=False, asin="B0CSTC2RD5", n_candidates=3), # sicura: NO
        _resolved_eligibility(is_ambiguous=True, asin="", n_candidates=3),            # unres: NO
    ]
    assert count_eligible_for_overrides(rows) == 3
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 137 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Count eligible mirato | `uv run pytest tests/unit/test_listino_input.py -k "count_eligible" -v` | **6 PASS** |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **688 PASS** (era 682, +6) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |

**Rischi residui:**
- **`_render_ambiguous_candidate_overrides` ancora duplica la condizione**:
  drift potenziale se la condizione cambia. Mitigazione: scope
  futuro refactor a helper condiviso `eligible_for_override_indices`.
- **6 test count_eligible coprono il puro count, non il render**:
  il render è Streamlit-side, già coperto integration-side
  (validazione manuale Leader CFO).
- **Performance**: O(N) sostituisce O(N) con stessa complessità.
  Costo singola function call trascurabile.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area ADR-0013
  consentita).
- **ADR-0016 vincoli rispettati:** helper puro testabile senza
  Streamlit (modulo `listino_input.py` zero-Streamlit). Pattern
  consolidato CHG-023/026/027.
- **Test unit puri:** ✓ (ADR-0019). 6 test mock-only senza dipendenza
  Streamlit / DB.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `count_eligible_for_overrides`
  → ADR-0016 (UI helper puro).
- **Backward compat:** modifica additiva 100%; helper nuovo, caller
  `dashboard.py` invariato semanticamente (stesso valore prodotto da
  helper invece di list-comp inline). Nessun caller esterno rompe.
- **Sicurezza:** zero secrets / PII; pure aggregazione boolean.
- **Impact analysis pre-edit:** simbolo nuovo, zero caller upstream.
  Risk LOW.
- **Detect changes pre-commit:** atteso risk LOW (3 file, 0 processi
  affetti — pattern simile CHG-026/027).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17). Refactor,
  no errata.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +6 unit**: 688 unit/gov/golden (era 682).
- **Code health**: rimossa duplicazione condizione (1 → 1, single
  source of truth in modulo dedicato). Drift potenziale `dashboard.py`
  ↔ `_render_*` rimosso.
- **Pattern helper count puro**: replicabile per future condizioni
  derivate (es. `count_unresolved`, `count_cache_hit`,
  `count_overridden`).

## Refs

- ADR: ADR-0016 (UI helper puri pattern), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test unit puri).
- Predecessori:
  - CHG-2026-05-01-023 (override candidato manuale A3): producer
    della condizione di eligibilità.
  - CHG-2026-05-01-024 (telemetria `ui.override_applied`): consumer
    del count.
  - CHG-2026-05-01-026/027 (caption UX): pattern helper puro
    consolidato.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato (refactor minore + 6 test mirati + change doc snello).
- Successore atteso: nessuno specifico in scope code health.
  Possibili rotte: refactor `_render_ambiguous_candidate_overrides`
  con `eligible_for_override_indices` condiviso, (B1) `structlog.bind`
  context tracing, (B2) refactor UI multi-page ADR-0016.
- Commit: `57ab540`.
