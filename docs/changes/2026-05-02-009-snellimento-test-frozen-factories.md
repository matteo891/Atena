---
id: CHG-2026-05-02-009
date: 2026-05-02
adr_ref: ADR-0019, ADR-0014
commit: TBD
---

## What

Snellimento test eccesso di zelo (round 2): rimossi 4 test che verificavano
garanzie del linguaggio Python (decorator `@dataclass`, `field(default_factory)`).

| File | Cosa rimosso |
|---|---|
| `tests/unit/test_orchestrator.py` | `test_session_input_is_frozen` (frozen=True garantito da `@dataclass`) |
| `tests/unit/test_asin_resolver_skeleton.py` | `test_resolution_candidate_is_frozen` |
| `tests/unit/test_ocr_pipeline.py` | `test_ocr_result_is_frozen` |
| `tests/unit/test_fallback_chain.py` | `test_product_data_default_factories_are_independent` (`field(default_factory=list)` garantisce per-istanza) |

## Tests

ruff/format/mypy strict OK. **874 PASS** (736 unit/gov/golden -4 + 138 integration). Behavior runtime invariato.

## Refs

- ADR-0019, ADR-0014.
- Direttiva Leader: "elimina ogni eccesso da governance e test".
- Predecessore CHG-2026-05-02-004 (snellimento round 1).
- Commit: TBD.
