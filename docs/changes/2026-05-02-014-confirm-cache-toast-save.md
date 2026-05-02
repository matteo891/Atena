---
id: CHG-2026-05-02-014
date: 2026-05-02
adr_ref: ADR-0016, ADR-0014
commit: TBD
---

## What

UX safety + feedback: confirm 2-step su reset cache (azione distruttiva)
+ `st.toast` post-save sessione.

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | Sidebar "Manutenzione cache": click "Svuota cache risoluzioni" → mostra warning "Confermi? Irreversibile" + bottoni "Sì, svuota" (primary) / "Annulla". Stato in `st.session_state["cache_reset_confirm_pending"]`. + `st.toast()` icone (`🧹` cache cleared, `✓` sessione salvata, `⚠️` errore persistenza) oltre `st.success/error`. Toast sono notifica non-blocking nell'angolo. |

## Tests

ruff/format/mypy strict OK. **878 PASS** (740 + 138). Pure UX, zero behavior runtime.

## Refs

- ADR-0016, ADR-0014.
- Predecessore: CHG-013 (UI polish).
- Commit: TBD.
