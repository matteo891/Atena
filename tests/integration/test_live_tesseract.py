"""Integration test live `_LiveTesseractAdapter` (CHG-2026-05-01-011, Fase 2 Path B).

Richiede il binario `tesseract-ocr` + lingue ita/eng installati di
sistema (`sudo apt install tesseract-ocr tesseract-ocr-ita
tesseract-ocr-eng`). Il test e' marcato `live`: pytest lo skippa
automaticamente se `tesseract` non e' raggiungibile via PATH.

Pattern: genera in-memory un'immagine PIL con testo noto, la
converte a numpy uint8 grayscale, la passa a
`_LiveTesseractAdapter.image_to_data` (live), verifica che il
testo estratto contenga i token attesi e la confidence aggregata
sia plausibile.

Quando arriveranno golden fixtures reali (PDF/immagini fornitore
Samsung), si aggiungeranno test `tests/golden/images/*.png` con
snapshot byte-exact dell'estrazione.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from talos.io_ import OcrPipeline, OcrStatus
from talos.io_.ocr import _LiveTesseractAdapter

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Skip module-level se il binario non e' installato (ambiente CI senza apt).
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        shutil.which("tesseract") is None,
        reason="tesseract binary not installed (skip Fase 2 live test)",
    ),
]


def _render_text_image(text: str, *, size: tuple[int, int] = (400, 80)) -> NDArray[np.uint8]:
    """Crea un'immagine grayscale uint8 con `text` su sfondo bianco.

    Usa il font default di PIL per evitare dipendenze da font specifici
    (deterministico cross-host).
    """
    image = Image.new("L", size, color=255)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=24)
    except TypeError:
        # PIL < 10.1 non supporta `size=` su load_default; fallback.
        font = ImageFont.load_default()
    draw.text((10, 20), text, fill=0, font=font)
    return np.array(image, dtype=np.uint8)


def test_live_tesseract_extracts_known_text_eng() -> None:
    """Tesseract eng estrae correttamente testo ASCII pulito."""
    image = _render_text_image("TALOS TEST 12345")
    adapter = _LiveTesseractAdapter(lang="eng")
    raw = adapter.image_to_data(image, lang="eng")
    assert "TALOS" in raw.text or "TEST" in raw.text or "12345" in raw.text
    valid_conf = [c for c in raw.word_confidences if c >= 0]
    assert len(valid_conf) > 0  # almeno un token riconosciuto
    assert max(valid_conf) > 50


def test_live_tesseract_returns_minus_one_sentinel_for_skipped_tokens() -> None:
    """Tesseract emette conf=-1 per blocchi/righe non-token; il sentinel e' preservato."""
    image = _render_text_image("Hello")
    adapter = _LiveTesseractAdapter(lang="eng")
    raw = adapter.image_to_data(image, lang="eng")
    # Tesseract emette token a vari livelli (page/block/par/line/word).
    # I livelli non-word hanno conf=-1; almeno uno deve essere presente.
    assert -1 in raw.word_confidences


def test_live_tesseract_via_ocr_pipeline_returns_ok_for_clear_text() -> None:
    """Pipeline end-to-end con preprocess Otsu + adapter live -> status OK."""
    image = _render_text_image("Galaxy S24 256GB")
    pipeline = OcrPipeline(confidence_threshold=40, lang="eng")  # soglia bassa per font default
    result = pipeline.process_image(image)
    assert result.status is OcrStatus.OK
    assert result.confidence >= 40
    assert result.source_kind == "image"
    assert result.text  # non vuoto


def test_live_tesseract_below_threshold_returns_ambiguous_on_noise() -> None:
    """Immagine rumorosa (random) -> nessun token affidabile -> AMBIGUOUS (R-01)."""
    rng = np.random.default_rng(seed=42)
    noise = rng.integers(0, 256, size=(80, 400), dtype=np.uint8)
    pipeline = OcrPipeline(confidence_threshold=70, lang="eng")
    result = pipeline.process_image(noise)
    assert result.status is OcrStatus.AMBIGUOUS
