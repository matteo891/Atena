---
id: CHG-2026-05-02-027
date: 2026-05-02
adr_ref: ADR-0016, ADR-0019, ADR-0014
commit: 1c792e6
---

## What

UI restyle FASE 1 step 3: cart table 13-colonne enriched ScalerBot-like.
Sostituisce le 6 colonne attuali (`asin/qty/cost_total/vgp_score/locked/
reason`) con 13 colonne ricche derivate da JOIN cart × enriched_df.

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | + helper puro `_build_enriched_cart_view(result) -> list[dict]` (JOIN cart_items × enriched_df su `asin`, costruisce dict 13-col + `vel_badge` classificato). + helper `_classify_velocity_badge(velocity_monthly) -> str` (R-01: ≥30/m=Veloce, ≥10/m=Buona, <10/m=Lento — soglie placeholder pre-errata ADR-0018). `_render_cart_table` aggiornato per consumare la nuova vista (column order ScalerBot-like: ASIN/HW_ID shell/PRODOTTO shell/FORNITORE shell/CST/PRFT_unit/VGP/MRG_shell/ROI/VEL/Q.15GG/STOCK shell/QTA/PRFT_total/SPESA_total/A/M shell/AZIONI). FORNITORE/STOCK/HW_ID/MRG/A/M sentinel `—` in attesa CHG-028+. Caption count "N/M ASIN allocati" + lista reason flag invariata. Export CSV preservato. |
| `tests/unit/test_dashboard_cart_enriched.py` | nuovo: 8 test puri (JOIN cart×enriched, vel_badge classification, sentinel shell, empty cart, qty=0 row preservation, locked flag, ASIN missing in enriched_df, column order sentinel). |

## Why

Mockup ScalerBot 500K (Leader 2026-05-02) mostra cart con 13 colonne
ricche di dato per CFO: HW ID composito (model/ram/rom/conn) + fornitore
+ 3 metriche PRFT/CST/VGP in cella + ROI/MRG percentuali + velocity badge
visivo + Q.15GG / STOCK / QTA editabile + PRFT/SPESA totali + A/M
validation + AZIONI inline.

Il nostro `enriched_df` ha già tutti i dati numerici (CHG-022 cart
exhaustive → CHG-038 ROI veto → CHG-053 referral fee resolved). Il JOIN
su `asin` produce la vista flat 13-col senza toccare pipeline/DB.

Le 5 colonne shell (`HW_ID`/`FORNITORE`/`STOCK`/`MRG`/`A/M`) sono
sentinel `—` come da decisione Leader 2026-05-02 round 7+: "tutto quello
che non capisci per ora è shell". Wireup in CHG-028+ (Anagrafica modal
preliminare) e ADR risk-filters Arsenale per `MRG`/`A/M`.

`vel_badge` classification: soglie deterministiche placeholder MVP
(≥30/m Veloce / ≥10/m Buona / <10/m Lento). Errata ADR-0018 con valori
ratificati Leader prevista FASE 2 del piano restyle.

## Tests

ruff/format/mypy strict OK. **TBD PASS** (TBD unit/gov/golden + 160 integration).

- 8 test `_build_enriched_cart_view` + `_classify_velocity_badge` puri.
- Test esistenti `_render_cart_table` invariati signature; smoke import
  preservato (CHG-026 sentinel kw-only ancora valido).
- Golden Samsung-mini snapshot invariato (cart row count e qty intatti;
  il display order è cosmetic UX).

## Test di Conformità

- ADR-0016 (UI): puro Streamlit + helper puri (JOIN pandas, classifier).
- ADR-0019 (test strategy): test parametrici velocity boundary 0/10/30/100.
- ADR-0014 (quality gates): ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: ASIN cart non presente in enriched_df → KeyError
  esplicito (non dovrebbe mai accadere — cart è subset di enriched).

## Refs

- ADR-0016, ADR-0019, ADR-0014.
- Predecessori: CHG-2026-05-02-022 (cart exhaustive), CHG-2026-05-02-026
  (tab strip).
- Mockup ScalerBot 500K (Leader 2026-05-02).
- Soglie velocity badge: placeholder MVP, errata ADR-0018 prevista
  FASE 2 (Leader ratificherà valori autoritativi).
- Commit: `1c792e6`.
