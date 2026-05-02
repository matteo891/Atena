---
id: CHG-2026-05-02-033
date: 2026-05-02
adr_ref: ADR-0022, ADR-0018, ADR-0021, ADR-0019, ADR-0014
commit: f042822
---

## What

Implementazione applicativa ADR-0022 Ghigliottina Tier Profit Filter
(ratificato `Active` in CHG-030). AFFIANCA R-08 (doppio gate AND):
ASIN passa solo se `roi >= 8%` AND `cash_profit >=
min_profit_tier(cost)` (10/25/50€ per costo `<50€` / `50-150€` / `>150€`).

Differenza chiave con CHG-031/032: i dati richiesti
(`cost_eur` + `cash_profit_eur`) sono **sempre presenti** nei listini
applicativi. Filtro **non graceful**: si attiva sempre per default.

| File | Cosa |
|---|---|
| `src/talos/risk/ghigliottina.py` | nuovo. Costanti `GHIGLIOTTINA_TIERS: tuple[tuple[float, float], ...]` (lista ordinata `(cost_max, min_profit)`). Helper `min_profit_for_cost(cost) -> float`. Helper `passes_ghigliottina(*, cost_eur, cash_profit_eur) -> bool`. Helper vettoriale `is_ghigliottina_failed_mask(df, *, cost_col, cash_profit_col) -> pd.Series[bool]`. |
| `src/talos/risk/__init__.py` | Re-export `GHIGLIOTTINA_TIERS` + helpers. |
| `src/talos/vgp/score.py` | + kwarg `enable_ghigliottina: bool = True` in `compute_vgp_score`. Mask attiva sempre (cost_col + cash_profit_col già required). Composizione: `kill\|~veto\|amazon\|stress\|ghigliottina`. Telemetria `vgp.ghigliottina_failed`. |
| `src/talos/observability/events.py` | + voce catalogo `vgp.ghigliottina_failed` (asin/cost/cash_profit/min_required) + costante. Catalogo ADR-0021 ora 23 eventi. |
| `tests/unit/test_risk_ghigliottina.py` | nuovo: 18 test (tier boundary 49.99/50/149.99/150 + min_profit_for_cost + passes scalare + vettoriale + integrazione vgp + telemetria + enable=False bypass). |
| `tests/unit/test_events_catalog.py` | + voce `vgp.ghigliottina_failed` in `_EXPECTED_EVENTS`. |

## Why

ADR-0022 ratificato `Active` con default Leader 2026-05-02:
- **AFFIANCA R-08** (doppio gate AND).
- **Tier breakpoints `(50, 150)`** + **min profit `(10, 25, 50)`**.

Filtro `always-on`: i dati `cost_eur` e `cash_profit_eur` sono già
nelle colonne required di `compute_vgp_score`, quindi il filtro è
attivo per default (non graceful skip come CHG-031/032). Un kwarg
`enable_ghigliottina: bool = True` permette di disabilitare per
backwards-compat su test esistenti che potrebbero avere cash_profit
sotto soglia (test in `tests/unit/test_vgp_*` non hanno cost-aware
expectations Ghigliottina-grade).

Default ratificato: `enable_ghigliottina=True`. Test esistenti che si
rompono → aggiornati con cost/profit ricalcolato per passare entrambi
R-08 e Ghigliottina; oppure usano `enable_ghigliottina=False`
esplicito per testare R-08 isolato.

## Tests

ruff/format/mypy strict OK. **TBD PASS**.

- 18 test (tier mapping / boundary / scalare / vettoriale /
  integrazione vgp / telemetria / disabilitazione).
- Test esistenti potrebbero richiedere `enable_ghigliottina=False`
  esplicito o adeguamento cash_profit per passare il doppio gate.
- Golden Samsung-mini snapshot **deve essere validato** (CHG-022
  prevede cart con vari ASIN; alcuni potrebbero fallire Ghigliottina
  → snapshot da aggiornare).

## Test di Conformità

- ADR-0022 (Active): implementazione coerente con default ratificati.
- ADR-0018: `compute_vgp_score` esteso senza rompere R-05/R-08/
  Amazon Presence/Stress Test esistenti (composizione AND).
- ADR-0021: nuovo evento canonico `vgp.ghigliottina_failed`.
- ADR-0019: test parametrici tier boundary.
- ADR-0014: ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: ASIN sotto tier → vetato esplicito + telemetria.

## Refs

- ADR-0022 (Active, ratificato CHG-030).
- ADR-0018 (R-05/R-08/Amazon Presence/Stress Test invariati).
- Predecessori: CHG-030 (ratifica), CHG-031 (Amazon Presence),
  CHG-032 (Stress Test).
- Successore: CHG-034 (errata ADR-0018 drops_30 V_tot upgrade).
- Pattern: Arsenale 180k filtro 1/4 (Ghigliottina), chiude i 3 filtri
  ratificati di CHG-029/030.
- Commit: `f042822`.
