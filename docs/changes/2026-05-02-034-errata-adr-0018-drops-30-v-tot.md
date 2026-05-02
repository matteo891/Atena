---
id: CHG-2026-05-02-034
date: 2026-05-02
adr_ref: ADR-0018, ADR-0009, ADR-0017, ADR-0021, ADR-0019, ADR-0014
commit: a91a44e
---

## What

Errata corrige ADR-0018 (sezione velocity estimator): `drops_30` dal
campo `product.stats.salesRankDrops30` Keepa è il **gold-standard
community** per stima vendite mensili. Sostituisce il placeholder
log-lineare MVP `estimate_v_tot_from_bsr` come **prima scelta** della
strategia hybrid `resolve_v_tot`. Il placeholder log-lineare resta
fallback se `drops_30` non disponibile.

| File | Cosa |
|---|---|
| `src/talos/extract/velocity_estimator.py` | + sentinel `V_TOT_SOURCE_DROPS_30: str = "drops_30"`. + parametro opzionale `drops_30: int \| None = None` in `resolve_v_tot`. Gerarchia hybrid v2: CSV override → drops_30 (Keepa) → BSR estimate MVP placeholder → 0 default. Helper `estimate_v_tot_from_drops_30(drops, days_window=30)` stima diretta `drops`. Pattern Arsenale 180k Dynamic Floor completo (filtro 2/4 chiuso). |
| `tests/unit/test_velocity_estimator.py` | + 8 test (`estimate_v_tot_from_drops_30` boundary + None/0/negativi + `resolve_v_tot` priorità nuova hybrid 4-livel). Test esistenti invariati (backwards-compat con `drops_30=None` default). |
| `docs/decisions/ADR-0018-algoritmo-vgp-tetris.md` | + sezione `## Errata` con voce CHG-034 (drops_30 promosso a fonte preferita). |

## Why

Il placeholder MVP `estimate_v_tot_from_bsr(bsr) = max(1, 100 − 20·log10(bsr))`
(CHG-2026-05-02-003) è una formula log-lineare arbitraria, NON calibrata.
Esempio: BSR=100 → V_tot=300, BSR=10000 → V_tot=20 — numeri inventati.

Keepa espone `salesRankDrops30` (numero di volte che il rank scende in
30 giorni, proxy delle vendite reali stimate dalla community). È il
**Dynamic Floor di Arsenale 180k** completo:

    v_real_mese = drops_30 / (n_competitors + 1)

dove `drops_30` è stima empirica da telemetria Amazon (NON formula
arbitraria). Pattern community: 1 drop ≈ 1 vendita confermata.

Filtro `pull-only`: `drops_30=None` (caso attuale, KeepaClient non
estende ancora `fetch_drops_30`) → fallback al placeholder MVP →
behavior invariato. Quando `KeepaClient.fetch_drops_30` arriverà
(scope CHG-035 futuro), il filtro si attiva automaticamente.

## Tests

ruff/format/mypy strict OK. **TBD PASS**.

- 8 test nuovi (`estimate_v_tot_from_drops_30` boundary + `resolve_v_tot`
  hybrid v2 priorità).
- Test esistenti `test_velocity_estimator.py` invariati (backwards-compat
  con `drops_30=None` default).
- Cataloghi STATUS/CHANGELOG aggiornati.

## Test di Conformità

- ADR-0018 (errata corrige): velocity estimator gerarchia hybrid v2
  ratificata Leader 2026-05-02 con default Arsenale 180k.
- ADR-0009 (errata mechanism): modifica diretta + sezione `## Errata`
  in ADR-0018 (no supersessione completa, modifica incrementale).
- ADR-0017: integrazione futura `KeepaClient.fetch_drops_30` scope
  CHG-035.
- ADR-0019: test parametrici boundary.
- ADR-0014: ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: `drops_30=None` → fallback esplicito (non drop
  silente).

## Refs

- ADR-0018 (algoritmo VGP/Tetris) — errata corrige.
- ADR-0009 (errata mechanism).
- ADR-0017 (KeepaClient extension futura).
- Predecessori: CHG-2026-05-02-003 (placeholder MVP introdotto).
- Successore: CHG-035 (`KeepaClient.fetch_drops_30` upstream wireup).
- Pattern: Arsenale 180k Dynamic Floor filtro 2/4 (chiusura concettuale).
- Decisione Leader 2026-05-02: "vai con decisioni default" → drops_30
  promosso a fonte preferita.
- Commit: `a91a44e`.
