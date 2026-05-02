---
id: ADR-0023
title: 90-Day Stress Test Filter — gating resilienza prezzo storico
date: 2026-05-02
status: Proposed
deciders: Leader (in attesa ratifica)
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

TALOS oggi calcola ROI/VGP/cash_profit basandosi sul **Buy Box live**
(Keepa NEW corrente, CHG-2026-05-01-015). Questo ha un rischio
nascosto: il prezzo NEW di oggi può essere **gonfiato temporaneamente**
(promo lampo, listino fresco, anomalia di mercato). Se compriamo
1000 unità a costo X assumendo Buy Box Y, ma in 30-60 giorni Y torna
alla **media storica più bassa**, la nostra ipotesi cash_profit è
falsa e andiamo in perdita.

Il pattern Arsenale 180k introduce il **90-Day Stress Test**: prima
di allocare un ASIN, verifica che `cash_inflow_eur(price=avg90)` —
calcolato col prezzo medio Buy Box degli ultimi 90 giorni invece del
prezzo live — sia comunque ≥ `cost_eur`. ASIN che falliscono lo
stress test sono troppo dipendenti dal prezzo gonfiato corrente.

**Domanda decisionale per Leader:**
1. **Window di stress test**: 90 giorni (default Arsenale) o
   parametrizzabile via `config_overrides` (es. 60/180gg)?
2. **Severità**: profit zero (stress=break-even) o margine minimo
   richiesto anche al prezzo medio (es. ≥ 5%)?
3. **Source del prezzo medio**: `product.stats.avg90[0]` (Buy Box NEW
   medio Keepa) o ricostruzione da `csv[1]` con filtro outlier?

## Decisione (proposta in attesa ratifica Leader)

**Proposta principale**: 90-Day Stress Test al **break-even**:
ASIN passa se `cash_inflow_eur(buy_box_avg90) >= cost_eur`. Profit
positivo non richiesto (è già coperto da R-08 ROI sul prezzo live;
lo stress test garantisce solo "non perdita catastrofica" se prezzo
torna a media storica).

**Implementazione** (fuori scope di questo ADR — vedi CHG-031 post ratifica):
- Estendere `KeepaClient` con `fetch_avg_price_90d(asin) -> Decimal | None`
  (campo `product.stats.avg90[0]` — già nel response esistente,
  zero token aggiuntivi). Miss → `None` (assume safe pass se Keepa
  non ha storia 90gg, R-01 ridondante con altri gate).
- Nuovo modulo `src/talos/risk/stress_test.py` con
  `passes_90d_stress_test(*, buy_box_avg90, cost, fee_fba, referral_fee_rate)
  -> bool` (riusa `cash_inflow_eur` esistente).
- Integrazione in `vgp/score.py:compute_vgp_score` come nuova mask
  `stress_test_mask`. ASIN che falliscono → `vgp_score = 0`.
- Telemetria evento canonico `vgp.stress_test_failed` (extra:
  `asin/buy_box_live/buy_box_avg90/cost`).
- `enriched_df` nuova colonna `buy_box_avg90` (audit trail).
- `lookup_product` (CHG-006) estende `ProductData` con `buy_box_avg90`.

**Costo Keepa**: zero. `stats.avg90` è già nel response `keepa.product()`
(usato oggi solo per `buy_box_eur` live).

## Conseguenze

**Positive:**
- Filtra ASIN con prezzo gonfiato di oggi (anomalie, promo, hype).
- Aderente al pattern Arsenale 180k.
- Zero costo Keepa aggiuntivo.

**Negative:**
- ASIN nuovi (< 90 giorni Keepa history) → `avg90=None` → policy
  decisione Leader: pass (default proposed) o fail (più conservativo).
- Mercati con trend rialzista forte → falsi negativi (prodotti
  legittimamente in crescita scartati). Mitigation: window
  parametrizzabile per ASIN/categoria.

**Performance:** trascurabile (1 lookup vector mask).

## Test di Conformità

- Testato in CHG-031 (post ratifica):
  - Unit `passes_90d_stress_test(buy_box_avg90, cost, ...)` con
    boundary break-even, profit positivo, profit negativo, avg90=None.
  - Integration `_LiveKeepaAdapter.fetch_avg_price_90d` live (1
    ASIN noto, stats.avg90 esistente, ~1 token Keepa).
  - Sentinel: ASIN con `buy_box_live > buy_box_avg90 * 1.2` (gonfiato
    20%+) deve fallire stress test.
  - Telemetria `vgp.stress_test_failed` via caplog.
- ADR coerenza:
  - `## Contesto` esplicita il rischio prezzo-gonfiato.
  - Source dati esplicitato (`stats.avg90[0]` Keepa).
  - 3 decisioni Leader esplicitate.

## Cross-References

- ADR-0017 (acquisizione dati): `KeepaClient` extension `fetch_avg_price_90d`.
- ADR-0018 (algoritmo VGP/Tetris): nuova mask in `compute_vgp_score`.
- ADR-0021 (logging telemetria): nuovo evento `vgp.stress_test_failed`.
- CHG-2026-05-02-029 (questo CHG): introduce ADR proposed.
- CHG-031 (futuro post ratifica): implementazione applicativa.
- Pattern riferimento: "Protocollo Arsenale 180k" (Leader 2026-05-02).
- Sister ADR proposed: ADR-0022 Ghigliottina, ADR-0024 Amazon
  Presence Filter.
- CHG-2026-05-01-015: `_LiveKeepaAdapter` ratificato (decisione A2
  buybox NEW); ADR-0023 estende lo stesso response Keepa.

## Rollback

Se 90-Day Stress Test si rivela troppo conservativo post-deploy:
1. Allentare la severità: passare da break-even a "stress profit ≥
   -5%" (perdita massima accettata se torno a media). Errata corrige.
2. Window configurabile per categoria (es. tech 60gg, FMCG 180gg).
   Errata corrige.
3. Disabilitare via `config_overrides` (`stress_test_enabled=false`).
   No code change.
4. Supersedere con nuovo ADR (regola ADR-0001).

Modulo `risk/stress_test.py` resta nel codebase disabilitato via flag
— nessun rollback distruttivo.
