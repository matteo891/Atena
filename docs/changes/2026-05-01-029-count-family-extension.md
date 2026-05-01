---
id: CHG-2026-05-01-029
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" estesa round 5+ — extension family count_* simmetrici)
status: Draft
commit: pending
adr_ref: ADR-0016, ADR-0014, ADR-0019
---

## What

Refactor minor: estensione della family `count_*` con 3 helper puri
simmetrici a `count_eligible_for_overrides` (CHG-028). Single source
of truth per gli aggregati `ResolvedRow` consumati da caption UX e
dashboard. I `format_*_caption` esistenti (CHG-026/027) ora usano
internamente i nuovi helper, eliminando duplicazione di list-comp
con il caller `dashboard.py`.

| Helper nuovo | Aggrega | Caller pre-CHG-029 | Caller post-CHG-029 |
|---|---|---|---|
| `count_resolved` | `r.asin` truthy | `dashboard.py` (inline) | `dashboard.py` |
| `count_cache_hit` | `r.is_cache_hit` | `format_cache_hit_caption` (inline) | `format_cache_hit_caption` |
| `count_with_verified_buybox` | `r.verified_buybox_eur is not None` | `format_buybox_verified_caption` (inline) | `format_buybox_verified_caption` |

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + 3 helper puri `count_resolved`, `count_cache_hit`, `count_with_verified_buybox`. Refactor: `format_cache_hit_caption` ora usa `count_cache_hit` internamente; `format_buybox_verified_caption` usa `count_with_verified_buybox`. Comportamento esterno invariato 100%. |
| `src/talos/ui/dashboard.py` | modificato | Sostituito `n_resolved = sum(1 for r in resolved_with_overrides if r.asin)` con `count_resolved(resolved_with_overrides)`. Import esteso. |
| `tests/unit/test_listino_input.py` | modificato | + 12 test mock-only (4 per ogni helper: empty / all positive / all negative / mixed). Riusa fixture esistenti `_resolved_with_cache_hit` e `_resolved_with_buybox` (CHG-026/027). + import 3 nuovi helper. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest unit:
**700 PASS** unit/gov/golden (era 688 a CHG-028, +12 nuovi count
extension). Pytest integration: **138 PASS** invariato. **838 PASS**
totali (era 826 a CHG-028).

## Why

CHG-028 ha estratto `count_eligible_for_overrides` come single source
of truth per la condizione di eligibilità override. Il pattern
`count_*` è chiaramente generalizzabile ad altri aggregati di
`ResolvedRow` già usati inline nel caption del flow descrizione+prezzo:

- **`n_resolved`** in `dashboard.py` — list-comp inline storica.
- **`n_hits`** dentro `format_cache_hit_caption` — list-comp inline
  CHG-026.
- **`n_verified`** dentro `format_buybox_verified_caption` — list-comp
  inline CHG-027.

CHG-029 chiude i 3 duplicati restanti applicando lo stesso pattern
di CHG-028:
- Single source of truth per ogni aggregato in modulo testabile.
- 12 test mock-only blindano ogni helper.
- I `format_*_caption` ora delegano l'aggregazione, restando
  responsabili solo del format string.

> Nota di scope: `n_total = len(resolved)` e `n_overrides = len(overrides)`
> NON hanno helper dedicato — `len()` è già single-line, chiarissimo,
> e l'astrazione aggiungerebbe rumore senza beneficio. `n_ambiguous`
> resta inline perché l'unico caller è `dashboard.py` con condizione
> specifica (`is_ambiguous AND asin`); estraibile in CHG futuro se
> emerge un secondo caller.

### Decisioni di design

1. **3 helper PUBBLICI senza `_`-prefisso**: pattern coerente con
   `count_eligible_for_overrides` (CHG-028). Importabili da test +
   future esigenze esterne.

2. **Refactor `format_*_caption` PRIMA di test, NON dopo**:
   `format_cache_hit_caption` e `format_buybox_verified_caption` sono
   test-coperti da CHG-026/027 (14 test esistenti). Il refactor
   interno deve preservare bytewise il comportamento — i test
   esistenti vengono ri-eseguiti come regression. Quality gate
   verde post-refactor garantisce zero drift semantico.

