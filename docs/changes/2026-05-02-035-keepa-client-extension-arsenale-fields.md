---
id: CHG-2026-05-02-035
date: 2026-05-02
adr_ref: ADR-0017, ADR-0024, ADR-0023, ADR-0018, ADR-0019, ADR-0014
commit: TBD
---

## What

KeepaClient extension upstream: 3 nuovi fetch per popolare i campi
richiesti dai filtri Arsenale 180k (CHG-031/032/034). I dati sono
GIÀ presenti nel response `keepa.product()` esistente — costo Keepa
zero, solo parsing aggiuntivo.

| File | Cosa |
|---|---|
| `src/talos/io_/keepa_client.py` | + costante `_AMAZON_SELLER_ID = "ATVPDKIKX0DER"`. + 3 campi opzionali in `KeepaProduct`: `drops_30: int \| None`, `buy_box_avg90: Decimal \| None`, `amazon_buybox_share: float \| None`. `_LiveKeepaAdapter.query()` parsa: `stats.salesRankDrops30` (drops community proxy), `stats.avg90[NEW_index]` (BuyBox avg 90gg), `buyBoxStats[AMAZON_SELLER]['percentageWon']` (Amazon share %). + 3 nuovi metodi `KeepaClient.fetch_drops_30(asin) -> int \| None`, `fetch_avg_price_90d(asin) -> Decimal \| None`, `fetch_buybox_amazon_share(asin) -> float \| None`. **Diversamente da `fetch_buybox`/`fetch_bsr`/`fetch_fee_fba`**: i 3 nuovi NON sollevano `KeepaMissError` — ritornano `None` su miss (dati ancillari non blocking, decisione Leader default). |
| `src/talos/io_/fallback_chain.py` | `ProductData` esteso con 3 nuovi campi opzionali. `lookup_product` chiama i 3 nuovi `fetch_*` e popola `ProductData`. Audit `sources` esteso. |
| `tests/unit/test_keepa_client.py` | + 9 test mock-only (parsing 3 campi nuovi + miss → None + integrazione `KeepaClient.fetch_*`). |
| `tests/unit/test_fallback_chain.py` | + 4 test (`lookup_product` propagation 3 nuovi campi + miss). |

## Why

CHG-031/032/034 hanno introdotto 3 risk-filter pull-only che si
attivano automaticamente quando il dataframe ha le colonne
`amazon_buybox_share`/`buy_box_avg90`/`drops_30` popolate. Senza
upstream wiring, restano dormienti.

**Costo Keepa = 0 chiamate aggiuntive**: il response `keepa.product()`
già conteneva `stats.avg90` / `buyBoxStats` / `salesRankDrops30`
prima di CHG-035. Cambiamento: parsing aggiuntivo nel `_LiveKeepaAdapter`,
non nuove HTTP requests.

**Out-of-scope CHG-035** (rimandato a CHG-036+):
- Propagation `ResolvedRow` + `listino_input.py` (`_fetch_buybox_live_or_none`
  → tuple esteso).
- Propagation `build_listino_raw_from_resolved` → 3 nuove colonne nel
  listino_raw.
- Orchestrator `_enrich_listino` propagation → `enriched_df`.
- Integration test live con `KEEPA_API_KEY` reale (1-2 token Keepa).

Senza CHG-036, i 3 filtri Arsenale restano dormienti (nessuna colonna
nel dataframe pipeline). CHG-035 chiude però la prima metà del wiring
(io_ layer pronto).

## Tests

ruff/format/mypy strict OK. **TBD PASS**.

- 9 test KeepaClient (parsing 3 campi via mock adapter + miss → None +
  fetch wrapper).
- 4 test lookup_product (propagation + miss).
- Test esistenti invariati (backwards-compat: `KeepaProduct` campi
  nuovi opzionali con default `None`).

## Test di Conformità

- ADR-0017 (acquisizione dati): KeepaClient esteso senza nuove deps.
- ADR-0024 / ADR-0023: campi richiesti popolati upstream.
- ADR-0018 / CHG-034: `drops_30` disponibile per `resolve_v_tot`
  (wiring pipeline scope CHG-036).
- ADR-0019: test mock + parametric.
- ADR-0014: ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: i 3 nuovi fetch ritornano `None` esplicito su
  miss (dati ancillari non blocking, distinto da `KeepaMissError` che
  resta per fields critici buybox/bsr).

## Refs

- ADR-0017 (KeepaClient).
- ADR-0024 (Amazon Presence — campo `amazon_buybox_share`).
- ADR-0023 (Stress Test — campo `buy_box_avg90`).
- ADR-0018 + CHG-034 (Dynamic Floor — campo `drops_30`).
- Predecessori: CHG-031/032/033/034 (filtri pull-only definiti).
- Successore: CHG-036 (propagation upstream end-to-end).
- Pattern Arsenale 180k filtri pull-only: completati lato `vgp/score.py`,
  questa il primo passo upstream `io_/keepa_client.py`.
- Commit: TBD.
