---
id: CHG-2026-05-02-032
date: 2026-05-02
adr_ref: ADR-0023, ADR-0018, ADR-0021, ADR-0019, ADR-0014
commit: 16ad542
---

## What

Implementazione applicativa ADR-0023 90-Day Stress Test (ratificato
`Active` in CHG-030). Hard veto ASIN dove `cash_inflow_eur(avg90)
< cost_eur` (perdita catastrofica se prezzo torna a media).

| File | Cosa |
|---|---|
| `src/talos/risk/stress_test.py` | nuovo. `passes_90d_stress_test(*, buy_box_avg90, cost_eur, fee_fba_eur, referral_fee_rate) -> bool` (riusa `cash_inflow_eur` esistente, R-01 break-even). `is_stress_test_failed_mask(df, *, avg90_col, cost_col, fee_fba_col, referral_fee_col) -> pd.Series[bool]` vettoriale. NaN `avg90` → False (= NOT failed = pass, decisione Leader default). |
| `src/talos/risk/__init__.py` | Re-export `passes_90d_stress_test` + `is_stress_test_failed_mask`. |
| `src/talos/vgp/score.py` | + kwarg `avg90_col: str = "buy_box_avg90"` in `compute_vgp_score`. Mask attiva graceful (skip se `avg90` non in colonne). Composizione: `kill\|~veto_passed\|amazon_dominant\|stress_test_failed`. Telemetria `vgp.stress_test_failed`. |
| `src/talos/observability/events.py` | + voce catalogo `vgp.stress_test_failed` (asin/buy_box_live/buy_box_avg90/cost) + costante `EVENT_VGP_STRESS_TEST_FAILED`. Catalogo ADR-0021 ora 22 eventi. |
| `tests/unit/test_risk_stress_test.py` | nuovo: 14 test (boundary break-even / NaN handling / vettoriale / integrazione vgp / telemetria / backwards-compat). |
| `tests/unit/test_events_catalog.py` | + voce `vgp.stress_test_failed` in `_EXPECTED_EVENTS`. |

## Why

ADR-0023 ratificato `Active` con default Leader 2026-05-02:
- Window: **90 giorni fisso**.
- Severità: **break-even** (`cash_inflow_eur(buy_box_avg90) >= cost_eur`).
- Source: **`product.stats.avg90[0]` Keepa** (campo già nel response).

Filtro `pull-only`: si attiva solo se la colonna `buy_box_avg90` è
presente nel DataFrame. Quando `KeepaClient` esporrà
`fetch_avg_price_90d` (CHG-035 futuro), il filtro si attiverà
automaticamente. Senza la colonna → 970 test esistenti continuano a
passare (backwards-compat 100%).

Riusa `cash_inflow_eur` esistente per coerenza formula L11b (fee_fba)
+ referral_fee. Stesso shape decisionale di Amazon Presence (CHG-031).

## Tests

ruff/format/mypy strict OK. **TBD PASS** (TBD unit/gov/golden + 160 integration).

- 14 test (boundary break-even / NaN pass / vettoriale / vgp integration / log_capture telemetria / backwards-compat sentinel).
- Test esistenti CHG-031 invariati (composizione gate AND coerente).

## Test di Conformità

- ADR-0023 (Active): implementazione coerente con default ratificati.
- ADR-0018: `compute_vgp_score` esteso senza rompere R-05/R-08/Amazon
  Presence esistenti.
- ADR-0021: nuovo evento canonico `vgp.stress_test_failed`.
- ADR-0019: test parametrici boundary inclusivi.
- ADR-0014: ruff strict + mypy strict + format puliti.
- ADR-0013: `risk/` cluster esistente (CHG-031), no nuove aree.
- R-01 NO SILENT DROPS: NaN avg90 → pass esplicito (decisione Leader),
  non drop silente.

## Refs

- ADR-0023 (Active, ratificato CHG-030).
- ADR-0018 (R-05/R-08/Amazon Presence invariati).
- ADR-0021 (catalogo eventi +1).
- Predecessori: CHG-030 (ratifica), CHG-031 (Amazon Presence — pattern
  identico).
- Successori: CHG-035 (`KeepaClient.fetch_avg_price_90d` +
  `lookup_product`/`enriched_df` upstream wireup).
- Pattern: Arsenale 180k filtro 3/4 (90-Day Stress Test).
- Commit: `16ad542`.
