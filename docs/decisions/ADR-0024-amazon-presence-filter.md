---
id: ADR-0024
title: Amazon Presence Filter — gating monopolio Amazon BuyBox
date: 2026-05-02
status: Proposed
deciders: Leader (in attesa ratifica)
category: architecture
supersedes: —
superseded_by: —
---

## Contesto

Quando Amazon (entità diretta, seller_id `ATVPDKIKX0DER`) detiene la
Buy Box per la **maggior parte del tempo**, i seller terzi (incluso
TALOS/CFO) faticano a vincere la Buy Box, anche con prezzo competitivo.
La Buy Box è il bottone "Aggiungi al carrello": senza Buy Box, le
vendite crollano del 70-90% (il customer compra raramente "Altri
venditori").

Competere direttamente contro Amazon è quasi sempre una battaglia
persa per:
- Logistica gratuita per Prime members (vantaggio strutturale Amazon).
- Pricing dinamico aggressivo Amazon (algoritmo automatico).
- Trust/familiarità del brand "Spedito da Amazon" sul cliente.

Il pattern Arsenale 180k introduce il **Amazon Presence Filter**:
scarta ASIN dove Amazon detiene la Buy Box per > 25% del tempo
osservato. È il filtro più "no-brainer" dei tre Arsenale: la metrica
è binaria (pass/fail), il dato è già nel response Keepa esistente,
zero ambiguità decisionale.

**Domanda decisionale per Leader:**
1. **Threshold**: 25% (default Arsenale) o configurabile per
   categoria? Es. categorie ad alta Amazon presence (Echo/Kindle)
   sono fuori scope per definizione, threshold più stringente?
2. **Modalità di gating**: hard veto (vgp_score=0) o soft penalty
   (decay vgp_score in proporzione a `amazon_share`)?
3. **Comportamento se dato mancante**: ASIN privati / nuovi senza
   `buyBoxStats` Amazon → pass (default proposed) o fail (più
   conservativo)?

## Decisione (proposta in attesa ratifica Leader)

**Proposta principale**: hard veto al 25% (default Arsenale). ASIN
con `amazon_buybox_share > 0.25` → `vgp_score = 0` (kill switch
vettoriale, simmetrico a R-05 e R-08).

**Implementazione** (fuori scope di questo ADR — vedi CHG-030 post ratifica):
- Estendere `KeepaClient` con `fetch_buybox_amazon_share(asin)
  -> float | None` (campo `product.buyBoxStats[ATVPDKIKX0DER]
  ['percentageWon']` — già nel response, zero token aggiuntivi).
- Nuovo modulo `src/talos/risk/amazon_presence.py` con costante
  `AMAZON_PRESENCE_MAX_SHARE: float = 0.25` + helper
  `passes_amazon_presence(amazon_share) -> bool`.
- Integrazione in `vgp/score.py:compute_vgp_score` come mask
  `amazon_presence_mask`. Telemetria evento canonico
  `vgp.amazon_dominant_seller` (extra: `asin/amazon_share/threshold`).
- `enriched_df` nuova colonna `amazon_buybox_share` (audit trail).
- `lookup_product` (CHG-006) estende `ProductData` con `amazon_buybox_share`.

**Costo Keepa**: zero. `buyBoxStats` è già nel response `keepa.product()`.

## Conseguenze

**Positive:**
- Filtra ASIN dove Amazon è seller dominante (basso win rate Buy
  Box → vendite reali ≪ V_tot stimato).
- Aderenza al pattern Arsenale 180k.
- Zero costo Keepa aggiuntivo.
- Filtro "no-brainer": metrica binaria, low-risk decisione.

**Negative:**
- ASIN dove Amazon è seller "occasional" (10-25% share) → policy
  pass: potrebbero comunque essere difficili. Mitigation: threshold
  configurabile per categoria.
- ASIN nuovi senza `buyBoxStats` Amazon → ambiguità (decisione Leader).

**Performance:** trascurabile.

## Test di Conformità

- Testato in CHG-030 (post ratifica):
  - Unit `passes_amazon_presence(share)` con boundary `0.0`, `0.25`,
    `0.2501`, `1.0` (test parametrici).
  - Integration `_LiveKeepaAdapter.fetch_buybox_amazon_share` live
    (1 ASIN dove Amazon è dominante + 1 dove non lo è, ~2 token
    Keepa).
  - Sentinel: ASIN con `amazon_share = 0.99` (es. AmazonBasics
    products) deve essere VETOed.
  - Telemetria `vgp.amazon_dominant_seller` via caplog.
- ADR coerenza:
  - Threshold value numerico (`0.25`).
  - Source dati esplicitato (`buyBoxStats` Keepa).
  - 3 decisioni Leader esplicitate.

## Cross-References

- ADR-0017 (acquisizione dati): `KeepaClient` extension
  `fetch_buybox_amazon_share`.
- ADR-0018 (algoritmo VGP/Tetris): nuova mask in `compute_vgp_score`.
- ADR-0021 (logging telemetria): nuovo evento `vgp.amazon_dominant_seller`.
- CHG-2026-05-02-029 (questo CHG): introduce ADR proposed.
- CHG-030 (futuro post ratifica): implementazione applicativa.
- Pattern riferimento: "Protocollo Arsenale 180k" (Leader 2026-05-02).
- Sister ADR proposed: ADR-0022 Ghigliottina, ADR-0023 90-Day Stress
  Test.

## Rollback

Se Amazon Presence Filter scarta troppi ASIN buoni:
1. Allentare threshold: `0.25` → `0.40` o `0.50`. Errata corrige.
2. Modalità soft penalty: `vgp_score *= (1 - amazon_share)` (decay
   continuo invece di hard veto). Errata corrige.
3. Threshold per categoria via `config_overrides`. Errata corrige.
4. Disabilitare via `config_overrides`
   (`amazon_presence_enabled=false`). No code change.
5. Supersedere con nuovo ADR (regola ADR-0001).

Modulo `risk/amazon_presence.py` resta nel codebase disabilitato
via flag — nessun rollback distruttivo.
