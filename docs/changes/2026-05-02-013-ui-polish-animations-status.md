---
id: CHG-2026-05-02-013
date: 2026-05-02
adr_ref: ADR-0016, ADR-0014
commit: TBD
---

## What

UI polish round 2: animazioni d'ingresso + status indicators sidebar +
hero mark gradient.

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | + CSS keyframes `talos-fade-in` (cards + hero ingresso 480ms) con stagger 60ms tra card. + `talos-pulse-gold` su bottoni primary focus. Hero mark `◆` con gradient oro multistop (`#C9A961 → #E8D08B → #C9A961`). + classe `.talos-status` con dot colorato (ok=verde glow / warn=ambra / off=grigio). + helper `_render_sidebar_status()` mostra DB/Keepa connection state in cima alla sidebar (CFO vede salute sistema a colpo d'occhio). |

## Tests

ruff/format/mypy strict OK. **878 PASS** (740 unit/gov/golden + 138 integration). Pure CSS/UI, zero behavior change.

## Refs

- ADR-0016, ADR-0014.
- Predecessore CHG-012 (portale + module cards).
- Commit: TBD.
