---
id: CHG-2026-05-02-028
date: 2026-05-02
adr_ref: ADR-0016, ADR-0015, ADR-0019, ADR-0014
commit: 0305290
---

## What

UI restyle FASE 1 step 4 (chiusura): bottoni funzionali Anagrafica
(modal AsinMaster) + Esporta ORDINE + STRATEGIA (CSV download con
metadata ciclo) + Override shell. Conclude il piano UI restyle base.

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | + helper `fetch_asin_masters_or_empty(factory, asins, *, tenant_id)` (graceful query AsinMaster ORM filtrata per ASIN list cart, ritorna list[dict]). + helper `_render_anagrafica_modal(factory, cart_items, *, tenant_id)` (expander con dataframe AsinMaster: ASIN/brand/model/ram/rom/category_node/last_seen_at). + helper `_build_ordine_strategia_csv(result, inp) -> bytes` (puro: cart enriched + commento header con metadata ciclo budget/velocity/veto/data). + helper `_render_export_ordine_strategia(result, inp)` (st.download_button CTA). + bottone shell "Override" nel header (4° pulsante shell, semantica per ASIN da chiarire). Render order: cycle overview → action_buttons (3 shell) + Override shell + Anagrafica + Esporta CTA → tabs. |
| `tests/unit/test_dashboard_anagrafica_export.py` | nuovo: 6 test puri (`_build_ordine_strategia_csv` content/header/empty cart, `fetch_asin_masters_or_empty` graceful None factory, smoke import helpers). |

## Why

Mockup ScalerBot 500K: 5 bottoni azione header (Override / Satura Cash /
WhatsApp / Anagrafica / Chiudi Ciclo) + CTA "Esporta ORDINE + STRATEGIA"
sopra il cart. CHG-026 ha aggiunto i 3 bottoni shell (Satura Cash /
WhatsApp / Chiudi Ciclo). CHG-028 chiude:

- **Anagrafica**: bottone REALE, AsinMaster già popolato in `asin_master`
  via `upsert_asin_master` (CHG-2026-05-01-005). Dati esistenti, zero
  blast radius pipeline. Mostra brand/model/ram/rom/category_node per
  ogni ASIN cart corrente.
- **Esporta ORDINE+STRATEGIA**: bottone REALE, CSV con cart 13-col + 5
  righe commento metadata ciclo (`# budget=…`, `# velocity_target=…`,
  `# veto_roi=…`, `# saturation=…`, `# generated=ISO`). CFO può forwardare
  l'ordine al fornitore con tutti i parametri di sessione.
- **Override**: bottone SHELL (4°). Semantica esatta da chiarire con
  Leader (override per ASIN? config_overrides global?). Tooltip dice
  "In arrivo".

`fetch_asin_masters_or_empty` graceful pattern già usato per altre
query (sessions/orders/replay): factory=None → list vuota; eccezione →
log + list vuota. UI mostra `st.info` placeholder se vuota.

## Tests

ruff/format/mypy strict OK. **TBD PASS** (TBD unit/gov/golden + 160 integration).

- 3 test `_build_ordine_strategia_csv` (content/header/empty).
- 1 test `fetch_asin_masters_or_empty` graceful None factory.
- 2 smoke test import helpers.
- Test esistenti `_render_cart_table` invariati.

## Test di Conformità

- ADR-0016 (UI): puro Streamlit + helper puri (CSV builder, query graceful).
- ADR-0015 (persistenza): query AsinMaster invariante schema (read-only).
- ADR-0019 (test strategy): test puri + graceful None pattern.
- ADR-0014 (quality gates): ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: factory=None → list vuota + UI placeholder
  (non drop silente, segnalato esplicitamente).

## Refs

- ADR-0016, ADR-0015, ADR-0019, ADR-0014.
- Predecessori: CHG-2026-05-02-027 (cart table 13-col enriched),
  CHG-2026-05-01-005 (asin_master_writer + telemetria).
- Mockup ScalerBot 500K (Leader 2026-05-02).
- Override semantica: scope futuro (CHG separato + decisione Leader).
- Commit: `0305290`.
