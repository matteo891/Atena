---
id: CHG-2026-05-02-012
date: 2026-05-02
adr_ref: ADR-0016, ADR-0019, ADR-0014
commit: TBD
---

## What

Redesign UI: portale TALOS multi-modulo + modulo Demetra · Scaler 500k.
Dispatch via `st.session_state.current_module`.

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | `main()` ora dispatcher portale/modulo. + `_render_portal()` (3 module cards: Demetra live + Hermes/Atena coming soon). + `_render_module_header(codename, module_name, subtitle)` con breadcrumb + back button. + `_section(num, title)` divider numerato con accent oro. Esistente `main()` body estratto in `_render_demetra_module()`. CSS sostanziale +200 righe: hero card gradient + module cards con hover lift + hero metric tiles + section dividers con underline oro + empty states con icone `◇ ◇ ◇` + sidebar polished + bottoni primary gradient + footer. Empty states `Cart vuoto`/`Panchina vuota` ora visivi (talos-empty container). 4 `st.subheader` interni → `_section()` numerati. |

## Tests

ruff/format/mypy strict OK. **878 PASS** (740 unit/gov/golden + 138 integration). Nessun behavior change su pipeline / DB / formule. UI puro.

## Refs

- ADR-0016 (UI Streamlit), ADR-0019, ADR-0014.
- Direttiva Leader: "portale TALOS → modulo Demetra via bottone, ingegnerizza interfaccia".
- Predecessore CHG-007 (theme oro tenue base).
- Commit: TBD.
