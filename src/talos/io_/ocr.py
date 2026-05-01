"""OcrPipeline — Tesseract OCR + soglia AMBIGUO + preprocessing minimo (ADR-0017 canale 3).

CHG-2026-05-01-003 inaugura il terzo canale della fallback chain
ADR-0017. Decisioni di design (D3 ratificata "default" Leader
2026-04-30 sera, memory `project_io_extract_design_decisions.md`):

- D3.a Lingua: A = `-l ita+eng` (entrambe insieme; tollerante a
  stringhe miste italiano-inglese tipiche dei listini Samsung).
- D3.b Preprocessing: B = minimo (deskew + binarize Otsu).
  Deskew rinviato a CHG-005 integratore (richiede cv2 / scikit-image
  o Hough projection custom). Otsu binarize implementato in pure numpy.
- D3.c PDF: B = detect text-layer prima, OCR solo su pagine senza
  testo nativo (rinviato CHG-005 — richiede `pypdf` import + fixture).

Adapter pattern: `TesseractAdapter` Protocol isola `pytesseract` per
testabilita' senza il binario tesseract-ocr di sistema.
`_LiveTesseractAdapter` e' uno skeleton (`NotImplementedError`)
da ratificare nell'integratore CHG-2026-05-01-005.

R-01 NO SILENT DROPS: confidence < soglia -> `OcrStatus.AMBIGUOUS`
(non `OcrStatus.OK`). Il caller (fallback chain) deve mostrare la
riga al CFO per validazione manuale e logga l'evento canonico
`ocr.below_confidence` (catalogo ADR-0021, dormiente in CHG-003,
attivato dall'integratore CHG-2026-05-01-005).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

import numpy as np
import pytesseract
import structlog
from pytesseract import Output

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

_logger = structlog.get_logger(__name__)

DEFAULT_OCR_CONFIDENCE_THRESHOLD = 70
DEFAULT_TESSERACT_LANG = "ita+eng"


class OcrStatus(StrEnum):
    """Esito di un singolo OCR (R-01 NO SILENT DROPS).

    - `OK`: confidence >= soglia, testo affidabile.
    - `AMBIGUOUS`: confidence < soglia, riga marcata per validazione
      manuale dal CFO. Non e' un errore (no raise) ma uno stato.
    """

    OK = "OK"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class RawOcrData:
    """Risposta normalizzata dal binario Tesseract.

    Riproduce il sottoinsieme minimal di `pytesseract.image_to_data`
    necessario per calcolare confidence e ricostruire il testo.

    - `text`: testo concatenato (spazi tra token; ordine top-left).
    - `word_confidences`: confidence per ogni token in [0, 100].
      Tesseract usa -1 per token saltati; il pipeline filtra.
    """

    text: str
    word_confidences: list[int]


@dataclass(frozen=True)
class OcrResult:
    """Output del pipeline OCR per una singola immagine/pagina."""

    text: str
    confidence: float
    status: OcrStatus
    source_kind: str  # "image" | "pdf_page" | "docx" (futuro)


class TesseractAdapter(Protocol):
    """Interfaccia minimal per Tesseract OCR.

    Astrazione dietro `pytesseract.image_to_data` per testabilita'
    senza binario tesseract-ocr installato. Test mockano questo
    Protocol; runtime e' `_LiveTesseractAdapter` (skeleton CHG-003).
    """

    def image_to_data(
        self,
        image: NDArray[np.uint8],
        *,
        lang: str,
    ) -> RawOcrData:
        """Esegue OCR e ritorna testo + confidence per token."""
        ...


def otsu_threshold(image: NDArray[np.uint8]) -> int:
    """Calcola la soglia ottimale Otsu per binarizzazione (intero in [0, 255]).

    Implementazione pure-numpy (no opencv / scikit-image): istogramma
    a 256 bin, scelta del threshold che massimizza la varianza inter-classe
    (Otsu 1979). Usato in `binarize_otsu` per il preprocessing minimo D3.b.

    Per immagini quasi uniformi (varianza zero) ritorna 128 (centro
    della scala) come fallback ragionevole.
    """
    if image.size == 0:
        msg = "otsu_threshold richiede un array non vuoto"
        raise ValueError(msg)
    flat = image.ravel().astype(np.int64)
    histogram = np.bincount(flat, minlength=256)[:256]
    total = flat.size
    sum_total = float((np.arange(256) * histogram).sum())
    sum_b = 0.0
    weight_b = 0
    max_variance = -1.0
    best_threshold = 128
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
        variance_between = weight_b * weight_f * (mean_b - mean_f) ** 2
        if variance_between > max_variance:
            max_variance = variance_between
            best_threshold = t
    return best_threshold


def binarize_otsu(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Binarizza un'immagine grayscale con Otsu (D3.b minimal).

    Ritorna array di stesso shape, valori 0 (foreground/inchiostro)
    o 255 (background/carta). Per uso classico Tesseract: testo nero
    su sfondo bianco.
    """
    threshold = otsu_threshold(image)
    return np.where(image > threshold, 255, 0).astype(np.uint8)


