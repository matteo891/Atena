---
id: CHG-2026-05-01-005
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" sessione attivata 2026-04-30 sera, prosegue oltre mezzanotte)
status: Draft
commit: [pending]
adr_ref: ADR-0017, ADR-0015, ADR-0021, ADR-0014, ADR-0019
---

## What

Quinto e ultimo CHG del blocco `io_/extract` Samsung (D5
ratificata "default" Leader) — chiusura **a livello primitive +
telemetria**. Due assi paralleli:

1. **`asin_master_writer`**: nuovo modulo `extract/asin_master_writer.py`
   con `AsinMasterInput` + `upsert_asin_master(db, *, data) -> str`.
   Implementa il pattern Postgres-native UPSERT atomico
   (D5.a) + merge `COALESCE` per i campi nullable (D5.b) +
   nessun trigger audit_log (D5.c).

2. **Telemetria 5 eventi canonici dormienti -> attivati**:
   ai 4 moduli skeleton del blocco (`KeepaClient`, `AmazonScraper`,
   `OcrPipeline`, `SamsungExtractor`) viene aggiunto
   `_logger = logging.getLogger(__name__)` + emissione
   `_logger.debug("event.name", extra={...})` ai punti dove le
   condizioni si verificano (catalogo ADR-0021).

Il **blocco si chiude a livello primitive**: non c'e' ancora
fallback chain orchestratrice (Keepa->Scraper->OCR) ne' live
adapter completi (richiedono `apt install tesseract-ocr-ita-eng`,
`playwright install chromium`, sandbox API key Keepa). Quei due
sono scope di una sessione successiva dedicata, fuori dalla
modalita' "macina" corrente.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/extract/asin_master_writer.py` | nuovo | `AsinMasterInput` (frozen dataclass: asin/title/brand/enterprise obbligatori, model/rom_gb/ram_gb/connectivity/color_family/category_node opzionali) + `upsert_asin_master(db, *, data) -> str` con `sqlalchemy.dialects.postgresql.insert` + `on_conflict_do_update(index_elements=[AsinMaster.asin], set_={...})` con merge `COALESCE(EXCLUDED.field, AsinMaster.field)` per i nullable e `func.now()` per `last_seen_at`. |
| `src/talos/extract/__init__.py` | modificato | + re-export `AsinMasterInput`, `upsert_asin_master`. |
| `src/talos/io_/keepa_client.py` | modificato | + `import logging` + `_logger = logging.getLogger(__name__)` + helper `_emit_miss(asin, *, field)` chiamato da ognuno dei tre `fetch_*` prima di `raise KeepaMissError` (evento `keepa.miss` con `asin/error_type/retry_count`); + emissione `keepa.rate_limit_hit` in `_fetch_one` prima di `raise KeepaRateLimitExceededError` (evento con `requests_in_window/limit`). Docstring esteso con riferimento CHG-005. |
| `src/talos/io_/scraper.py` | modificato | + `import logging` + `_logger = logging.getLogger(__name__)` + emissione `scrape.selector_fail` (evento con `asin/selector_name/html_snippet_hash`) in `_resolve_field` quando TUTTI i CSS+XPath falliscono, **anche con `missing_ok=True`** (segnale di drift selettori reale, vale loggare). `html_snippet_hash="<no-html>"` in CHG-005 (il modulo non ha accesso all'HTML completo via `BrowserPageProtocol`; scope futuro l'integratore live). |
| `src/talos/io_/ocr.py` | modificato | + `import logging` + `_logger = logging.getLogger(__name__)` + emissione `ocr.below_confidence` (evento con `file/confidence/threshold/text_extracted`) in `process_image` quando lo `status` calcolato e' `AMBIGUOUS`. `file="<image>"` in CHG-005 (PDF/DOCX scope futuro integratore). |
| `src/talos/extract/samsung.py` | modificato | + `import logging` + `_logger = logging.getLogger(__name__)` + emissione `extract.kill_switch` (evento con `asin/reason/mismatch_field/expected/actual`) in `match` quando scatta R-05 hard (`supplier.model != amazon.model`, entrambi non None). `asin="<n/a>"` in CHG-005 (l'extractor non riceve l'asin come kwarg; scope futuro integratore puo' wrappare con context). |
| `tests/unit/test_io_extract_telemetry.py` | nuovo | 10 test caplog (no Tesseract, no Chromium, no API): 3 parametrici `keepa.miss[buybox/bsr/fee_fba]`; 1 `keepa.rate_limit_hit`; 2 `scrape.selector_fail` (missing_ok=True con scrape_product / missing_ok=False con `_resolve_field` raise SelectorMissError); 2 `ocr.below_confidence` (emesso su AMBIGUOUS / non emesso su OK); 2 `extract.kill_switch` (emesso su R-05 hard / non emesso su low confidence senza model mismatch). Verifica campi `extra` di ogni evento (catalogo ADR-0021). |
| `tests/integration/test_asin_master_writer.py` | nuovo | 5 test integration su Postgres reale: insert nuovo ASIN + UPSERT overwrite NOT NULL fields + UPSERT merge `COALESCE` (input None preserva esistente, non-null overwrite) + `last_seen_at` aggiornato a NOW() su ogni upsert + verifica D5.c (nessuna riga in `audit_log` per `asin_master` post-upsert). Cleanup pre/post via `DELETE FROM asin_master WHERE asin = ANY([...])`. |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | + riga `asin_master_writer.py` (D5 details). + nota telemetria attivata in righe esistenti `keepa_client.py` / `scraper.py` / `ocr.py` / `samsung.py`. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**624 PASS** (519 unit/governance/golden + 105 integration).
Delta: +15 (10 telemetry unit + 5 asin_master integration).

## Why

Il blocco `io_/extract` Samsung (4-5 CHG attesi, decisioni Leader
D1-D5 ratificate "default" 2026-04-30 sera) era a 4/5 dopo CHG-004.
Il quinto CHG aveva due deliverable separati ma intrinsecamente
collegati:

1. **D5 (asin_master_writer)** chiude la coppia "estrazione ->
   anagrafica". Senza il writer, gli output di
   `SamsungExtractor.parse_title()` rimanevano in memoria — non
   c'era persistenza dell'apprendimento incrementale (ASIN visto
   per la prima volta, model risolto da Amazon scraping etc.).

2. **Telemetria attivata** chiude la coppia "produzione segnale ->
   evento canonico". I 5 eventi del catalogo ADR-0021 dichiarati
   dormienti dall'esordio del blocco (CHG-2026-05-01-001) sarebbero
   rimasti latenti senza un punto di emissione. Il pattern coerente
   con CHG-046 / CHG-049 / CHG-058 (telemetria gia' applicata in
   `tetris/`, `vgp/`, `orchestrator.py`) e' aggiungere
   `_logger.debug` ai siti di produzione del segnale.

Il blocco chiude **a livello primitive**: non c'e' ancora
fallback chain orchestratrice (Keepa->Scraper->OCR) e i live
adapter (`_LiveKeepaAdapter`, `_PlaywrightBrowserPage`,
`_LiveTesseractAdapter`) restano skeleton (`NotImplementedError`).
Quei due sono scope di una sessione dedicata successiva, perche':

- Live adapter Keepa richiede sandbox API key reale per ratificare
  il mapping CSV indici (BUY_BOX_SHIPPING idx 18, SALES idx 3,
  fee_fba estrazione).
- Live adapter Playwright richiede `playwright install chromium`
  (~150 MB) + golden HTML statici raccolti da Amazon reale per
  validare i selettori `selectors.yaml`.
- Live adapter Tesseract richiede `apt install tesseract-ocr
  tesseract-ocr-ita tesseract-ocr-eng` di sistema + fixture
  immagini per integration test.

Tutte e tre le attivazioni sono operazioni di sistema con setup
non triviale e richiedono interazione esplicita del Leader prima
di procedere. La modalita' "macina" corrente (clausola di
sessione) non e' il contesto giusto.

