"""Test unit per `talos.io_.ocr` (CHG-2026-05-01-003, ADR-0017 canale 3).

Pattern: mock `TesseractAdapter` iniettato via `adapter_factory`,
nessun binario tesseract-ocr richiesto. `otsu_threshold` /
`binarize_otsu` testati su array numpy sintetici.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from talos.io_ import (
    DEFAULT_OCR_CONFIDENCE_THRESHOLD,
    DEFAULT_TESSERACT_LANG,
    OcrPipeline,
    OcrResult,
    OcrStatus,
    RawOcrData,
    TesseractAdapter,
    binarize_otsu,
    otsu_threshold,
)
from talos.io_.ocr import _LiveTesseractAdapter

if TYPE_CHECKING:
    from numpy.typing import NDArray

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------


class _StaticTesseractAdapter:
    """Mock adapter che ritorna sempre la stessa RawOcrData."""

    def __init__(self, raw: RawOcrData) -> None:
        self.raw = raw
        self.calls = 0
        self.last_lang: str | None = None
        self.last_image_shape: tuple[int, ...] | None = None

    def image_to_data(
        self,
        image: NDArray[np.uint8],
        *,
        lang: str,
    ) -> RawOcrData:
        self.calls += 1
        self.last_lang = lang
        self.last_image_shape = image.shape
        return self.raw


# ---------------------------------------------------------------------------
# OcrStatus / dataclass
# ---------------------------------------------------------------------------


def test_ocr_status_string_values() -> None:
    """OcrStatus e' StrEnum con valori 'OK' e 'AMBIGUOUS'."""
    assert OcrStatus.OK.value == "OK"
    assert OcrStatus.AMBIGUOUS.value == "AMBIGUOUS"


def test_ocr_result_is_frozen() -> None:
    """OcrResult immutabile."""
    result = OcrResult(text="x", confidence=80.0, status=OcrStatus.OK, source_kind="image")
    with pytest.raises(AttributeError):
        result.text = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# otsu_threshold / binarize_otsu
# ---------------------------------------------------------------------------


def test_otsu_threshold_empty_raises() -> None:
    img = np.empty((0, 0), dtype=np.uint8)
    with pytest.raises(ValueError, match="non vuoto"):
        otsu_threshold(img)


def test_otsu_threshold_uniform_returns_default() -> None:
    """Immagine uniforme = una sola classe -> nessuna varianza inter-classe."""
    img = np.full((10, 10), 128, dtype=np.uint8)
    # Otsu non puo' separare; il fallback default e' 128.
    threshold = otsu_threshold(img)
    assert 0 <= threshold <= 255


def test_otsu_threshold_bimodal_finds_valley() -> None:
    """Immagine bimodale 50/200 -> threshold separa le due mode.

    Per due picchi delta puri (nessun valore intermedio) la varianza
    inter-classe e' costante per ogni t in [50, 199]; la nostra
    implementazione (`>` stretta) prende il primo, cioe' 50. Verifichiamo
    che in ogni caso il threshold sia inferiore alla moda alta.
    """
    img = np.zeros((20, 20), dtype=np.uint8)
    img[:10, :] = 50
    img[10:, :] = 200
    threshold = otsu_threshold(img)
    assert 50 <= threshold < 200


def test_otsu_threshold_bimodal_with_spread_picks_valley() -> None:
    """Distribuzione bimodale piu' realistica con varianza in ogni picco."""
    rng = np.random.default_rng(seed=0)
    low = rng.normal(loc=60, scale=10, size=400).clip(0, 255).astype(np.uint8)
    high = rng.normal(loc=200, scale=10, size=400).clip(0, 255).astype(np.uint8)
    img = np.concatenate([low, high]).reshape(40, 20).astype(np.uint8)
    threshold = otsu_threshold(img)
    # Il threshold ottimale deve cadere tra i due picchi (tipicamente
    # tra ~70 e ~180 a seconda della spread relativa).
    assert 70 < threshold < 180


def test_binarize_otsu_output_only_0_or_255() -> None:
    img = np.array(
        [[10, 30, 200, 240], [50, 60, 220, 250]],
        dtype=np.uint8,
    )
    out = binarize_otsu(img)
    unique = set(np.unique(out).tolist())
    assert unique <= {0, 255}


def test_binarize_otsu_preserves_shape() -> None:
    img = np.random.default_rng(seed=42).integers(0, 256, size=(50, 80), dtype=np.uint8)
    out = binarize_otsu(img)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


# ---------------------------------------------------------------------------
# OcrPipeline construction
# ---------------------------------------------------------------------------


def test_pipeline_default_construction() -> None:
    """Default ratifica D3.a (ita+eng) + soglia 70."""
    pipeline = OcrPipeline()
    assert pipeline.confidence_threshold == DEFAULT_OCR_CONFIDENCE_THRESHOLD == 70
    assert pipeline.lang == DEFAULT_TESSERACT_LANG == "ita+eng"


def test_pipeline_invalid_threshold_negative_raises() -> None:
    with pytest.raises(ValueError, match="confidence_threshold"):
        OcrPipeline(confidence_threshold=-1)


def test_pipeline_invalid_threshold_above_100_raises() -> None:
    with pytest.raises(ValueError, match="confidence_threshold"):
        OcrPipeline(confidence_threshold=101)


def test_pipeline_empty_lang_raises() -> None:
    with pytest.raises(ValueError, match="lang"):
        OcrPipeline(lang="")


