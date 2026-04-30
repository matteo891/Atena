---
id: CHG-2026-05-01-003
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" sessione attivata 2026-04-30 sera, prosegue oltre mezzanotte)
status: Draft
commit: 1da38b0
adr_ref: ADR-0017, ADR-0014, ADR-0019, ADR-0021
---

## What

Aggiunge `OcrPipeline` a `src/talos/io_/` — terzo canale della
fallback chain ADR-0017 (pipeline OCR Tesseract per PDF/immagini
non strutturati). Adapter pattern: `TesseractAdapter` Protocol
isola `pytesseract` per testabilita' senza il binario tesseract-ocr
di sistema. `_LiveTesseractAdapter` e' uno skeleton
(`NotImplementedError`) — la ratifica live richiede
`apt install tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng`
ed e' rinviata a CHG-2026-05-01-005 integratore.

R-01 NO SILENT DROPS: confidence < soglia -> `OcrStatus.AMBIGUOUS`
(non scarto silenzioso). Soglia configurabile via
`TalosSettings.ocr_confidence_threshold`.

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | + dep `pytesseract>=0.3.13,<1` (canale 3 ADR-0017). + override `[[tool.mypy.overrides]] module=["pytesseract.*"] ignore_missing_imports=true` (la libreria community non distribuisce stubs ufficiali; importata solo dal `_LiveTesseractAdapter` skeleton, runtime scope CHG-005). Commento aggiornato: "Tesseract aggiunto, le altre deps come pdf2image/python-docx/pypdf entrano con CHG-005 integratore". |
| `src/talos/config/settings.py` | modificato | + `ocr_confidence_threshold: int = 70` (env `TALOS_OCR_CONFIDENCE_THRESHOLD`). + `field_validator` che impone `0 <= v <= 100` (scala Tesseract). Default 70 verbatim ADR-0017. Override runtime possibile via `config_overrides` (key `ocr_confidence_threshold` — pattern CHG-050). |
| `src/talos/io_/ocr.py` | nuovo | Costanti `DEFAULT_OCR_CONFIDENCE_THRESHOLD=70`, `DEFAULT_TESSERACT_LANG="ita+eng"`. `class OcrStatus(StrEnum)`: `OK`, `AMBIGUOUS`. `@dataclass(frozen=True) RawOcrData(text, word_confidences)`. `@dataclass(frozen=True) OcrResult(text, confidence, status, source_kind)`. `TesseractAdapter` Protocol con `image_to_data(image, *, lang)`. Helper pure-numpy `otsu_threshold(image) -> int` (Otsu 1979 max varianza inter-classe) + `binarize_otsu(image) -> np.uint8` (D3.b preprocessing minimo). `OcrPipeline(*, confidence_threshold, lang, adapter_factory, preprocess)` con `process_image(image)` che applica preprocess Otsu, chiama adapter, calcola confidence (media `word_confidences >= 0`, filtra Tesseract -1 sentinel), ritorna `OcrResult` con `OK`/`AMBIGUOUS`. `_LiveTesseractAdapter` skeleton: `image_to_data` lancia `NotImplementedError` esplicito (cita CHG-005 + apt install). |
| `src/talos/io_/__init__.py` | modificato | + re-export `OcrPipeline`, `OcrResult`, `OcrStatus`, `RawOcrData`, `TesseractAdapter`, `binarize_otsu`, `otsu_threshold`, `DEFAULT_OCR_CONFIDENCE_THRESHOLD`, `DEFAULT_TESSERACT_LANG`. Docstring esteso: "esteso in CHG-2026-05-01-003 con OcrPipeline". |
| `tests/unit/test_ocr_pipeline.py` | nuovo | 22 test puri (mock `TesseractAdapter` + array numpy sintetici, no binario tesseract): 2 schema (`OcrStatus` valori, `OcrResult` frozen); 5 Otsu (empty raises, uniform, bimodale delta, bimodale spread, output 0/255, shape preservato); 4 construction (default + 3 invalid); 8 `process_image` (high-conf OK, low-conf AMBIGUOUS, filtra -1, no valid -> AMBIGUOUS, threshold custom, preprocess=False, lang propagato, 3D raises); 1 adapter factory injection; 1 `_LiveTesseractAdapter` skeleton raises NotImplementedError. |
| `tests/unit/test_settings.py` | modificato | + 6 test sui nuovi campi: `ocr_confidence_threshold` default 70 / env override / boundaries 0/100 accettati / negative rejected / >100 rejected. |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Riga `src/talos/io_/ocr.py` aggiornata con descrizione completa scope CHG-003. Settings row aggiornata con il nuovo campo + validator. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest
**578 PASS** (478 unit/governance/golden + 100 integration).
Delta unit: +28 (22 `test_ocr_pipeline.py` + 6 nuovi
`test_settings.py`).