3. **`count_resolved` su `r.asin` truthy (non `bool(r.asin)`)**:
   coerente con il pattern Python che valuta string vuota come
   falsy. Resolver fail / cache miss senza candidato = `asin=""` →
   non contato. R-01 UX-side preservato (riga ancora visibile in
   tabella).

4. **`count_cache_hit` su flag boolean diretto**: aggrega
   `is_cache_hit=True` set in `_resolved_row_from_result` (CHG-019).
   Cache disabilitata (`factory=None`) → tutti `is_cache_hit=False` →
   count 0. Coerente con telemetria `cache.hit/miss` di CHG-025.

5. **`count_with_verified_buybox` su `is not None`** (non
   `> 0`): la presenza è il KPI, non il valore. Buy Box = 0.00
   (edge case Amazon NEW gratis o errore di lookup) sarebbe contato
   come "verified" se passasse `is not None`. Decisione: se Amazon
   restituisce 0 lo trattiamo come dato live valido (non `None`).

6. **Test fixture `_resolved_with_cache_hit` riusato** (CHG-026):
   già esistente, già con `is_cache_hit` parameter. `count_resolved`
   testato variando `asin` (default vs `""`).

7. **Test fixture `_resolved_with_buybox` riusato** (CHG-027):
   già esistente, già con `verified_buybox_eur` parameter.
   `count_with_verified_buybox` testato direttamente.

8. **NO refactor in `_render_descrizione_prezzo_flow` di
   `n_ambiguous`**: la condizione `r.is_ambiguous and r.asin`
   è 1-line list-comp con singolo caller. Estrarre `count_ambiguous`
   sarebbe over-design: scope futuro se emerge secondo caller.

9. **NO refactor `_render_ambiguous_candidate_overrides`** per usare
   `count_eligible_for_overrides`: serve la lista di coppie
   `(idx, row)`, non il count. Out-of-scope CHG-028 esplicito.

### Out-of-scope

- **`count_ambiguous_resolved` helper**: 1-line `sum(1 for r in
  resolved if r.is_ambiguous and r.asin)` con singolo caller. Estraibile
  se emerge consumatore esterno.
- **`count_with_overrides(overrides_dict) -> int`**: già `len(overrides)`,
  banale.
- **`count_with_notes(resolved) -> int`**: scope futuro se serve
  KPI "righe con audit trail R-01 popolato".
- **Aggregato unico `compute_resolution_summary(resolved) -> dict`**:
  sarebbe consolidation refactor (PIC4 round 5+). Scope futuro se
  caption/telemetria evolvono in dashboard observability dedicata.
- **`count_*` per categoria/brand**: aggregazione granulare, scope
  multi-page B2.

## How

### `listino_input.py` (highlight 3 nuovi helper)

```python
def count_resolved(resolved: list[ResolvedRow]) -> int:
    """Count righe risolte (ASIN truthy)."""
    return sum(1 for r in resolved if r.asin)


def count_cache_hit(resolved: list[ResolvedRow]) -> int:
    """Count righe con is_cache_hit=True."""
    return sum(1 for r in resolved if r.is_cache_hit)


def count_with_verified_buybox(resolved: list[ResolvedRow]) -> int:
    """Count righe con verified_buybox_eur is not None."""
    return sum(1 for r in resolved if r.verified_buybox_eur is not None)
```

### `format_*_caption` post-refactor (highlight)

```python
def format_cache_hit_caption(resolved):
    if not resolved:
        return ""
    n_total = len(resolved)
    n_hits = count_cache_hit(resolved)  # era list-comp inline
    pct = n_hits / n_total * 100
    return f"Cache: {n_hits}/{n_total} hit ({pct:.0f}%)."
```

### `dashboard.py` (highlight diff)

```diff
- n_resolved = sum(1 for r in resolved_with_overrides if r.asin)
+ n_resolved = count_resolved(resolved_with_overrides)
```

### Test pattern (highlight mixed)

