---
id: CHG-2026-05-02-040
date: 2026-05-02
adr_ref: ADR-0017, ADR-0009, ADR-0018, ADR-0019, ADR-0014
commit: TBD
---

## What

Errata corrige ADR-0017 sezione policy fee_fba: decisione alpha-prime
INVERTITA post calibrazione ground truth ScalerBot500K (CHG-039).
`_LiveKeepaAdapter` ora popola `fee_fba_eur` da
`product["fbaFees"]["pickAndPackFee"]` Keepa (atomica, cents → EUR /100).
`fee_fba_manual` L11b resta fallback solo per ASIN dove Keepa non
espone il campo.

| File | Cosa |
|---|---|
| `src/talos/io_/keepa_client.py` | `_LiveKeepaAdapter.query()` ora parsa `product["fbaFees"]["pickAndPackFee"]` cents → EUR Decimal. Restituisce `KeepaProduct(fee_fba_eur=Decimal | None)`. Docstring aggiornata con riferimento errata. |
| `src/talos/extract/asin_resolver.py` | `ResolutionCandidate` esteso con `fee_fba_eur: Decimal \| None = None`. `_LiveAsinResolver.resolve_description` propaga da `ProductData.fee_fba_eur`. |
| `src/talos/ui/listino_input.py` | `ResolvedRow` + `_LiveLookupSnapshot` estesi con `fee_fba_eur`. `_fetch_buybox_live_or_none` propagation. `_resolved_row_from_result` + `apply_candidate_overrides` propagation. `build_listino_raw_from_resolved` aggiunge colonna `fee_fba_eur_keepa`. |
| `src/talos/orchestrator.py:_enrich_listino` | Se colonna `fee_fba_eur_keepa` presente + valore non None → usa quello. Fallback a `fee_fba_manual` L11b altrimenti (backwards-compat). |
| `docs/decisions/ADR-0017-stack-acquisizione-dati.md` | Sezione `## Errata` con voce CHG-040 + razionale + pattern propagation. |
| `tests/unit/test_keepa_client.py` | + 3 test (KeepaProduct atomica field optional, fetch_fee_fba ritorna atomica quando presente, KeepaMissError quando None). |
| `tests/unit/test_orchestrator_fee_fba_keepa_priority.py` | nuovo: 3 test (Keepa fee usata quando presente, fallback L11b quando None, backwards-compat senza colonna). |
| `tests/integration/test_live_keepa.py` | 2 test legacy aggiornati (test live tollerante a entrambi gli stati post-errata). |

## Why

Calibrazione CHG-039 con ground truth Leader (`ordine_scaler500k (22).xlsx`)
ha rivelato:
- ScalerBot500K (sistema CFO) usa fee atomica Keepa pickAndPackFee (~€3
  Samsung) per calcolo ROI/cart.
- TALOS L11b (formula Frozen Leader) ~€22 → 5/6 ASIN sotto VETO_ROI 8%
  → cart vuoto → bot inutilizzabile.

Decisione Leader 2026-05-02 ratificata: opzione **B** (sostituisci L11b
→ atomica Keepa quando disponibile, L11b solo fallback). Allinea TALOS
con il sistema operativo CFO ground truth.

`fee_fba_manual` L11b NON viene rimossa: resta come fallback Samsung MVP
quando Keepa non espone `pickAndPackFee` (ASIN nuovi, Keepa miss, etc.)
o per listini test/dev senza KEEPA_API_KEY.

Pipeline propagation completa: `KeepaProduct → ProductData →
ResolutionCandidate → ResolvedRow → listino_raw colonna
fee_fba_eur_keepa → orchestrator._enrich_listino preferenza Keepa,
L11b fallback`.

## Tests

ruff/format/mypy strict OK. **1049 PASS** (+6 vs 1043 CHG-039).

- 3 test KeepaClient (atomica field, fetch_fee_fba ritorna atomica,
  KeepaMiss su None).
- 3 test orchestrator priority (Keepa preferred / L11b fallback /
  backwards-compat).
- 2 test integration live aggiornati (tolleranti a Keepa atomica o miss).

## Test di Conformità

- ADR-0017 errata `## Errata` ratificata Leader.
- ADR-0009 errata mechanism (modifica diretta + sezione Errata).
- ADR-0018 invariato: F1/F2 formule. `cash_inflow_eur` consuma il
  nuovo `fee_fba_eur` senza cambi.
- ADR-0019: test mock + sentinel + integration.
- ADR-0014: ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: KeepaMiss esplicito su None → caller fallback
  L11b documentato.

## Refs

- ADR-0017 (KeepaClient α'' policy invertita).
- ADR-0009 (errata mechanism).
- Predecessore: CHG-039 (ground truth ScalerBot500K calibrazione che
  ha scoperto la discrepanza).
- CHG-2026-05-01-015 (decisione α'' originale, ora invertita).
- Ground truth Leader: `ordine_scaler500k (22).xlsx`.
- Successore atteso: integration test live con KEEPA_API_KEY +
  validazione completa 7/7 ASIN ground truth.
- Commit: TBD.
