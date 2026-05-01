---
id: CHG-2026-05-02-003
date: 2026-05-02
author: Claude (su autorizzazione Leader, modalità "ultra macinata" round 7 — sblocco MVP CFO operativo)
status: Draft
commit: TBD
adr_ref: ADR-0017, ADR-0018, ADR-0014, ADR-0019
---

## What

**Velocity estimator V_tot da BSR root + integrazione hybrid CSV→BSR→default**.
Sblocca la falla #9 della review post round 7: il flow Path B' MVP CFO con
CSV minimal (`descrizione,prezzo`) produceva sempre cart vuoto perché
`v_tot=0` (default) → `q_m=0` → `qty_final=0` → ASIN escluso dal Tetris.

Strategia hybrid (decisione Leader-implicita ratificata in macina):

1. **CSV `v_tot > 0`** → usa quello (override esplicito del CFO).
2. **CSV `v_tot = 0` AND `bsr_root` disponibile** → stima MVP da Keepa
   BSR con formula log-lineare placeholder (calibrata Samsung MVP).
3. **Altrimenti** → `0.0` con flag `default_zero` (ASIN escluso a valle).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/velocity_estimator.py` | nuovo | `estimate_v_tot_from_bsr(bsr) -> float` (formula log MVP placeholder), `resolve_v_tot(*, csv_v_tot, bsr_root) -> (v_tot, source)` (strategy hybrid), 3 costanti audit `V_TOT_SOURCE_{CSV,BSR_ESTIMATE,DEFAULT_ZERO}`. Doctest + warning espliciti che formula richiede ricalibrazione su dati storici. |
| `src/talos/extract/__init__.py` | modificato | Re-export 5 nuovi simboli. |
| `src/talos/extract/asin_resolver.py` | modificato | `ResolutionCandidate` + `bsr_root: int \| None = None`. `_LiveAsinResolver.resolve_description`: propaga `product.bsr` (Keepa) nel candidato. |
| `src/talos/ui/listino_input.py` | modificato | `ResolvedRow` + `bsr_root: int \| None = None`. `_fetch_buybox_live_or_none`: signature da 2-tuple a 3-tuple `(buybox, bsr, notes)`. Cache hit branch + `_resolved_row_from_result` + `apply_candidate_overrides` propagano `bsr_root`. `build_listino_raw_from_resolved` usa `resolve_v_tot` e aggiunge colonna audit `v_tot_source`. |
| `tests/unit/test_velocity_estimator.py` | nuovo | 12 test unit (estimator scaling, monotonicità, clamp, hybrid resolver, audit flags distinct). |
| `tests/unit/test_listino_input.py` | modificato | `_FakeProductData` stub + `bsr` attr; `_resolved` helper test + `bsr_root` opzionale; 3 test sentinel `build_listino_raw` per le 3 vie del resolve hybrid. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **731 PASS** unit/gov/golden (era 716, **+15 nuovi**).
- **138 PASS** integration (invariato).
- **869 PASS** totali.

Detect_changes: 29 simboli touched, 6 file, **0 processi affetti**,
**risk LOW**.

## Why

Identificato in review post-round 7 (Leader: "ma questo sarebbe il
prodotto finito?"): le formule erano implementate canonicamente ma il
flow MVP CFO Path B' era operativamente **monco** — il CFO che caricava
CSV minimal otteneva sempre cart vuoto perché `v_tot=0` portava a tutti
gli ASIN con `qty_final=0`.

Pre-CHG-003 catena del bug:

```
CSV v_tot=0 (default)
→ q_m = 0 / (s_comp+1) = 0
→ qty_target = 0 * 15/30 = 0
→ qty_final = floor(0/5)*5 = 0
→ Tetris skip qty_final<=0 (CHG-041)
→ Cart vuoto sempre
→ Panchina vuota sempre (R-09 esige vgp_score>0, ma vgp_score>0 senza qty_final non genera nulla)
→ MVP non utilizzabile
```

Post-CHG-003: il `bsr` è già disponibile in `ProductData` da Keepa
(CHG-2026-05-01-015) o scraper (CHG-2026-05-01-013). Il resolver propaga
`bsr_root` nel candidato → ResolvedRow → listino_raw → l'estimator
calcola `v_tot ≈ 100 - 20·log10(bsr)`. Per Samsung MVP con BSR ~1k-10k,
risultato `v_tot ≈ 20-40`, sufficiente per allocazioni significative.

### Decisioni di design

1. **Formula log-lineare placeholder**: scelta MVP non calibrata. Forma
   `V_tot = max(1, INTERCEPT - SLOPE · log10(bsr))` con INTERCEPT=100,
   SLOPE=20. Approssima distribuzione tipica Cell Phones IT. **Documentata
   esplicitamente come placeholder** con TODO esplicito di ricalibrazione
   tramite ground truth (errata ADR-0018 futura).

2. **Hybrid CSV-override / BSR-fallback / default_zero**: non breaking
   per chi specifica `v_tot` nel CSV. Auto-fallback per chi non lo fa.
   Audit trail tramite colonna `v_tot_source` nel listino_raw + DataFrame
   output (3 valori distinti).

3. **`bsr_root` propagato attraverso 4 layer** (ResolutionCandidate →
   ResolvedRow → ResolvedRow override → listino_raw): full traceability
   dal Keepa lookup fino al final v_tot resolution. Cache hit branch
   chiama `lookup_callable` per buybox (CHG-039 pattern); estende
   ritorno per includere anche `bsr` (signature change interno
   `_fetch_buybox_live_or_none`).

4. **Default `bsr_root=None`** (frozen dataclass): backward compat 100%
   per chi crea `ResolvedRow` manualmente nei test.

5. **`v_tot_source` come colonna del listino_raw**: visibile in
   `enriched_df` audit/debug expander della dashboard. Il CFO può
   distinguere "valore mio CSV" da "stima MVP" da "zero default" quando
   ispeziona i numeri.

6. **Estimator come modulo separato `extract/velocity_estimator.py`**:
   non in `formulas/` perché non è una formula canonica PROJECT-RAW
   (è uno **stimatore approssimato**, distinta semantica). In
   `extract/` perché interpreta dati esterni Amazon (BSR).

7. **Doctest sull'estimator**: facile sentinel sui boundary
   (BSR=1, BSR=10000, BSR=None, BSR=0).

8. **`_MIN_V_TOT = 1.0` clamp**: evita 0 spurio quando `INTERCEPT -
   SLOPE·log10(bsr)` va negativo per BSR molto alti. R-01 NO SILENT
   DROPS: l'ASIN non viene escluso silenziosamente, riceve un v_tot
   minimo che lo lascia in pista (qty_final=0 per cost alto = decisione
   downstream del Tetris, non dell'estimator).

9. **NB: la formula NON è canonica**: errata ADR-0018 quando avremo
   dati reali. Il test sentinel verifica la **forma** (monotonia,
   clamp, scaling log), non i valori specifici (che cambieranno con
   calibrazione).

### Out-of-scope

- **Calibrazione formula su dati reali**: scope futuro (richiede
  raccolta ground truth N>=20 ASIN Samsung con BSR snapshot + vendite
  reali).
- **Categoria-specifica calibration** (Samsung Cell Phones vs Apple
  Headphones vs ...): scope post-MVP. Oggi formula universale
  approssimativa.
- **Sales Estimates feature paid Keepa**: se il piano del Leader la
  include, può sostituire l'estimator log con dati direttamente da
  Keepa. Decisione operativa Leader.
- **Telemetria evento `v_tot.estimated_from_bsr`**: catalogo ADR-0021
  non esteso in CHG-003. Errata catalogo se serve audit aggregato.

## How

### `velocity_estimator.py` (highlight)

```python
def estimate_v_tot_from_bsr(bsr: int | None) -> float:
    if bsr is None or bsr <= 0:
        return 0.0
    estimated = 100.0 - 20.0 * math.log10(bsr)
    return max(1.0, estimated)