### Decisioni di design (D5 + telemetria)

1. **D5.a UPSERT Postgres-native** (A): `pg_insert` +
   `on_conflict_do_update`. Atomico server-side, nessun race
   condition. Pattern coerente con CHG-2026-04-30-050
   (`set_config_override_numeric`).

2. **D5.b Merge `COALESCE`** (C): per i campi nullable
   (`model`, `rom_gb`, `ram_gb`, `connectivity`, `color_family`,
   `category_node`) si applica `COALESCE(EXCLUDED.field,
   asin_master.field)`. Input non-null vince; input None preserva
   il valore esistente. Razionale: la fallback chain risolve
   incrementalmente (Keepa risolve `rom_gb`, lo scraper risolve
   `model`, etc.); chiamate successive con campi parziali NON
   devono cancellare quanto gia' appreso.

3. **D5.c Audit trigger NO** (B): `asin_master` e' anagrafica
   relativamente stabile. Il trigger AFTER ogni INSERT/UPDATE
   creerebbe migliaia di righe in `audit_log` ad ogni run di
   acquisizione (1 fila per ASIN per refresh). Costo
   storage/perf > valore audit (gli altri 3 trigger CHG-018
   restano: `sessions`, `config_overrides`, `locked_in`,
   `storico_ordini`).

