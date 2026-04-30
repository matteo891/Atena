---
id: CHG-2026-04-30-018
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Decima e ultima tabella dell'Allegato A** (10/10): `AuditLog` (tabella `audit_log`) — registro append-only delle modifiche sulle tabelle critiche. Schema dell'Allegato A **completo**.

Migration `6e03f2a4f5a3` introduce 3 elementi:
1. La tabella `audit_log` (8 colonne, **due colonne JSONB**, no FK).
2. La funzione PL/pgSQL `record_audit_log()` che cattura `session_user`, mappa `TG_OP` su `'I'`/`'U'`/`'D'` e serializza OLD/NEW in JSONB.
3. **Tre trigger AFTER** (`trg_audit_storico_ordini`, `trg_audit_locked_in`, `trg_audit_config_overrides`) sulle tabelle critiche.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/audit_log.py` | nuovo | `class AuditLog(Base)` con 8 colonne dell'Allegato A: `id` BigInt PK, `actor` Text NOT NULL, `table_name` Text NOT NULL, `op` CHAR(1) NOT NULL, `row_id` BigInt NULL, `before_data` JSONB NULL, `after_data` JSONB NULL, `at` TIMESTAMPTZ default NOW NOT NULL (regola CHG-010). Type hint per JSONB: `Mapped[dict[str, Any] \| None]` |
| `migrations/versions/6e03f2a4f5a3_create_audit_log_with_triggers.py` | nuovo | `op.create_table` + `op.execute(_FUNCTION_BODY)` PL/pgSQL + loop su `_AUDITED_TABLES` per i 3 `CREATE TRIGGER`. Downgrade simmetrico (drop trigger × 3, drop function, drop table) |
| `tests/unit/test_audit_log_model.py` | nuovo | 19 test invarianti: 11 strutturali (incluso `test_no_foreign_keys`, `test_op_char_1_not_null`, JSONB type su `before_data`/`after_data`), 4 schema-aware sul file di migration (funzione PL/pgSQL, mapping I/U/D, 3 trigger, downgrade simmetrico), 4 costruzioni runtime (campi minimi, payload JSONB, INSERT/UPDATE/DELETE op codes) |
| `src/talos/persistence/models/__init__.py` + `persistence/__init__.py` | modificati | Re-export `AuditLog` |

Quality gate locale verde: **153 test PASS** (era 134, +19), mypy strict pulito su 17 source file.

## Why

**Conclude la copertura dello schema dell'Allegato A di ADR-0015.** Tutte le 10 tabelle sono ora inscritte come ORM model + Alembic revision in catena, con SQL offline coerente verbatim allo schema dell'ADR.

`audit_log` è la **spina dorsale** dell'integrità Zero-Trust:
- Ogni mutazione su `storico_ordini` (R-03 registro permanente), `locked_in` (R-04 Manual Override), `config_overrides` (parametri di runtime) viene tracciata automaticamente lato DB.
- Il record cattura `session_user` come actor — non un identificatore applicativo che potrebbe essere falsificato.
- Le colonne JSONB `before_data`/`after_data` permettono ricostruzione completa dello stato prima/dopo la modifica.

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `actor` | `TEXT NOT NULL` | `Mapped[str] = mapped_column(Text, nullable=False)` |
| `table_name` | `TEXT NOT NULL` | `Mapped[str] = mapped_column(Text, nullable=False)` |
| `op` | `CHAR(1) NOT NULL` | `Mapped[str] = mapped_column(CHAR(1), nullable=False)` |
| `row_id` | `BIGINT` | `Mapped[int \| None] = mapped_column(BigInteger, nullable=True)` |
| `before_data` | `JSONB` | `Mapped[dict[str, Any] \| None] = mapped_column(JSONB, nullable=True)` |
| `after_data` | `JSONB` | `Mapped[dict[str, Any] \| None] = mapped_column(JSONB, nullable=True)` |
| `at` | `TIMESTAMPTZ DEFAULT NOW()` | `Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)` (regola CHG-010) |

JSONB importato da `sqlalchemy.dialects.postgresql.JSONB`. Il tipo Python `Mapped[dict[str, Any] | None]` accetta sia letterali Python (`{"key": "value"}`) sia oggetti JSON deserializzati.

### Funzione PL/pgSQL `record_audit_log()`

Singola funzione, riusabile per tutti i trigger (Allegato A non li differenzia):

```sql
CREATE OR REPLACE FUNCTION record_audit_log()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (actor, table_name, op, row_id, before_data, after_data)
    VALUES (
        session_user,
        TG_TABLE_NAME,
        CASE TG_OP
            WHEN 'INSERT' THEN 'I'
            WHEN 'UPDATE' THEN 'U'
            WHEN 'DELETE' THEN 'D'
        END,
        COALESCE(NEW.id, OLD.id),
        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE row_to_json(OLD)::jsonb END,
        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE row_to_json(NEW)::jsonb END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

**Decisioni:**
- `session_user` (built-in Postgres) come `actor`: cattura il ruolo DB della sessione corrente — non manipolabile dall'applicazione.
- `TG_TABLE_NAME` (variabile trigger): nome tabella catturato in automatico, no hard-coding.
- `COALESCE(NEW.id, OLD.id)`: assume che ogni tabella audited abbia colonna `id` BigInt PK. Le 3 tabelle critiche soddisfano la condizione (verificato dai loro test).
- `RETURN COALESCE(NEW, OLD)`: il trigger AFTER richiede di tornare la riga; la `COALESCE` copre tutti i casi (INSERT/UPDATE → NEW, DELETE → OLD).

### Trigger AFTER su 3 tabelle critiche

Loop f-string su `_AUDITED_TABLES = ("storico_ordini", "locked_in", "config_overrides")`:

```python
for table_name in _AUDITED_TABLES:
    op.execute(f"""
        CREATE TRIGGER trg_audit_{table_name}
        AFTER INSERT OR UPDATE OR DELETE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION record_audit_log()
    """)
```

Pattern DRY: aggiungere una nuova tabella audited = appender al tuple, non duplicare lo statement.

### Out-of-scope di questa migration

L'Allegato A include anche:
- `CREATE ROLE talos_admin/talos_app/talos_audit WITH LOGIN PASSWORD :…`
- `GRANT INSERT ON audit_log TO talos_app`
- `REVOKE UPDATE, DELETE ON audit_log FROM talos_app`
- `GRANT SELECT ON audit_log TO talos_audit`

Questi statement richiedono **ruoli pre-esistenti** e gestione delle password (env-var / secrets / placeholder). Non hanno luogo in una migration applicativa Alembic. Sono in scope di un futuro CHG dedicato che introdurrà `scripts/db-bootstrap.sh` (idempotente, parametrizzato da env-var sui password).

In sviluppo locale (utente superuser/admin) la tabella `audit_log` è scrivibile da chiunque — protezione di default Postgres. La disciplina append-only si chiude **solo in produzione** con il bootstrap dei ruoli e dei `GRANT/REVOKE`. Documentato come "rischio residuo" qui sotto.

### Validazione end-to-end (offline SQL)

`alembic upgrade e7a92c0260fa:6e03f2a4f5a3 --sql` produce:

```sql
CREATE TABLE audit_log (
    id BIGSERIAL NOT NULL,
    actor TEXT NOT NULL,
    table_name TEXT NOT NULL,
    op CHAR(1) NOT NULL,
    row_id BIGINT,
    before_data JSONB,
    after_data JSONB,
    at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);
CREATE OR REPLACE FUNCTION record_audit_log() RETURNS TRIGGER AS $$ ... $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_audit_storico_ordini AFTER INSERT OR UPDATE OR DELETE ON storico_ordini ... EXECUTE FUNCTION record_audit_log();
CREATE TRIGGER trg_audit_locked_in AFTER INSERT OR UPDATE OR DELETE ON locked_in ... EXECUTE FUNCTION record_audit_log();
CREATE TRIGGER trg_audit_config_overrides AFTER INSERT OR UPDATE OR DELETE ON config_overrides ... EXECUTE FUNCTION record_audit_log();
```

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 34 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 17 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 153 passed in 0.34s |
| Migration offline | `uv run alembic upgrade e7a92c0260fa:6e03f2a4f5a3 --sql` | ✅ DDL + funzione + 3 trigger coerenti |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (19): 8 strutturali (tablename, metadata, 8 colonne, PK, no FK, actor/table_name NOT NULL, op CHAR(1) NOT NULL, row_id nullable) + 2 specifici JSONB (`before_data`, `after_data`) + 1 default `at NOW NOT NULL` + 4 schema-aware sul file di migration (CREATE FUNCTION, mapping I/U/D, 3 CREATE TRIGGER, downgrade simmetrico) + 1 set columns + 3 costruzioni runtime (campi minimi, INSERT con payload, UPDATE con before+after).

**Rischi residui:**
- **Append-only effettivo richiede ruoli + GRANT/REVOKE**, gestiti fuori da questa migration. In sviluppo locale chiunque può eseguire `UPDATE`/`DELETE` su `audit_log`. Documentato. Risolvibile con CHG futuro su `scripts/db-bootstrap.sh`.
- La funzione `record_audit_log()` assume che la tabella audited abbia colonna `id` BigInt PK. Vero per le 3 tabelle attuali; se in futuro si vorrà auditare una tabella senza `id`, va estesa la funzione (parametrizzata o specializzata).
- Test "schema-aware" su file di migration coprono la **presenza** dei trigger e della funzione, non l'**effetto** runtime. Quando arriverà Postgres in Docker, integration test reali (`tests/integration/test_audit_log_triggers.py`) verificheranno: INSERT su `storico_ordini` → 1 riga in `audit_log` con `op='I'`, `before_data IS NULL`, `after_data` JSONB del payload.
- JSONB type a runtime usa `Mapped[dict[str, Any] | None]`: `Any` è una scelta consapevole (gli oggetti JSONB possono contenere qualsiasi tipo serializzabile).
- `op` CHAR(1) accetta qualsiasi singolo carattere; `'I'/'U'/'D'` è solo convenzione applicativa enforced dalla funzione `record_audit_log()`. Volendo, una errata corrige di ADR-0015 potrebbe aggiungere un `CHECK (op IN ('I', 'U', 'D'))`.

## Refs

- ADR: ADR-0015 (Allegato A — schema completo, ora 10/10), ADR-0014 (mypy + ruff strict), ADR-0013 (struttura `models/`), ADR-0019 (test unit + schema-aware)
- Predecessore: CHG-2026-04-30-017 (`locked_in`)
- **Conclude la sequenza CHG-008 → CHG-018: 9 tabelle dell'Allegato A introdotte come ORM + 1 errata corrige di chiarimento (CHG-010 "DEFAULT → NOT NULL")**
- Successore atteso: setup bootstrap ruoli/GRANT/REVOKE (`scripts/db-bootstrap.sh`) oppure cambio direzione verso un altro modulo applicativo
- Commit: `<pending>`
