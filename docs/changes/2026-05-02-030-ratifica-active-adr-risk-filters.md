---
id: CHG-2026-05-02-030
date: 2026-05-02
adr_ref: ADR-0022, ADR-0023, ADR-0024, ADR-0001, ADR-0009
commit: TBD
---

## What

Ratifica Leader 2026-05-02 (round 7+): flip status `Proposed` → `Active`
sui 3 ADR risk-filters Arsenale 180k. Decisioni operative ratificate
con i default proposti (Leader: "vai con decisioni default").

| File | Cosa |
|---|---|
| `docs/decisions/ADR-0022-ghigliottina-tier-profit-filter.md` | Frontmatter `status: Active` + `deciders` aggiornato a "Leader (ratificato 2026-05-02 con decisioni default)". |
| `docs/decisions/ADR-0023-90-day-stress-test-filter.md` | Idem. |
| `docs/decisions/ADR-0024-amazon-presence-filter.md` | Idem. |
| `docs/decisions/INDEX.md` | Status `Proposed` → `Active` per le 3 righe + note futuro modulo applicativo (CHG-031/032/033 in macina). |

## Why

Decisione Leader 2026-05-02 round 7+: `vai con decisioni default`.
Le decisioni "default" sono quelle proposte da Claude in ognuno dei
3 ADR proposed (CHG-029):

**ADR-0022 Ghigliottina:**
1. Decisione: AFFIANCA R-08 (doppio gate AND).
2. Tier values: `(50€, 150€)` breakpoints + `(10€, 25€, 50€)` min profit.

**ADR-0023 90-Day Stress Test:**
1. Decisione: window 90 giorni FISSO (non configurabile in MVP).
2. Severità break-even: `cash_inflow_eur(buy_box_avg90) >= cost_eur`.
3. Source: `product.stats.avg90[0]` Keepa (preconfezionato).

**ADR-0024 Amazon Presence Filter:**
1. Threshold: 25% (default Arsenale).
2. Modalità: hard veto (`vgp_score = 0`).
3. ASIN nuovi senza dati `buyBoxStats[Amazon]` → pass (più liberale).

Le decisioni difensive ("più conservativo") restano scope futuro
(errata corrige) se il CFO segnala falsi positivi post-deploy.

## Tests

Test manuale documentato (ADR-0011 ammette test manuali per
governance):
- Comando: `git diff docs/decisions/INDEX.md docs/decisions/ADR-002[234]*.md`
- Esito atteso: 3 ADR con `status: Active` + INDEX aggiornato +
  pre-commit hook accetta sezioni obbligatorie già esistenti.
- Pre-commit applicativo: PASS (ADR già validati in CHG-029).

## Test di Conformità

- ADR-0001 (meta-ADR): status flip ammesso (lifecycle Proposed → Active).
- ADR-0009 (errata corrige): non applicabile (status flip != errata).
- ADR-0011 (operational policies): test manuale documentato ammesso.

## Refs

- ADR-0022, ADR-0023, ADR-0024 (ratificati `Active` con questa ratifica).
- ADR-0001 (meta-ADR): governance lifecycle ADR.
- Predecessore: CHG-2026-05-02-029 (DRAFT proposed).
- Successori previsti: CHG-031 Amazon Presence (impl), CHG-032
  Stress Test (impl), CHG-033 Ghigliottina (impl), CHG-034 errata
  ADR-0018 drops_30.
- Decisione Leader 2026-05-02: "vai con decisioni default".
- Commit: TBD.
