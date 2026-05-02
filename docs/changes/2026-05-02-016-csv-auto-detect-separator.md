---
id: CHG-2026-05-02-016
date: 2026-05-02
adr_ref: ADR-0016, ADR-0017, ADR-0019
commit: TBD
---

## What

Auto-detect separatore CSV (`,`/`;`/`\t`/`|`) via `csv.Sniffer` con
fallback heuristico. Tolleranza Excel italiano (`;` default).

| File | Cosa |
|---|---|
| `src/talos/ui/document_parser.py` | `_parse_csv`: read raw bytes → `csv.Sniffer().sniff(sample, delimiters=",;\t|")` → `pd.read_csv(BytesIO(raw), sep=sep)`. Fallback su `csv.Error`: heuristic `count(';') > count(',') → ';' else ','`. |
| `tests/unit/test_document_parser.py` | + 2 test (semicolon Excel italiano, tab TSV). Totale 8 test (era 6). |

## Tests

ruff/format/mypy strict OK. **880 PASS** (742 unit/gov/golden + 138 integration).

## Refs

- ADR-0016, ADR-0017, ADR-0019.
- Driver: CFO Excel italiano salva CSV con `;` default → bug semantico
  parse silente (CHG-2026-05-02-007 base supportava solo `,`).
- Commit: TBD.
