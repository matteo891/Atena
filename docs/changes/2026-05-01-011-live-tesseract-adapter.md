---
id: CHG-2026-05-01-011
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 2 attiva, Path B target — apertura Fase 3)
status: Draft
commit: TBD
adr_ref: ADR-0017, ADR-0014, ADR-0019, ADR-0021
---

## What

Implementa `_LiveTesseractAdapter.image_to_data` (era skeleton
`NotImplementedError` da CHG-2026-05-01-003). Primo live adapter
della Fase 3 Path B, sbloccato dall'installazione `apt install
tesseract-ocr-ita-eng` (Fase 2 step 1 completata Leader-side).

Pipeline live:

1. `pytesseract.image_to_data(image, lang=lang,
   output_type=Output.DICT)` ritorna un dict con `text: list[str]`
   e `conf: list[int|str]`.
2. I token a livello page/block/par/line sono `text=""` e
   `conf=-1`; il sentinel `-1` viene preservato nei
   `word_confidences` (filtrato a valle dal pipeline).
3. Il `text` di output e' la concatenazione dei soli token
   non-vuoti (`text.strip()`), separatore spazio.

**Bug fix R-01 emerso dai test live**: il pipeline `OcrPipeline.process_image`
dichiarava `OcrStatus.OK` su rumore puro perche' Tesseract emette
`text=""` ma `confidence=95` ai livelli aggregati page/block.
Aggiunto controllo `has_text = bool(raw.text.strip())`: senza text
estratto -> `OcrStatus.AMBIGUOUS` (R-01 NO SILENT DROPS).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/io_/ocr.py` | modificato | `_LiveTesseractAdapter.image_to_data` ratificato live: `pytesseract.image_to_data(...)` + parsing dict + sentinel `-1` preservato. `import pytesseract` + `from pytesseract import Output` runtime (mypy override `ignore_missing_imports` gia' presente da CHG-003). + bug fix `OcrPipeline.process_image`: `has_text` check evita `OcrStatus.OK` con text vuoto (caso rumore puro / immagine senza testo). Docstring `_LiveTesseractAdapter` aggiornato (skeleton -> implementato). |
| `tests/integration/test_live_tesseract.py` | nuovo | 4 test integration live (skip module-level se `tesseract` non in PATH): estrazione testo eng noto / sentinel `-1` preservato / pipeline end-to-end OK su testo nitido / immagine rumorosa -> AMBIGUOUS (verifica bug fix R-01). |
| `tests/unit/test_ocr_pipeline.py` | modificato | Rimosso `test_live_adapter_raises_not_implemented` (obsoleto post-CHG-011) + rimosso import `_LiveTesseractAdapter` non piu' usato. Sostituito con commento esplicativo che rinvia ai test integration live. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**663 PASS** (547 unit/governance/golden + 116 integration; era
660, +3 netto: +4 nuovi live tesseract −1 legacy unit rimosso).

## Why

Il setup Fase 2 step 1 (apt install tesseract-ocr-ita-eng) e'
completato Leader-side. Tesseract 5.3.4 raggiungibile via
`pytesseract` con lingue ita/eng/osd disponibili. Lo skeleton
NotImplementedError di CHG-003 era documentato come "ratifica
in CHG dedicato post setup di sistema": ora c'e'.

Il bug fix R-01 nel pipeline e' un dividendo dei test live:
solo eseguendo il binario reale su un'immagine rumorosa abbiamo
visto che Tesseract emette confidence aggregati alti anche
senza riconoscere word, mascherando l'assenza di testo. Pattern
classico di bug "mock-non-rilevabile": il test mock controlla
`word_confidences` ma non verifica che `text` sia non vuoto.
Aggiungere `has_text` chiude il gap.

### Decisioni di design

1. **Import `pytesseract` runtime top-level**: il modulo
   `pytesseract` e' gia' dep dichiarata (CHG-003) e
   l'`ignore_missing_imports` e' gia' nel pyproject. Top-level
   import e' piu' chiaro di lazy import (chiamato sempre dal
   live adapter).