def resolve_v_tot(*, csv_v_tot: int, bsr_root: int | None) -> tuple[float, str]:
    if csv_v_tot > 0:
        return float(csv_v_tot), V_TOT_SOURCE_CSV
    estimated = estimate_v_tot_from_bsr(bsr_root)
    if estimated > 0:
        return estimated, V_TOT_SOURCE_BSR_ESTIMATE
    return 0.0, V_TOT_SOURCE_DEFAULT_ZERO
```

### `asin_resolver.py` (highlight diff)

```diff
 @dataclass(frozen=True)
 class ResolutionCandidate:
     asin: str
     title: str
     buybox_eur: Decimal | None
     fuzzy_title_pct: float
     delta_price_pct: float | None
     confidence_pct: float
+    bsr_root: int | None = None  # CHG-003

 # _LiveAsinResolver.resolve_description loop:
+bsr_root: int | None = None
 try:
     product = self._lookup(serp_item.asin)
     buybox = product.buybox_eur
+    bsr_root = product.bsr  # CHG-003
 except Exception as exc:
     ...
 candidates.append(
     ResolutionCandidate(..., bsr_root=bsr_root),
 )
```

### `listino_input.py` (highlight diff)

```diff
-def _fetch_buybox_live_or_none(...) -> tuple[Decimal | None, tuple[str, ...]]:
+def _fetch_buybox_live_or_none(...) -> tuple[Decimal | None, int | None, tuple[str, ...]]:
     if lookup_callable is None:
