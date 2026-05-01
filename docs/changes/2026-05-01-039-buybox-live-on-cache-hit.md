---
id: CHG-2026-05-01-039
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 7 — fix architetturale Path B' MVP CFO)
status: Draft
commit: 60488bf
adr_ref: ADR-0017, ADR-0014, ADR-0019, ADR-0016
---

## What

**Cache hit fa fetch buybox live** + **rate limit Keepa via settings**.
Due fix correlati che chiudono il bug architetturale identificato live
dal Leader: dopo la prima resolve, ogni run successivo (cache hit)
dava `verified_buybox_eur=None` → fallback `buy_box_eur=cost_eur`
in `build_listino_raw_from_resolved` → `profit = -fee` sistematico
→ R-08 VETO ROI fallito su tutto → cart vuoto, panchina vuota.

**Decisione Leader 2026-05-01 round 7 ratificata**: opzione A
("buybox sempre live"). La cache `description_resolutions` mappa
solo `descrizione → ASIN` (invariante); il Buy Box è volatile e
va sempre verificato (1 token Keepa per cache hit).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + helper `_fetch_buybox_live_or_none(lookup_callable, asin)` (R-01: errori → `(None, notes)`). + parametro `lookup_callable: Callable[[str], ProductData] \| None = None` a `resolve_listino_with_cache` (default None = retro-compat per test/CLI). Cache hit branch ora chiama il helper e popola `verified_buybox_eur` + `notes`. Docstring `resolve_listino_with_cache` + `build_listino_raw_from_resolved` aggiornati. |
| `src/talos/ui/dashboard.py` | modificato | `KeepaClient(rate_limit_per_minute=20)` hardcoded → `settings.keepa_rate_limit_per_minute` (env `TALOS_KEEPA_RATE_LIMIT_PER_MINUTE`, default 60 da `TalosSettings`). + passa `lookup_callable` a `resolve_listino_with_cache`. |
| `tests/unit/test_listino_input.py` | modificato | + 3 test mock-only CHG-039: cache hit chiama lookup_callable e popola buybox; cache hit + lookup raise → buybox=None + nota R-01; cache hit + lookup_callable=None (default) → retro-compat (buybox=None, no notes). + helper `_FakeCachedRow` / `_FakeProductData` / `_FakeFactory`. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **709 PASS** unit/gov/golden (era 706, +3 test CHG-039).
- **138 PASS** integration (invariato).
- **847 PASS** totali.

Detect_changes: 27 simboli touched, 3 file, **0 processi affetti**,
**risk LOW**.

## Why

Bug architetturale identificato in produzione (browser smoke test
Leader 2026-05-01 round 7, post CHG-038):

1. **CSV Galaxy demo** caricato 2 volte. Prima resolve consuma SERP
   + Keepa, popola cache. Seconda resolve hit cache → costruisce
   `ResolvedRow` con `verified_buybox_eur=None` (la tabella
   `description_resolutions` non ha colonna buybox, by design
   CHG-019).
2. `build_listino_raw_from_resolved` con `verified_buybox_eur=None`
   → fallback `buy_box_eur = prezzo_eur = cost_eur` (CHG-022 graceful
   pre-CHG-039).
3. Pipeline VGP: `cash_inflow = buy_box - fee_fba - buy_box*0.08 ≈
   buy_box * 0.84`. `cash_profit = cash_inflow - cost ≈ -0.16 * cost`
   (negativo). `roi ≈ -16%`. R-08 VETO (ROI < 8%) → `vgp_score = 0`
   per tutti.
4. Cart vuoto, Panchina vuota (R-09 esclude `vgp_score = 0`),
   Budget T+1 = budget originale.

Fix architetturale: la cache memorizza l'unica cosa **invariante**
(la mappa `descrizione → ASIN`); il `verified_buybox_eur` è
volatile e va **sempre** chiamato live, anche su cache hit. Costo:
1 token Keepa per ASIN (vs 0 oggi). Beneficio: pipeline VGP
funzionante.

