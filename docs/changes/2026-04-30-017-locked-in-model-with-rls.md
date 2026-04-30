---
id: CHG-2026-04-30-017
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019, ADR-0018
---

## What

**Nona tabella dell'Allegato A** (9/10): `LockedInItem` (tabella `locked_in`) — set di ASIN che il CFO ha forzato a entrare nel carrello a Priorità ∞ (R-04 Manual Override). **Standalone** (no FK), **terza tabella con RLS Zero-Trust** (dopo `config_overrides` e `storico_ordini`). Revision Alembic `e7a92c0260fa` in catena.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/locked_in_item.py` | nuovo | `class LockedInItem(Base)` con 6 colonne dell'Allegato A: `id` BigInt PK, `asin` CHAR(10) NOT NULL, `qty_min` Integer NOT NULL, `notes` Text NULL, `created_at` TIMESTAMPTZ default NOW NOT NULL (regola CHG-010), `tenant_id` BigInt default 1 NOT NULL. Nessuna FK, nessuna relationship |
| `migrations/versions/e7a92c0260fa_create_locked_in_with_rls.py` | nuovo | `op.create_table` + `op.execute` per `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation`. Downgrade simmetrico |
| `tests/unit/test_locked_in_item_model.py` | nuovo | 15 test invarianti: 8 strutturali (incluso `test_no_foreign_keys` esplicito), 1 `notes` nullable, 3 schema-aware sul file di migration (RLS / policy / downgrade), 2 costruzioni runtime, 1 set columns |
| `src/talos/persistence/models/__init__.py` + `persistence/__init__.py` | modificati | Re-export `LockedInItem` |

Quality gate locale verde: **134 test PASS** (era 119, +15), mypy strict pulito su 16 source file.

## Why

R-04 Manual Override (PROJECT-RAW.md sezione 4.1.13): il CFO può inserire ASIN "fissi" che il Tetris allocator deve sempre mettere in carrello, **a Priorità ∞**, riservando il loro budget al di fuori del ranking VGP. Il flag `cart_items.locked_in` (CHG-014) marca queste righe **dentro il carrello**; la tabella `locked_in` invece è la **definizione persistente** di "quali ASIN sono lock-in per quel tenant".

Beneficio:
1. Sblocca il pattern di Tetris allocator: SELECT da `locked_in` per tenant → INSERT in `cart_items` con `locked_in=true` → fill VGP-based del residuo budget.
2. Pattern RLS riusato per la **terza** volta in modo identico (stessa policy `tenant_isolation`, stesso template `op.execute`). Disciplina ratificata: ogni futura tabella con RLS userà esattamente questo template.
3. Standalone (no FK): nessun delete cascade da gestire, nessuna relationship da configurare.

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `asin` | `CHAR(10) NOT NULL` | `Mapped[str] = mapped_column(CHAR(10), nullable=False)` |
| `qty_min` | `INT NOT NULL` | `Mapped[int] = mapped_column(Integer, nullable=False)` |
| `notes` | `TEXT` | `Mapped[str \| None] = mapped_column(Text, nullable=True)` |
| `created_at` | `TIMESTAMPTZ DEFAULT NOW()` | `Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)` (regola CHG-010) |
| `tenant_id` | `BIGINT NOT NULL DEFAULT 1` | `Mapped[int] = mapped_column(BigInteger, server_default=text("1"), nullable=False)` |

**Aderenza letterale all'Allegato A:** nessun `UNIQUE(tenant_id, asin)`. Concettualmente per un tenant un ASIN dovrebbe apparire una sola volta (validazione applicativa). Errata corrige di ADR-0015 ammessa se in futuro si vuole irrigidire.

### Validazione end-to-end (offline SQL)

```sql
CREATE TABLE locked_in (
    id BIGSERIAL NOT NULL,
    asin CHAR(10) NOT NULL,
    qty_min INTEGER NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    tenant_id BIGINT DEFAULT 1 NOT NULL,
    PRIMARY KEY (id)
);
ALTER TABLE locked_in ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON locked_in
    USING (tenant_id = current_setting('talos.tenant_id', true)::bigint);
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 32 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 16 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 134 passed in 0.31s |
| Migration offline | `uv run alembic upgrade a074ee67895c:e7a92c0260fa --sql` | ✅ DDL + RLS + POLICY coerenti |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (15): set colonne, PK, **`test_no_foreign_keys` esplicito** (lock-in standalone), tipi/nullable di tutte le 6 colonne, defaults `now()`/`1`, 3 schema-aware sul file di migration (RLS / policy / downgrade), 2 costruzioni runtime (campi minimi + con notes).

**Rischi residui:**
- Nessun `UNIQUE(tenant_id, asin)`: il CFO potrebbe inserire 2 volte lo stesso ASIN per lo stesso tenant. Validazione applicativa nel modulo `ui/` (ADR-0016) — pattern "INSERT ... ON CONFLICT DO UPDATE" o controllo pre-INSERT.
- `qty_min > 0` non vincolato a livello CHECK.
- Test RLS statici (file migration). Integration test reale in attesa di Postgres in Docker.

## Refs

- ADR: ADR-0015 (Allegato A), ADR-0018 (consumatore: `tetris/allocator.py` — R-04 Priorità ∞), ADR-0014, ADR-0013, ADR-0019
- Predecessore: CHG-2026-04-30-016 (`storico_ordini`)
- Pattern RLS riusato da: CHG-2026-04-30-012 (`config_overrides`), CHG-2026-04-30-016 (`storico_ordini`)
- Successore atteso: ultima tabella Allegato A — `audit_log` (append-only, REVOKE UPDATE/DELETE su talos_app)
- Commit: `<pending>`
