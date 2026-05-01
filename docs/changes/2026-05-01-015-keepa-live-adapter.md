---
id: CHG-2026-05-01-015
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 4 — sblocco canale 1 Keepa live post arrivo private API key)
status: Draft
commit: bb5a9cd
adr_ref: ADR-0017, ADR-0014, ADR-0019, ADR-0021
---

## What

`_LiveKeepaAdapter` ratificato live (era skeleton `NotImplementedError`
da CHG-2026-05-01-001). Sblocca canale 1 di acquisizione (ADR-0017)
con key Keepa privata caricata via `.env` (CHG-014).

Decisioni Leader ratificate 2026-05-01 round 4 dopo
diagnostic empirico su B0CSTC2RDW (Galaxy S24, ASIN gia' usato in
test live scraping CHG-013):

- **A2** `buybox_eur` source hierarchy: `data['BUY_BOX_SHIPPING']`
  -> `data['NEW']` -> `data['AMAZON']`. Il piano subscription
  corrente del Leader **non espone `BUY_BOX_SHIPPING`** (csv[18]
  assente nel response, scoperto in diagnostic). `data['NEW']` (prezzo
  offerta nuova piu' bassa) coincide empiricamente col Buy Box reale
  per B0CSTC2RDW (Keepa NEW €549.00 == scraper live CHG-013 €549.00).
  Fallback `AMAZON` (Amazon-as-seller) per ASIN dove NEW assente.
- **A** `bsr` source `data['SALES']` (BSR root categoria, ADR-0017
  canonico).
- **alpha''** `fee_fba_eur` SEMPRE `None` -> caller riceve
  `KeepaMissError` -> fallback `fee_fba_manual` (L11b Frozen del
  Leader, CHG-022). Razionale: il `pickAndPackFee` di Keepa
  (es. €4.10 per Galaxy S24) NON e' equivalente alla Fee FBA
  totale stimata da L11b (es. €43.45). Differenza ordine di
  grandezza ~10x: la formula L11b approssima referral 7% +
  pick&pack (~€38.43 + €4.10 ≈ €42.5), Keepa espone solo
  pick&pack atomico. Sostituzione diretta avrebbe inquinato
  Cash_Profit / ROI / VGP (sovrastima ~10x).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/io_/keepa_client.py` | modificato | `_LiveKeepaAdapter.query` ratificato live: lazy init `keepa.Keepa(api_key)` al primo `query()`, `domain="IT"` (Amazon.it). Hierarchy `_BUYBOX_SOURCE_HIERARCHY=("BUY_BOX_SHIPPING","NEW","AMAZON")` modulo-level + helper `_last_valid_value(arr)` (skip None/NaN/-1/negativi, R-01 pulizia time-series). `bsr` parsing da `data['SALES']`. `fee_fba_eur=None` hardcoded (decisione alpha''). Errori adapter (network/shape) -> `KeepaTransientError` -> retry. + costante `DEFAULT_KEEPA_DOMAIN="IT"`. + import top-level `math`, `Decimal`, `Any`. + `Iterable` in TYPE_CHECKING. |
| `tests/integration/test_live_keepa.py` | nuovo | 4 test integration live (skip module-level se `TalosSettings().keepa_api_key is None`): `query()` -> buybox/bsr popolati, fee_fba_eur=None / `fetch_buybox` -> Decimal > 0 / `fetch_bsr` -> int > 0 / `fetch_fee_fba` -> `KeepaMissError` (decisione alpha''). Range plausibile €400-1500 per Galaxy S24. Quota consumata ~4 token. |
| `tests/unit/test_keepa_client.py` | modificato | Rimosso `test_default_factory_query_raises_not_implemented` (skeleton non piu' esistente; copertura live nei nuovi integration). Rimosso import `_LiveKeepaAdapter` non piu' usato. Sostituito con commento esplicativo che rinvia ai test integration live (pattern coerente CHG-011/012). |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **693
PASS** (567 unit/governance/golden + 126 integration; era 690, netto
+3: -1 legacy unit rimosso, +4 nuovi live integration).

## Why

Il Leader ha consegnato la private Keepa API key. CHG-014 ha attivato
il caricamento ergonomico via `.env`. Mancava la ratifica del **mapping
dei dati Keepa reali** in `_LiveKeepaAdapter.query()`, che dal
CHG-001 era skeleton `NotImplementedError` esplicito.

Il diagnostic empirico ha rivelato discrepanze rilevanti rispetto
alle assunzioni teoriche di CHG-001:

1. `BUY_BOX_SHIPPING` (csv[18]) NON presente sul piano subscription
   corrente. Decisione iniziale "A=BUY_BOX_SHIPPING" non applicabile.
2. `pickAndPackFee` di Keepa misura un sottoinsieme della commissione
   FBA, non la commissione totale stimata da L11b. Sostituzione
   diretta avrebbe rotto la semantica del modello finanziario del
   Leader. Pattern "Adapter dumb reporter, formula L11b unica
   source-of-truth" preservato.

Modifiche al canale 1:
- Caller (`KeepaClient.fetch_*`) gia' progettato per `KeepaMissError`
  + telemetria `keepa.miss` (CHG-005). Tutto continua a funzionare:
  `fee_fba` ora SEMPRE miss → SEMPRE `keepa.miss` event → caller
  fallback `fee_fba_manual` (architettura CHG-006 fallback chain
  pronta).
- `lookup_product` (CHG-006) e tutti i suoi consumer
  (`lookup_products` CHG-009, `acquire_and_persist` CHG-010) sono
  invarianti: ricevono `KeepaProduct` con shape gia' nota, comportamento
  identico al pattern mock-only di Fase 1 Path B.

### Decisioni di design

1. **Lazy init `keepa.Keepa(api_key)`**: il client `_LiveKeepaAdapter`
   non istanzia la libreria al `__init__`. Pattern coerente con
   `_PlaywrightBrowserPage` (CHG-012). Test unit non pagano
   overhead network (anche se non chiamano `query()`, `KeepaClient`
   default factory invocava `_LiveKeepaAdapter(key)`); test live
   pagano solo al primo `query()` reale.

2. **Lazy import `keepa`**: `import keepa` in `_ensure_api()`,
   non top-level. Razionale: la libreria community `keepa` fa side
   effects all'import (logging config, requests session) — meglio
   ritardare al primo uso. Coerente con `import pytesseract`/import
   playwright in CHG-011/012.

3. **`domain="IT"` di default**: il Leader scaler 500k opera su
   Amazon.it. Future operatività multi-marketplace richiedera'
   parametro per ASIN o per sessione (scope CHG futuro).

4. **`_BUYBOX_SOURCE_HIERARCHY` come tuple modulo-level**: documenta
   l'ordine di preferenza in modo testuale, evita stringhe inline,
   facilmente estendibile (es. quando Leader upgradera' piano e
   `BUY_BOX_SHIPPING` apparira' empirically).

5. **`_last_valid_value` come helper modulo-level (no membro)**:
   pure function (input -> output), testabile in isolamento, riusabile
   se future implementazioni Keepa richiedessero parsing CSV grezzo
   (oggi usiamo `data` dict gia' parsato dalla libreria).

6. **Sentinel `-1` filtrato come "out of stock"**: convenzione Keepa
   documentata. Per i prezzi, `-1` significa "Amazon non disponibile
   in quel momento". Iteriamo a ritroso e prendiamo il primo numero
   reale finito >= 0.

7. **`Exception` generica in `query()` -> `KeepaTransientError`**:
   la libreria community puo' sollevare un range ampio
   (`requests.RequestException`, `ConnectionError`, `JSONDecodeError`,
   `KeyError` in caso di response shape inattesa). Catch generico +
   wrap in `KeepaTransientError` permette al `KeepaClient` di
   ritentare via `tenacity`. R-01 NO SILENT DROPS preservato:
   eccezioni non perse (chained via `from exc`).

8. **`asin mismatch` -> `KeepaTransientError`**: se l'API ritorna
   un asin diverso da quello richiesto (raro flap), trattiamolo
   come transient e ritentiamo. Caller riceve eventuale fallimento
   pulito dopo retry esauriti.

9. **`fee_fba_eur=None` hardcoded (no flag)**: decisione alpha''
   non e' parametrizzata in CHG-015. Estensione via flag (`enable_keepa_fee_fba`)
   sarebbe scope futuro se Leader cambiasse policy (es. piano
   subscription espone "Fee FBA totale" invece che pick&pack).

### Out-of-scope

- **`referralFeePercent` top-level**: il response Keepa espone
  questo campo (es. `7` per Galaxy S24). Bonus L12: leggibile
  senza scraping, potrebbe automatizzare il populating di
  `config_overrides` (referral_fee per categoria, CHG-051).
  Scope CHG futuro dedicato (es. CHG-016 "Keepa-driven config
  overrides bootstrap").
- **`title` da Keepa**: il response include `title` top-level.
  Oggi `lookup_product` lo prende dallo scraper se Keepa miss
  o dal Keepa adapter (NON estende title da Keepa in CHG-015,
  resta scope `_LiveKeepaAdapter` per i 3 campi storici buybox/bsr/fee).
  Scope CHG futuro se serve title da Keepa per matching.
- **Multi-ASIN batch query**: oggi `query(asin)` chiama
  `api.query([asin])`. La libreria supporta liste (`api.query([a1,a2,...])`).
  Ottimizzazione token (1 token per ASIN ~= 1 token per N ASIN
  in batch?) scope CHG futuro se profiling lo richiede.
- **Cache locale (sqlite)**: D1.a ratificata Leader 2026-04-30 sera
  = solo cache Streamlit `@st.cache_data`. Nessun layer locale
  qui dentro. Scope futuro se quota diventa stretta.
- **Stress test rate limiter contro API reale**: i test rate
  limiter (CHG-001) sono mock-only, sufficienti. Test live in CHG-015
  scope = ratificare mapping dati, non rate limit.
- **Telemetria `keepa.cache_hit` / `keepa.fetch_success`**: scope
  futuro errata catalogo ADR-0021 quando la pipeline e' sotto carico
  e si vuole monitorare hit rate.

## How

### `_LiveKeepaAdapter.query` (highlight)

```python
def query(self, asin: str) -> KeepaProduct:
    api = self._ensure_api()
    try:
        products = api.query([asin], domain=self._domain)
    except Exception as exc:
        msg = f"Keepa API call failed for {asin}: {type(exc).__name__}: {exc}"
        raise KeepaTransientError(msg) from exc

    if not products:
        msg = f"Keepa returned empty product list for {asin}"
        raise KeepaTransientError(msg)
    product = products[0]
    if product.get("asin") != asin:
        raise KeepaTransientError(f"Keepa ASIN mismatch ...")

    data = product.get("data") or {}
    buybox_eur = None
    for source in _BUYBOX_SOURCE_HIERARCHY:
        value = _last_valid_value(data.get(source))
        if value is not None:
            buybox_eur = Decimal(str(value))
            break

    bsr_value = _last_valid_value(data.get("SALES"))
    bsr = int(bsr_value) if bsr_value is not None else None

    return KeepaProduct(
        asin=asin,
        buybox_eur=buybox_eur,
        bsr=bsr,
        fee_fba_eur=None,  # alpha''
    )
```

### `_last_valid_value` (highlight)

```python
def _last_valid_value(arr):
    if arr is None:
        return None
    for v in reversed(list(arr)):
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f) or f < 0:
            continue
        return f
    return None
