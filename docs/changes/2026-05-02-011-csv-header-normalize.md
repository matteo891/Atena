---
id: CHG-2026-05-02-011
date: 2026-05-02
adr_ref: ADR-0016, ADR-0017, ADR-0019
commit: TBD
---

## What

Hardening parsing CSV: header normalizzati (strip + lower) per tolleranza
Excel italiano / variazioni di case. CFO che esporta da Excel con header
"Descrizione"/"PREZZO"/"  descrizione  " ora passa la validazione.

| File | Cosa |
|---|---|
| `src/talos/ui/listino_input.py` | `parse_descrizione_prezzo_csv` rinomina colonne con `df.rename(columns=lambda c: str(c).strip().lower())` prima del check `missing`. Behavior pre-CHG: case-sensitive + whitespace-sensitive (CFO bloccato). Behavior post-CHG: tolerant. |
| `tests/unit/test_listino_input.py` | + 1 test parametrico (4 cases: title case, upper case, leading whitespace, trailing). |

## Tests

ruff/format/mypy strict OK. **878 PASS** (740 unit/gov/golden +4 + 138 integration). Risk LOW.

## Refs

- ADR-0016 (UI), ADR-0017 (input), ADR-0019.
- Driver: bug semantico CSV emerso live (CFO Excel italiano).
- Commit: TBD.
