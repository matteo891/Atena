"""SamsungExtractor — NLP regex + rapidfuzz + R-05 KILL-SWITCH (ADR-0017 + R-05).

CHG-2026-05-01-004 inaugura `src/talos/extract/`. Decisioni di
design (D4 ratificata "default" Leader 2026-04-30 sera, memory
`project_io_extract_design_decisions.md`):

- D4.a NLP: C = regex pure + `rapidfuzz` per fuzzy matching
  (no spaCy: trasparenza > resilienza marginale, dep leggera).
- D4.b Whitelist 5G: C = YAML versionato in
  `extract/samsung_whitelist.yaml` (patch operativa rapida).
- D4.c Confidence: B = weighted sum (`model=3, ram_gb=2,
  rom_gb=2, color=1, connectivity=1`); soglie `SICURO`/`AMBIGUO`
  configurabili.

Pipeline interna (PROJECT-RAW L07): tokenize -> estrai entita'
(modello/ROM/RAM/connettivita'/colore/Enterprise) -> applica
whitelist 5G -> confronta lati fornitore/Amazon -> emit
`MATCH_SICURO` / `AMBIGUO` / `MISMATCH`.

R-05 KILL-SWITCH HARDWARE: sul `MISMATCH` dell'identita' del
modello (entrambi non None ma diversi), il caller (orchestrator
+ vgp.score) deve forzare `vgp_score=0` (verbatim PROJECT-RAW
riga 223) e loggare l'evento canonico `extract.kill_switch`
(ADR-0021 dormiente; attivato in CHG-2026-05-01-005).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from rapidfuzz import fuzz, process

if TYPE_CHECKING:
    from collections.abc import Mapping

_logger = logging.getLogger(__name__)

DEFAULT_WHITELIST_YAML = Path(__file__).parent / "samsung_whitelist.yaml"

# Pesi confidence (D4.c default; configurabili via SamsungExtractor)
DEFAULT_FIELD_WEIGHTS: dict[str, int] = {
    "model": 3,
    "ram_gb": 2,
    "rom_gb": 2,
    "color": 1,
    "connectivity": 1,
}
DEFAULT_CONFIDENCE_SICURO_THRESHOLD = 0.85
DEFAULT_CONFIDENCE_AMBIGUO_THRESHOLD = 0.50
DEFAULT_COLOR_FUZZY_THRESHOLD = 80


class MatchStatus(StrEnum):
    """Esito del confronto fornitore vs Amazon (R-05).

    - `SICURO`: confidence >= sicuro_threshold; la riga puo' procedere.
    - `AMBIGUO`: ambiguo_threshold <= confidence < sicuro_threshold;
      esclusa dal carrello, mostrata al CFO per validazione manuale.
    - `MISMATCH`: confidence < ambiguo_threshold OPPURE model
      mismatch hard (R-05). Il caller forza VGP=0 + evento
      `extract.kill_switch`.
    """

    SICURO = "SICURO"
    AMBIGUO = "AMBIGUO"
    MISMATCH = "MISMATCH"


@dataclass(frozen=True)
class SamsungEntities:
    """Attributi normalizzati estratti da un titolo Samsung.

    Tutti i campi sono opzionali: `None` significa "non estratto".
    Il match usa la presenza/assenza per il calcolo confidence
    (campi None contano come 0 nello score).
    """

    model: str | None = None
    ram_gb: int | None = None
    rom_gb: int | None = None
    color: str | None = None
    connectivity: str | None = None
    enterprise: bool = False


@dataclass(frozen=True)
class MatchResult:
    """Risultato del confronto fornitore vs Amazon.

    `confidence` in [0, 1]: 1 = match perfetto su tutti i campi
    pesati. `matched_fields` / `mismatched_fields` per audit.
    """

    status: MatchStatus
    confidence: float
    matched_fields: list[str]
    mismatched_fields: list[str]


@dataclass(frozen=True)
class _Whitelist:
    """Schema interno parsed di samsung_whitelist.yaml."""

    models_5g: list[str]
    ram_gb_canonical: list[int]
    rom_gb_canonical: list[int]
    colors_canonical: list[str]


def load_whitelist(path: Path = DEFAULT_WHITELIST_YAML) -> _Whitelist:
    """Carica e valida `samsung_whitelist.yaml`."""
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        msg = f"samsung_whitelist.yaml invalido in {path}: deve essere un mapping"
        raise TypeError(msg)
    required = ("models_5g", "ram_gb_canonical", "rom_gb_canonical", "colors_canonical")
    missing = [k for k in required if k not in raw]
    if missing:
        msg = f"samsung_whitelist.yaml in {path}: mancano chiavi {missing}"
        raise ValueError(msg)
    return _Whitelist(
        models_5g=list(raw["models_5g"]),
        ram_gb_canonical=list(raw["ram_gb_canonical"]),
        rom_gb_canonical=list(raw["rom_gb_canonical"]),
        colors_canonical=list(raw["colors_canonical"]),
    )


# Regex compilate riusabili
_RAM_PATTERN = re.compile(r"\b(\d{1,2})\s?GB\s?RAM\b", re.IGNORECASE)
_RAM_INLINE_PATTERN = re.compile(r"\b(\d{1,2})\+(\d{2,4})\b")
_ROM_GB_PATTERN = re.compile(r"\b(\d{2,4})\s?GB\b", re.IGNORECASE)
_CONNECTIVITY_PATTERN = re.compile(r"\b(5G|4G|LTE)\b", re.IGNORECASE)
_ENTERPRISE_PATTERN = re.compile(r"\b(Enterprise(?:\s+Edition)?|EE)\b", re.IGNORECASE)


class SamsungExtractor:
    """Estrattore NLP per smartphone Samsung — MVP (L06).

    Architettura modulare: candidata implementazione futura
    `BrandExtractor` interface astratta. Multi-brand
    (`AppleExtractor`, `XiaomiExtractor`) rinviato post-MVP.

    Uso:
        extractor = SamsungExtractor()
        sup = extractor.parse_title("Samsung Galaxy S24 5G 256GB 12GB RAM Titanium Black")
        amz = extractor.parse_title(amazon_title)
        result = extractor.match(supplier=sup, amazon=amz)
        if result.status is MatchStatus.MISMATCH:
            # R-05 KILL-SWITCH: caller forza VGP=0 + evento extract.kill_switch
            ...
    """

    def __init__(
        self,
        *,
        whitelist_path: Path = DEFAULT_WHITELIST_YAML,
        field_weights: Mapping[str, int] | None = None,
        sicuro_threshold: float = DEFAULT_CONFIDENCE_SICURO_THRESHOLD,
        ambiguo_threshold: float = DEFAULT_CONFIDENCE_AMBIGUO_THRESHOLD,
        color_fuzzy_threshold: int = DEFAULT_COLOR_FUZZY_THRESHOLD,
    ) -> None:
        if not 0 < ambiguo_threshold < sicuro_threshold <= 1:
            msg = (
                f"thresholds invalide: 0 < ambiguo({ambiguo_threshold}) "
                f"< sicuro({sicuro_threshold}) <= 1"
            )
            raise ValueError(msg)
        if not 0 <= color_fuzzy_threshold <= 100:  # noqa: PLR2004
            msg = (
                f"color_fuzzy_threshold invalido: {color_fuzzy_threshold}. "
                "Deve essere intero in [0, 100] (scala rapidfuzz)."
            )
            raise ValueError(msg)
        self._whitelist = load_whitelist(whitelist_path)
        self._weights = (
            dict(field_weights) if field_weights is not None else dict(DEFAULT_FIELD_WEIGHTS)
        )
        self._sicuro_threshold = sicuro_threshold
        self._ambiguo_threshold = ambiguo_threshold
        self._color_fuzzy_threshold = color_fuzzy_threshold

    @property
    def whitelist_5g_models(self) -> list[str]:
        return list(self._whitelist.models_5g)

    @property
    def field_weights(self) -> Mapping[str, int]:
        return dict(self._weights)

    def parse_title(self, raw_title: str) -> SamsungEntities:
        """Estrae entita' canoniche da titolo grezzo. Tutti i campi opzionali."""
        normalized = raw_title.strip()
        return SamsungEntities(
            model=self._extract_model(normalized),
            ram_gb=self._extract_ram(normalized),
            rom_gb=self._extract_rom(normalized),
            color=self._extract_color(normalized),
            connectivity=self._extract_connectivity(normalized),
            enterprise=bool(_ENTERPRISE_PATTERN.search(normalized)),
        )

    def _extract_model(self, text: str) -> str | None:
        """Longest-match dalla whitelist (case-insensitive). 'S24 Ultra' prima di 'S24'."""
        text_lower = text.lower()
        candidates = sorted(self._whitelist.models_5g, key=len, reverse=True)
        for model in candidates:
            if model.lower() in text_lower:
                return model
        return None

    def _extract_ram(self, text: str) -> int | None:
        """Estrae RAM in GB; ritorna solo se nella whitelist canonica."""
        m = _RAM_PATTERN.search(text)
        if m:
            value = int(m.group(1))
            if value in self._whitelist.ram_gb_canonical:
                return value
        m2 = _RAM_INLINE_PATTERN.search(text)
        if m2:
            ram_value = int(m2.group(1))
            if ram_value in self._whitelist.ram_gb_canonical:
                return ram_value
        return None

    def _extract_rom(self, text: str) -> int | None:
        """Estrae ROM in GB; salta i match seguiti da 'RAM' (e' la RAM)."""
        for match in _ROM_GB_PATTERN.finditer(text):
            value = int(match.group(1))
            after = text[match.end() : match.end() + 6].upper()
            if "RAM" in after:
                continue
            if value in self._whitelist.rom_gb_canonical:
                return value
        m2 = _RAM_INLINE_PATTERN.search(text)
        if m2:
            rom_value = int(m2.group(2))
            if rom_value in self._whitelist.rom_gb_canonical:
                return rom_value
        return None

    def _extract_color(self, text: str) -> str | None:
        """Estrae colore via `rapidfuzz.partial_ratio` (D4.a)."""
        best = process.extractOne(
            text,
            self._whitelist.colors_canonical,
            scorer=fuzz.partial_ratio,
            score_cutoff=self._color_fuzzy_threshold,
        )
        return str(best[0]) if best else None

    def _extract_connectivity(self, text: str) -> str | None:
        m = _CONNECTIVITY_PATTERN.search(text)
        if not m:
            return None
        value = m.group(1).upper()
        return "4G" if value in {"4G", "LTE"} else "5G"

    def match(
        self,
        *,
        supplier: SamsungEntities,
        amazon: SamsungEntities,
    ) -> MatchResult:
        """Confronta fornitore vs Amazon e calcola status R-05.

        Pesi (D4.c default): `model=3`, `ram_gb=2`, `rom_gb=2`,
        `color=1`, `connectivity=1`. Confidence = score / sum(pesi).
        Campi `None` contano come zero (no contributo allo score).

        R-05 hard: model mismatch (entrambi non None ma diversi)
        forza `MISMATCH` a prescindere dalla confidence aggregata.
        Il caller (orchestrator + vgp.score) forza `vgp_score=0`.
        """
        max_weight = sum(self._weights.values())
        matched_fields: list[str] = []
        mismatched_fields: list[str] = []
        score = 0
        model_mismatch_hard = (
            supplier.model is not None
            and amazon.model is not None
            and supplier.model != amazon.model
        )
        for field_name, sup_value, amz_value in (
            ("model", supplier.model, amazon.model),
            ("ram_gb", supplier.ram_gb, amazon.ram_gb),
            ("rom_gb", supplier.rom_gb, amazon.rom_gb),
            ("color", supplier.color, amazon.color),
            ("connectivity", supplier.connectivity, amazon.connectivity),
        ):
            if sup_value is None or amz_value is None:
                continue
            if sup_value == amz_value:
                score += self._weights.get(field_name, 0)
                matched_fields.append(field_name)
            else:
                mismatched_fields.append(field_name)
        confidence = score / max_weight if max_weight > 0 else 0.0
        if model_mismatch_hard:
            # Telemetria CHG-2026-05-01-005: R-05 KILL-SWITCH HARDWARE.
            # Catalogo ADR-0021 evento canonico `extract.kill_switch`.
            # Il caller (orchestrator + vgp.score) forza vgp_score=0.
            _logger.debug(
                "extract.kill_switch",
                extra={
                    "asin": "<n/a>",
                    "reason": "model_mismatch",
                    "mismatch_field": "model",
                    "expected": supplier.model,
                    "actual": amazon.model,
                },
            )
            return MatchResult(
                status=MatchStatus.MISMATCH,
                confidence=confidence,
                matched_fields=matched_fields,
                mismatched_fields=mismatched_fields,
            )
        if confidence >= self._sicuro_threshold:
            status = MatchStatus.SICURO
        elif confidence >= self._ambiguo_threshold:
            status = MatchStatus.AMBIGUO
        else:
            status = MatchStatus.MISMATCH
        return MatchResult(
            status=status,
            confidence=confidence,
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
        )
