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

from talos.extract.acquisition import acquire_and_persist
from talos.extract.asin_master_writer import (
    AsinMasterInput,
    build_asin_master_input,
    upsert_asin_master,
)
from talos.extract.asin_resolver import (
    CONFIDENCE_WEIGHT_PRICE,
    CONFIDENCE_WEIGHT_TITLE,
    DEFAULT_AMBIGUOUS_THRESHOLD_PCT,
    AsinResolverProtocol,
    ResolutionCandidate,
    ResolutionResult,
    compute_confidence,
    is_ambiguous,
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
from talos.extract.velocity_estimator import (
    V_TOT_SOURCE_BSR_ESTIMATE,
    V_TOT_SOURCE_CSV,
    V_TOT_SOURCE_DEFAULT_ZERO,
    estimate_v_tot_from_bsr,
    resolve_v_tot,
)

__all__ = [
    "CONFIDENCE_WEIGHT_PRICE",
    "CONFIDENCE_WEIGHT_TITLE",
    "DEFAULT_AMBIGUOUS_THRESHOLD_PCT",
    "DEFAULT_COLOR_FUZZY_THRESHOLD",
    "DEFAULT_CONFIDENCE_AMBIGUO_THRESHOLD",
    "DEFAULT_CONFIDENCE_SICURO_THRESHOLD",
    "DEFAULT_FIELD_WEIGHTS",
    "DEFAULT_WHITELIST_YAML",
    "V_TOT_SOURCE_BSR_ESTIMATE",
    "V_TOT_SOURCE_CSV",
    "V_TOT_SOURCE_DEFAULT_ZERO",
    "AsinMasterInput",
    "AsinResolverProtocol",
    "MatchResult",
    "MatchStatus",
    "ResolutionCandidate",
    "ResolutionResult",
    "SamsungEntities",
    "SamsungExtractor",
    "acquire_and_persist",
    "build_asin_master_input",
    "compute_confidence",
    "estimate_v_tot_from_bsr",
    "is_ambiguous",
    "load_whitelist",
    "resolve_v_tot",
    "upsert_asin_master",
]
