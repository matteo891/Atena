---
id: ADR-0022
title: Ghigliottina Tier Profit Filter — gating profitto assoluto stratificato
date: 2026-05-02
status: Active
deciders: Leader (ratificato 2026-05-02 con decisioni default)
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

Il pattern operativo "Protocollo Arsenale 180k" (riferito dal Leader
2026-05-02) introduce un filtro decisionale aggiuntivo che TALOS oggi
NON ha. Lo chiamiamo **Ghigliottina**: gating del profitto netto
**assoluto** (in EUR), stratificato in tier basati sul costo
fornitore, da applicare a ogni ASIN prima dell'allocazione Tetris.

**Differenza con R-08 (VETO ROI esistente):**
- **R-08** (ADR-0018): scarta ASIN con `roi < 8%` (soglia percentuale).
  Su un ASIN da 1000€ pretende `cash_profit ≥ 80€`.
- **Ghigliottina**: scarta ASIN con `cash_profit < min_profit_tier(cost)`
  (soglia assoluta crescente con il costo). Su un ASIN da 1000€ pretende
  `cash_profit ≥ 50€` (tier alto), che è ≡ 5% ROI — meno aggressivo del
  veto 8% MA assicura un assoluto significativo per giustificare il
  rischio di immobilizzo capitale.

**Tier di default Arsenale (placeholder, ratifica Leader necessaria):**

| Cost fornitore (EUR) | Min profit assoluto (EUR) | ROI implicito |
|---|---|---|
| `< 50` | `10` | `≥ 20%` |
| `50 .. 150` | `25` | `≥ 16.7%` (su 150) — `50%` (su 50) |
| `> 150` | `50` | `≥ 33%` (su 150) — `5%` (su 1000) |

I tier hanno senso perché il rischio di immobilizzo capitale è
**non-lineare nel costo**: un prodotto da 1000€ che resta in giacenza
brucia capitale enormemente più di un prodotto da 100€, anche se la
percentuale di ROI è identica.

**Domanda decisionale per Leader:**
1. Ghigliottina **sostituisce** R-08 (single gate) o **affianca** R-08
   (entrambi devono passare = doppio gate più conservativo)?
2. Tier values: confermi `(50, 150)` come breakpoints e `(10, 25, 50)`
   come min profit assoluti? Oppure altri valori?

## Decisione (proposta in attesa ratifica Leader)

**Proposta principale**: Ghigliottina **affianca** R-08 (doppio gate
AND): un ASIN passa se `roi >= veto_threshold AND cash_profit >=
min_profit_tier(cost)`. Più conservativo, simmetrico a R-04 + R-08
+ R-09 (multi-gate compositi).

**Implementazione** (fuori scope di questo ADR — vedi CHG-032 post ratifica):
- Nuovo modulo `src/talos/risk/ghigliottina.py` con costanti
  `GHIGLIOTTINA_TIERS: tuple[tuple[float, float], ...]` (lista di
  `(cost_max, min_profit)` ordinata) + helper `min_profit_for_cost(cost)`
  + `passes_ghigliottina(cost, cash_profit) -> bool`.
- Integrazione in `vgp/score.py:compute_vgp_score` come nuova mask
  `ghigliottina_mask` analoga a `roi_veto_mask` (R-08 esistente).
  ASIN che falliscono Ghigliottina → `vgp_score = 0` (kill switch
  vettoriale come R-05 / R-08).
- Telemetria evento canonico `vgp.ghigliottina_failed` (extra:
  `asin/cost/cash_profit/min_required/tier`).
- Configurabile via `config_overrides` (chiave `ghigliottina_tiers`?
  da decidere — scope CHG-032).

**Costo Keepa**: zero. Usa `cash_profit_eur` e `cost_eur` già nel
listino raw / enriched_df.

## Conseguenze

**Positive:**
- Aderenza al pattern Arsenale 180k (mitigation rischio capitale per
  costi alti).
- Nessuna nuova chiamata Keepa (zero impatto quota).
- Compone bene con R-08 (gate complementari: R-08 punisce % bassa,
  Ghigliottina punisce assoluto basso).

**Negative:**
- Introduce un secondo gate decisionale; cart può essere più magro
  (più ASIN scartati). Mitigation: tier conservativi all'inizio
  (i valori in tabella sono già ratificati Arsenale).
- `config_overrides` schema da estendere se vogliamo tier
  configurabili per tenant (decisione Leader pendente).

**Performance:** trascurabile (1 lookup per riga in vector mask).

## Test di Conformità

- Testato in CHG-032 (post ratifica) come modulo applicativo:
  - Unit test `passes_ghigliottina(cost, profit)` con boundary `49.99`,
    `50.0`, `149.99`, `150.0`, `150.01` (test parametrici).
  - Integration test in `vgp/score.py` con DataFrame Samsung-mini
    snapshot byte-exact (golden test post-Ghigliottina).
  - Telemetria `vgp.ghigliottina_failed` via caplog.
- ADR coerenza:
  - `## Contesto` esplicita la differenza con R-08 esistente.
  - Tier values numerici tabellari (deterministici, no fuzzy).
  - Decisione Leader pendente esplicitata in 2 punti (sostituzione vs
    affiancamento; tier values).

## Cross-References

- ADR-0018 (algoritmo VGP/Tetris): R-08 VETO ROI affiancato.
- ADR-0021 (logging telemetria): nuovo evento canonico
  `vgp.ghigliottina_failed`.
- CHG-2026-05-02-029 (questo CHG): introduce ADR proposed.
- CHG-032 (futuro post ratifica): implementazione applicativa.
- Pattern riferimento: "Protocollo Arsenale 180k" (Leader 2026-05-02).
- Sister ADR proposed: ADR-0023 90-Day Stress Test, ADR-0024 Amazon
  Presence Filter.

## Rollback

Se Ghigliottina si rivela troppo restrittiva post-deploy:
1. Allentare i tier values (errata corrige ADR-0022, sezione `## Errata`).
2. Cambiare la composizione da AND a OR con R-08 (un ASIN passa se
   ALMENO uno dei due gate passa). Errata corrige.
3. Disabilitare per default tenant via `config_overrides` (set
   `ghigliottina_enabled=false`). No code change.
4. Supersedere ADR-0022 con nuovo ADR (regola ADR-0001) se la
   strategia decisionale cambia in modo non-incrementale.

In ogni caso il modulo `risk/ghigliottina.py` resta nel codebase,
disabilitato via flag — nessun rollback distruttivo.
