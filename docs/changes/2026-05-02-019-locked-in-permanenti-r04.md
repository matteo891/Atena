---
id: CHG-2026-05-02-019
date: 2026-05-02
adr_ref: ADR-0015, ADR-0016, ADR-0018, ADR-0019
commit: TBD
---

## What

R-04 LockedInItem persistence: tabella `locked_in` (schema CHG-2026-04-30-017)
ora wired al flow CFO. ASIN forzati permanenti che si combinano col text
input transient della UI (sessione singola).

| File | Cosa |
|---|---|
| `src/talos/persistence/locked_in_repository.py` | nuovo: `LockedInSummary` dataclass + `add_locked_in(asin/qty_min/notes/tenant_id)` con normalizzazione UPPER + validazione (asin 10 char, qty_min>0). + `list_locked_in` ORDER BY created_at DESC + `list_locked_in_asins` helper + `delete_locked_in(item_id) -> bool`. RLS Zero-Trust via `with_tenant`. |
| `src/talos/persistence/__init__.py` | re-export 4 simboli + `LockedInSummary`. |
| `src/talos/ui/dashboard.py` | sidebar expander "Locked-in permanenti (R-04)" con CRUD: lista corrente + delete-per-row + form ASIN/qty/notes + add. UNION DB locked-in con text_input transient nel `_render_demetra_module` (`set(transient) ∪ set(db)` sortato). Telemetry debug `locked_in.db_load_failed` su graceful fallback. |
| `tests/integration/test_locked_in_repository.py` | 8 test (empty, add+list, uppercase normalize, invalid asin length, invalid qty_min, delete-found/not-found, list_asins helper). |

## Tests

ruff/format/mypy strict OK. **896 PASS** (742 unit/gov/golden + 154 integration). Risk LOW.

## Refs

- ADR-0015 (R-04 Manual Override schema), ADR-0016 (UI), ADR-0018 (Tetris allocator R-04 priorità ∞), ADR-0019.
- Predecessore CHG-017/018 (storico_ordini wiring).
- R-04 PROJECT-RAW.md riga 222.
- Commit: TBD.
