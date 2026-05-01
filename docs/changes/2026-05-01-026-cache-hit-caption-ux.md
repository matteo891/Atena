---
id: CHG-2026-05-01-026
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" estesa round 5+ — quick win UX hit rate cache)
status: Draft
commit: pending
adr_ref: ADR-0016, ADR-0014, ADR-0019
---

## What

Quick win UX **frontend-only**: il caption del flow descrizione+prezzo
ora include in linea l'hit rate della cache `description_resolutions`
(`Cache: N/M hit (X%).`). Il CFO vede l'efficacia della cache **prima**
ancora che la telemetria CHG-025 venga consumata da una dashboard
observability a valle.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + helper puro `format_cache_hit_caption(resolved: list[ResolvedRow]) -> str`. Aggrega `is_cache_hit` su tutto il listino risolto: ritorna `""` se lista vuota, altrimenti `f"Cache: {n_hits}/{n_total} hit ({pct:.0f}%)."`. Zero deps Streamlit, testabile mock-only. |
| `src/talos/ui/dashboard.py` | modificato | Import `format_cache_hit_caption` + integrazione nel `_render_descrizione_prezzo_flow`: `cache_caption = format_cache_hit_caption(resolved_with_overrides)` calcolato pre-`st.caption`, concatenato condizionalmente al caption esistente (suppress se stringa vuota, pattern coerente con `Override CFO applicati: N`). |
| `tests/unit/test_listino_input.py` | modificato | + helper `_resolved_with_cache_hit(*, is_cache_hit, asin)` + 7 test mock-only: empty (string vuota), all hits 5/5, all misses 4/4, mixed 3/12 (25%), single hit/miss, mixed con riga unresolved (asin=""). + import `format_cache_hit_caption`. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest unit:
**675 PASS** unit/gov/golden (era 668 a CHG-025, +7 nuovi cache caption).
Pytest integration: **138 PASS** invariato. **813 PASS** totali (era
806 a CHG-025).

## Why

Il flow descrizione+prezzo ha ora telemetria completa (`cache.hit` /
`cache.miss` da CHG-025). Ma quella telemetria è asincrona — richiede
una pipeline di consumo (Loki/Grafana/whatever) per essere fruita.
**Il CFO che usa la dashboard ora ha bisogno di feedback immediato**:
"il sistema sta usando la cache o sta consumando quota Keepa per
ogni riga?".

Aggregando `ResolvedRow.is_cache_hit` (campo esistente da CHG-019)
si genera il dato senza ulteriore round-trip DB. Pattern simmetrico
al "Override CFO applicati: N" di CHG-024: feedback in tempo reale
nello stesso caption.

Use-case CFO concreti:
- **Cache hit alta (>70%)**: il listino è prevalentemente ricorrente,
  costo Keepa minimo, decisione "ri-eseguo questa sessione" è
  economica.
- **Cache miss dominante (<30%)**: il CFO ha aggiunto molti nuovi
  prodotti; quota Keepa sta venendo consumata. Decisione informata
  sulla frequenza con cui ri-aggiornare.
- **0% hit (factory=None o cache fredda)**: feedback chiaro che la
  cache non sta dando valore in questo run; si può investigare se
  il DB è disponibile o aspettare il secondo run.

### Decisioni di design

1. **Helper `format_cache_hit_caption` come funzione PUBBLICA**:
   coerente con `format_confidence_badge`, `apply_candidate_overrides`,
   `build_listino_raw_from_resolved`. Importabile da `dashboard.py`.

2. **Lista vuota → stringa vuota**: il caller (dashboard) suppress
   con concatenazione condizionale `(f" {cache_caption}" if cache_caption else "")`.
   Pattern coerente con "Override CFO applicati: N" che viene mostrato
   solo se `n_overrides > 0`. Nessuna eccezione `ValueError`.

3. **Format `Cache: {hits}/{total} hit ({pct:.0f}%)."`**: punto finale
   per coerenza grammaticale con il caption multi-segment esistente.
   Percentuale arrotondata all'intero (`pct:.0f`): più leggibile
   `(25%)` di `(25.0%)`.

