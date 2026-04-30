---
id: CHG-2026-04-30-016
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Ottava tabella dell'Allegato A** (8/10): `StoricoOrdine` (tabella `storico_ordini`) — registro permanente degli ordini effettuati (R-03 ORDER-DRIVEN MEMORY). **Seconda tabella con RLS Zero-Trust** dopo `config_overrides`. **Differenza chiave** rispetto a tutte le altre tabelle con FK: `session_id` e `cart_item_id` **NON hanno `ON DELETE CASCADE`** (aderenza letterale all'Allegato A — è un registro contabile permanente). Revision Alembic `a074ee67895c` in catena (revises `618105641c27`).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/storico_ordine.py` | nuovo | `class StoricoOrdine(Base)` con 8 colonne dell'Allegato A: `id` BigInt PK, `session_id`+`cart_item_id` BigInt FK NOT NULL **senza CASCADE**, `asin` CHAR(10) NOT NULL, `qty` Integer NOT NULL, `unit_cost_eur` Numeric(12,2) NOT NULL, `ordered_at` TIMESTAMPTZ default NOW NOT NULL (regola CHG-010), `tenant_id` BigInt default 1 NOT NULL. Relationship `session: Mapped[AnalysisSession]` + `cart_item: Mapped[CartItem]` (no `passive_deletes`/cascade) |
| `migrations/versions/a074ee67895c_create_storico_ordini_with_rls.py` | nuovo | `op.create_table` con 2 `sa.ForeignKey` **senza `ondelete=`** + `op.execute("ALTER TABLE ... ENABLE ROW LEVEL SECURITY")` + `op.execute("CREATE POLICY tenant_isolation ...")`. Downgrade simmetrico con `DROP POLICY IF EXISTS` + `DISABLE` |
| `tests/unit/test_storico_ordine_model.py` | nuovo | 17 test invarianti: 11 strutturali (incluso 2 espliciti per `fk.ondelete is None` su entrambe le FK), 2 relationship con `passive_deletes is False`, 3 schema-aware sul file di migration (ENABLE RLS, policy, downgrade), 1 costruzione runtime |
| `src/talos/persistence/models/analysis_session.py` | modificato | Aggiunta relationship `storico_ordini: Mapped[list[StoricoOrdine]] = relationship(back_populates="session")` (no `passive_deletes`) |
| `src/talos/persistence/models/cart_item.py` | modificato | Aggiunta relationship `storico_ordini: Mapped[list[StoricoOrdine]] = relationship(back_populates="cart_item")` (no `passive_deletes`) |
| `src/talos/persistence/models/__init__.py` + `persistence/__init__.py` | modificati | Re-export `StoricoOrdine` |

Quality gate locale verde: **119 test PASS** (era 102, +17), mypy strict pulito su 15 source file.

## Why

R-03 ORDER-DRIVEN MEMORY (PROJECT-RAW.md sezione 4) richiede che ogni ordine effettuato sia registrato in modo permanente, indipendentemente dal ciclo di vita della sessione che lo ha generato. L'Allegato A inscrive questa intenzione **omettendo deliberatamente** `ON DELETE CASCADE` sulle FK di `storico_ordini` (a differenza di `cart_items`/`panchina_items`/`vgp_results`/`listino_items` che cascadano).

**Conseguenza operativa:**
- Cancellare una sessione referenziata da uno `storico_ordine` → fallisce a livello DB (default RESTRICT).
- Stesso comportamento per cart_item.
- Questo è il **comportamento desiderato per un registro contabile**: lo storico è "per sempre".

**Conseguenza ORM:**
- Le relationship inverse su `AnalysisSession.storico_ordini` e `CartItem.storico_ordini` **non** hanno `passive_deletes=True`.
- SQLAlchemy default cascade ("save-update, merge"): nessuna logica di delete cascade. Se il caller tenta `session.delete(analysis_session)` con storico_ordini collegati, otterrà l'errore di FK constraint da Postgres — comportamento desiderato.
- I test `test_relationship_session_no_passive_deletes` e `test_relationship_cart_item_no_passive_deletes` bloccano regressioni accidentali.

**Pattern RLS** identico a `config_overrides` (CHG-012): `op.execute("ALTER TABLE ... ENABLE ROW LEVEL SECURITY")` + `CREATE POLICY tenant_isolation ON storico_ordini USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)`. Riusabile anche per `locked_in` (prossima tabella con RLS).

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `session_id` | `BIGINT NOT NULL REFERENCES sessions(id)` (no CASCADE) | `Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id"), nullable=False)` |
| `cart_item_id` | `BIGINT NOT NULL REFERENCES cart_items(id)` (no CASCADE) | `Mapped[int] = mapped_column(BigInteger, ForeignKey("cart_items.id"), nullable=False)` |
| `asin` | `CHAR(10) NOT NULL` | `Mapped[str] = mapped_column(CHAR(10), nullable=False)` |
| `qty` | `INT NOT NULL` | `Mapped[int] = mapped_column(Integer, nullable=False)` |
| `unit_cost_eur` | `NUMERIC(12,2) NOT NULL` | `Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)` |
| `ordered_at` | `TIMESTAMPTZ DEFAULT NOW()` | `Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)` (regola CHG-010) |
| `tenant_id` | `BIGINT NOT NULL DEFAULT 1` | `Mapped[int] = mapped_column(BigInteger, server_default=text("1"), nullable=False)` |