-        return None, ()
+        return None, None, ()
     try:
         product = lookup_callable(asin)
     except Exception as exc:
-        return None, (f"buybox lookup live failed: {type(exc).__name__}",)
+        return None, None, (f"buybox lookup live failed: {type(exc).__name__}",)
-    return product.buybox_eur, ()
+    return product.buybox_eur, product.bsr, ()


 # build_listino_raw_from_resolved:
+v_tot_resolved, v_tot_source = resolve_v_tot(
+    csv_v_tot=r.v_tot, bsr_root=r.bsr_root,
+)
 record: dict[str, object] = {
     ...,
-    "v_tot": r.v_tot,
+    "v_tot": v_tot_resolved,
+    "v_tot_source": v_tot_source,
     ...
 }
```

### Test sentinella (highlight)

```python
def test_build_listino_v_tot_estimated_from_bsr_when_csv_zero():
    rows = [_resolved("B0AAA", 100.0, v_tot=0, bsr_root=10000)]
    df = build_listino_raw_from_resolved(rows)
    assert df.iloc[0]["v_tot"] == pytest.approx(20.0)  # 100 - 20·log10(10000)
    assert df.iloc[0]["v_tot_source"] == "bsr_estimate_mvp"
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 140 files left unchanged |
| Type | `uv run mypy src/` | 0 issues (55 source files) |
| Velocity estimator dedicated | `uv run pytest tests/unit/test_velocity_estimator.py -q` | **12 PASS** |
| Listino input integration | `uv run pytest tests/unit/test_listino_input.py -q` | **77 PASS** (era 74, +3) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **731 PASS** (era 716, +15) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (`ResolvedRow`, `ResolutionCandidate`, `_fetch_buybox_live_or_none`) | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 29 simboli / 6 file, **0 processi affetti**, **risk LOW** |
| **Validazione browser** | Streamlit live: ricarica CSV minimal (no v_tot) → cart non vuoto post-Conferma | scope post-commit (Leader) |

**Rischi residui:**

- **Formula log non calibrata**: documentata esplicitamente. Scope
  futuro errata ADR-0018.