## Why

ADR-0017 designa Tesseract OCR come canale 3 della fallback
chain (per file non strutturati: PDF, immagini, DOCX). Senza
un wrapper isolato, ogni caller dovrebbe gestire confidence
threshold inline + R-01 NO SILENT DROPS verrebbe applicato
inconsistentemente.

CHG-2026-05-01-003 e' il terzo CHG del blocco `io_/extract`
Samsung (4-5 attesi, decisioni Leader D1-D5 ratificate "default"
2026-04-30 sera). D3 applicata in questo CHG.

### Decisioni di design (D3 ratificata)

1. **D3.a Lingua: A = `-l ita+eng`**: lingue pacchettate insieme
   nel binario Tesseract. Tollerante a stringhe miste (i listini
   Samsung hanno spesso titoli inglesi + descrizioni italiane).
   Costo: leggero overhead modello vs `-l ita` puro.

2. **D3.b Preprocessing: B = minimo (deskew + binarize Otsu)**:
   - **Otsu binarize implementato in pure-numpy** (no opencv,
     no scikit-image). ~30 righe, testabile su array sintetici.
     Massimizza la varianza inter-classe per separare
     foreground/background ottimalmente.
   - **Deskew rinviato a CHG-005 integratore**: richiede Hough
     transform o projection profile custom; complesso da
     implementare in pure-numpy senza dep pesanti. Skip
     inscritto come "TODO documentato" nel docstring del
     pipeline.

3. **D3.c PDF text-layer detection: B**: rinviato a CHG-005
   integratore. Richiede `pypdf` import + fixture PDF.
   Helper signature gia' progettata (`_pdf_has_text_layer(path)
   -> bool`) ma non implementato in CHG-003 per scope minimal.

4. **Adapter Pattern + Protocol**: `TesseractAdapter` espone
   un solo metodo `image_to_data(image, *, lang) -> RawOcrData`.
   Il pipeline non importa `pytesseract` -> binario tesseract
   NON necessario per i test unit. `_LiveTesseractAdapter`
   adapter live e' uno skeleton (R-01 NO SILENT DROPS via
   `NotImplementedError`).

5. **`RawOcrData` come ABI tra adapter e pipeline**: `text` +
   `word_confidences: list[int]`. Il pipeline calcola la
   confidence aggregata (media tokens >= 0), filtrando il
   sentinel `-1` di Tesseract (token saltato).

6. **`OcrStatus` come `StrEnum`**: serializza naturalmente in
   JSON/log strutturati. Valori `"OK"` / `"AMBIGUOUS"` (verbatim
   ADR-0017).

7. **`OcrResult.source_kind: str`**: campo aperto (`"image"`,
   futuro `"pdf_page"`, `"docx"`). Non e' un Enum per evitare
   coupling rigido finche' i caller non sono ratificati.

8. **`confidence_threshold` come `int [0, 100]`**: validator
   in `TalosSettings` (env-overridable) E in `OcrPipeline`
   constructor (per uso programmatico). Coerente con la scala
   Tesseract (`pytesseract.image_to_data` ritorna conf in
   [0, 100]).

9. **`adapter_factory: Callable[..., TesseractAdapter]`**:
   accetta kwargs (in CHG-003 solo `lang`) per estensibilita'
   futura. Pattern coerente con CHG-001 KeepaClient.

### Out-of-scope

- **`_LiveTesseractAdapter` live wrapper**: richiede
  `apt install tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng`
  + `pytesseract.image_to_data(...)` + parsing del dict.
  Ratifica in CHG-2026-05-01-005 integratore.
- **PDF text-layer detection** (`pypdf`): scope CHG-005.
- **DOCX text extraction** (`python-docx`): scope CHG-005.
- **PDF -> immagini** (`pdf2image`): scope CHG-005.
- **Deskew automatico**: scope CHG-005 (Hough projection o
  scikit-image).
- **Telemetria evento `ocr.below_confidence`**: catalogo
  ADR-0021 (dormiente). Attivata nell'integratore CHG-005
  quando il caller gestisce il `OcrStatus.AMBIGUOUS`.
- **Override runtime via `config_overrides`**: la chiave
  `ocr_confidence_threshold` e' menzionata in settings ma
  non c'e' ancora il pattern UI (sarebbe analogo a
  CHG-050 per `roi_veto_threshold`).

## How

### Otsu pure-numpy (highlight)

```python
def otsu_threshold(image: NDArray[np.uint8]) -> int:
    flat = image.ravel().astype(np.int64)
    histogram = np.bincount(flat, minlength=256)[:256]
    total = flat.size
    sum_total = float((np.arange(256) * histogram).sum())
    sum_b, weight_b, max_var, best_t = 0.0, 0, -1.0, 128
    for t in range(256):
        weight_b += int(histogram[t])
        if weight_b == 0:
            continue
        weight_f = total - weight_b
        if weight_f == 0:
            break
        sum_b += float(t * int(histogram[t]))
        mean_b = sum_b / weight_b
        mean_f = (sum_total - sum_b) / weight_f
        var = weight_b * weight_f * (mean_b - mean_f) ** 2
        if var > max_var:
            max_var, best_t = var, t
    return best_t