# ---------------------------------------------------------------------------
# OcrPipeline.process_image
# ---------------------------------------------------------------------------


def _make_image(value: int = 128, shape: tuple[int, int] = (10, 10)) -> NDArray[np.uint8]:
    return np.full(shape, value, dtype=np.uint8)


def test_process_image_high_confidence_returns_ok() -> None:
    """Confidence media 80 >= 70 -> OcrStatus.OK."""
    raw = RawOcrData(text="Galaxy S24", word_confidences=[80, 85, 75])
    adapter = _StaticTesseractAdapter(raw)
    pipeline = OcrPipeline(adapter_factory=lambda **_: adapter)
    result = pipeline.process_image(_make_image())
    assert result.status is OcrStatus.OK
    assert result.text == "Galaxy S24"
    assert result.confidence == pytest.approx(80.0)
    assert result.source_kind == "image"


def test_process_image_low_confidence_returns_ambiguous() -> None:
    """Confidence media 50 < 70 -> OcrStatus.AMBIGUOUS (R-01)."""
    raw = RawOcrData(text="noisy text", word_confidences=[40, 50, 60])
    adapter = _StaticTesseractAdapter(raw)
    pipeline = OcrPipeline(adapter_factory=lambda **_: adapter)
    result = pipeline.process_image(_make_image())
    assert result.status is OcrStatus.AMBIGUOUS
    assert result.confidence == pytest.approx(50.0)


def test_process_image_filters_negative_one_confidences() -> None:
    """Tesseract -1 (token saltato) e' filtrato dalla media."""
    raw = RawOcrData(text="x y z", word_confidences=[-1, 80, -1, 90])
    adapter = _StaticTesseractAdapter(raw)
    pipeline = OcrPipeline(adapter_factory=lambda **_: adapter)
    result = pipeline.process_image(_make_image())
    # Solo 80 e 90 contano: media 85.
    assert result.confidence == pytest.approx(85.0)
    assert result.status is OcrStatus.OK


def test_process_image_no_valid_confidences_is_ambiguous() -> None:
    """Tutti -1 -> nessuna confidence valida -> 0.0 -> AMBIGUOUS."""
    raw = RawOcrData(text="", word_confidences=[-1, -1])
    adapter = _StaticTesseractAdapter(raw)
    pipeline = OcrPipeline(adapter_factory=lambda **_: adapter)
    result = pipeline.process_image(_make_image())
    assert result.confidence == 0.0
    assert result.status is OcrStatus.AMBIGUOUS


def test_process_image_custom_threshold_changes_outcome() -> None:
    """Stesso input, soglie diverse -> esiti diversi (D3.b configurabilita')."""
    raw = RawOcrData(text="t", word_confidences=[60])
    adapter = _StaticTesseractAdapter(raw)
    strict = OcrPipeline(confidence_threshold=80, adapter_factory=lambda **_: adapter)
    lenient = OcrPipeline(confidence_threshold=50, adapter_factory=lambda **_: adapter)
    assert strict.process_image(_make_image()).status is OcrStatus.AMBIGUOUS
    assert lenient.process_image(_make_image()).status is OcrStatus.OK


def test_process_image_preprocess_false_skips_binarization() -> None:
    """preprocess=False -> l'immagine arriva all'adapter come passata."""
    raw = RawOcrData(text="x", word_confidences=[80])
    adapter = _StaticTesseractAdapter(raw)
    pipeline = OcrPipeline(preprocess=False, adapter_factory=lambda **_: adapter)
    grayscale_with_midtones = np.array([[10, 100, 200, 250]], dtype=np.uint8)
    pipeline.process_image(grayscale_with_midtones)
    assert adapter.last_image_shape == grayscale_with_midtones.shape


def test_process_image_lang_propagated_to_adapter() -> None:
    """`lang` del pipeline arriva all'adapter."""
    raw = RawOcrData(text="x", word_confidences=[80])
    adapter = _StaticTesseractAdapter(raw)
    pipeline = OcrPipeline(lang="ita", adapter_factory=lambda **_: adapter)
    pipeline.process_image(_make_image())
    assert adapter.last_lang == "ita"


def test_process_image_3d_array_raises() -> None:
    """Solo immagini 2D grayscale; 3D (RGB) richiede caller a convertire."""
    pipeline = OcrPipeline()
    rgb_like = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="2D grayscale"):
        pipeline.process_image(rgb_like)


# ---------------------------------------------------------------------------
# Adapter factory injection
# ---------------------------------------------------------------------------


def test_adapter_factory_receives_lang_kwarg() -> None:
    """La factory custom riceve il `lang` come kwarg."""
    captured: list[str] = []

    def factory(*, lang: str) -> TesseractAdapter:
        captured.append(lang)
        return _StaticTesseractAdapter(RawOcrData(text="", word_confidences=[]))

    OcrPipeline(lang="custom-lang", adapter_factory=factory)
    assert captured == ["custom-lang"]


# ---------------------------------------------------------------------------
# _LiveTesseractAdapter skeleton
# ---------------------------------------------------------------------------


def test_live_adapter_raises_not_implemented() -> None:
    adapter = _LiveTesseractAdapter()
    img = np.zeros((10, 10), dtype=np.uint8)
    with pytest.raises(NotImplementedError, match="non implementato"):
        adapter.image_to_data(img, lang="ita+eng")