- **`apply_candidate_overrides` propaga `bsr_root` del candidato
  override**: se override candidato non ha BSR (improbabile, ma
  possibile su rate limit Keepa selettivo), `bsr_root=None` →
  estimator ritorna `default_zero`. UX comprensibile (CFO ha
  override volutamente).
- **`v_tot_source` colonna nel DataFrame `listino_raw`**: aggiuntiva
  vs schema 7-col canonico CHG-039. Tutti i caller esistenti che
  fanno `.columns >= REQUIRED_INPUT_COLUMNS` continuano a passare
  (set inclusion); chi enumera fixed columns potrebbe vedere il
  campo extra. Nessun caller scoperto in audit pre-CHG.
- **Backward compat sul `_FakeProductData` test stub**: aggiornato
  con `bsr` attr default None.

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/`, `src/talos/ui/`,
  `tests/unit/` ✓ (aree ADR-0013 + ADR-0017).
- **ADR-0017 (Path B')**: `bsr` da `ProductData` (Keepa CHG-015) ora
  consumato anche per stima v_tot, oltre che per fallback `bsr_chain`
  (CHG-013).
- **ADR-0018 (algoritmo VGP)**: la pipeline downstream (`q_m`,
  `qty_target`, `qty_final`) **non cambia**. Cambia solo l'**input**
  (`v_tot` ora popolato da estimator quando manca CSV). La docstring
  della formula `q_m` resta verbatim PROJECT-RAW.
- **ADR-0014 (mypy/ruff strict)**: 0 issues.
- **ADR-0019 (test strategy)**: unit puri ✓ + property-style test su
  monotonicità.
- **R-01 NO SILENT DROPS**: `default_zero` flag esplicito nel listino
  audit, nessuna riga azzerata silenziosamente.
- **Backward compat**: `bsr_root=None` default su ResolvedRow e
  ResolutionCandidate. Caller esistenti senza override invariati.
- **Sicurezza**: zero secrets/PII; no nuove deps; no migration DB.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 29 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +15**: 731 unit/gov/golden + 138 integration = **869
  PASS**.
- **🎯 MVP CFO Path B' operativamente sbloccato**: il flow CSV minimal
  ora produce cart non vuoto (qty_final > 0 per ASIN con BSR
  ragionevole). Falla #9 review post-round 7 chiusa.
- **Audit trail v_tot**: il CFO vede in dashboard `v_tot_source` per
  capire da dove viene il valore (CSV, stima, default).
- **Sblocca**: validation iterativa CFO sul flow reale, calibrazione
  futura della formula con dati storici.
- **Code health**: +1 modulo dedicato isolato; +1 colonna audit; +15
  test sentinel; signature `_fetch_buybox_live_or_none` esplicita su
  3 tuple anziché 2.

## Refs

- ADR: ADR-0017 (Path B'), ADR-0018 (formule VGP/Tetris pipeline),
  ADR-0014 (mypy/ruff strict), ADR-0019 (test strategy).
- Predecessori:
  - CHG-2026-05-01-013 (BSR multi-livello scraper, primo consumatore).
  - CHG-2026-05-01-015 (Keepa live: `data['SALES']` → `bsr`).
  - CHG-2026-05-01-018 (`_LiveAsinResolver` composer end-to-end,
    primo punto di propagazione BSR a valle).
  - CHG-2026-05-01-039 (cache hit fa fetch buybox live — pattern di
    helper `_fetch_buybox_live_or_none` esteso a 3-tuple).
- Falla identificata in review post-round 7 (Leader: "ma questo sarebbe
  il prodotto finito?"): #9 `v_tot=0 default → cart vuoto`. Chiusa
  da CHG-003.
- Successore atteso: errata ADR-0018 con formula calibrata su dati
  storici (scope sessione dedicata + raccolta ground truth Samsung).
  Possibili rotte secondarie: telemetria evento
  `v_tot.estimated_from_bsr` per audit aggregato; UI dashboard
  visualizza `v_tot_source` esplicitamente.
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: TBD (backfill hash post-commit).