```python
def test_count_cache_hit_mixed() -> None:
    """2 hit + 7 miss -> 2."""
    rows = [
        *[_resolved_with_cache_hit(is_cache_hit=True) for _ in range(2)],
        *[_resolved_with_cache_hit(is_cache_hit=False) for _ in range(7)],
    ]
    assert count_cache_hit(rows) == 2
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 137 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Count family mirato | `uv run pytest tests/unit/test_listino_input.py -k "count_resolved or count_cache_hit or count_with_verified" -v` | **12 PASS** |
| Format caption regression | `uv run pytest tests/unit/test_listino_input.py -k "format_cache_hit_caption or format_buybox_verified_caption" -v` | **14 PASS** (CHG-026/027 invariati post-refactor) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **700 PASS** (era 688, +12) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |

**Rischi residui:**
- **Drift fra count_resolved e n_total semantica**: `count_resolved`
  risponde "quante righe hanno asin truthy?", `n_total = len(resolved)`
  risponde "quante righe ci sono in totale?". I 2 sono diversi
  (resolver fail = riga in totale ma non risolta). I caller usano
  entrambi correttamente. Mitigazione: docstring esplicita.
- **`count_with_verified_buybox` non discrimina cache hit con buybox=None
  da resolver fail con buybox=None**: scope futuro errata se serve
  distinguere "cache fredda" da "lookup fail" (out-of-scope CHG-022
  decisione 2).
- **`format_*_caption` refactor**: i test CHG-026/027 esistenti (14
  test) coprono il behavior esterno end-to-end. Pre/post refactor
  ottenendo 14/14 verde garantisce zero regression.
- **Performance**: O(N) sostituisce O(N), stessa complessità. Costo
  function call ~ns, irrilevante su listini <100 righe.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area ADR-0013
  consentita).
- **ADR-0016 vincoli rispettati:** helper puri testabili senza
  Streamlit (modulo `listino_input.py` zero-Streamlit). Pattern
  consolidato CHG-023/026/027/028.
- **Test unit puri:** ✓ (ADR-0019). 12 test mock-only senza dipendenza
  Streamlit / DB.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `count_resolved` /
  `count_cache_hit` / `count_with_verified_buybox` → ADR-0016 (UI
  helper puri).
- **Backward compat:** modifica additiva 100%; helper nuovi, refactor
  interno `format_*_caption` preserva I/O bytewise. Nessun caller
  esterno rompe. Test esistenti CHG-026/027 verdi senza modifiche.
- **Sicurezza:** zero secrets / PII; aggregazioni puramente boolean.
- **Impact analysis pre-edit:** simboli nuovi, zero caller upstream.
  Risk LOW.
- **Detect changes pre-commit:** atteso risk LOW (3 file, 0 processi
  affetti — pattern simile CHG-028).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17). Refactor
  family, no errata.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +12 unit**: 700 unit/gov/golden (era 688).
- **Code health**: rimosse 3 duplicazioni list-comp (`n_resolved`
  inline + `n_hits` interno + `n_verified` interno). Pattern
  `count_*` ora completo per tutti i KPI esposti in caption.
- **Pattern consolidato**: 4 helper `count_*` (eligible/resolved/cache_hit/
  with_verified_buybox) + 2 helper `format_*_caption` (cache/buybox)
  + 1 helper `apply_*_overrides` (CHG-023). Family chiusa per il
  flow descrizione+prezzo MVP CFO.
- **Single source of truth** per ogni aggregato — drift potenziale
  caller↔caption rimosso.

## Refs

- ADR: ADR-0016 (UI helper puri pattern), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test unit puri).
- Predecessori:
  - CHG-2026-05-01-019 (cache `description_resolutions`): producer
    `is_cache_hit`.
  - CHG-2026-05-01-022 (verified_buybox_eur): producer
    `verified_buybox_eur`.
  - CHG-2026-05-01-026 (caption cache): caller di `count_cache_hit`
    post-refactor.
  - CHG-2026-05-01-027 (caption buybox): caller di
    `count_with_verified_buybox` post-refactor.
  - CHG-2026-05-01-028 (count_eligible_for_overrides DRY): pattern
    helper count puro consolidato.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato (refactor minore + 12 test mirati + change doc snello).
- Successore atteso: nessuno specifico in scope code health.
  Possibili rotte (decisione Leader): (B1) `structlog.bind` context
  tracing, (B2) refactor UI multi-page ADR-0016, errata `tenant_id`
  in eventi UI per multi-tenant prep, (β) `upsert_session` semantica.
- Commit: pending.
