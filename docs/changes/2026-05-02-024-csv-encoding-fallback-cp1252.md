---
id: CHG-2026-05-02-024
date: 2026-05-02
adr_ref: ADR-0017, ADR-0019, ADR-0014
commit: TBD
---

## What

Bug fix encoding CSV: `_parse_csv` ora tenta una catena di encoding
(UTF-8 → UTF-8-sig BOM → cp1252 → latin-1) prima di fallire.
Excel italiano salva CSV in cp1252 (Windows-1252), non UTF-8: il
byte `0x97` (em-dash `—` in cp1252) faceva esplodere `pd.read_csv`
con `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in
position 30: invalid start byte` al primo upload del CFO.

| File | Cosa |
|---|---|
| `src/talos/ui/document_parser.py` | + costante `CSV_ENCODING_CHAIN` (frozen tuple `("utf-8-sig", "cp1252", "latin-1")` — `utf-8-sig` come primo copre BOM Excel office 365 + UTF-8 plain). + helper `_decode_with_fallback(raw) -> str` (catena encoding per detection separatore). `_parse_csv` ora itera la catena su `pd.read_csv`: prima encoding che decodifica vince. `latin-1` finale è catch-all (single-byte, mai solleva). |
| `tests/unit/test_document_parser.py` | + 5 test parametrici (utf-8 ASCII puro, utf-8 italiano accenti, utf-8-sig BOM, cp1252 em-dash 0x97, cp1252 accenti italiano `è/à`). |

## Why

Bug live segnalato dal Leader 2026-05-02 round 7+ post-CHG-023:
upload CSV CFO da Excel/LibreOffice italiano → errore
`'utf-8' codec can't decode byte 0x97 in position 30: invalid start byte`.

Diagnosi: `pd.read_csv(io.BytesIO(raw), sep=sep)` senza `encoding=`
default UTF-8 strict. Excel su Windows italiano salva CSV in cp1252
(em-dash `—` = `0x97`, accenti `è`/`à`/`ò` = byte 0xE8-EF). UTF-8
strict rifiuta la sequenza.

Strategia fallback chain (R-01: deterministica, no chardet/fuzzy):
1. **utf-8-sig** — copre UTF-8 plain + UTF-8 con BOM (Excel office 365).
   `utf-8-sig` rimuove il BOM `﻿` se presente, altrimenti decode
   identico a UTF-8 standard.
2. **cp1252** — Windows italiano legacy (target principale del fix).
3. **latin-1** — single-byte catch-all (mai fallisce, salva il
   parsing anche su file di provenienza ignota).

L'helper `_decode_with_fallback` riusato anche per il sample del
separator detector (linea 60), per coerenza.

## Tests

ruff/format/mypy strict OK. **921 PASS** (+5 vs 916).

- 5 test parametrici nuovi (UTF-8 ASCII / UTF-8 italiano / UTF-8-sig BOM / cp1252 em-dash / cp1252 accenti).
- Test esistenti `test_parse_csv_*` invariati (backwards-compat).

## Test di Conformità

- ADR-0017 (acquisizione dati): R-01 NO SILENT DROPS — `latin-1` catch-all
  garantisce decodifica per qualsiasi byte stream; il content errato è
  responsabilità del CFO (mojibake visibile in tabella → riconoscibile).
- ADR-0019 (test strategy): test parametrici con bytes literal espliciti.
- ADR-0014 (quality gates): ruff strict + mypy strict + format puliti.

## Refs

- ADR-0017, ADR-0019, ADR-0014.
- Predecessore: CHG-2026-05-02-007 (multi-format upload).
- Bug Leader 2026-05-02: `'utf-8' codec can't decode byte 0x97 in position 30`.
- Commit: TBD.
