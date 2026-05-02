---
id: CHG-2026-05-02-015
date: 2026-05-02
adr_ref: ADR-0016, ADR-0014
commit: TBD
---

## What

`st.spinner` durante resolve descrizioni → `st.status` rich con step
log. CFO vede cosa sta facendo il sistema invece di "spinner mute".

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | `with st.spinner(...)` → `with st.status(...) as status`. Step trace verbose: apertura browser headless, SERP top-3 candidati, verifica live Keepa, confidence scoring. Update finale "Risolte N righe ✓" + `state="complete"`. |

## Tests

ruff/format/mypy strict OK. **878 PASS** (740 + 138). Zero behavior runtime.

## Refs

- ADR-0016, ADR-0014.
- Predecessore: CHG-014 (toast).
- Commit: TBD.
