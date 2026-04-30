---
id: CHG-2026-04-30-015
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 69cb614
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019, ADR-0018
---

## What

**Settima tabella dell'Allegato A** (7/10): `PanchinaItem` (tabella `panchina_items`) — archivio R-09. Gli ASIN con `vgp_score > 0` (match passato + ROI ≥ veto + non kill-switched) **non** entrati nel carrello per saturazione del budget vengono archiviati qui in ordine `vgp_score` decrescente. Schema isomorfo a `cart_items` ma più snello (4 colonne vs 6: niente `unit_cost_eur`, niente `locked_in`). Doppia FK CASCADE. Revision Alembic `618105641c27` in catena (revises `fa6408788e73`).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/panchina_item.py` | nuovo | `class PanchinaItem(Base)` con 4 colonne: `id` BigInt PK, `session_id`+`vgp_result_id` BigInt FK NOT NULL CASCADE, `qty_proposed` Integer NOT NULL. Relationship verso `AnalysisSession` e `VgpResult` |
| `migrations/versions/618105641c27_create_panchina_items.py` | nuovo | `op.create_table` con 2 `sa.ForeignKey(..., ondelete="CASCADE")`. Nessun indice (Allegato A letterale) |
| `tests/unit/test_panchina_item_model.py` | nuovo | 10 test invarianti (7 strutturali + 2 relationship + 1 costruzione) |
| `src/talos/persistence/models/analysis_session.py` | modificato | Aggiunta relationship `panchina_items: Mapped[list[PanchinaItem]]` con `passive_deletes=True` |
| `src/talos/persistence/models/vgp_result.py` | modificato | Aggiunta relationship `panchina_items: Mapped[list[PanchinaItem]]` con `passive_deletes=True` |
| `src/talos/persistence/models/__init__.py` + `persistence/__init__.py` | modificati | Re-export `PanchinaItem` |

Quality gate locale verde: **102 test PASS** (era 92, +10), mypy strict pulito su 14 source file.

## Why

R-09 (archiviazione) è il complemento di R-06 (saturazione carrello): ogni sessione produce un carrello di acquisto + una "panchina" di candidati validi non scelti per limiti di budget. Il CFO può promuovere manualmente dalla panchina al carrello eliminando un ASIN già scelto. Senza la tabella `panchina_items` questa funzione resta non persistita.

Schema **isomorfo a `cart_items`** ma volutamente più snello:
- Niente `unit_cost_eur`: il costo è recuperabile via FK → `vgp_results.cash_profit_eur` o tramite `listino_items.cost_eur`. Allegato A non lo duplica.
- Niente `locked_in`: la panchina è per definizione "non scelta" — R-04 (Manual Override) si applica solo al carrello.

Pattern già ratificato in CHG-014 (`cart_items`): doppia FK CASCADE + relationship triple su `AnalysisSession`/`VgpResult`. Costo di introduzione minimo, copertura test analoga.

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `session_id` | `BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE` | `Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)` |
| `vgp_result_id` | `BIGINT NOT NULL REFERENCES vgp_results(id) ON DELETE CASCADE` | `Mapped[int] = mapped_column(BigInteger, ForeignKey("vgp_results.id", ondelete="CASCADE"), nullable=False)` |
| `qty_proposed` | `INT NOT NULL` | `Mapped[int] = mapped_column(Integer, nullable=False)` |

**Aderenza letterale all'Allegato A:** nessun indice secondario.

### Validazione end-to-end (offline SQL)

`alembic upgrade fa6408788e73:618105641c27 --sql` produce:

```sql
CREATE TABLE panchina_items (
    id BIGSERIAL NOT NULL,
    session_id BIGINT NOT NULL,
    vgp_result_id BIGINT NOT NULL,
    qty_proposed INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE,
    FOREIGN KEY(vgp_result_id) REFERENCES vgp_results (id) ON DELETE CASCADE
);
```

Coerente verbatim con Allegato A.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 28 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 14 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 102 passed in 0.31s |
| Migration offline | `uv run alembic upgrade fa6408788e73:618105641c27 --sql` | ✅ DDL coerente |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (10): 7 invarianti strutturali (tablename, metadata, 4 colonne, PK, 2 FK CASCADE distinte, qty_proposed Int NOT NULL) + 2 relationship bidirezionali + 1 costruzione runtime.

**Rischi residui:**
- Senza indice `(session_id)` la query "tutta la panchina di una sessione" farà sequential scan. Identico discorso di `cart_items` (CHG-014): rivedibile via errata corrige di ADR-0015 se la performance reale lo rende necessario.
- `qty_proposed > 0` non vincolato a livello CHECK: validazione applicativa nel modulo `tetris/panchina.py` (ADR-0018).
- L'ordinamento "vgp_score decrescente" della panchina è una proprietà applicativa: la query del Tetris allocator userà `JOIN vgp_results ORDER BY vgp_score DESC` sfruttando l'indice `idx_vgp_session_score` di CHG-013.

## Refs

- ADR: ADR-0015 (Allegato A — schema), ADR-0018 (consumatore: `tetris/panchina.py` — R-09 archiviazione), ADR-0014, ADR-0013, ADR-0019
- Predecessore: CHG-2026-04-30-014 (`cart_items` — schema isomorfo)
- Successore atteso: prossima tabella Allegato A — `storico_ordini` (RLS + FK doppia, R-03 ORDER-DRIVEN MEMORY) o `locked_in` (RLS standalone, R-04)
- Commit: `69cb614`
