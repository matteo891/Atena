---
id: CHG-2026-05-01-010
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 2 attiva, Path B target — chiusura Fase 1)
status: Draft
commit: e425d14
adr_ref: ADR-0017, ADR-0015, ADR-0014, ADR-0019
---

## What

Inaugura `src/talos/extract/acquisition.py` con
`acquire_and_persist(asin_list, *, db, keepa, brand,
enterprise=False, scraper=None, page=None, extractor=None,
title_fallbacks=None, category_node=None) -> list[str]`.
Orchestratore Fase 1 Path B che chiude il flusso "input N ASIN
→ output N anagrafiche persistite su `asin_master`" componendo
le primitive dei CHG-006..009.

Pipeline per ogni ASIN:

1. `lookup_products` (CHG-009) batch → `list[ProductData]`
2. Per ogni `ProductData`:
   a. Se `extractor` fornito e `product_data.title` non None →
      `extractor.parse_title(title)` → `SamsungEntities`;
      altrimenti `entities = None` (merge `COALESCE` D5.b
      preservera').
   b. `build_asin_master_input(product_data, brand=..., ...,
      samsung_entities=entities, title_fallback=fallbacks.get(asin),
      category_node=...)` (CHG-008) → `AsinMasterInput`. Solleva
      `ValueError` se `product_data.title is None` e
      `title_fallbacks[asin]` assente (R-01 NO SILENT DROPS).
   c. `upsert_asin_master(db, data=input)` (CHG-005) → riga
      `asin_master` UPSERT.
3. Ritorna `list[str]` ASIN persistiti in ordine.

**Pattern Unit-of-Work**: il caller controlla commit/rollback;
l'orchestratore esegue solo `INSERT ... ON CONFLICT DO UPDATE`
ma NON chiama `db.commit()`. Coerente con `save_session_result`
(CHG-2026-04-30-042).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/acquisition.py` | nuovo | `acquire_and_persist(...)`. 7 hint indipendenti (asin_list + db + keepa + brand + 6 opzionali). `noqa: PLR0913` motivato. Pipeline lineare: `lookup_products` → loop con `parse_title` opzionale → `build_asin_master_input` → `upsert_asin_master`. Empty list = no-op (`lookup_products([])` = `[]`). |
| `src/talos/extract/__init__.py` | modificato | + re-export `acquire_and_persist`. |
| `tests/integration/test_acquire_and_persist.py` | nuovo | 5 test integration (Postgres reale + mock chains): empty list no-op / batch 3 ASIN round-trip (Galaxy S24/A55/Z Fold5, modelli/ram/rom/colore corretti) / title_fallback usato quando scrape miss / `ValueError` su title None senza fallback (rollback verificato: nulla persistito) / no-extractor lascia campi nullable a None. |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | + riga `src/talos/extract/acquisition.py`. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**660 PASS** (548 unit/governance/golden + 112 integration; era
655, +5 nuovi integration).

## Why

I CHG-006..009 hanno costruito le primitive del flusso
acquisizione (lookup_product/lookup_products) +
estrazione/match (SamsungExtractor + asin kwarg) +
write (upsert_asin_master) + bridge (build_asin_master_input).
Mancava un **orchestratore unico** che dimostri come si
compongono in produzione.

`acquire_and_persist` chiude la Fase 1 Path B:
- Il caller (CFO con CSV manuale o, in Fase 3, integratore live)
  invoca un'unica funzione, non una catena di 4-5 chiamate
  intrecciate.
- La firma esplicita quali parametri sono necessari (Keepa
  obbligatorio, scraper/page/extractor opzionali) e quali
  caller-side decisions sono attese (brand, enterprise,
  title_fallbacks, category_node).
- I test sentinella `test_acquire_and_persist_*` ancorano il
  flusso completo a 5 scenari: la suite resta valida quando
  Fase 3 sostituira' i mock con `_LiveKeepaAdapter` +
  `_PlaywrightBrowserPage` + `_LiveTesseractAdapter`.

### Decisioni di design

1. **Funzione top-level (non classe)**: pattern coerente con
   `upsert_asin_master`, `lookup_product`, `lookup_products`.
   Stateless: niente stato accumulato fra chiamate. Caller
   passa `keepa`/`scraper`/`page` gia' configurati.

2. **Pattern Unit-of-Work (no commit interno)**: il caller
   gestisce la transazione. Permette pattern "una sessione DB
   per batch" o "una sessione DB per ASIN" (es. retry per-ASIN
   senza rollback collettivo). Coerente con tutti i repository
   esistenti.

3. **`extractor` opzionale**: Path A (CFO con CSV manuale che
   contiene gia' brand/model/ram/...) puo' chiamare
   `acquire_and_persist` SENZA extractor → tutti i campi
   nullable a None → la merge `COALESCE` di `upsert_asin_master`
   preserva eventuali valori esistenti per l'ASIN, oppure
   inserisce con None che poi un secondo upsert con
   `samsung_entities` valorizzati popolera' (apprendimento
   incrementale).

4. **`title_fallbacks: dict[str, str] | None = None`**: il
   caller fornisce un mapping ASIN → titolo fornitore *solo
   per gli ASIN per cui necessario*. Pattern coerente con
   "salvataggio progressivo": gli ASIN con scrape successo non
   richiedono fallback. La signature non costringe a fornire
   fallback per TUTTI gli ASIN.

5. **`category_node` per-batch (non per-ASIN)**: scelta
   conservativa di scope. Tutti gli ASIN del batch ricevono
   lo stesso `category_node` (caso comune: batch monocategoria
   "smartphones"). Caller che vuole categorie diverse fa piu'
   chiamate con `acquire_and_persist` separate. Se in futuro
   serve mapping per-asin, aggiungere `category_nodes:
   dict[str, str]` come parametro additivo.

6. **`brand`/`enterprise` per-batch**: stessa logica di
   `category_node`. Un batch di ASIN Samsung consumer e' la
   norma; mix consumer+enterprise sono caso d'uso futuro.

7. **Fail-fast totale**: `ValueError` sul primo title None
   senza fallback **interrompe** il batch (gli ASIN successivi
   non vengono processati). Razionale: l'errore e' un signal
   "configurazione caller incompleta", non un problema di un
   singolo ASIN; conviene fail-fast per non confondere il
   caller con esecuzione parziale. Caller che vogliono
   "skip-on-error" gestiscono try/except per asin singolo.

### Out-of-scope

- **Telemetria nuova** (`acquisition.completed`, `acquisition.batch_summary`):
  scope futuro errata catalogo ADR-0021 quando il flusso e'
  in produzione e si vorra' osservabilita' aggregata.
- **Cache di `asin_master`**: l'`@st.cache_data` di Streamlit
  (ADR-0016) non si applica al write. Eventuale cache di
  letture batch (es. ASIN gia' visti recentemente) e' scope
  futuro.
- **Concurrency**: `lookup_products` e' sequenziale (CHG-009);
  l'orchestratore eredita la sequenzialita'. Async/threading
  e' decisione Leader futura.
- **Retry per-asin con backoff**: il rate-limit Keepa e' gia'
  hard via `pyrate-limiter`; transient errors sono retry-ati
  internamente da `KeepaClient`. Errori applicativi (es.
  IntegrityError DB) propagano per visibilita'.
- **Bridge a `SessionInput`**: scope CHG futuro (orchestratore
  "estended" che acquisisce + esegue `run_session`).

## How

### `acquire_and_persist` (highlight)

```python
def acquire_and_persist(
    asin_list: list[str],
    *,
    db: Session,
    keepa: KeepaClient,
    brand: str,
    enterprise: bool = False,
    scraper: AmazonScraper | None = None,
    page: BrowserPageProtocol | None = None,
    extractor: SamsungExtractor | None = None,
    title_fallbacks: dict[str, str] | None = None,
    category_node: str | None = None,
) -> list[str]:
    products = lookup_products(asin_list, keepa=keepa, scraper=scraper, page=page)
    fallbacks = title_fallbacks or {}
    persisted: list[str] = []
    for product_data in products:
        entities = (
            extractor.parse_title(product_data.title)
            if extractor is not None and product_data.title is not None
            else None
        )
        inp = build_asin_master_input(
            product_data,
            brand=brand,
            enterprise=enterprise,
            samsung_entities=entities,
            title_fallback=fallbacks.get(product_data.asin),
            category_node=category_node,
        )
        upsert_asin_master(db, data=inp)
        persisted.append(product_data.asin)
    return persisted
```

### Test plan eseguito

5 test integration in `tests/integration/test_acquire_and_persist.py`:

- `test_acquire_and_persist_empty_list_is_noop`: empty input → []
  ritorna, mock keepa configurato per KeyError su qualunque
  query non viene chiamato.
- `test_acquire_and_persist_batch_round_trip`: 3 ASIN
  (B0ACQ0001..003) con titoli Samsung realistici (Galaxy S24,
  A55, Z Fold5). Verifica round-trip ORM su tutti e 3 (asin,
  brand, model, ram_gb, rom_gb, color_family, connectivity,
  category_node).
- `test_acquire_and_persist_uses_title_fallback_when_scrape_misses`:
  scrape miss su B0ACQ0001 + `title_fallbacks={asin:
  "Listino..."}` → riga persistita con title fallback.
- `test_acquire_and_persist_raises_when_no_title_and_no_fallback`:
  scrape miss + nessun fallback → `ValueError` raise; rollback
  esplicito + verifica nulla persistito.
- `test_acquire_and_persist_without_extractor_leaves_nullable_fields_none`:
  ASIN con title da scrape + extractor=None → solo title/brand
  popolati, model/ram/rom/color/connectivity tutti None.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/extract/acquisition.py src/talos/extract/__init__.py tests/integration/test_acquire_and_persist.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/integration/test_acquire_and_persist.py` | 0 issues (50 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **548 PASS** (invariato; nessun unit nuovo, l'orchestratore e' testato a livello integration) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **112 PASS** (era 107, +5) |

**Rischi residui:**
- **Whitelist `models_5g` mismatch literal**: il test
  `test_batch_round_trip` ha rivelato che la whitelist usa
  "Galaxy Z Fold5" (no spazio) mentre il titolo di mercato
  spesso usa "Z Fold 5". Il test usa la formula whitelist; nei
  dati reali Fase 3 occorrera' o estendere la whitelist con
  varianti, o aggiungere un normalizzatore `_normalize_model_string`
  in `SamsungExtractor`. Documentato come scope CHG futuro.
- **Errore di un solo ASIN abortisce il batch**: pattern
  "fail-fast" scelto. Se la produzione mostra che un singolo
  ASIN problematico interrompe batch grandi, il pattern andra'
  rivisto (es. "skip-on-error con error log"). Per ora la
  filosofia R-01 dell'ADR-0017 favorisce fail-fast.
- **`brand` per-batch**: caller con mix brand passa
  `acquire_and_persist` separate. Pattern futuro: dispatch su
  brand auto-detected.

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/acquisition.py`
  ✓ (area `extract/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Composizione esplicita Keepa primario + Scraper fallback
    + estrattore Samsung (tutto via primitive esistenti) ✓
  - R-01 NO SILENT DROPS: `ValueError` fail-fast su title None
    senza fallback ✓
  - Pattern Unit-of-Work (caller commits) ✓
- **ADR-0015 vincoli rispettati:**
  - `upsert_asin_master` invocato senza modifica (UPSERT
    atomico + merge `COALESCE` D5.b preservato) ✓
- **Test integration sotto `tests/integration/`:** ✓
  (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:**
  `acquire_and_persist` → ADR-0017 (orchestrazione canale
  acquisizione) + ADR-0015 (output writer modello DB).
- **Backward compat:** modulo nuovo, niente break.
- **Impact analysis pre-edit:** orchestratore di primitive,
  zero caller esistenti.

## Impact

- **🎯 Fase 1 Path B CHIUSA**: 5/5 CHG (CHG-006 fallback chain
  + CHG-007 asin kwarg + CHG-008 bridge + sentinella e2e
  + CHG-009 lookup_products + CHG-010 acquire_and_persist).
- **`pyproject.toml` invariato** (no nuove deps).
- **`extract/` package esteso**: 4 moduli (`samsung`,
  `samsung_whitelist.yaml`, `asin_master_writer`,
  `acquisition`). API pubblica completa per il flusso
  acquisizione.
- **Pronto per Fase 2**: tutto il valore architetturale
  producibile senza setup di sistema e' chiuso. Le installazioni
  di sistema (apt tesseract + playwright chromium + sandbox
  Keepa key) sono il prossimo blocco strategico, seguite da
  Fase 3 (live adapters + 5 decisioni Leader pre-flight).
- **Sentinella e2e ancora il flusso per Fase 3**: i 5 test
  `test_acquire_and_persist_*` resteranno verdi quando i mock
  saranno sostituiti con `_LiveKeepaAdapter` + Chromium +
  Tesseract (factory injection, zero modifica codice
  applicativo).
- **Catalogo ADR-0021**: invariato (10/11 viventi).

## Refs

- ADR: ADR-0017 (canale acquisizione), ADR-0015 (asin_master
  schema + UPSERT), ADR-0014 (mypy/ruff strict), ADR-0019
  (test integration pattern).
- Predecessori CHG: CHG-2026-05-01-005 (`upsert_asin_master`),
  CHG-2026-05-01-006 (`lookup_product`), CHG-2026-05-01-007
  (`SamsungExtractor.match` asin kwarg), CHG-2026-05-01-008
  (`build_asin_master_input` + sentinella e2e),
  CHG-2026-05-01-009 (`lookup_products` bulk).
- Pattern Unit-of-Work di riferimento:
  `save_session_result` (CHG-2026-04-30-042),
  `set_config_override_numeric` (CHG-2026-04-30-050).
- Memory: `project_io_extract_design_decisions.md` (D1-D5
  ratificate), `project_session_handoff_2026-05-01.md`
  (signature attesa per integratore).
- Successore atteso: **Fase 2 Path B** (installazioni di
  sistema: `sudo apt install tesseract-ocr-ita-eng` + `uv run
  playwright install chromium` + sandbox `TALOS_KEEPA_API_KEY`)
  → poi Fase 3 (live adapters + golden HTML/PDF/img + 5
  decisioni Leader pre-flight).
- Commit: `e425d14`.