### Validazione end-to-end (offline SQL)

`alembic upgrade 618105641c27:a074ee67895c --sql` produce:

```sql
CREATE TABLE storico_ordini (
    id BIGSERIAL NOT NULL,
    session_id BIGINT NOT NULL,
    cart_item_id BIGINT NOT NULL,
    asin CHAR(10) NOT NULL,
    qty INTEGER NOT NULL,
    unit_cost_eur NUMERIC(12, 2) NOT NULL,
    ordered_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    tenant_id BIGINT DEFAULT 1 NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(session_id) REFERENCES sessions (id),
    FOREIGN KEY(cart_item_id) REFERENCES cart_items (id)
);
ALTER TABLE storico_ordini ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON storico_ordini
    USING (tenant_id = current_setting('talos.tenant_id', true)::bigint);
```

**Notare**: `FOREIGN KEY(session_id) REFERENCES sessions (id)` **senza** `ON DELETE CASCADE`. Aderente all'Allegato A.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 30 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 15 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 119 passed in 0.33s |
| Migration offline | `uv run alembic upgrade 618105641c27:a074ee67895c --sql` | ✅ DDL + 2 FK senza CASCADE + RLS + POLICY coerenti |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (17): 8 invarianti strutturali base (tablename, metadata, 8 columns, PK, asin/qty/unit_cost NOT NULL, ordered_at default NOW NOT NULL, tenant_id default 1 NOT NULL) + **2 test espliciti per `fk.ondelete is None` su entrambe le FK** + 2 relationship inverse senza `passive_deletes` + 3 schema-aware sul file di migration (RLS / POLICY / downgrade) + 1 costruzione runtime + 1 categoria copertura set-colonne.

**Rischi residui:**
- Nessun indice secondario (Allegato A letterale). Le query "tutti gli ordini di una sessione" o "tutti gli ordini di un tenant" faranno sequential scan finché il volume cresce. Errata corrige di ADR-0015 valutabile in futuro per `Index("idx_storico_session", "session_id")` o `Index("idx_storico_tenant", "tenant_id")`.
- Test RLS ancora **statici** (file migration). Quando arriverà Postgres in Docker → integration test `tests/integration/test_storico_ordini_rls.py` con flusso `SET LOCAL → INSERT → cross-tenant SELECT`.
- Comportamento "RESTRICT" sulle FK è enforced solo a livello DB. Lato applicativo, se il caller **non** ha storico_ordini collegati, `session.delete(analysis_session)` funzionerà normalmente. Disciplina applicativa: in `ui/` di ADR-0016 il bottone "elimina sessione" deve verificare l'assenza di ordini storici prima di abilitarsi.
- `qty > 0` e `unit_cost_eur > 0` non vincolati a livello CHECK: validazione applicativa.

## Refs

- ADR: ADR-0015 (Allegato A — schema + RLS), ADR-0014 (mypy + ruff strict), ADR-0013 (struttura `models/`), ADR-0019 (test unit + schema-aware)
- Predecessore: CHG-2026-04-30-015 (`panchina_items`)
- Pattern RLS riusato da: CHG-2026-04-30-012 (`config_overrides`)
- Successore atteso: prossima tabella Allegato A — `locked_in` (RLS standalone, R-04) o `audit_log` (append-only)
- Commit: `<pending>`
