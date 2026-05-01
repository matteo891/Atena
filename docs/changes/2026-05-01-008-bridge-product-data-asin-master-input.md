---
id: CHG-2026-05-01-008
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 2 attiva, Path B target)
status: Draft
commit: TBD
adr_ref: ADR-0017, ADR-0015, ADR-0014, ADR-0019
---

## What

Bridge architetturale + sentinella e2e che chiude il loop "acquisizione →
anagrafica DB" senza live adapters. Due deliverable accoppiati:

1. **`build_asin_master_input(product_data, *, brand, enterprise=False,
   samsung_entities=None, title_fallback=None, category_node=None)`**
   in `src/talos/extract/asin_master_writer.py`. Converte un
   `ProductData` (output `lookup_product` CHG-006) in
   `AsinMasterInput` (input `upsert_asin_master` CHG-005). Mapping:
   - `asin/title` ← `product_data` (con `title_fallback` se title None;
     `ValueError` se entrambi None — R-01 NO SILENT DROPS, `AsinMaster.title`
     e' NOT NULL)
   - `brand/enterprise/category_node` ← parametri caller (non derivabili
     da `ProductData` ne' da `KeepaProduct`/`ScrapedProduct` correnti)
   - `model/rom_gb/ram_gb/connectivity/color_family` ← da
     `samsung_entities` se fornito (output `SamsungExtractor.parse_title`);
     altrimenti `None` (la merge `COALESCE` D5.b di `upsert_asin_master`
     preserva eventuali valori esistenti).

2. **Sentinella e2e** `tests/integration/test_lookup_to_asin_master.py`
   con 2 test integration su Postgres reale, mock-only sui canali esterni:
   - `test_e2e_lookup_to_asin_master_round_trip`: mock `KeepaApiAdapter`
     ritorna `KeepaProduct` full + mock `BrowserPageProtocol` ritorna
     titolo Samsung realistico → `lookup_product` → `parse_title` →
     `build_asin_master_input` → `upsert_asin_master` → query DB verifica
     round-trip su `AsinMaster` (10 colonne).
   - `test_e2e_second_pass_merges_via_coalesce`: secondo upsert con
     titolo non-Samsung (parse_title produce entita' parziali) +
     `samsung_entities=None` esplicito → merge `COALESCE` preserva
     model/ram/rom/color_family/connectivity esistenti, title overwrite
     (NOT NULL); dimostra che la chain rispetta D5.b in produzione.

Lo scenario simula il flusso che eseguira' l'integratore Fase 3 quando
i live adapter saranno disponibili. Sostituendo gli adapter mock con
`_LiveKeepaAdapter` + `_PlaywrightBrowserPage` + `_LiveTesseractAdapter`
post Fase 2, il codice del bridge non cambia.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/asin_master_writer.py` | modificato | + import condizionale `ProductData`, `SamsungEntities` (TYPE_CHECKING). + `build_asin_master_input(product_data, *, brand, enterprise=False, samsung_entities=None, title_fallback=None, category_node=None) -> AsinMasterInput`. Logica: title precedence `product_data.title` > `title_fallback` > `ValueError`; samsung_entities=None → tutti i nullable a None; `enterprise` param prevale su `samsung_entities.enterprise` (caller esplicito vince). `noqa: PLR0913` motivato in commento (raggruppare in dataclass intermedio sarebbe wrapper inerte). |
| `src/talos/extract/__init__.py` | modificato | + re-export `build_asin_master_input` in `__all__` ordinato. |
| `tests/unit/test_build_asin_master_input.py` | nuovo | 8 test puri (mock-only, no DB): mapping core (4: title da product_data / samsung_entities popola nullable / enterprise param wins / category_node passa); title fallback (3: usa fallback se product_title None / raise se entrambi None / product_title precede fallback); edge case (1: samsung_entities parziale lascia altri None). |
| `tests/integration/test_lookup_to_asin_master.py` | nuovo | 2 test integration (Postgres reale + mock chains): round-trip e2e completo (lookup → parse_title → bridge → upsert → query) + second-pass merge `COALESCE` con samsung_entities=None preserva valori esistenti. Fixture `selectors.yaml` minimale via `tmp_path`. Cleanup ASIN test pre/post. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**651 PASS** (544 unit/governance/golden + 107 integration; era 641,
+10 totali: +8 unit + +2 integration).

## Why

I CHG-001..007 hanno introdotto primitive isolate (KeepaClient,
AmazonScraper, OcrPipeline, SamsungExtractor, asin_master_writer,
fallback_chain `lookup_product`, kwarg `asin` su match). **Nessuna
sentinella** dimostrava che le primitive si componessero in un
flusso utilizzabile end-to-end.

Senza il bridge `ProductData → AsinMasterInput`, l'integratore Fase 3
avrebbe dovuto scrivere un mapping ad hoc inline; questo:
- avrebbe duplicato la logica di "title fallback" in piu' punti (con
  rischio di silent default a stringa vuota, violazione R-01);
- avrebbe lasciato implicita la decisione "enterprise dal caller, non
  dal NLP" (il `samsung_entities.enterprise` esiste ma e' poco
  affidabile in un titolo Amazon — il caller fornitore e' la fonte
  canonica);
- non avrebbe avuto un test e2e che verifica il merge `COALESCE`
  funzioni davvero in catena (i test CHG-005 verificavano UPSERT
  isolato, non il flusso integrato).

La sentinella e2e mock-only e' anche un *punto di ancoraggio* per
Fase 3: quando i live adapter sostituiranno i mock, basta swappare
le factory; il flusso testato resta lo stesso.

### Decisioni di design

1. **`title_fallback` parametro esplicito (non default `""`)**:
   R-01 NO SILENT DROPS. `AsinMaster.title` e' NOT NULL: il caller
   deve fornire un valore consapevolmente, non subire un default
   silenzioso. `ValueError` se entrambi None e' fail-fast.

2. **`enterprise` param prevale su `samsung_entities.enterprise`**:
   il caller (CFO o integratore Fase 3) conosce `enterprise` dal
   listino fornitore, NON dal titolo Amazon scrapato. NLP su titolo
   Amazon e' approssimato e Samsung Enterprise SKU sono dual
   (consumer + enterprise spesso indistinguibili a livello listing).
   La fonte canonica e' il listino fornitore.

3. **`samsung_entities.color → color_family` mapping diretto**:
   pattern coerente con il test integration esistente CHG-005
   (`color_family="Titanium Black"`). La distinzione semantica
   "color vs color_family" del modello DB e' un dettaglio di
   schema; il bridge non re-classifica (es. "Titanium Black" →
   famiglia "Black"). Scope futuro se servisse aggregazione
   per famiglie.

4. **`category_node` mai derivato dal bridge**: richiede mapping
   Amazon Browse Node (es. `2422156011`) al sistema interno
   ("electronics/smartphones"). Fuori scope CHG-008. Caller
   (CFO o integratore) lo passa esplicitamente.

5. **`samsung_entities=None` ammesso (no-op sui nullable)**: caller
   in early-stage (es. solo lookup Keepa, no scraper Playwright,
   no parse_title) puo' costruire un input minimo brand+title.
   Successivi upsert con samsung_entities popolato faranno merge
   `COALESCE` (D5.b: input non-null vince, null preserva). Questo
   incarna il "apprendimento incrementale" del modello D5.b.

6. **Bridge function-level (non metodo di una classe)**: pattern
   coerente con `upsert_asin_master` (anche lui top-level
   function). Il bridge e' stateless, niente da incapsulare.

7. **`# noqa: PLR0913` motivato**: 6 parametri (1 posizionale + 5
   kwarg) sono il minimo necessario per coprire i campi NOT NULL
   di `AsinMasterInput` + le 2 fonti di title (product_data,
   fallback) + la fonte di entita' brand (samsung_entities). Un
   wrapper dataclass intermedio sarebbe scaffold inerte.

8. **Sentinella e2e in `tests/integration/`** (non `tests/golden/`):
   richiede DB Postgres reale (`pg_engine` fixture). I test golden
   sono byte-exact su pipeline pure (no DB); la sentinella richiede
   round-trip ORM. Pattern coerente con `test_asin_master_writer.py`
   esistente (cleanup pre/post via `DELETE FROM asin_master WHERE
   asin = :asin`).

### Out-of-scope

- **Bridge `ProductData → SessionInput row`**: caller diverso, scope
  futuro (sessione orchestratore Path B end-to-end).
- **Bridge `lookup_product` integrato in `run_session`**: oggi
  `run_session` riceve listino raw pre-acquisito. Acquisizione + run
  e' scope di un orchestratore "estended" futuro.
- **Mapping Amazon Browse Node → `category_node`**: caller param,
  scope futuro.
- **`samsung_entities.enterprise` letto dal bridge**: oggi ignorato.
  Caller futuro che voglia override-ratificato puo' modificare la
  signature.
- **Bulk bridge (lista di ProductData → lista AsinMasterInput)**:
  caller chiama in loop. Quando il volume sara' significativo
  (es. acquisizione batch 500 ASIN), si potra' aggiungere un
  helper `bulk_build` con validazione fail-fast collettiva.
- **Telemetria nuova**: nessun nuovo evento canonico. Il bridge e'
  pura conversione, non produce segnale strutturato osservabile
  oltre quello gia' emesso da `lookup_product` (niente, e'
  orchestrazione) e `SamsungExtractor.match` (kill_switch su R-05).

## How

### `build_asin_master_input` (highlight)

```python
def build_asin_master_input(  # noqa: PLR0913
    product_data: ProductData,
    *,
    brand: str,
    enterprise: bool = False,
    samsung_entities: SamsungEntities | None = None,
    title_fallback: str | None = None,
    category_node: str | None = None,
) -> AsinMasterInput:
    title = product_data.title if product_data.title is not None else title_fallback
    if title is None:
        raise ValueError(...)
    return AsinMasterInput(
        asin=product_data.asin,
        title=title,
        brand=brand,
        enterprise=enterprise,
        model=samsung_entities.model if samsung_entities else None,
        ...
        category_node=category_node,
    )
```

### Sentinella e2e (highlight)

```python
keepa = KeepaClient(api_key="test", adapter_factory=lambda _: _KeepaAdapter(...))
scraper = AmazonScraper(selectors_path=selectors_yaml)
page = _ScrapedPage(title="Samsung Galaxy S24 12GB RAM 256GB Titanium Black 5G")

product_data = lookup_product(_TEST_ASIN, keepa=keepa, scraper=scraper, page=page)
entities = SamsungExtractor().parse_title(product_data.title)
inp = build_asin_master_input(
    product_data, brand="Samsung", samsung_entities=entities,
    category_node="electronics/smartphones",
)
upsert_asin_master(orm_session, data=inp)
orm_session.commit()

row = orm_session.get(AsinMaster, _TEST_ASIN)
assert row.model == "Galaxy S24"
assert row.color_family == "Titanium Black"
# ... full round-trip verification
```

### Test plan eseguito

8 unit test in `tests/unit/test_build_asin_master_input.py`:

- 2 mapping core (product_title / samsung_entities popola nullable)
- 1 enterprise param wins
- 1 category_node passa
- 1 title_fallback usato quando product_title None
- 1 ValueError quando entrambi None
- 1 product_title precede fallback
- 1 samsung_entities parziale (solo model) -> altri None

2 integration test in `tests/integration/test_lookup_to_asin_master.py`:

- round-trip completo (lookup → parse → bridge → upsert → query)
- second-pass merge COALESCE preserva valori esistenti

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/extract/asin_master_writer.py src/talos/extract/__init__.py tests/unit/test_build_asin_master_input.py tests/integration/test_lookup_to_asin_master.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_build_asin_master_input.py tests/integration/test_lookup_to_asin_master.py` | 0 issues (50 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **544 PASS** (era 536, +8) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **107 PASS** (era 105, +2) |

**Rischi residui:**
- **`enterprise` param obbligatorio? oggi default False**: se il
  caller dimentica di passarlo, l'ASIN viene marcato come consumer.
  Per Samsung il SKU enterprise e' un superset; la sottostima e'
  conservativa. Caller vigile passa `enterprise=True` esplicito
  per i SKU dedicati.
- **`title_fallback` non valida lunghezza**: pattern coerente con
  il modello (NOT NULL ma no length check applicativo lato bridge).
  Validazione di formato (es. lunghezza max) e' demandata al DB.
- **`samsung_entities` colore "exotic"**: rapidfuzz puo' produrre
  colori non perfettamente corrispondenti al `color_family` storico
  in DB. Su seconda upsert, il `COALESCE(EXCLUDED.color_family,
  asin_master.color_family)` overwriterebbe (input non-null
  vince). Caller futuro che voglia preservare il color_family
  storico deve passare `samsung_entities=None` (test
  `test_e2e_second_pass_merges_via_coalesce` documenta questo
  pattern).

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/asin_master_writer.py`
  + test sotto `tests/unit/` e `tests/integration/` ✓ (aree
  consentite ADR-0013).
- **ADR-0017 vincoli rispettati:**
  - Nessun nuovo wrapper di libreria esterna (solo composizione) ✓
  - R-01 NO SILENT DROPS: `ValueError` su title None senza
    fallback ✓
- **ADR-0015 vincoli rispettati:**
  - UPSERT pattern preservato (solo nuovo input builder, writer
    invariato) ✓
  - D5.b merge `COALESCE` testato meccanicamente nel second-pass ✓
- **Test unit + integration:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `build_asin_master_input`
  → ADR-0017 (modulo coperto) + ADR-0015 (output e' input writer
  modello DB).
- **Backward compat:** modifica additiva, niente break sui caller
  esistenti (i test CHG-005 `test_asin_master_writer.py` passano
  invariati).
- **Impact analysis pre-edit:** detect_changes 0 affected processes,
  risk LOW. `AsinMasterInput` toccato solo per import di tipo (no
  modifica a campi).

## Impact

- **Loop "io_/ → extract/ → DB" chiuso a livello primitive**:
  4 moduli compongono in un flusso testato e2e.
- **Fase 1 Path B avanzamento**: 3/N CHG (CHG-006 fallback chain +
  CHG-007 asin kwarg + CHG-008 bridge + sentinella). Catena CHG
  2026-05-01: 001..008.
- **`pyproject.toml` invariato** (no nuove deps).
- **`extract/__init__.py` esteso**: `build_asin_master_input`
  esposto come API pubblica del package.
- **Sentinella e2e come "ancora di test" per Fase 3**: l'integratore
  live sostituira' i mock con `_LiveKeepaAdapter` + `_LivePlaywright`
  + `_LiveTesseractAdapter`; la sentinella attuale resta valida
  perche' testa il flusso con mock e non depende dai live.
- **R-01 NO SILENT DROPS rinforzato** sul `title`: i caller non
  possono creare `AsinMasterInput` con title fittizio per accident.

## Refs

- ADR: ADR-0017 (canale `extract/`), ADR-0015 (asin_master schema +
  D5.b merge), ADR-0014 (mypy/ruff strict), ADR-0019 (test pattern).
- Predecessori CHG: CHG-2026-05-01-005 (`upsert_asin_master`),
  CHG-2026-05-01-006 (`lookup_product`), CHG-2026-05-01-007
  (`SamsungExtractor.match` asin kwarg).
- Pattern fixture integration: `tests/integration/test_asin_master_writer.py`
  (cleanup pre/post via DELETE WHERE asin).
- Memory: `project_io_extract_design_decisions.md` (D5 ratificata
  "default", merge COALESCE).
- Successore atteso (Fase 3): integratore live che sostituira' i
  mock della sentinella e2e con `_LiveKeepaAdapter` +
  `_PlaywrightBrowserPage` + `_LiveTesseractAdapter`.
- Commit: TBD.