```

### `process_image` (highlight)

```python
def process_image(self, image):
    if image.ndim != 2:
        raise ValueError(...)
    prepared = binarize_otsu(image) if self._preprocess else image
    raw = self._adapter.image_to_data(prepared, lang=self._lang)
    valid = [c for c in raw.word_confidences if c >= 0]
    confidence = float(sum(valid)) / len(valid) if valid else 0.0
    status = OcrStatus.OK if confidence >= self._confidence_threshold else OcrStatus.AMBIGUOUS
    return OcrResult(text=raw.text, confidence=confidence, status=status, source_kind="image")
```

### Test plan eseguito

22 unit test sul modulo `ocr.py` + 6 settings:

- 2 schema (`OcrStatus` valori; `OcrResult` frozen)
- 5 Otsu (empty raises; uniform fallback; bimodale delta;
  bimodale spread realistica; output 0/255; shape preservato)
- 4 construction (default + 3 validator: threshold negativo /
  >100 / lang vuoto)
- 8 `process_image` (high conf OK; low conf AMBIGUOUS;
  filtra -1 Tesseract sentinel; tutti -1 -> AMBIGUOUS;
  threshold custom strict/lenient; preprocess=False;
  lang propagato all'adapter; 3D RGB array raises)
- 1 adapter factory injection (riceve `lang` come kwarg)
- 1 `_LiveTesseractAdapter` skeleton raises NotImplementedError
- 6 settings (ocr_confidence_threshold default/env override/
  boundaries 0/100 accettati/negative rejected/>100 rejected)

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/talos/io_/ tests/unit/test_ocr_pipeline.py tests/unit/test_settings.py` | All checks passed |
| Format | `uv run ruff format --check ...` | tutti formattati |
| Type | `uv run mypy src/ tests/unit/test_ocr_pipeline.py tests/unit/test_settings.py` | 0 issues (46 source files) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **478 PASS** (era 450, +28) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **100 PASS** (invariato) |

**Rischi residui:**
- **Otsu su immagine uniforme**: ritorna 128 di default (non
  separa). Comportamento documentato + testato. Caller deve
  trattare immagini uniformi a monte se necessario.
- **`_LiveTesseractAdapter` skeleton chiamato direttamente**:
  raise immediato `NotImplementedError` con messaggio esplicito
  che cita CHG-005 + `apt install`. R-01 rispettato.
