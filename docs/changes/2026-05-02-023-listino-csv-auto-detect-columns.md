---
id: CHG-2026-05-02-023
date: 2026-05-02
adr_ref: ADR-0016, ADR-0017, ADR-0019, ADR-0014
commit: aaad10f
---

## What

Auto-detect colonne descrizione/prezzo nel CSV listino input. Header
canonici (`descrizione`/`prezzo`) non più obbligatori: il parser
identifica le 2 colonne via alias + heuristica price-parseable.
Vincolo invariato: i due dati DEVONO restare in colonne separate
(no concatenazione "desc, prezzo" in unica colonna).

| File | Cosa |
|---|---|
| `src/talos/ui/listino_input.py` | + costanti `DESCRIZIONE_HEADER_ALIASES` / `PREZZO_HEADER_ALIASES` (frozenset). + helper `_column_price_parseable_ratio(series) -> float` (frazione valori parseable via `parse_eur` + numerici nativi). + helper `_detect_columns(df) -> tuple[str, str]` (priorità: alias canonico → heuristica price ≥80% + descrizione avg-len ≥4 char). `parse_descrizione_prezzo_csv` ora chiama `_detect_columns` e rinomina internamente le 2 colonne riconosciute a `descrizione`/`prezzo`. R-01 NO SILENT DROPS: `ValueError` esplicito su 1 sola colonna / nessun candidato prezzo / ambiguità tie / nessun candidato descrizione. Colonne opzionali (`v_tot`/`s_comp`/`category_node`) invariate (sempre per nome canonico). |
| `tests/unit/test_listino_input.py` | + 12 test parametrici nuovi (alias `prodotto`/`costo`, header anonimi numerici+stringhe, mix CSV reali, edge cases 1-col/all-string/all-numeric/tie ambiguo, opzionali preservate post-detect). Test esistenti backwards-compat invariati. |

## Why

Decisione Leader 2026-05-02 round 7: il CFO non deve riformattare il
proprio CSV per matchare i nostri header. Esempio realistico: export
di un gestionale interno con colonne `Articolo` + `Costo unitario` o
`Prodotto` + `Prezzo €`. Vincolo separazione mantenuto: 2 colonne
distinte (no `"Galaxy S24, 549"` in unica colonna).

Strategia heuristica deterministica:
1. **Match per alias** (case-insensitive, `frozenset` lookup):
   - desc: `descrizione/description/prodotto/product/title/titolo/nome/name/articolo`
   - prezzo: `prezzo/price/costo/cost/prezzo_fornitore/prezzo_eur/costo_eur/cst`
2. **Heuristica price-parseable** (≥80% righe via `parse_eur` o numerico
   nativo). Pick max ratio; tie esatto → `ValueError` esplicito.
3. **Heuristica descrizione** (avg string length ≥4 char). Pick max
   avg-len fra colonne residue.
4. Fallisce esplicitamente se: <2 colonne / 0 candidati prezzo /
   tie esatto sul max / 0 candidati descrizione.

Backwards-compat 100%: i CSV esistenti con header `descrizione`/`prezzo`
matchano via alias al primo step (zero behavior change). Le colonne
opzionali (`v_tot`/`s_comp`/`category_node`) restano per nome canonico.

## Tests

ruff/format/mypy strict OK. **TBD PASS** (TBD unit/gov/golden + 160 integration).

- 6 test parametrici nuovi su alias (case/whitespace/varianti `prodotto`/`costo`/`articolo`).
- 4 test heuristica (header anonimi, numerici detected come prezzo, stringhe lunghe detected come desc, fallback opzionali invariate post-detect).
- 4 test errori espliciti (1-col / no-price-candidate / tie-ambiguous / all-numeric).
- 11 test esistenti `test_parse_csv_*` invariati (backwards-compat).

## Test di Conformità

- ADR-0017 (acquisizione dati): `parse_eur` (CHG-2026-05-01-002) riusato come oracle price-detection. Zero nuove deps, zero nuovi eventi canonici.
- ADR-0016 (UI): `parse_descrizione_prezzo_csv` resta helper puro (no Streamlit dep), testabile mock-only.
- ADR-0019 (test strategy): test parametrici + edge cases espliciti + backwards-compat sentinel.
- ADR-0014 (quality gates): ruff strict + mypy strict + format puliti.
- R-01 NO SILENT DROPS: `ValueError` esplicito (no fallback silente, no skip silente, no detection guess unsafe).

## Refs

- ADR-0016, ADR-0017, ADR-0019, ADR-0014.
- Predecessore: CHG-2026-05-01-020 (`parse_descrizione_prezzo_csv` MVP), CHG-2026-05-02-011 (header normalization).
- `parse_eur` riusato da `src/talos/io_/scraper.py:238`.
- Decisione Leader 2026-05-02 round 7: "i listini accettati non devono iniziare con `descrizione`/`prezzo`, i due dati devono essere in colonne separate".
- Commit: `aaad10f`.