class _LiveTesseractAdapter:
    """Adapter live su `pytesseract`.

    Implementato in CHG-2026-05-01-011 (Fase 2 Path B): richiede il
    binario `tesseract` installato di sistema (`apt install
    tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng`).

    Pipeline:

    1. `pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)`
       ritorna un dict con (almeno) le chiavi `text: list[str]` e
       `conf: list[int|str]`.
    2. Tesseract emette righe non-token (blocchi/paragrafi/righe)
       con `text=""` e `conf=-1`. Vengono incluse nei
       `word_confidences` come sentinel `-1`; il pipeline downstream
       (`OcrPipeline`) filtra per il calcolo della confidence
       aggregata (CHG-2026-05-01-003).
    3. Il `text` di output e' la concatenazione (separatore spazio)
       dei soli token non-vuoti (`text.strip()`), preservando
       l'ordine top-left -> bottom-right di Tesseract.
    """

    def __init__(self, *, lang: str = DEFAULT_TESSERACT_LANG) -> None:
        self._lang = lang

    def image_to_data(
        self,
        image: NDArray[np.uint8],
        *,
        lang: str,
    ) -> RawOcrData:
        data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)
        texts: list[str] = list(data["text"])
        confs_raw = data["conf"]
        word_confidences = [int(c) for c in confs_raw]
        text = " ".join(t for t in texts if t.strip())
        return RawOcrData(text=text, word_confidences=word_confidences)


def _default_adapter_factory(*, lang: str) -> TesseractAdapter:
    return _LiveTesseractAdapter(lang=lang)


class OcrPipeline:
    """Pipeline OCR Tesseract con soglia confidence + preprocessing minimo.

    Uso runtime:

        pipeline = OcrPipeline()  # confidence_threshold da TalosSettings
        # image: np.ndarray uint8 grayscale
        result = pipeline.process_image(image)
        if result.status is OcrStatus.AMBIGUOUS:
            ...  # caller marca riga per validazione CFO

    Uso test (mock adapter, no Tesseract binario):

        pipeline = OcrPipeline(adapter_factory=lambda *, lang: my_mock)
        result = pipeline.process_image(image)
    """

    def __init__(
        self,
        *,
        confidence_threshold: int = DEFAULT_OCR_CONFIDENCE_THRESHOLD,
        lang: str = DEFAULT_TESSERACT_LANG,
        adapter_factory: Callable[..., TesseractAdapter] | None = None,
        preprocess: bool = True,
    ) -> None:
        if not 0 <= confidence_threshold <= 100:  # noqa: PLR2004
            msg = (
                f"confidence_threshold invalido: {confidence_threshold}. "
                "Deve essere intero in [0, 100] (scala Tesseract)."
            )
            raise ValueError(msg)
        if not lang:
            msg = "lang non puo' essere vuoto"
            raise ValueError(msg)
        self._confidence_threshold = confidence_threshold
        self._lang = lang
        self._preprocess = preprocess
        factory = adapter_factory or _default_adapter_factory
        self._adapter = factory(lang=lang)

    @property
    def confidence_threshold(self) -> int:
        return self._confidence_threshold

    @property
    def lang(self) -> str:
        return self._lang

    def process_image(self, image: NDArray[np.uint8]) -> OcrResult:
        """OCR di una singola immagine grayscale (uint8).

        Pipeline:
          1. (opzionale, default ON) preprocessing D3.b: `binarize_otsu`.
             Skip se l'immagine e' gia' binarizzata o il caller passa
             `preprocess=False` al constructor.
          2. Adapter OCR: ritorna `RawOcrData` (text + word_confidences).
          3. Calcolo confidence: media aritmetica delle word_confidences
             >= 0 (Tesseract usa -1 per token saltati). Se nessuna
             word confidence valida -> confidence=0.0 -> AMBIGUOUS.
          4. Status: confidence >= threshold -> OK; altrimenti AMBIGUOUS.
        """
        if image.ndim != 2:  # noqa: PLR2004
            msg = (
                f"process_image richiede immagine 2D grayscale uint8, ricevuto shape={image.shape}"
            )
            raise ValueError(msg)
        prepared = binarize_otsu(image) if self._preprocess else image
        raw = self._adapter.image_to_data(prepared, lang=self._lang)
        valid_conf = [c for c in raw.word_confidences if c >= 0]
        confidence = float(sum(valid_conf)) / len(valid_conf) if valid_conf else 0.0
        # R-01 NO SILENT DROPS (CHG-2026-05-01-011): testo vuoto e' AMBIGUOUS
        # anche se Tesseract aggrega confidence alti sui livelli page/block.
        # Caso emerso dai test live su immagini rumorose: il binario emette
        # conf=95 a livello page senza word riconosciute -> il pipeline pre-fix
        # dichiarava OK con text="" (silent drop).
        has_text = bool(raw.text.strip())
        status = (
            OcrStatus.OK
            if has_text and confidence >= self._confidence_threshold
            else OcrStatus.AMBIGUOUS
        )
        if status is OcrStatus.AMBIGUOUS:
            # Telemetria CHG-2026-05-01-005: evento canonico ADR-0021.
            # Il caller (fallback chain) deve mostrare la riga al CFO.
            _logger.debug(
                "ocr.below_confidence",
                file="<image>",
                confidence=confidence,
                threshold=self._confidence_threshold,
                text_extracted=raw.text,
            )
        return OcrResult(
            text=raw.text,
            confidence=confidence,
            status=status,
            source_kind="image",
        )