**Bug secondario corretto in stesso CHG**: il rate limit Keepa
era hardcoded a `20/min` in `dashboard.py:984`, ignorando
`TalosSettings.keepa_rate_limit_per_minute`. Per N rows × top-N
candidati SERP × M lookup, il bucket pyrate-limiter saturava
istantaneamente. Sono fix correlati (entrambi riguardano la
quota Keepa per il flow Path B'); 1 CHG combinato per coerenza.

### Decisioni di design

1. **`lookup_callable` parametro opzionale (default None)**: zero
   breaking change per i test esistenti che passano solo
   `resolver_provider`. Solo dashboard production-side lo passa.
   Pattern coerente con `factory: ... | None`.

2. **Helper `_fetch_buybox_live_or_none` isolato**: testabilità
   diretta + riusabilità future (es. invalidate-on-stale check).
   Cattura `Exception` ampio (KeepaMiss/RateLimit/Transient/
   Selector/network) → tutti collassano in `(None, notes)`. R-01
   UX-side: row sempre esposta, errore in `notes`.

3. **`max_candidates=3` SERP invariato**: scope CHG-039 è "live
   buybox su cache hit", non "ottimizzazione candidati SERP".

4. **Rate limit via settings, non parametro UI dashboard**: `.env`
   è il punto di tuning operativo (no UI clutter per CFO).
   Default `TalosSettings.keepa_rate_limit_per_minute = 60`
   invariato; l'override avviene via env var.

5. **3 test mock-only sufficienti**: il path "cache hit + buybox
   live" è 1 funzione + 1 helper. Coverage: success / lookup-fail
   (R-01) / no-lookup (retro-compat). Test integration live già
   coperti dalla pipeline e2e (138 PASS).

6. **`monkeypatch.setattr` su `find_resolution_by_hash`** invece
   di mock factory full: il modulo target è facilmente
   monkey-patchable a livello import (`talos.ui.listino_input.find_resolution_by_hash`).
   Meno boilerplate, più leggibile.

7. **`_FakeFactory` con `__call__` + context manager**: stub
   minimo per soddisfare la firma `factory()` + `with` block.
   Nessuna chiamata reale al DB nei test mock-only.

8. **`_resolved_row_from_result` invariato**: il flow cache miss
   passa già da resolver che fornisce `verified_buybox_eur` via
   `_LiveAsinResolver.resolve_description` → `lookup_callable`
   (CHG-018). CHG-039 NON modifica quel branch.

### Out-of-scope

- **Cache TTL** o re-resolve completo: scope CHG futuro se la
  mappa desc→ASIN deve invalidarsi (es. ASIN delisted Amazon,
  brand change). Oggi assumiamo invariante.
- **Schema `description_resolutions` esteso con `buybox` + TTL**:
  CHG-039 sceglie deliberatamente di NON cachare il buybox (vs
  opzione C). Cachare un valore stale del buybox sarebbe peggio
  del fetch live.
- **Bottone UI "force re-resolve"**: scope CHG futuro (opzione D).
- **Help text dashboard "prezzo = costo fornitore"**: scope
  CHG-040 candidato (bug semantico CSV).
- **Alzare default `keepa_rate_limit_per_minute` da 60 a 600**:
  scope decisione Leader (default vs `.env` override). Oggi 60
  resta default conservativo; produzione live deve settare env.

## How

### `listino_input.py` (highlight)

```python
def _fetch_buybox_live_or_none(
    lookup_callable: Callable[[str], ProductData] | None,
    asin: str,
) -> tuple[Decimal | None, tuple[str, ...]]:
    if lookup_callable is None:
        return None, ()
    try:
        product = lookup_callable(asin)
    except Exception as exc:
        return None, (f"buybox lookup live failed: {type(exc).__name__}",)
    return product.buybox_eur, ()


def resolve_listino_with_cache(
    rows, *, factory, resolver_provider, tenant_id=1,
    lookup_callable: Callable[[str], ProductData] | None = None,
):
    # ... cache hit branch:
    if cached_asin is not None:
        buybox_live, lookup_notes = _fetch_buybox_live_or_none(
            lookup_callable, cached_asin,
        )
        out.append(ResolvedRow(
            ...,
            verified_buybox_eur=buybox_live,
            notes=lookup_notes,
        ))
```

### `dashboard.py` (highlight)

```diff
-keepa_client = KeepaClient(api_key=api_key, rate_limit_per_minute=20)
+keepa_client = KeepaClient(
+    api_key=api_key,
+    rate_limit_per_minute=settings.keepa_rate_limit_per_minute,
+)
 ...
 resolved = resolve_listino_with_cache(
     rows,
     factory=factory,
     resolver_provider=resolver_provider,
     tenant_id=DEFAULT_TENANT_ID,
+    lookup_callable=lookup_callable,
 )
```

### Test sentinella (highlight)

```python
def test_cache_hit_calls_lookup_callable_for_live_buybox(monkeypatch):
    monkeypatch.setattr(
        "talos.ui.listino_input.find_resolution_by_hash",
        lambda _db, *, tenant_id, description_hash: _FakeCachedRow(
            asin="B0CSTC2RDW", confidence_pct=92.5,
        ),
    )
    lookup_calls = []

    def lookup_stub(asin):
        lookup_calls.append(asin)
        return _FakeProductData(buybox_eur=Decimal("549.00"))

    resolved = resolve_listino_with_cache(
        [_row()], factory=_FakeFactory(),
        resolver_provider=lambda: _MockResolver({}),
        lookup_callable=lookup_stub,
    )
    assert resolved[0].verified_buybox_eur == Decimal("549.00")
    assert lookup_calls == ["B0CSTC2RDW"]
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed (1 RUF003 unicode autocorrected) |
| Format | `uv run ruff format --check src/ tests/` | 138 files already formatted |
| Type | `uv run mypy src/` | 0 issues (54 source files) |
| Listino input dedicated | `uv run pytest tests/unit/test_listino_input.py -q` | **74 PASS** (era 71, +3 CHG-039) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **709 PASS** (era 706, +3) |
| Integration full (incl. live) | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **138 PASS** (invariato) |
| GitNexus impact pre-edit | (resolve_listino_with_cache + build_listino_raw_from_resolved) | risk LOW |
| GitNexus detect_changes | `gitnexus_detect_changes()` | 27 simboli / 3 file, **0 processi affetti**, **risk LOW** |
| **Validazione bug fix end-to-end** | Streamlit live in browser, CSV cost realistici, cache pre-popolata | scope post-commit (Leader) |

**Rischi residui:**

- **+1 token Keepa per ASIN cache hit**: documentato + intenzionale.
  Per 100 ASIN × 1 token = 100 token/run. Gestibile col rate limit
  via env (`TALOS_KEEPA_RATE_LIMIT_PER_MINUTE=600` consigliato per
  produzione MVP).
- **`Exception` ampio in `_fetch_buybox_live_or_none`**: cattura
  anche `KeyboardInterrupt`/`SystemExit`? No: `Exception` esclude
  `BaseException`. Sicuro.
- **Dashboard ora dipende da `settings.keepa_rate_limit_per_minute`**:
  validator già in `TalosSettings` (default 60, > 0). Nessun impatto
  per chi non setta env.
- **Test esistenti con `lookup_callable=None`**: 4 test
  `test_resolve_with_no_factory_*` + altri usano la signature pre-CHG.
  Default None = invariato. Nessuna modifica richiesta.
- **`_LiveAsinResolver.resolve_description` (cache miss)** continua
  a chiamare `lookup_callable` per ogni candidato SERP top-N (3 ×
  rows). CHG-039 aggiunge +1 chiamata per ASIN cache hit. Total
  con cache mista: O(rows × top-N) cache miss + O(rows) cache hit.

## Test di Conformità

- **Path codice applicativo:** `src/talos/ui/`, `tests/unit/` ✓
  (aree ADR-0013 + ADR-0016).
- **ADR-0017 (Path B')**: `lookup_product` resta canonico fonte
  buybox; CHG-039 estende il chiamante (cache hit ora chiama
  anche lui).
- **ADR-0014 (mypy/ruff strict)**: 0 issues.
- **ADR-0019 (test strategy)**: unit puri + mock-only ✓.
- **R-01 NO SILENT DROPS** (ADR-0021): errori lookup → notes
  esplicite, row esposta. Test `test_cache_hit_lookup_failure`
  blinda il contratto.
- **Backward compat**: `lookup_callable` default None → 4 test
  esistenti `resolve_listino_with_cache` invariati. 138 integration
  live invariati.
- **Sicurezza**: zero secrets/PII; no nuove deps; no migration DB.
- **Impact analysis pre-edit**: risk LOW.
- **Detect changes pre-commit**: 27 simboli, 0 processi, risk LOW.
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **`feedback_concisione_documentale.md` rispettato**.

## Impact

- **`pyproject.toml` invariato** (no nuove deps).
- **Catalogo eventi canonici ADR-0021**: invariato (17/17 voci).
- **Test suite +3**: 709 unit/gov/golden + 138 integration = **847
  PASS**.
- **🎯 Path B' MVP CFO production-ready end-to-end**: cache hit
  ora produce VGP corretti (non più veto sistematico). Bug
  architetturale chiuso.
- **Rate limit tuning operativo**: `.env`
  `TALOS_KEEPA_RATE_LIMIT_PER_MINUTE=600` (o altro) ora ha effetto
  (era ignorato da hardcoded 20).
- **Sblocca**: smoke browser CFO-side completo (TEST-DEBT-003) +
  golden Samsung 1000 ASIN (B5) + bulk_resolve_async (B4) — tutti
  dipendevano dal flow cache hit funzionante.
- **Code health**: -1 hardcoded magic number (rate limit 20).
  +1 helper isolato testabile (`_fetch_buybox_live_or_none`).

## Refs

- ADR: ADR-0017 (`io_/`/`extract/` Path B'), ADR-0014 (mypy/ruff
  strict), ADR-0019 (test strategy), ADR-0016 (UI Streamlit).
- Predecessori:
  - CHG-2026-05-01-019 (`description_resolutions` cache schema —
    decisione di NON salvare il buybox, by design).
  - CHG-2026-05-01-020 (UI flow descrizione+prezzo, primo caller
    di `resolve_listino_with_cache`).
  - CHG-2026-04-30-022 (`fee_fba_manual` L11b — il fee che
    rendeva ROI negativo su buy_box=cost).
  - CHG-2026-04-30-025 (`cash_inflow_eur` formula, contratto
    `referral_fee_rate` in [0, 1]).
  - CHG-2026-05-01-038 (fix unit drift `referral_fee_pct` —
    stesso flow Path B' MVP CFO, sessione round 7).
- Bug rilevato live in browser dal Leader durante validazione
  smoke Path B' (sessione 2026-05-01 round 7, post CHG-038):
  "non alloca nessun asin... forse quando c'è cache hit non va
  in analisi vera perchè tutti i campi buy box sono vuoti".
- Decisione Leader 2026-05-01 round 7 ratificata: **opzione A**
  ("a buybox sempre live").
- Successore atteso: nessuno specifico. Possibili rotte:
  CHG-040 candidato (help text dashboard "prezzo = costo
  fornitore"), B5 (golden 1000), B4 (bulk async).
- Memory: nessuna nuova; `feedback_concisione_documentale.md`
  rispettato.
- Commit: `60488bf`.
