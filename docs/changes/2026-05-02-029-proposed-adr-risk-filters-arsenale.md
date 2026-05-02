---
id: CHG-2026-05-02-029
date: 2026-05-02
adr_ref: ADR-0022, ADR-0023, ADR-0024, ADR-0001, ADR-0018, ADR-0017, ADR-0021
commit: 2ab92ce
---

## What

DRAFT 3 ADR proposed risk-filters Arsenale 180k (in attesa ratifica
Leader). NESSUNA modifica codice applicativo. Solo deliverable
documentale per abilitare la decisione strategica.

| File | Cosa |
|---|---|
| `docs/decisions/ADR-0022-ghigliottina-tier-profit-filter.md` | Status `Proposed`. Ghigliottina: gating profitto netto assoluto stratificato per tier di costo (10€/25€/50€ per `<50€/50-150€/>150€`). Affianca o sostituisce R-08 (decisione Leader). |
| `docs/decisions/ADR-0023-90-day-stress-test-filter.md` | Status `Proposed`. 90-Day Stress Test: gating resilienza prezzo storico (avg90 Keepa). Veto ASIN dove `cash_inflow_eur(buy_box_avg90) < cost_eur` (perdita catastrofica se prezzo torna a media). |
| `docs/decisions/ADR-0024-amazon-presence-filter.md` | Status `Proposed`. Amazon Presence: hard veto ASIN dove Amazon detiene Buy Box > 25% (no-brainer, dato già in `buyBoxStats` Keepa). |

## Why

Decisione Leader 2026-05-02 round 7+: integrare il pattern operativo
"Protocollo Arsenale 180k" (4 filtri totali: Ghigliottina / Dynamic
Floor / 90-Day Stress Test / Amazon Presence). TALOS oggi implementa
1/4 (Dynamic Floor = F4.A `q_m = V_tot / (S_comp + 1)`, ratificato in
CHG-2026-04-30-038); restano 3/4 da introdurre.

Costo operativo zero in fase pre-implementazione: gli ADR sono
deliverable documentali. Costo Keepa zero in fase implementazione:
i 3 dati necessari (`stats.avg90`, `buyBoxStats[Amazon]`,
`cost`/`cash_profit`) sono già nel response `keepa.product()`
esistente — il fix è solo parsing aggiuntivo, non chiamate aggiuntive.

Il Leader deve ratificare 3 decisioni operative per ognuno degli
ADR (totale 9 decisioni puntuali). Ogni ADR contiene la sezione
"Domanda decisionale per Leader" esplicita.

**Sequenza operativa post ratifica:**
1. Leader ratifica ADR-0024 (most no-brainer) → CHG-030 implementazione.
2. Leader ratifica ADR-0023 → CHG-031 implementazione.
3. Leader ratifica ADR-0022 → CHG-032 implementazione (decisione
   sostituisce/affianca R-08 + tier values).
4. Errata ADR-0018 separata (CHG-033) per `drops_30` come V_tot
   accurato (Dynamic Floor Arsenale al posto del placeholder MVP
   `estimate_v_tot_from_bsr` log-lineare).

## Tests

Test manuali documentati (ADR-0011 ammette test manuali per
infrastruttura/governance):
- `pre-commit` hook valida sezioni obbligatorie ADR
  (`## Contesto`, `## Decisione`, `## Conseguenze`, `## Test di
  Conformità`, `## Cross-References`, `## Rollback`).
- Esecuzione: pre-commit applicativo a HEAD (parte del flusso commit
  standard).
- Esito atteso: 3 ADR validati syntactically; INDEX.md NON aggiornato
  (ADR-0001: solo `Active` vanno in INDEX).

## Test di Conformità

- ADR-0001 (meta): ADR proposed NON sono `Active` finché non
  referenziati in INDEX.md. Questo CHG NON modifica INDEX.md.
- ADR-0009 (errata corrige): nessuna modifica a ADR esistenti
  (ADR-0018 errata rinviata a CHG-033 separato post ratifica
  ADR-0022/0023/0024).
- ADR-0011 (operational policies): test manuale documentato ammesso
  per change docs.

## Refs

- ADR-0001 (meta-ADR): governance proposed status.
- ADR-0018 (algoritmo VGP/Tetris): R-08 esistente menzionato come
  context comparativo in ADR-0022.
- ADR-0017 (acquisizione dati): `KeepaClient` extension prevista
  in ADR-0023/0024 implementazione.
- ADR-0021 (logging telemetria): nuovi 3 eventi canonici previsti
  (`vgp.ghigliottina_failed` / `vgp.stress_test_failed` /
  `vgp.amazon_dominant_seller`).
- Pattern Arsenale 180k: "Protocollo" comunicato da Leader
  2026-05-02 (round 7+).
- Decisione Leader: "lavora tutto insieme" (UI + risk-filters).
- Predecessori: chiusura blocco UI restyle FASE 1 (CHG-023..028).
- Successori previsti: CHG-030/031/032 implementazioni post ratifica
  + CHG-033 errata ADR-0018 drops_30.
- Commit: `2ab92ce`.
