---
id: CHG-2026-05-02-036
date: 2026-05-02
adr_ref: ADR-0017, ADR-0024, ADR-0023, ADR-0022, ADR-0018, ADR-0019, ADR-0014
commit: TBD
---

## What

Propagation upstream end-to-end dei 3 campi Arsenale 180k. Chiude il
loop iniziato in CHG-035: i dati ora fluiscono `Keepa →
ProductData → ResolutionCandidate → ResolvedRow → listino_raw →
enriched_df → compute_vgp_score`. I 3 filtri pull-only
(Amazon Presence/Stress Test/Ghigliottina già attivi via dati
`cost_eur`/`cash_profit`) ora si attivano completamente quando
KEEPA_API_KEY popola le 3 colonne live.

| File | Cosa |
|---|---|
| `src/talos/extract/asin_resolver.py` | `ResolutionCandidate` esteso con 3 campi opzionali (`drops_30`/`buy_box_avg90`/`amazon_buybox_share`). `_LiveAsinResolver.resolve_description` popola dai `ProductData` (CHG-035) per ogni candidato SERP. |
| `src/talos/ui/listino_input.py` | `ResolvedRow` esteso con 3 campi. + dataclass `_LiveLookupSnapshot` (sostituisce 3-tuple di `_fetch_buybox_live_or_none`). `_resolved_row_from_result` + `apply_candidate_overrides` propagation. `build_listino_raw_from_resolved` aggiunge 3 colonne (`drops_30`/`buy_box_avg90`/`amazon_buybox_share`) al DataFrame + chiama `resolve_v_tot(drops_30=...)` (CHG-034 errata). |
| `tests/unit/test_listino_input.py` | + 4 test propagation (default None / build_listino_raw include 3 colonne / drops_30 → v_tot source / fields None se assenti). + `_FakeProductData` esteso con 3 campi opzionali. |

## Why

CHG-031/032/033 hanno introdotto i 3 risk-filter pull-only.
CHG-035 ha esteso `KeepaClient` + `ProductData`. Mancava il "pipe"
upstream che porta i dati da `ProductData` (CHG-035) fino al DataFrame
consumato da `compute_vgp_score`.

Senza CHG-036, **i 3 filtri Arsenale erano dormienti in produzione**:
le 3 colonne richieste non arrivavano mai nel `enriched_df`. Con
CHG-036, basta che il `lookup_callable` Keepa sia configurato
(`KEEPA_API_KEY` in env) e i filtri si attivano end-to-end.

`drops_30` ora fluisce a `resolve_v_tot` (CHG-034 errata): la
gerarchia hybrid v2 (csv → drops_30 → bsr_estimate → 0) è LIVE.

## Tests

ruff/format/mypy strict OK. **1034 PASS** (+4 vs 1030 CHG-035).

- 4 test propagation puri (mock-only).
- Test esistenti backwards-compat 100% (campi default None).

## Test di Conformità

- ADR-0017: `lookup_product` (CHG-006/035) consumato da `_LiveAsinResolver`.
- ADR-0024/0023/0022: filtri pull-only ora attivabili end-to-end.
- ADR-0018 errata CHG-034: `resolve_v_tot(drops_30=...)` LIVE.
- ADR-0019: test mock-only puri (no Keepa live in CHG-036).
- ADR-0014: ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: campi None graceful (filter pull-only skip
  esplicito, non drop).

## Refs

- ADR-0017/0024/0023/0022/0018/0019/0014.
- Predecessori: CHG-031/032/033 (filtri logici), CHG-034 (errata
  drops_30), CHG-035 (KeepaClient + ProductData).
- Successori: integration test live con `KEEPA_API_KEY` reale (1-2
  token Keepa per ASIN, scope CHG separato).
- Pattern Arsenale 180k: PIPELINE END-TO-END CHIUSA (mancano solo dati
  reali per attivare i filtri, ma il telaio è pronto).
- Commit: TBD.
