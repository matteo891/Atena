---
id: CHG-2026-04-30-011
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Terza tabella dell'Allegato A**: `ListinoItem` (tabella `listino_items`) — riga del listino fornitore. **Primo modello con FK** (`session_id → sessions.id ON DELETE CASCADE`), e prima relationship bidirezionale `AnalysisSession.listino_items ↔ ListinoItem.session`. Revision Alembic `d6ab9ffde2a2` in catena (revises `d4a7e3cefbb1`). Migration validata offline.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/listino_item.py` | nuovo | `class ListinoItem(Base)` con 8 colonne dell'Allegato A: `id` BigInt PK, `session_id` BigInt FK→sessions(id) ON DELETE CASCADE NOT NULL, `asin` CHAR(10) NULL **(senza FK, da Allegato A letterale)**, `raw_title` TEXT NOT NULL, `cost_eur` NUMERIC(12,2) NOT NULL, `qty_available` Integer NULL, `match_status` TEXT NULL, `match_reason` TEXT NULL. `__table_args__ = (Index("idx_listino_session", "session_id"),)`. Relationship `session: Mapped[AnalysisSession] = relationship(back_populates="listino_items")` |
| `src/talos/persistence/models/analysis_session.py` | modificato | Aggiunta relationship inversa: `listino_items: Mapped[list[ListinoItem]] = relationship(back_populates="session", passive_deletes=True)`. Import `relationship`. Import `ListinoItem` in `TYPE_CHECKING` (forward reference) |
| `migrations/versions/d6ab9ffde2a2_create_listino_items.py` | nuovo | `op.create_table("listino_items", ...)` con `sa.ForeignKey("sessions.id", ondelete="CASCADE")` + `op.create_index("idx_listino_session", ...)`. Catena: `Revises: d4a7e3cefbb1` |
| `tests/unit/test_listino_item_model.py` | nuovo | 12 test invarianti, **incluso test esplicito della relationship bidirezionale e della cascade** |
| `src/talos/persistence/models/__init__.py` | modificato | Re-export anche `ListinoItem` |
| `src/talos/persistence/__init__.py` | modificato | Re-export anche `ListinoItem` |

Quality gate locale verde: **48 test PASS** (era 36, +12), mypy strict pulito su 10 source file, `alembic upgrade head --sql` produce DDL coerente con Allegato A (FK ON DELETE CASCADE inscritto nel SQL).

## Why

ADR-0015 prescrive `listino_items` come prima tabella dipendente da `sessions` (FK). Introdurre questo modello sblocca:
1. Pattern **FK + relationship bidirezionale + ON DELETE CASCADE** ratificato e testato. I prossimi 7 modelli (`vgp_results`, `cart_items`, `panchina_items`, `storico_ordini`, `locked_in`, `config_overrides`, `audit_log`) usano lo stesso pattern.
2. Pattern **forward reference circolare con `TYPE_CHECKING`**: `analysis_session.py` ↔ `listino_item.py` si referenziano a vicenda senza import circolare a runtime. Funziona perché SQLAlchemy 2.0 risolve le annotazioni `Mapped["ClassName"]` via `Base._sa_registry` lazily al primo accesso.
3. Pattern **cascade DB-side, non ORM-side**: `ON DELETE CASCADE` è dichiarato in `ForeignKey(ondelete="CASCADE")`; lato `AnalysisSession.listino_items` uso `passive_deletes=True` per evitare doppia logica (SQLAlchemy non emette DELETE individuali sui figli — il DB se ne occupa).
4. Test coverage del pattern: `test_session_id_is_required_foreign_key_with_cascade` verifica esplicitamente FK target + `ondelete == "CASCADE"`. `test_relationship_session_back_populates_listino_items` verifica le due relationship sono speculari.

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `session_id` | `BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE` | `Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)` |
| `asin` | `CHAR(10)` (nullable) | `Mapped[str \| None] = mapped_column(CHAR(10), nullable=True)` |
| `raw_title` | `TEXT NOT NULL` | `Mapped[str] = mapped_column(Text, nullable=False)` |
| `cost_eur` | `NUMERIC(12,2) NOT NULL` | `Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)` |
| `qty_available` | `INT` | `Mapped[int \| None] = mapped_column(Integer, nullable=True)` |
| `match_status` | `TEXT` | `Mapped[str \| None] = mapped_column(Text, nullable=True)` |
| `match_reason` | `TEXT` | `Mapped[str \| None] = mapped_column(Text, nullable=True)` |

### Decisione: `asin` senza FK ad `asin_master`

L'Allegato A scrive **letteralmente** `asin CHAR(10)` (senza `REFERENCES asin_master(asin)`). Aderenza letterale: nessuna FK introdotta. Razionale (verbatim Allegato A): *"nullable: match Amazon avviene dopo"*. Il match ASIN è in-flight via Keepa/scraping (ADR-0017): `asin_master` può non essere ancora popolato al momento dell'ingestion.