4. **`title` / `brand` / `enterprise` sempre overwrite**:
   sono campi NOT NULL. Il caller li fornisce sempre — la merge
   `COALESCE` su NOT NULL non avrebbe senso (un input non puo'
   essere None per definizione). Pattern: NOT NULL = last-write-wins.

5. **`last_seen_at = NOW()` sempre refresh**: ogni UPSERT e' una
   "vista" dell'ASIN; il timestamp viene aggiornato a prescindere
   dal merge. Utile per logiche "stale data" future (es.
   "ri-scrappa ASIN visto > 24h fa").

6. **Telemetria: `_logger.debug` (non INFO)**: pattern coerente
   con CHG-046, CHG-049, CHG-058. Default INFO+ in produzione ->
   silente; opt-in via handler dedicato per audit operativo.

7. **Telemetria: stringhe letterali rilevabili**: nomi degli eventi
   passati come literal a `_logger.debug` (no costanti importate).
   Pattern CHG-046 (governance test fa grep su literal del
   catalogo).

8. **`scrape.selector_fail` emesso anche con `missing_ok=True`**:
   ogni miss totale di selettori e' un drift segnalabile, anche
   se il caller dichiara il campo opzionale. Razionale: drift
   senza fallimento applicativo e' il caso peggiore (silent
   degradation). Loggare e' sempre meglio che tacere (R-01
   spirito).

9. **`extract.kill_switch` emesso solo su model mismatch hard**:
   non sui MISMATCH "soft" (low confidence aggregata, model None
   da una parte). Razionale: solo il modello mismatch e' R-05
   hardware (PROJECT-RAW riga 223 verbatim). Gli altri MISMATCH
   sono "soft" (caller decide se mostrare al CFO).