4. **Include righe unresolved nel total**: `is_cache_hit=False` per
   riga `asin=""`, `n_total = len(resolved)`. Decisione: il KPI è
   "tasso di lookup serviti dalla cache", non "tasso di lookup di
   successo". Riga unresolved è un lookup (cache miss + resolver fail).
   Coerente con telemetria `cache.miss` di CHG-025.

5. **Caption frontend-only, ZERO emit telemetria nuova**: la telemetria
   `cache.hit` / `cache.miss` di CHG-025 copre già il dato. Aggiungere
   `ui.cache_summary` sarebbe ridondante (le aggregate si calcolano a
   valle dalla telemetria individuale).

6. **Aggregazione su `resolved_with_overrides`, non `resolved`**:
   pattern coerente con il resto del caption (`n_resolved`, `n_total`,
   `n_ambiguous` calcolati su `resolved_with_overrides` post-CHG-023).
   L'override sostituisce ASIN/buybox/confidence ma NON cambia
   `is_cache_hit` — l'override è sempre flagged come "non cache" per
   definizione (il candidato originale era nella cache, ma il nuovo
   non lo è). Decisione: l'aggregazione resta corretta (override =
   nuova risoluzione fresh, non cache hit).

7. **No campo log nuovo**: catalogo ADR-0021 invariato (17/17).
   Quick win UX puro, no errata.

8. **Helper testato in `test_listino_input.py` (file esistente),
   non nuovo file**: il modulo è cohesive, non serve nuovo file di
   test per 7 test correlati. Sezione dedicata con commento ancorante
   CHG-026.

### Out-of-scope

- **Errata catalogo `ui.cache_summary`**: ridondante con `cache.hit/miss`
  di CHG-025.
- **Visualizzazione grafica hit rate (gauge/sparkline) in dashboard**:
  scope multi-page B2.
- **Hit rate per categoria/brand**: aggregazione granulare. Scope
  futuro analytics dashboard.
- **Persistenza hit rate in `analysis_session.metadata`**: scope
  futuro se serve trend storico.
- **Caption simmetrico per altre cache** (es. config_overrides): le
  altre non hanno hit/miss tracking applicativo. Scope futuro se serve.

## How

### `listino_input.py` (highlight)

```python
def format_cache_hit_caption(resolved: list[ResolvedRow]) -> str:
    """Caption UX hit rate cache `description_resolutions`."""
    if not resolved:
        return ""
    n_total = len(resolved)
    n_hits = sum(1 for r in resolved if r.is_cache_hit)
    pct = n_hits / n_total * 100
    return f"Cache: {n_hits}/{n_total} hit ({pct:.0f}%)."
```

### `dashboard.py` (highlight integrazione)

```python
cache_caption = format_cache_hit_caption(resolved_with_overrides)
caption = (
    f"Risolti {n_resolved}/{n_total} (di cui {n_ambiguous} ambigui)."
    + (f" Override CFO applicati: {n_overrides}." if n_overrides else "")
    + (f" {cache_caption}" if cache_caption else "")
    + " Le righe ambigue restano nel listino: il CFO valuta caso per caso."
)
st.caption(caption)
```

### Test pattern (highlight)

