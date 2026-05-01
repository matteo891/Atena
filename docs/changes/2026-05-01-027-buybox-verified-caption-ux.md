---
id: CHG-2026-05-01-027
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" estesa round 5+ — quick win UX rate buybox verificato simmetrico a CHG-026)
status: Draft
commit: pending
adr_ref: ADR-0016, ADR-0014, ADR-0019
---

## What

Quick win UX **frontend-only** simmetrico a CHG-026: il caption del
flow descrizione+prezzo ora include in linea il **rate di Buy Box
verificato live** (`Buy Box verificato: N/M righe (X%).`). Il CFO vede
immediatamente l'**accuratezza del ROI calcolato downstream** — quanti
ASIN del listino hanno il prezzo Amazon NEW reale (CHG-022) vs quanti
usano il fallback `prezzo_eur` fornitore.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + helper puro `format_buybox_verified_caption(resolved: list[ResolvedRow]) -> str`. Aggrega `verified_buybox_eur is not None` su tutto il listino: ritorna `""` se lista vuota, altrimenti `f"Buy Box verificato: {n_verified}/{n_total} righe ({pct:.0f}%)."`. Stessa firma + comportamento di `format_cache_hit_caption` (CHG-026), zero deps Streamlit. |
| `src/talos/ui/dashboard.py` | modificato | Import `format_buybox_verified_caption` + integrazione nel `_render_descrizione_prezzo_flow`: `buybox_caption = format_buybox_verified_caption(resolved_with_overrides)` calcolato post-`cache_caption`, concatenato condizionalmente al caption esistente (suppress se vuoto). |
| `tests/unit/test_listino_input.py` | modificato | + helper `_resolved_with_buybox(*, verified_buybox_eur, asin)` + 7 test mock-only: empty (string vuota), all verified 5/5, none verified 4/4, mixed 3/12 (25%), single verified/fallback, mixed con riga unresolved (asin=""). + import `format_buybox_verified_caption`. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest unit:
**682 PASS** unit/gov/golden (era 675 a CHG-026, +7 nuovi buybox caption).
Pytest integration: **138 PASS** invariato. **820 PASS** totali (era
813 a CHG-026).

## Why

CHG-022 ha separato `verified_buybox_eur` da `cost_eur` in `ResolvedRow`,
permettendo a `build_listino_raw_from_resolved` di usare il Buy Box
reale Amazon NEW per il calcolo VGP/ROI quando disponibile, fallback
a `prezzo_eur` per cache hit / lookup fail. Ma fino a CHG-026 il dato
era invisibile al CFO durante l'uso reale:

- **Quanti ASIN del listino hanno ROI accurato vs ROI conservativo?**
  Sconosciuto. Il preview espone la colonna `buy_box_verificato` per
  riga, ma su listini >20 righe il CFO non aggrega visivamente.
- **Cache hit dominante = ROI conservativo dominante**: questa
  correlazione (CHG-022 OOS 1) non era visibile.
- **Decisione "ri-resolve manuale per refresh Buy Box"**: oggi il
  CFO non ha un trigger informato.

CHG-027 espone il dato in tempo reale nel caption, simmetrico a
CHG-026 (cache hit rate). Use-case CFO concreti:

- **Verified rate alta (>80%)**: ROI accurato, classifica VGP affidabile.
- **Verified rate bassa (<30%)**: cache fredda o lookup falliti
  dominanti. ROI è conservativo, decisione di "ri-resolve" informata.
- **0% verified**: cache satura ma TTL inesistente (out-of-scope CHG-022).
  Segnale chiaro per Leader sul valore di TTL.

### Decisioni di design

1. **Pattern simmetrico a `format_cache_hit_caption` (CHG-026)**:
   stessa firma `(resolved: list[ResolvedRow]) -> str`, stesso
   format `f"... {n}/{total} ... ({pct:.0f}%)."`, stesso comportamento
   empty → `""`. Beneficio: il CFO impara un solo template visivo.

2. **Aggregazione su `resolved_with_overrides`, non `resolved`**:
   coerenza con tutto il caption (override può cambiare
   `verified_buybox_eur` se il candidato alternativo ha buybox diverso —
   CHG-023 propaga `match.buybox_eur`).