Test esplicito: `test_asin_nullable_no_foreign_key` verifica `len(list(col.foreign_keys)) == 0`. Se in futuro il Leader vorrà introdurre la FK opzionale, sarà un'errata corrige tracciabile.

### Pattern relationship bidirezionale (SQLAlchemy 2.0 typed)

In `listino_item.py`:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from talos.persistence.models.analysis_session import AnalysisSession

class ListinoItem(Base):
    ...
    session: Mapped[AnalysisSession] = relationship(back_populates="listino_items")
```

In `analysis_session.py`:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from talos.persistence.models.listino_item import ListinoItem

class AnalysisSession(Base):
    ...
    listino_items: Mapped[list[ListinoItem]] = relationship(
        back_populates="session",
        passive_deletes=True,
    )
```

`from __future__ import annotations` (già attivo in entrambi i file) trasforma le annotazioni in stringhe lazy. SQLAlchemy 2.0 le risolve cercando le classi nel `Base._sa_registry`. Nessun import circolare a runtime.

### Decisione: `passive_deletes=True` su `AnalysisSession.listino_items`

`ON DELETE CASCADE` è gestito **dal DB**. Lato ORM, `passive_deletes=True` dice a SQLAlchemy di NON emettere DELETE individuali sui figli quando si cancella una sessione: il DB cascade è autoritativo. Senza `passive_deletes`, SQLAlchemy farebbe `SELECT children → DELETE one by one`, ridondante e lento.

Trade-off: con `passive_deletes=True`, eventuali listener Python su `before_delete` di `ListinoItem` non vengono chiamati per i figli cascade-deleted. Decisione: per `listino_items` non serve listener (no logica applicativa al delete), accettato.

### Validazione end-to-end (offline SQL)

`alembic upgrade head --sql` produce per `listino_items`:

```sql
CREATE TABLE listino_items (
    id BIGSERIAL NOT NULL,
    session_id BIGINT NOT NULL,
    asin CHAR(10),
    raw_title TEXT NOT NULL,
    cost_eur NUMERIC(12, 2) NOT NULL,
    qty_available INTEGER,
    match_status TEXT,
    match_reason TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);
CREATE INDEX idx_listino_session ON listino_items (session_id);
```

Coerente con Allegato A (8 colonne, FK con CASCADE, indice secondario).

Catena revision: `9d9ebe778e40` (sessions) → `d4a7e3cefbb1` (asin_master) → `d6ab9ffde2a2` (listino_items).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 20 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 10 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 48 passed in 0.26s |
| Migration offline | `uv run alembic upgrade head --sql` | ✅ DDL `listino_items` con FK CASCADE + indice coerenti |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (12):
- 10 invarianti strutturali (tablename, metadata, columns, PK, FK con CASCADE, asin nullable senza FK, NOT NULL su raw_title/cost_eur, optional columns, indice)
- 1 test relationship bidirezionale (`session` ↔ `listino_items`, target classe, `back_populates`, `passive_deletes`)
- 1 test costruzione runtime con campi minimi

**Rischi residui:**
- Forward reference `Mapped[AnalysisSession]` con `TYPE_CHECKING` import: funziona perché SQLAlchemy 2.0 risolve via `Base._sa_registry`. Se in futuro il pattern fallisse (es. SQLAlchemy 3.0), passerei a stringhe esplicite (`Mapped["AnalysisSession"]`) o import runtime nel file figlio.
- `passive_deletes=True` evita logiche Python sui figli al cascade. Se in futuro servirà un audit log row su `ListinoItem` cancellati, va aggiunto un trigger DB (coerente con il design Zero-Trust di ADR-0015) — non un listener Python.
- Nessun test integration con DB reale: la cascade è verificata solo dichiarativamente. Quando arriverà Postgres in Docker, aggiungere `tests/integration/test_listino_items_cascade.py` che esegue effettivamente `DELETE FROM sessions WHERE id=...` e verifica che le righe `listino_items` siano sparite.
- `match_status` è `TEXT` libero (Allegato A letterale). I valori validi `MATCH_SICURO` / `AMBIGUO` / `KILLED` sono enforced solo a livello applicativo (futuro modulo `extract/`). Eventuale promozione a Postgres ENUM type è errata corrige di ADR-0015 da discutere.

## Refs

- ADR: ADR-0015 (Allegato A — schema + regola "DEFAULT → NOT NULL" da CHG-010), ADR-0014 (mypy + ruff strict), ADR-0013 (struttura `models/`), ADR-0019 (test unit invarianti incluso relationship)
- Predecessore: CHG-2026-04-30-010 (errata DEFAULT → NOT NULL)
- Successore atteso: prossima tabella Allegato A — probabilmente `vgp_results` (FK doppia: session_id + listino_item_id) o `config_overrides` (RLS attiva, primo modello con policy)
- Commit: `<pending>`