10. **Sentinel `<no-html>`, `<image>`, `<n/a>` nei campi
    catalogo non popolabili in CHG-005**: i moduli skeleton non
    hanno accesso a tutti i campi del catalogo (es. scraper non
    ha l'HTML completo via Protocol; OCR non ha il `file` path
    perche' riceve `np.ndarray` direttamente). Sentinel espliciti
    > campi mancanti -> il caller sa che il campo "esiste ma e'
    placeholder per CHG futuro".

### Out-of-scope

- **Fallback chain orchestratrice** (`lookup_product(asin) ->
  ProductData` con try Keepa/scraper/OCR): scope sessione
  dedicata successiva.
- **Live adapter `_LiveKeepaAdapter` / `_PlaywrightBrowserPage` /
  `_LiveTesseractAdapter`**: tutti restano skeleton. Richiedono
  setup di sistema + sandbox -> sessione dedicata.
- **`asin_master.last_seen_at` come trigger di refresh
  automatico**: scope orchestratore (es. "se `last_seen_at >
  TTL` -> rerun acquisizione"); CHG-005 espone solo il primitive.
- **Cache Streamlit `@st.cache_data` su `upsert_asin_master`**:
  l'UPSERT non e' un read, e' un write -> cache non applicabile.
- **`db.audit_log_write` evento canonico**: gia' nel catalogo,
  attivato in CHG-018 (PostgreSQL trigger lato DB), non da
  applicativo. Resta dormiente lato Python (replicato dal
  trigger).

## How

### `upsert_asin_master` (highlight)

```python
stmt = pg_insert(AsinMaster).values(
    asin=data.asin,
    title=data.title,
    brand=data.brand,
    enterprise=data.enterprise,
    model=data.model,
    rom_gb=data.rom_gb,
    ...
)
excluded = stmt.excluded
stmt = stmt.on_conflict_do_update(
    index_elements=[AsinMaster.asin],
    set_={
        "title": excluded.title,                 # NOT NULL: overwrite
        "brand": excluded.brand,
        "enterprise": excluded.enterprise,
        "model": func.coalesce(excluded.model, AsinMaster.model),  # nullable: merge
        "rom_gb": func.coalesce(excluded.rom_gb, AsinMaster.rom_gb),
        "ram_gb": func.coalesce(excluded.ram_gb, AsinMaster.ram_gb),
        ...
        "last_seen_at": func.now(),              # sempre refresh
    },
)
db.execute(stmt)
return data.asin
```

### Telemetria — pattern (highlight su keepa_client)

```python
import logging
_logger = logging.getLogger(__name__)

# In ogni fetch_* prima del raise KeepaMissError:
self._emit_miss(asin, field="buybox")
raise KeepaMissError(asin, field="buybox")

@staticmethod
def _emit_miss(asin: str, *, field: str) -> None:
    _logger.debug(
        "keepa.miss",
        extra={"asin": asin, "error_type": field, "retry_count": 0},
    )
```

### Test plan eseguito

10 unit caplog test:

- 3 parametrici `keepa.miss[buybox/bsr/fee_fba]` con field-level mock
- 1 `keepa.rate_limit_hit` (rate_limit=1, secondo fetch oltre permit)
- 2 `scrape.selector_fail` (missing_ok=True via scrape_product /
  missing_ok=False via `_resolve_field`)
- 2 `ocr.below_confidence` (emesso su AMBIGUOUS / non emesso su OK)
- 2 `extract.kill_switch` (R-05 model mismatch hard / non emesso
  su low confidence senza model mismatch)

5 integration test su Postgres reale:

- `test_upsert_inserts_new_asin` (round-trip campi completi)
- `test_upsert_overwrites_not_null_fields_on_conflict` (title/brand/
  enterprise sempre overwrite)
- `test_upsert_merges_nullable_fields_via_coalesce` (D5.b: 1° upsert
  full / 2° upsert solo ram_gb / model+rom_gb+color_family preservati)
- `test_upsert_refreshes_last_seen_at` (NOW() avanza tra upsert)
- `test_upsert_does_not_trigger_audit_log` (D5.c: count(audit_log
  WHERE table_name='asin_master') invariato)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/ src/talos/extract/ tests/unit/test_io_extract_telemetry.py tests/integration/test_asin_master_writer.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_io_extract_telemetry.py` | 0 issues (48 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **519 PASS** (era 509, +10) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **105 PASS** (era 100, +5) |

**Rischi residui:**
- **Sentinel `<no-html>`, `<image>`, `<n/a>` nei log**: degradano
  la qualita' del segnale. Caller dovra' wrap-pare con context
  per avere campi completi in CHG futuro.
- **`extract.kill_switch` con `asin="<n/a>"`**: scope futuro
  integratore puo' passare `asin` come kwarg a
  `SamsungExtractor.match` o cambiare signature per accettare
  `asin: str | None = None`.
- **`scrape.selector_fail` `html_snippet_hash="<no-html>"`**:
  l'integratore live (CHG futuro) potra' passare l'HTML completo
  alla page e calcolare hash via `hashlib.sha256(html).hexdigest()`.
- **`asin_master_writer` non chiama `with_tenant`**: l'anagrafica
  ASIN e' (per ora) globale, non tenant-scoped. Scope futuro RLS
  asin_master se necessario.
- **No batch upsert**: il writer accetta un `AsinMasterInput`
  alla volta. Per popolazione bulk (es. fallback chain su
  500 ASIN), il caller chiama in loop. Scope futuro
  `bulk_upsert_asin_master(db, *, data_list)` con `INSERT ...
  VALUES (...), (...), ... ON CONFLICT`.

## Test di Conformità

- **Path codice applicativo:** `src/talos/extract/asin_master_writer.py`,
  modifiche a `src/talos/io_/{keepa_client,scraper,ocr}.py`,
  `src/talos/extract/samsung.py` ✓ (aree consentite ADR-0013).
- **ADR-0017 vincoli rispettati:**
  - Telemetria strutturata ✓ (`_logger.debug` con `extra={...}`)
  - Eventi canonici da catalogo ADR-0021 ✓ (5/5 attivati)
  - R-01 NO SILENT DROPS ✓ (ogni evento di scarto/miss e' loggato)
- **ADR-0015 vincoli rispettati:**
  - UPSERT atomico via `pg_insert` ✓
  - Pattern Unit-of-Work (caller fa commit/rollback) ✓
- **R-05 KILL-SWITCH HARDWARE:** `extract.kill_switch` emesso solo
  su model mismatch hard (verbatim PROJECT-RAW riga 223) ✓.
- **Test unit caplog + integration:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `AsinMasterInput`,
  `upsert_asin_master`, `_emit_miss` -> ADR-0017 + ADR-0015.
- **Backward compat:** modifiche additive ai 4 moduli skeleton
  (logger import + emissione eventi). Niente break sui caller
  esistenti (zero call sites).
- **Impact analysis pre-edit:** modifiche additive; i 4 moduli
  skeleton non hanno caller funzionali (l'integratore e' scope
  futuro). `asin_master_writer` e' modulo nuovo (zero caller).

## Impact

- **Blocco `io_/extract` Samsung chiuso a livello primitive +
  telemetria**. 5/5 CHG completati (CHG-001..005).
- **Catalogo eventi canonici ADR-0021: 10/11 viventi** (era 5/11).
  Restano dormienti solo `db.audit_log_write` (replicato da
  trigger Postgres lato DB, gia' attivo in CHG-018; non si
  attiva da Python applicativo).
- **`pyproject.toml` invariato** (no nuove deps, telemetria usa
  `logging` stdlib).
- **`asin_master_writer.upsert_asin_master`**: primo punto di
  scrittura atomica anagrafica ASIN. Pronto per consumer dalla
  fallback chain integratrice (CHG futuro).
- **Pattern telemetria attivato in 4 moduli del blocco**: ogni
  futuro caller (orchestratore, fallback chain) eredita
  automaticamente il segnale strutturato senza modificare il
  proprio codice.
- **Sessione successiva attesa**: live adapters
  (`_LiveKeepaAdapter`, `_PlaywrightBrowserPage`,
  `_LiveTesseractAdapter`) + fallback chain orchestratrice +
  golden HTML/PDF statici per integration test. Setup di sistema
  richiesto: `apt install tesseract-ocr-ita-eng`,
  `playwright install chromium`, sandbox API key Keepa.

## Refs

- ADR: ADR-0017 (canale extract + telemetria), ADR-0015
  (asin_master schema + UPSERT pattern), ADR-0021 (catalogo
  eventi canonici), ADR-0014 (mypy/ruff strict), ADR-0019 (test
  unit + integration pattern).
- Predecessori CHG di blocco: CHG-2026-05-01-001 (`KeepaClient`),
  CHG-2026-05-01-002 (`AmazonScraper`), CHG-2026-05-01-003
  (`OcrPipeline`), CHG-2026-05-01-004 (`SamsungExtractor` +
  R-05).
- Pattern telemetria di riferimento: CHG-2026-04-30-046
  (`tetris.skipped_budget`), CHG-2026-04-30-049
  (`vgp.veto_roi_failed/kill_switch_zero/panchina.archived`),
  CHG-2026-04-30-058 (`session.replayed`).
- Pattern UPSERT di riferimento: CHG-2026-04-30-050
  (`set_config_override_numeric`).
- Memory: `project_io_extract_design_decisions.md` (D5
  ratificata "default").
- PROJECT-RAW: R-05 KILL-SWITCH HARDWARE (riga 223), L18
  (Tesseract locale + soglia AMBIGUO).
- Successore atteso (sessione dedicata): live adapter Keepa /
  Playwright / Tesseract + fallback chain orchestratrice +
  golden HTML/PDF statici + integration con `apt install
  tesseract-ocr-ita-eng` e `playwright install chromium`.
- Commit: `[pending]`.