3. **Numerator = `verified_buybox_eur is not None`**: il dato è
   "fresh" anche se la riga è cache hit. Cache hit del CHG-019 oggi
   NON salva buybox (decisione CHG-022 dec. 2), quindi cache hit →
   verified=None. Future estensioni cache con buybox + TTL
   cambieranno la semantica: scope futuro errata se serve
   distinguere "verified live" da "verified from cache".

4. **Include righe unresolved nel total**: pattern coerente con
   CHG-026. Il KPI è "tasso di righe con prezzo NEW reale", non
   "tasso di righe risolte con buybox". Riga unresolved =
   `verified_buybox_eur=None` per definizione.

5. **Caption frontend-only, ZERO emit telemetria**: il dato è
   derivato da `verified_buybox_eur` (esistente). Aggregare in
   evento canonico `ui.buybox_summary` sarebbe ridondante con
   `ui.resolve_confirmed` (che potrebbe estendersi in futuro con
   `n_verified_buybox` come errata aggiuntiva — out-of-scope).

6. **Caption multi-segment cresce a 5 segmenti potenziali**: oggi
   abbiamo `Risolti N/M (di cui K ambigui)` + `Override CFO` +
   `Cache:` + `Buy Box verificato:` + nota finale. Pattern Streamlit
   `st.caption` wrappa responsivo. Mitigazione futura: split in
   colonne / badge / mini-dashboard se il pattern non scala.
   Scope multi-page B2.

7. **`format_buybox_verified_caption` PRIMA di `format_cache_hit_caption`
   nell'import (alfabetico)**: minor — ruff isort policy. Nel caption
   visivo: cache PRIMA di buybox (logico: cache è infrastruttura,
   buybox è KPI prodotto).

8. **Helper test `_resolved_with_buybox`** locale al file (non
   esportato). Pattern simmetrico a `_resolved_with_cache_hit`
   (CHG-026), separato per chiarezza intent del singolo test.

### Out-of-scope

- **Errata catalogo `ui.buybox_summary`**: ridondante con dati derivati.
  Scope futuro errata `ui.resolve_confirmed.n_verified_buybox` se
  serve tracking telemetria.
- **Cache TTL `description_resolutions` con buybox**: scope futuro
  decisione Leader (sblocca anche by CHG-027 che mostra impatto cache
  fredda sul rate verified).
- **Re-resolve manuale Buy Box per riga**: scope futuro UX (button
  per riga "Refresh Buy Box live").
- **Aggregazione per categoria/brand**: scope multi-page B2.
- **Confronto verified live vs cost (delta % medio)**: utile ma
  scope analytics dashboard.
- **Caption simmetrico per `is_ambiguous` rate**: già presente
  inline `(di cui {n_ambiguous} ambigui)`. Scope coperto.

## How

### `listino_input.py` (highlight)

```python
def format_buybox_verified_caption(resolved: list[ResolvedRow]) -> str:
    """Caption UX rate Buy Box verificato live."""
    if not resolved:
        return ""
    n_total = len(resolved)
    n_verified = sum(1 for r in resolved if r.verified_buybox_eur is not None)
    pct = n_verified / n_total * 100
    return f"Buy Box verificato: {n_verified}/{n_total} righe ({pct:.0f}%)."
```

### `dashboard.py` (highlight integrazione)

```python
cache_caption = format_cache_hit_caption(resolved_with_overrides)
buybox_caption = format_buybox_verified_caption(resolved_with_overrides)
caption = (
    f"Risolti {n_resolved}/{n_total} (di cui {n_ambiguous} ambigui)."
    + (f" Override CFO applicati: {n_overrides}." if n_overrides else "")
    + (f" {cache_caption}" if cache_caption else "")
    + (f" {buybox_caption}" if buybox_caption else "")
    + " Le righe ambigue restano nel listino: il CFO valuta caso per caso."
)
st.caption(caption)
```

### Test pattern (highlight)