- **Mypy override per `pytesseract.*`**: `ignore_missing_imports`
  inscritto in pyproject. Quando CHG-005 importera' davvero
  `pytesseract`, l'override resta valido (la libreria non ha
  py.typed).
- **`process_image` non gestisce immagini RGB/RGBA**: il caller
  deve convertire a grayscale (PIL `convert("L")` o numpy
  `np.mean(rgb, axis=2)`). Documentato nella docstring;
  `ndim != 2` raise esplicito.
- **`OcrPipeline.process_pdf_*` / `process_docx`**: NON esistono
  ancora. Scope CHG-005 integratore. La signature corrente
  fornisce solo `process_image`.

## Test di Conformità

- **Path codice applicativo:** `src/talos/io_/ocr.py` ✓ (area
  `io_/` ADR-0013 consentita).
- **ADR-0017 vincoli rispettati:**
  - Wrapper isolato pytesseract dietro `TesseractAdapter` ✓
  - `pytesseract` come binding di Tesseract locale ✓ (dichiarato
    in pyproject)
  - Soglia confidence default 70 ✓ (verbatim ADR-0017)
  - Sotto soglia -> status AMBIGUO (R-01) ✓
  - Configurabile via `TalosSettings` + `config_overrides` ✓
- **R-01 NO SILENT DROPS (governance test):** ✓
  (`ocr.below_confidence` menzionato esplicitamente nel
  docstring; il governance test cerca la stringa).
- **Test unit sotto `tests/unit/`:** ✓ (ADR-0019 + ADR-0011).
- **Quality gate verde:** tutti pass (ADR-0014).
- **No nuovi simboli senza ADR Primario:** `OcrPipeline`,
  `OcrStatus`, `OcrResult`, `RawOcrData`, `TesseractAdapter`,
  `_LiveTesseractAdapter`, `otsu_threshold`, `binarize_otsu`
  -> ADR-0017.
- **Backward compat:** modulo nuovo, niente break.
- **Impact analysis pre-edit:** primo `ocr.py` (zero caller).
  `__init__.py` re-export estesi (additivo). Settings esteso
  retrocompat (default value).

## Impact

- **Terzo canale ADR-0017 attivato a livello primitive.**
  Resta da implementare il live adapter + PDF/DOCX support
  (CHG-005).
- **`pyproject.toml` cresce di 1 dep applicativa**:
  `pytesseract`. Niente trascina (binario tesseract NON
  installato qui).
- **`mypy` override per `pytesseract.*`**: prima override del
  progetto. Pattern documentato per future librerie senza
  py.typed.
- **5 eventi dormienti ADR-0021** (`keepa.miss`,
  `keepa.rate_limit_hit`, `scrape.selector_fail`,
  `ocr.below_confidence`, `extract.kill_switch`) attendono
  ancora i CHG successivi per attivarsi davvero.
- **`otsu_threshold` / `binarize_otsu` come helper riusabili**:
  module-level, candidati per consumo da
  `extract/samsung.py` (CHG-004) o orchestratore (preprocessing
  ASIN images).
- **`TalosSettings` cresce a 9 campi** (era 8 — aggiunto
  `ocr_confidence_threshold`).
- **Avanzamento blocco `io_/extract` Samsung: 3/5**.

## Refs

- ADR: ADR-0017 (canale 3 OCR Tesseract), ADR-0014 (mypy/ruff
  strict + override deroga `pytesseract.*`), ADR-0019 (test
  unit pattern), ADR-0021 (catalogo eventi `ocr.below_confidence`
  dormiente).
- Predecessori: CHG-2026-05-01-001 (`KeepaClient`), CHG-2026-05-01-002
  (`AmazonScraper`) — pattern adapter + R-01 + skeleton live
  adapter coerente.
- Successori attesi: CHG-2026-05-01-004 (`extract/samsung.py`
  SamsungExtractor + R-05); CHG-2026-05-01-005 (integratore
  fallback chain + tutti i live adapter + telemetria 5 eventi
  + `process_pdf_page`, `process_docx`, deskew, text-layer
  detection).
- Memory: `project_io_extract_design_decisions.md` (D3 ratificata
  "default").
- Commit: `1da38b0`.