```python
def test_format_cache_hit_caption_mixed() -> None:
    """Mixed 3 hit / 12 totali -> 25%."""
    rows = [_resolved_with_cache_hit(is_cache_hit=True) for _ in range(3)] + [
        _resolved_with_cache_hit(is_cache_hit=False) for _ in range(9)
    ]
    assert format_cache_hit_caption(rows) == "Cache: 3/12 hit (25%)."
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 137 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Cache caption mirato | `uv run pytest tests/unit/test_listino_input.py -k "cache_hit_caption" -v` | **7 PASS** |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **675 PASS** (era 668, +7) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |

**Rischi residui:**
- **Caption può crescere troppo**: oggi il caption ha 4 segmenti
  potenziali (resolved/ambigui + override + cache + nota finale).
  Pattern Streamlit `st.caption` ha layout responsive ma su mobile
  potrebbe wrappare male. Mitigazione: scope futuro split caption
  in più `st.caption` o badge.
- **`is_cache_hit` semantics post-override**: l'override (CHG-023)
  imposta nuovi valori ma non muta `is_cache_hit`. Decisione esplicita
  punto 6 sopra. Se in futuro l'override viene salvato in cache come
  "preferenza CFO", la semantica `is_cache_hit` andrà rivisitata.
- **`pct = 0/0 × 100`**: prevenuto da `if not resolved: return ""`
  upstream. Test `test_format_cache_hit_caption_empty` blinda il caso.
- **Arrotondamento percentuale `:.0f`**: 25.5% diventa "26%". Trade-off:
  leggibilità vs precisione. Il CFO non ha bisogno di precisione
  decimale per un KPI di efficacia cache.
- **Helper test usa `Decimal` e `_resolved_with_cache_hit`**: il
  helper `_resolved_with_cache_hit` è locale al test (non riusato).
  Pattern coerente con altri helper test del file.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area ADR-0013
  consentita).
- **ADR-0016 vincoli rispettati:** helper puro testabile senza
  Streamlit (modulo `listino_input.py` resta zero-Streamlit). Render
  Streamlit-side gestito in `dashboard.py`.
- **Test unit puri:** ✓ (ADR-0019). 7 test mock-only senza dipendenza
  Streamlit / DB.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `format_cache_hit_caption`
  → ADR-0016 (UI helper puro).
- **Backward compat:** modifica additiva 100%; helper è nuovo,
  caption esistente preserva struttura. Nessun caller esterno rompe.
  `dashboard.py` re-export non necessario (consumer interno).
- **Sicurezza:** zero secrets / PII; aggregazione su flag boolean
  applicativo.
- **Impact analysis pre-edit:** `format_cache_hit_caption` nuovo
  simbolo, zero caller. `_render_descrizione_prezzo_flow` zero caller
  upstream esterni. Risk LOW.
- **Detect changes pre-commit:** `gitnexus_detect_changes` risk
  **LOW** (7 simboli touched, 0 processi affetti, 3 file).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17). Quick
  win frontend, no errata.
- **`feedback_concisione_documentale.md` rispettato**: helper minimo,
  test mirati, change doc snello.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +7 unit**: 675 unit/gov/golden (era 668).
- **MVP CFO target**: hardening UX incrementale; il flow descrizione+prezzo
  ora espone immediatamente il KPI di efficacia cache senza richiedere
  consumer telemetria a valle.
- **Pattern aggregato `format_*_caption`**: replicabile per altre
  aggregate (es. `format_buybox_verified_caption` se serve KPI sul
  rate di Buy Box live).
- **Sblocca decisione cache TTL Leader-side**: il CFO può rilevare
  cache fredda visivamente senza aspettare consumer telemetria.

## Refs

- ADR: ADR-0016 (UI Streamlit, helper puri pattern), ADR-0014
  (mypy/ruff strict), ADR-0019 (test unit puri).
- Predecessori:
  - CHG-2026-05-01-019 (cache `description_resolutions`): producer
    del flag `is_cache_hit`.
  - CHG-2026-05-01-020 (UI flow descrizione+prezzo): caller del
    caption esteso.
  - CHG-2026-05-01-023 (override candidato A3): pattern caption
    multi-segment ereditato (`Override CFO applicati: N`).
  - CHG-2026-05-01-024 (telemetria UI): pattern simmetrico (telemetria
    backend + caption frontend).
  - CHG-2026-05-01-025 (telemetria cache): produttore del segnale che
    CHG-026 espone in UI live.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato (helper minimo + 7 test mirati + change doc snello).
- Successore atteso: nessuno specifico in scope hardening UX.
  Possibili rotte (decisione Leader): cache TTL ora supportata da
  evidenza, (B1) `structlog.bind` context tracing, (B2) refactor UI
  multi-page ADR-0016, (β) `upsert_session` semantica, (POLICY-001)
  Velocity bsr_chain.
- Commit: pending.
