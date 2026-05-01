---
id: CHG-2026-05-02-008
date: 2026-05-02
adr_ref: ADR-0017, ADR-0018, ADR-0016, ADR-0019
commit: TBD
---

## What

Burst valore CFO: calibration scaffolding + export CSV cart/panchina.

| File | Cosa |
|---|---|
| `scripts/calibrate_v_tot.py` | nuovo: fit log-lineare ai minimi quadrati su CSV ground truth (`asin,bsr,v_tot_real`). Output: `intercept`, `slope`, `R²` + suggerimento errata ADR-0018. Helper Leader per ricalibrare formula MVP placeholder quando avrà dati storici reali. |
| `tests/unit/test_calibrate_v_tot.py` | 3 test (perfect-fit recovery, insufficient sample, invalid BSR). |
| `src/talos/ui/dashboard.py` | + `st.download_button` per export Cart e Panchina come CSV. CFO può scaricare per inviare ordini al fornitore senza copy-paste. |

## Tests

ruff/format/mypy strict OK. Pytest **878 PASS** (740 unit/gov/golden + 138 integration). Risk LOW.

## Refs

- ADR: ADR-0017 (acquisizione), ADR-0018 (formule), ADR-0016 (UI), ADR-0019 (test).
- Direttiva Leader: "valore CFO reale".
- Predecessore: CHG-2026-05-02-007 (multi-format upload + UI redesign).
- Commit: TBD.
