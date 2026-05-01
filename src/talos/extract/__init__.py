"""Estrazione entita' brand-specific — ADR-0017.

Inaugurato in CHG-2026-05-01-004 con `SamsungExtractor` (MVP
Samsung-only, L06 PROJECT-RAW). Architettura modulare:
`SamsungExtractor` implementa la futura interfaccia
`BrandExtractor` astratta. Estensione multi-brand
(`AppleExtractor`, `XiaomiExtractor`, ...) rinviata post-MVP.

Pipeline interna (L07): tokenize -> estrai entita' -> whitelist
5G -> confronta -> emit `MATCH_SICURO` / `AMBIGUO` / `MISMATCH`
(R-05 KILL-SWITCH HARDWARE forza VGP=0 sul caller).

Vedi memory `project_io_extract_design_decisions.md` per il
pacchetto D1-D5 ratificato dal Leader.
"""

from talos.extract.asin_master_writer import (
    AsinMasterInput,
    build_asin_master_input,
    upsert_asin_master,
)
from talos.extract.samsung import (
    DEFAULT_COLOR_FUZZY_THRESHOLD,
    DEFAULT_CONFIDENCE_AMBIGUO_THRESHOLD,
    DEFAULT_CONFIDENCE_SICURO_THRESHOLD,
    DEFAULT_FIELD_WEIGHTS,
    DEFAULT_WHITELIST_YAML,
    MatchResult,
    MatchStatus,
    SamsungEntities,
    SamsungExtractor,
    load_whitelist,
)

__all__ = [
    "DEFAULT_COLOR_FUZZY_THRESHOLD",
    "DEFAULT_CONFIDENCE_AMBIGUO_THRESHOLD",
    "DEFAULT_CONFIDENCE_SICURO_THRESHOLD",
    "DEFAULT_FIELD_WEIGHTS",
    "DEFAULT_WHITELIST_YAML",
    "AsinMasterInput",
    "MatchResult",
    "MatchStatus",
    "SamsungEntities",
    "SamsungExtractor",
    "build_asin_master_input",
    "load_whitelist",
    "upsert_asin_master",
]