2. **Sentinel `-1` preservato in `word_confidences`**: il
   pipeline downstream filtra (`[c for c in valid_conf if c >= 0]`).
   Pattern coerente con CHG-003.

3. **Concatenazione token con separatore spazio**: Tesseract
   emette ordine top-left -> bottom-right, separatore implicito
   spazio. Non si fa newline tra blocchi (semplificazione
   accettabile per l'estrazione attesa: titoli prodotto, label
   campo).

4. **Bug fix `has_text` nel pipeline (non nel adapter)**: l'adapter
   deve essere "honest reporter" del binario; il pipeline e' il
   livello di policy R-01. `text=""` con conf=95 e' una verita'
   del binario; e' il pipeline che decide come trattare.
   Localizzare il fix nel pipeline preserva la separazione.

5. **Test live skip module-level**: `pytestmark.skipif(shutil.which("tesseract") is None, ...)`
   garantisce che CI senza apt non fallisca. Pattern coerente
   con `test_rls_isolation.py` (skip se TALOS_DB_URL assente).

6. **Rimozione `test_live_adapter_raises_not_implemented`**:
   il test era una "tombstone" del skeleton; ora che
   l'implementazione esiste e' contraddittorio. La copertura
   live e' nei test integration nuovi.

7. **Fixture immagine via PIL `load_default(size=24)`**:
   font integrato in Pillow, deterministico cross-host.
   Try/except per compat con PIL <10.1 (`size=` non supportato).

### Out-of-scope

- **PDF text-layer detection** (`pypdf`): scope CHG futuro.
- **`pdf2image` + multi-page OCR**: scope CHG futuro (richiede
  installazione `poppler-utils`).
- **DOCX parsing** (`python-docx`): scope CHG futuro.
- **Deskew**: rinviato a CHG futuro (Hough transform o
  scikit-image; pure-numpy custom complesso).
- **Confidence aggregata "smarter"** (es. media pesata sui soli
  word, esclusi blocchi): scope CHG futuro se i livelli
  aggregati creano ambiguita'.
- **Telemetria nuova**: il bug fix `has_text` produce piu'
  AMBIGUOUS, che gia' emettono `ocr.below_confidence`
  (CHG-005). Catalogo invariato.

## How

### `_LiveTesseractAdapter.image_to_data` (highlight)

```python
def image_to_data(self, image, *, lang):
    data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)
    texts: list[str] = list(data["text"])
    confs_raw = data["conf"]
    word_confidences = [int(c) for c in confs_raw]
    text = " ".join(t for t in texts if t.strip())
    return RawOcrData(text=text, word_confidences=word_confidences)
```

### Bug fix `OcrPipeline.process_image` (highlight)

```python
# Pre-fix: status = OK se confidence >= threshold (anche con text="")
# Post-fix: status = OK solo se has_text AND confidence >= threshold
has_text = bool(raw.text.strip())
status = (
    OcrStatus.OK
    if has_text and confidence >= self._confidence_threshold
    else OcrStatus.AMBIGUOUS
)
```

### Test plan eseguito

4 test integration in `tests/integration/test_live_tesseract.py`:

- `test_live_tesseract_extracts_known_text_eng`: PIL crea
  "TALOS TEST 12345" -> Tesseract eng ritorna text contenente
  almeno uno dei token + confidence > 50.
- `test_live_tesseract_returns_minus_one_sentinel_for_skipped_tokens`:
  verifica che `-1` sia presente in `word_confidences` (livelli
  aggregati page/block).
- `test_live_tesseract_via_ocr_pipeline_returns_ok_for_clear_text`:
  pipeline end-to-end con preprocess Otsu + threshold 40 ->
  status OK + text non vuoto.
