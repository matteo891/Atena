---
id: CHG-2026-04-30-014
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 9a587cc
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019, ADR-0018
---

## What

**Sesta tabella dell'Allegato A** (6/10): `CartItem` (tabella `cart_items`) — carrello finale del Tetris allocator. Doppia FK CASCADE (`session_id`, `vgp_result_id`) + flag `locked_in` (R-04 Manual Override) con default `false` (NOT NULL implicito da regola CHG-010). Revision Alembic `fa6408788e73` in catena (revises `c9527f017d5c`). Migration validata offline.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/cart_item.py` | nuovo | `class CartItem(Base)` con 6 colonne dell'Allegato A: `id` BigInt PK, `session_id`/`vgp_result_id` BigInt FK NOT NULL CASCADE, `qty` Integer NOT NULL, `unit_cost_eur` Numeric(12,2) NOT NULL, `locked_in` Boolean default `false` NOT NULL. Relationship `session: Mapped[AnalysisSession]` + `vgp_result: Mapped[VgpResult]` |
| `migrations/versions/fa6408788e73_create_cart_items.py` | nuovo | `op.create_table` con 2 `sa.ForeignKey(..., ondelete="CASCADE")`. No indici espliciti (Allegato A non li dichiara) |
| `tests/unit/test_cart_item_model.py` | nuovo | 13 test invarianti: 9 strutturali + 2 relationship bidirezionali + 2 costruzioni (default e con `locked_in=True`) |
| `src/talos/persistence/models/analysis_session.py` | modificato | Aggiunta relationship `cart_items: Mapped[list[CartItem]] = relationship(back_populates="session", passive_deletes=True)`. Forward reference `CartItem` in `TYPE_CHECKING` |
| `src/talos/persistence/models/vgp_result.py` | modificato | Aggiunta relationship `cart_items: Mapped[list[CartItem]] = relationship(back_populates="vgp_result", passive_deletes=True)`. Forward reference `CartItem` in `TYPE_CHECKING` |
| `src/talos/persistence/models/__init__.py` | modificato | Re-export `CartItem` |
| `src/talos/persistence/__init__.py` | modificato | Re-export `CartItem` |

Quality gate locale verde: **92 test PASS** (era 79, +13), mypy strict pulito su 13 source file.

## Why

Il `cart_items` è l'output principale della sessione di analisi: ciò che il CFO può "ordinare". L'Allegato A lo definisce come tabella semplice — 6 colonne, doppia FK, un solo flag (`locked_in` per R-04). Questa è una tabella **operativa** (non analitica): la pipeline VGP → Tetris (ADR-0018) la popola al termine della run con il carrello saturato al 99.9% (R-06) + i lock-in.

Beneficio:
1. Pattern relationship triple su `VgpResult` ratificato (`session`, `listino_item`, **`cart_items`**) — il decisore VGP è ora "agganciato" sia all'input (listino_item) sia all'output (cart_items).
2. Il flag `locked_in` (R-04) sblocca il pattern di Tetris allocator: SELECT delle righe `locked_in=true` per primi a Priorità ∞.
3. `panchina_items` (prossima tabella) avrà schema isomorfo a `cart_items` (eccetto `qty_proposed` invece di `qty` + niente `locked_in`).

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `session_id` | `BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE` | `Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)` |
| `vgp_result_id` | `BIGINT NOT NULL REFERENCES vgp_results(id) ON DELETE CASCADE` | `Mapped[int] = mapped_column(BigInteger, ForeignKey("vgp_results.id", ondelete="CASCADE"), nullable=False)` |
| `qty` | `INT NOT NULL` | `Mapped[int] = mapped_column(Integer, nullable=False)` |
| `unit_cost_eur` | `NUMERIC(12,2) NOT NULL` | `Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)` |
| `locked_in` | `BOOLEAN DEFAULT FALSE` | `Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)` (regola CHG-010 "DEFAULT → NOT NULL") |

**Aderenza letterale all'Allegato A:** nessun indice secondario è dichiarato per `cart_items`. Le query "tutto il carrello di una sessione" useranno l'index implicito sulla FK `session_id` (Postgres crea automaticamente indici sulle FK in SQLAlchemy/Alembic? **No**, Alembic non li crea — Postgres stesso non li crea. Eventuale errata corrige di ADR-0015 se le query operative mostrano lentezza.

### Validazione end-to-end (offline SQL)

`alembic upgrade c9527f017d5c:fa6408788e73 --sql` produce:

```sql
CREATE TABLE cart_items (
    id BIGSERIAL NOT NULL,
    session_id BIGINT NOT NULL,
    vgp_result_id BIGINT NOT NULL,
    qty INTEGER NOT NULL,
    unit_cost_eur NUMERIC(12, 2) NOT NULL,
    locked_in BOOLEAN DEFAULT false NOT NULL,
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
| Format | `uv run ruff format --check src/ tests/` | ✅ 26 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 13 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 92 passed in 0.29s |
| Migration offline | `uv run alembic upgrade c9527f017d5c:fa6408788e73 --sql` | ✅ DDL + 2 FK CASCADE coerenti |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (13): 9 invarianti strutturali (tablename, metadata, 6 colonne, PK, 2 FK CASCADE distinte, qty NOT NULL, unit_cost NUMERIC(12,2), locked_in default false NOT NULL) + 2 relationship bidirezionali + 2 costruzioni runtime (campi minimi, `locked_in=True`).

**Rischi residui:**
- Nessun indice secondario su `session_id` o `vgp_result_id`. Le query operative ("tutto il carrello di una sessione") faranno full scan o useranno l'index implicito Postgres? **Nessuno automatico**: Postgres non crea indice sulla FK. Se in futuro si presenta lentezza su carrelli grandi, errata corrige di ADR-0015 con un `Index("idx_cart_session", "session_id")`.
- `locked_in=True` è R-04 Manual Override (Priorità ∞). La logica di "entrare per primi" nel Tetris è disciplina applicativa di `tetris/allocator.py` (ADR-0018) — non vincolo DB.
- Allegato A non vincola `qty > 0` né `unit_cost_eur > 0` a livello CHECK constraint. Validazione applicativa.

## Refs

- ADR: ADR-0015 (Allegato A — schema), ADR-0018 (consumatore: Tetris allocator), ADR-0014 (mypy + ruff strict), ADR-0013 (struttura `models/`), ADR-0019 (test unit invarianti)
- Predecessore: CHG-2026-04-30-013 (`vgp_results` — nucleo decisore)
- Tag intermedio: `checkpoint/2026-04-30-02` su `37fdc7e` (post CHG-013)
- Successore atteso: prossima tabella Allegato A — probabilmente `panchina_items` (R-09 archiviazione, schema isomorfo a `cart_items` con `qty_proposed`)
- Commit: `9a587cc`
