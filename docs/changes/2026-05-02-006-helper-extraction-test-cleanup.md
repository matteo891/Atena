---
id: CHG-2026-05-02-006
date: 2026-05-02
author: Claude (modalità "ultra macinata burst medium" round 7)
status: Draft
adr_ref: ADR-0016, ADR-0019, ADR-0014
commit: abbbf22
---

## What

**Burst code health**: estrazione helper testabile + cleanup test residuo.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/ui/listino_input.py` | modificato | + `format_v_tot_source_caption(df) -> str` (helper puro testabile, simmetrico a `format_cache_hit_caption` / `format_buybox_verified_caption`). Aggrega `v_tot_source` da listino_raw output di `build_listino_raw_from_resolved`; ritorna stringa per CFO audit. Empty df / colonna mancante / counts 0 -> stringa vuota (caller suppress). |
| `src/talos/ui/dashboard.py` | modificato | Inline logic V_tot caption (CHG-005 ~12 righe) → 2 righe import + chiamata helper. -10 righe LOC dashboard, +1 funzione testabile in isolamento. |
| `tests/unit/test_listino_input.py` | modificato | + 1 test parametrico `test_format_v_tot_source_caption` (4 cases: empty / single CSV / single BSR estimate / mixed 3-way). |
| `tests/unit/test_velocity_estimator.py` | modificato | -1 test `test_estimate_doctest_consistency` (replica del doctest già presente nel modulo source — eccesso di zelo). -1 import `math` non più necessario. |

Quality gate **verde**: ruff/format/mypy strict puliti. Pytest:
- **731 PASS** unit/gov/golden (era 728: +4 cases parametrico - 1 rimosso = +3 net).
- **138 PASS** integration (invariato).
- **869 PASS** totali.

## Why

Direttiva Leader "ultra macinata + snellire eccesso di zelo":

1. **Helper extraction** (`format_v_tot_source_caption`): la logica
   inline in `dashboard.py` (CHG-005) era 12 righe, non testabile in
   isolamento, divergente dal pattern dei sibling helper
   `format_*_caption`. Estrazione = simmetria + testabilità +
   riduzione complessità funzione `_render_descrizione_prezzo_flow_body`.

2. **Test doctest replicato**: `test_estimate_doctest_consistency`
   verificava `estimate_v_tot_from_bsr(10000) == 100 - 20*log10(10000)`
   — ma il doctest del modulo source già asserisce `round(... 2) == 20.0`
   per quel caso. Test unit ridondante (eccesso di zelo).

## Tests

| Step | Esito |
|---|---|
| ruff/format/mypy strict | All passed |
| Unit/gov/golden | **731 PASS** (+3 net: +4 parametrici, -1 doctest replica) |
| Integration | **138 PASS** invariato |
| Sentinel `format_v_tot_source_caption` | empty / single-source / multi-source |

## Test di Conformità

- ADR-0016 (UI Streamlit) ✓: pattern helper formatter coerente.
- ADR-0019 (test strategy) ✓: rule-of-three soddisfatta (`format_*_caption`
  family ora 4 helper + 4 test parametrici).
- ADR-0014 (mypy/ruff strict): 0 issues.
- Behavior runtime invariato 100% (caption render identico, solo
  source location moved).
- `feedback_concisione_documentale.md` rispettato.

## Refs

- ADR: ADR-0016, ADR-0019, ADR-0014.
- Predecessore: CHG-2026-05-02-005 (logic inline introdotta).
- Pattern fratelli: `format_cache_hit_caption` (CHG-026),
  `format_buybox_verified_caption` (CHG-027).
- Commit: TBD.
