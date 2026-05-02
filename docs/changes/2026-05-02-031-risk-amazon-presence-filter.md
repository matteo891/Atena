---
id: CHG-2026-05-02-031
date: 2026-05-02
adr_ref: ADR-0024, ADR-0018, ADR-0021, ADR-0019, ADR-0014
commit: TBD
---

## What

Implementazione applicativa ADR-0024 Amazon Presence Filter (ratificato
`Active` in CHG-030). Hard veto ASIN dove Amazon detiene la Buy Box per
> 25% del tempo. Pattern Arsenale 180k completo per questo filtro.

| File | Cosa |
|---|---|
| `src/talos/risk/__init__.py` | nuovo cluster `risk` (8° area applicativa permessa ADR-0013). Re-export `passes_amazon_presence` + `AMAZON_PRESENCE_MAX_SHARE`. |
| `src/talos/risk/amazon_presence.py` | nuovo modulo. Costante `AMAZON_PRESENCE_MAX_SHARE: float = 0.25`. Helper puro `passes_amazon_presence(amazon_share: float \| None) -> bool` (None → True per ASIN nuovi senza dati, decisione default Leader). Helper vettoriale `is_amazon_dominant_mask(series) -> pd.Series[bool]` per integrazione `compute_vgp_score`. |
| `src/talos/vgp/score.py` | + kwarg opzionale `amazon_share_col: str = "amazon_buybox_share"` in `compute_vgp_score`. Se la colonna è presente, applica `is_amazon_dominant_mask` e include nel `blocked` mask (`kill | ~veto_passed | amazon_dominant`). Telemetria evento `vgp.amazon_dominant_seller` (extra: `asin/amazon_share/threshold`). Se la colonna è assente → skip silenzioso (backwards-compat 100%). |
| `src/talos/observability/log_events.yaml` | + voce catalogo eventi `vgp.amazon_dominant_seller`. |
| `tests/unit/test_risk_amazon_presence.py` | nuovo: 12 test parametrici (boundary 0.0/0.25/0.2501/0.50/1.0/None, vettoriale mask, integrazione `compute_vgp_score` con/senza colonna, telemetria caplog, smoke import). |

## Why

ADR-0024 ratificato `Active` con default Leader 2026-05-02:
- Threshold: **25%** (Arsenale).
- Modalità: **hard veto** (`vgp_score = 0` come R-05/R-08).
- ASIN nuovi senza dati: **pass** (None → True, più liberale).

Filtro `pull-only`: aggiunge mask in `compute_vgp_score` se colonna
`amazon_buybox_share` presente. NON forza l'upstream a popolarla:
quando `KeepaClient` esporrà `fetch_buybox_amazon_share` (CHG futuro
out-of-scope qui), il filtro si attiva automaticamente.

Backwards-compat 100%: 953 test esistenti devono continuare a passare
senza modifiche (la colonna non c'è → mask non applicato → behavior
invariato).

## Tests

ruff/format/mypy strict OK. **TBD PASS** (TBD unit/gov/golden + 160 integration).

- 12 test parametrici (boundary share / vettoriale / integrazione vgp / telemetria).
- Sentinel: `compute_vgp_score(df_senza_amazon_col)` invariato (backwards-compat).
- Golden Samsung-mini snapshot invariato (no `amazon_buybox_share` nel listino test).

## Test di Conformità

- ADR-0024 (Active): implementazione coerente con default ratificati.
- ADR-0018 (algoritmo VGP/Tetris): `compute_vgp_score` esteso senza
  rompere R-05/R-08 esistenti.
- ADR-0021 (logging telemetria): nuovo evento canonico
  `vgp.amazon_dominant_seller` aggiunto a `log_events.yaml`.
- ADR-0019 (test strategy): test parametrici boundary inclusivi.
- ADR-0014 (quality gates): ruff strict + mypy strict + format puliti.
- ADR-0013 (project structure): nuovo cluster `risk/` (8ª area permessa).
- R-01 NO SILENT DROPS: `None` → pass esplicito (decisione Leader),
  non drop silente.

## Refs

- ADR-0024 (Active, ratificato CHG-030).
- ADR-0018 (R-05/R-08 invariati).
- ADR-0021 (catalogo eventi +1).
- ADR-0013 (cluster `risk/`).
- Predecessori: CHG-030 (ratifica ADR risk-filters), CHG-2026-04-30-049
  (telemetria vgp eventi).
- Successori previsti: CHG-035 (`KeepaClient.fetch_buybox_amazon_share`
  + integrazione `lookup_product`/`enriched_df` upstream).
- Pattern: Arsenale 180k filtro 4/4 (Amazon Presence).
- Commit: TBD.