```python
def test_format_buybox_verified_caption_mixed() -> None:
    """Mixed 3 verified / 12 totali -> 25%."""
    rows = [_resolved_with_buybox(verified_buybox_eur=Decimal("599.00")) for _ in range(3)] + [
        _resolved_with_buybox(verified_buybox_eur=None) for _ in range(9)
    ]
    assert format_buybox_verified_caption(rows) == "Buy Box verificato: 3/12 righe (25%)."
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format src/ tests/` | 137 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Buybox caption mirato | `uv run pytest tests/unit/test_listino_input.py -k "buybox_verified_caption" -v` | **7 PASS** |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **682 PASS** (era 675, +7) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |

**Rischi residui:**
- **Caption a 5 segmenti**: pattern simmetrico a CHG-026 in fila può
  apparire denso. Mitigazione: scope multi-page B2 (mini-dashboard
  con badge).
- **Cache hit branch sempre `verified=None` oggi**: il rate sarà
  sempre ≤ rate "non cache hit". Aspetto atteso, ma il CFO può
  inferire "0% verified su cache hit dominante" e chiedere TTL.
  Mitigazione strutturale: cache TTL out-of-scope CHG-022.
- **Override candidato (CHG-023) propaga `verified_buybox_eur` del
  nuovo candidato**: il rate post-override può divergere dal rate
  pre-override. Atteso. Test con override non aggiunto perché
  ridondante con CHG-023 propagation test.
- **Arrotondamento `:.0f`**: 49.5% → "50%". Pattern coerente con
  CHG-026.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/` ✓ (area ADR-0013
  consentita).
- **ADR-0016 vincoli rispettati:** helper puro testabile senza
  Streamlit (modulo `listino_input.py` zero-Streamlit). Render
  Streamlit-side gestito in `dashboard.py`.
- **Test unit puri:** ✓ (ADR-0019). 7 test mock-only senza dipendenza
  Streamlit / DB.
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `format_buybox_verified_caption`
  → ADR-0016 (UI helper puro).
- **Backward compat:** modifica additiva 100%; helper nuovo, caption
  esistente preserva struttura. Nessun caller esterno rompe.
- **Sicurezza:** zero secrets / PII; aggregazione su flag `Decimal | None`
  applicativo.
- **Impact analysis pre-edit:** simbolo nuovo, zero caller upstream.
  Risk LOW.
- **Detect changes pre-commit:** atteso risk LOW (3 file, 0 processi
  affetti — pattern identico a CHG-026).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17). Quick
  win frontend, no errata.
- **`feedback_concisione_documentale.md` rispettato**: helper minimo,
  test mirati, change doc snello + simmetrico a CHG-026 (catena
  consolidata).

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +7 unit**: 682 unit/gov/golden (era 675).
- **MVP CFO target**: hardening UX incrementale; il flow descrizione+prezzo
  ora espone immediatamente i 2 KPI di efficacia (cache hit + buybox
  verified) nel caption live.
- **Pattern aggregato `format_*_caption`**: ulteriormente consolidato.
  Replicabile per future aggregate (es. ROI medio/min/max, override
  rate).
- **Sblocca decisione cache TTL Leader-side**: il CFO può rilevare
  cache fredda + ROI conservativo simultaneamente.

## Refs

- ADR: ADR-0016 (UI Streamlit, helper puri pattern), ADR-0014
  (mypy/ruff strict), ADR-0019 (test unit puri).
- Predecessori:
  - CHG-2026-05-01-022 (verified_buybox_eur separato): producer del
    flag aggregato in CHG-027.
  - CHG-2026-05-01-023 (override candidato A3): caller del caption
    multi-segment esteso.
  - CHG-2026-05-01-026 (caption cache hit): pattern simmetrico
    ereditato.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Successore atteso: nessuno specifico in scope hardening UX.
  Possibili rotte (decisione Leader): cache TTL ora supportata da
  evidenza doppia (rate cache + rate verified), (B1) `structlog.bind`
  context tracing, (B2) refactor UI multi-page ADR-0016, (β)
  `upsert_session` semantica, (POLICY-001) Velocity bsr_chain.
- Commit: pending.