- `test_live_tesseract_below_threshold_returns_ambiguous_on_noise`:
  immagine random uint8 -> AMBIGUOUS (bug fix R-01 verificato).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/ocr.py tests/integration/test_live_tesseract.py tests/unit/test_ocr_pipeline.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/integration/test_live_tesseract.py` | 0 issues (50 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **547 PASS** (era 548; netto −1 per rimozione legacy `test_live_adapter_raises_not_implemented`) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **116 PASS** (era 112, +4 nuovi live tesseract) |

**Rischi residui:**
- **Performance Tesseract**: ~50-200ms per immagine 400x80 testo
  pulito; molto piu' alto su immagini complesse (PDF pagine
  multi-MB). Caller batch deve dimensionare time-out. Scope
  futuro: `concurrent.futures.ThreadPoolExecutor` su batch
  immagini.
- **Cross-platform fonts**: il test `test_live_tesseract_extracts_known_text_eng`
  usa `ImageFont.load_default()` di Pillow. Pillow 10+ ha font
  Bitstream Vera bundlato; versioni vecchie potrebbero usare
  font diverso. Il test e' tollerante: verifica solo la presenza
  di un token tra "TALOS"/"TEST"/"12345" + confidence > 50.
- **`has_text` rigoroso**: testo composto solo da spazi/whitespace
  ora viene marcato AMBIGUOUS. Se Tesseract estrae letteralmente
  "  " (whitespace puro), il caller deve trattarlo come
  AMBIGUOUS. Pattern coerente con R-01.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/ocr.py` ✓ (area
  `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Wrapper isolato `pytesseract` dietro `TesseractAdapter`
    Protocol ✓
  - R-01 NO SILENT DROPS rinforzato (`has_text` check) ✓
- **R-01 NO SILENT DROPS (governance test):** ✓
  (`ocr.below_confidence` gia' menzionato nel docstring; bug fix
  rinforza la garanzia).
- **Test integration live + unit ridotti:** ✓ (ADR-0019 +
  ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** modifica di funzione
  esistente -> ADR-0017 (modulo coperto).
- **Backward compat:** API `_LiveTesseractAdapter.image_to_data`
  invariata (signature identica, solo body); `OcrPipeline.process_image`
  cambia comportamento solo nel caso `text==""` con conf >=
  threshold (caso non documentato in CHG-003 ne' coperto da test).
- **Impact analysis pre-edit:** modifica live adapter privato
  + bug fix pipeline; impact LOW (caller di OcrPipeline gia'
  trattano AMBIGUOUS in modo definito).

## Impact

- **Fase 3 Path B aperta**: 1/N CHG (CHG-011, primo live
  adapter ratificato). Restano `_PlaywrightBrowserPage` (CHG
  futuro) e `_LiveKeepaAdapter` (post Fase 2 step 3 = sandbox
  API key Keepa).
- **`pyproject.toml` invariato** (`pytesseract>=0.3.13` gia'
  presente da CHG-003).
- **Bug fix R-01 nel pipeline**: scoperto da test live, fix
  scope adatto CHG-011. Pattern dimostra il valore del passaggio
  mock -> live: solo l'esecuzione reale rivela bug invisibili
  ai mock.
- **Catalogo eventi canonici ADR-0021**: invariato (10/11
  viventi). `ocr.below_confidence` ora emesso anche su text
  vuoto + conf alta (caso pre-fix silente).
- **Sentinella e2e CHG-008/010 non impattata**: usano mock,
  comportamento invariato.

## Refs

- ADR: ADR-0017 (canale OCR), ADR-0014 (mypy/ruff strict),
  ADR-0019 (test integration pattern), ADR-0021 (R-01).
- Predecessori: CHG-2026-05-01-003 (`OcrPipeline` skeleton +
  `_LiveTesseractAdapter` `NotImplementedError`),
  CHG-2026-05-01-005 (telemetria `ocr.below_confidence`
  attivata).
- Setup di sistema preflight: `sudo apt install tesseract-ocr
  tesseract-ocr-ita tesseract-ocr-eng` ✓ completato 2026-05-01.
- Successore atteso: CHG-2026-05-01-012
  (`_PlaywrightBrowserPage` live, sbloccato da `playwright
  install chromium` ✓ completato 2026-05-01).
- Memory: `project_io_extract_design_decisions.md` (D3
  ratificata).
- Commit: TBD.