```

### Test plan eseguito (live, ~4 token consumati)

- `test_live_query_returns_buybox_bsr_and_fee_none`: query reale ->
  `buybox_eur > 0` (range €400-1500 plausible Galaxy S24), `bsr > 0`,
  **`fee_fba_eur is None`** (decisione alpha'').
- `test_live_fetch_buybox_returns_decimal`: `KeepaClient.fetch_buybox`
  -> Decimal positivo.
- `test_live_fetch_bsr_returns_int`: `KeepaClient.fetch_bsr` -> int
  positivo.
- `test_live_fetch_fee_fba_raises_keepa_miss`: `fetch_fee_fba` ->
  `KeepaMissError` con `field="fee_fba"` (verifica alpha'' end-to-end
  passando per il `fetch_*` -> `_emit_miss` -> `keepa.miss` event ->
  raise).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (49 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **567 PASS** (era 568, netto -1 per rimozione legacy `test_default_factory_query_raises_not_implemented`) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **126 PASS** (era 122, +4 nuovi live keepa) |
| Diagnostic Keepa schema | `uv run python -c "import keepa; ..."` | Confermato `BUY_BOX_SHIPPING` assente sul piano, `NEW=€549` per Galaxy S24, `pickAndPackFee=410` cents, `referralFeePercent=7` |

**Rischi residui:**
- **Plan upgrade Leader**: se Leader upgradera' piano e
  `BUY_BOX_SHIPPING` diventera' disponibile, `_BUYBOX_SOURCE_HIERARCHY`
  preferira' automaticamente quel source senza modifiche di codice.
  Backward compat strict.
- **Quota costo per ASIN**: 1 token per `query()`. La libreria community
  espone batch ma `_LiveKeepaAdapter.query` accetta singolo ASIN
  per ora. Scope futuro batch se profiling rivela bottleneck.
- **Domain hardcoded "IT"**: future Italia-only. Multi-marketplace
  scope futuro.
- **Errori `keepa.Keepa(...)` al primo lazy init**: se la key e'
  invalida o il server Keepa e' down, il primo `query()` solleva
  `KeepaTransientError` dopo retry esauriti. Caller (`lookup_product`)
  vede l'errore propagato (R-01 fail-now coerente).
- **Catch `Exception` generico**: necessario per la libreria
  community che non documenta esaustivamente le sue eccezioni.
  Mitigazione: chained via `from exc` -> stack trace preservato
  per diagnosi.
- **`pickAndPackFee` field NON usato**: documentato come scope
  decisione alpha''. Caller futuro che vuole comporre fee
  hybrid (es. CHG ipotetico con flag `use_keepa_fee=True`) ha
  field disponibile in response ma non parsato.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/keepa_client.py` ✓
  (area `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Wrapper isolato libreria community `keepa` dietro
    `KeepaApiAdapter` Protocol ✓
  - Canale 1 (Keepa primario) live ✓
  - Decisione D1 (CHG-001) preservata: rate limit + retry +
    R-01 invarianti
- **R-01 NO SILENT DROPS:** ✓ `KeepaProduct` con `None` -> caller
  emette `keepa.miss` (telemetria CHG-005) -> `KeepaMissError`
  esplicito. Errori network -> `KeepaTransientError` chained.
- **Test integration live + unit ridotti:** ✓ (ADR-0019 +
  ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** modifica skeleton
  esistente -> ADR-0017. Helper `_last_valid_value` privato
  modulo-level (non symbol pubblico).
- **Backward compat:** `KeepaApiAdapter` Protocol invariato;
  `KeepaProduct` invariata; `KeepaClient.fetch_*` API invariata.
  L'unica differenza comportamentale: `_LiveKeepaAdapter.query` ora
  ritorna risultato vero invece di `NotImplementedError`. Test
  unit di `KeepaClient` usano mock via `adapter_factory` (pattern
  ADR-0017) e non sono impattati. Caller `lookup_product` (CHG-006)
  riceve `KeepaProduct` con la stessa shape - comportamento
  identico al pattern mock di Fase 1.
- **Sicurezza:** la key e' caricata via `.env` -> `TalosSettings`
  (CHG-014). Non viene loggata, non viene serializzata. La key
  rimane esclusivamente sul disco locale del Leader (`.env`
  gitignored).
- **Impact analysis pre-edit:** GitNexus risk LOW
  (`_LiveKeepaAdapter` 0 caller upstream applicativi; modifica
  body interno, signature invariata). `KeepaClient.fetch_*`
  hanno contract invariato verso caller (CHG-006/009/010).

## Impact

- **Canale 1 live ratificato**: `_LiveKeepaAdapter` non e' piu'
  skeleton. Sblocca TEST-DEBT-004 (CHG-015 = quel CHG dichiarato
  in `STATUS.md` come "atteso post Keepa key").
- **Path B end-to-end con Keepa**: la fallback chain
  `lookup_product` (CHG-006) puo' ora chiamare Keepa live. Nello
  scenario "buy_box presente da Keepa NEW" + "BSR root da Keepa
  SALES" + "fee_fba via L11b manual fallback": tutto funziona end-to-end.
  Path B ora **non e' piu' "scraping-only"**, e' "Keepa primario +
  scraper complementare per BSR multi-livello". MVP target avanzato.
- **`pyproject.toml` invariato** (`keepa>=1.4` gia' dep CHG-001).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11 viventi).
  `keepa.miss` ora si attiva live per `fee_fba` (era dormiente
  effetto dello skeleton CHG-001).
- **Test suite cresce di +3 netto**: 693 PASS totali (era 690),
  -1 unit legacy + 4 integration live.
- **Quota Keepa consumata in CHG-015**: ~4 token (suite live).
  Il rate limiter di CHG-001 e' applicabile a runtime.
- **Pronto per integrazione `lookup_product` live end-to-end**
  (CHG-016): la chain `keepa -> scraper fallback -> ocr placeholder`
  diventa live al 100% e si possono aggiungere golden integration
  test "1-shot" stile CHG-013 (scraper) ma per Keepa+scraper
  combined.

## Refs

- ADR: ADR-0017 (canale Keepa, mapping ratificato), ADR-0014
  (mypy/ruff strict + lazy import pattern), ADR-0019 (test
  integration live skip-on-missing-secret), ADR-0021 (telemetria
  `keepa.miss` ora live attivata per `fee_fba`).
- Predecessori:
  - CHG-2026-05-01-001: `KeepaClient` skeleton + `_LiveKeepaAdapter`
    `NotImplementedError`.
  - CHG-2026-05-01-005: telemetria `keepa.miss` attivata.
  - CHG-2026-05-01-014: `TalosSettings.env_file=".env"` per
    caricamento Keepa key.
- Setup di sistema:
  - ✓ `TALOS_KEEPA_API_KEY` in `.env` locale (CHG-014)
  - ✓ Quota Keepa attiva (private API access)
- Decisioni Leader ratificate 2026-05-01 round 4 (post-diagnostic):
  - **A2** buy_box source hierarchy `BUY_BOX_SHIPPING -> NEW -> AMAZON`
  - **A** bsr source `data['SALES']`
  - **alpha''** fee_fba SEMPRE `KeepaMissError` (preserva L11b)
  - scope test ~4-6 token (consumati ~4)
- Sibling: CHG-2026-05-01-011 (`_LiveTesseractAdapter`),
  CHG-2026-05-01-012 (`_PlaywrightBrowserPage`).
- Memory: scope futuro `project_keepa_decisions_round4.md` se
  decisioni A2/A/alpha'' devono persistere (per ora documentate
  solo in change doc + docstring `_LiveKeepaAdapter`).
- Successore atteso: CHG-2026-05-01-016 (sblocco asin_resolver
  description→ASIN, oppure golden integration test live combined
  Keepa+scraper).
- Commit: `bb5a9cd`.
