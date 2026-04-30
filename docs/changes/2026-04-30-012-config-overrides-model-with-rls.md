---
id: CHG-2026-04-30-012
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Quarta tabella dell'Allegato A**: `ConfigOverride` (tabella `config_overrides`) — override runtime di parametri di configurazione (`veto_roi_pct`, `referral_fee_pct`) con scoping `global`/`category`/`asin`. **Prima tabella con Row-Level Security (RLS) Zero-Trust attiva** + **prima con indice UNIQUE composito a 4 colonne**. Revision Alembic `027a145f76a8` in catena (revises `d6ab9ffde2a2`). Migration validata offline.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/config_override.py` | nuovo | `class ConfigOverride(Base)` con 8 colonne dell'Allegato A: `id` BigInt PK, `scope`/`key` Text NOT NULL, `scope_key`/`value_numeric`/`value_text` NULL, `value_numeric` Numeric(12,4), `updated_at` TIMESTAMP TZ default NOW NOT NULL (regola CHG-010 "DEFAULT → NOT NULL"), `tenant_id` BigInt default 1 NOT NULL. `__table_args__ = (Index("idx_config_unique", "tenant_id", "scope", "scope_key", "key", unique=True),)` |
| `migrations/versions/027a145f76a8_create_config_overrides_with_rls.py` | nuovo | `op.create_table` + `op.create_index(unique=True)` + `op.execute("ALTER TABLE ... ENABLE ROW LEVEL SECURITY")` + `op.execute("CREATE POLICY tenant_isolation ...")`. `downgrade()` simmetrico: `DROP POLICY IF EXISTS` → `DISABLE RLS` → `drop_index` → `drop_table`. Catena: `Revises: d6ab9ffde2a2` |
| `tests/unit/test_config_override_model.py` | nuovo | 15 test invarianti: 12 sul modello + **3 verifiche statiche del file di migration** sulla presenza di `ENABLE ROW LEVEL SECURITY`, della policy `tenant_isolation` con `current_setting('talos.tenant_id'`, e del downgrade simmetrico (`DROP POLICY IF EXISTS` + `DISABLE`) |
| `src/talos/persistence/models/__init__.py` | modificato | Re-export anche `ConfigOverride` |
| `src/talos/persistence/__init__.py` | modificato | Re-export anche `ConfigOverride` |

Quality gate locale verde: **63 test PASS** (era 48, +15), mypy strict pulito su 11 source file, `alembic upgrade --sql` produce DDL + `CREATE UNIQUE INDEX` + `ENABLE RLS` + `CREATE POLICY` coerenti.

## Why

ADR-0015 prescrive `config_overrides` come tabella critica per gli override di runtime (`veto_roi_pct`, `referral_fee_pct`) e indica esplicitamente:
- **Indice UNIQUE composito** su `(tenant_id, scope, scope_key, key)` per evitare collisioni della stessa chiave di config nello stesso scope per lo stesso tenant.
- **RLS attiva** con policy `tenant_isolation` (predispone multi-tenancy futura, MVP single-tenant con default `tenant_id=1`).

Beneficio strutturale:
1. **Pattern RLS ratificato** per le 3 tabelle che lo richiedono nell'Allegato A: `storico_ordini`, `locked_in`, `config_overrides`. I prossimi 2 modelli con RLS riuseranno lo stesso schema (`op.execute("ALTER TABLE ... ENABLE ROW LEVEL SECURITY")` + `CREATE POLICY tenant_isolation ... USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)`).
2. **Pattern UNIQUE INDEX composito** ratificato (in SQLAlchemy 2.0: `Index(name, *cols, unique=True)`).
3. **Test "schema-aware sulle migration"**: 3 test verificano staticamente il contenuto del file di revision per RLS e policy. È un livello di test in più rispetto a quelli puri sui mapper — utile finché non c'è Postgres reale per integration test.

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `scope` | `TEXT NOT NULL` | `Mapped[str] = mapped_column(Text, nullable=False)` |
| `scope_key` | `TEXT` | `Mapped[str \| None] = mapped_column(Text, nullable=True)` |
| `key` | `TEXT NOT NULL` | `Mapped[str] = mapped_column(Text, nullable=False)` |
| `value_numeric` | `NUMERIC(12,4)` | `Mapped[Decimal \| None] = mapped_column(Numeric(12, 4), nullable=True)` |
| `value_text` | `TEXT` | `Mapped[str \| None] = mapped_column(Text, nullable=True)` |
| `updated_at` | `TIMESTAMPTZ DEFAULT NOW()` | `Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)` (regola CHG-010 "DEFAULT → NOT NULL") |
| `tenant_id` | `BIGINT NOT NULL DEFAULT 1` | `Mapped[int] = mapped_column(BigInteger, server_default=text("1"), nullable=False)` |

### Indice UNIQUE composito

```python
__table_args__ = (
    Index(
        "idx_config_unique",
        "tenant_id",
        "scope",
        "scope_key",
        "key",
        unique=True,
    ),
)
```

L'ordine delle colonne nell'indice **combacia letteralmente con l'Allegato A**: `(tenant_id, scope, scope_key, key)`. L'ordine ha rilevanza per gli scan parziali (es. lookup per solo `tenant_id` usa l'indice; lookup per solo `key` no). Il test `test_unique_composite_index_present` blocca eventuali permutazioni.

### RLS Zero-Trust nella migration

SQLAlchemy ORM non ha API native per RLS (è un costrutto Postgres-specifico). La migration esegue raw SQL via `op.execute()`:

```python
# upgrade()
op.execute("ALTER TABLE config_overrides ENABLE ROW LEVEL SECURITY")
op.execute("""
    CREATE POLICY tenant_isolation ON config_overrides
        USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)
""")

# downgrade()
op.execute("DROP POLICY IF EXISTS tenant_isolation ON config_overrides")
op.execute("ALTER TABLE config_overrides DISABLE ROW LEVEL SECURITY")
```

**`current_setting('talos.tenant_id', true)`**: il secondo argomento `true` evita errore se la variabile non è settata (la query restituisce stringa vuota, e il cast a `bigint` su stringa vuota poi fallisce — ma se la connessione applicativa ha sempre `SET LOCAL talos.tenant_id`, non si arriva mai lì). Il bootstrap della connessione (futuro CHG su `engine`/`SessionLocal`) imposterà la variabile.

**`DROP POLICY IF EXISTS`**: difensivo nel downgrade. Se per qualche motivo la policy fosse già stata rimossa fuori da Alembic, il `DROP POLICY` plain fallirebbe; con `IF EXISTS` il downgrade resta idempotente.

### Test "schema-aware" sul file di migration

Tre test leggono staticamente il file `027a145f76a8_create_config_overrides_with_rls.py` e verificano la presenza dei pezzi RLS-critici:

```python
@pytest.mark.unit
def test_migration_file_contains_rls_enable() -> None:
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in content

@pytest.mark.unit
def test_migration_file_contains_tenant_isolation_policy() -> None:
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE POLICY tenant_isolation" in content
    assert "current_setting('talos.tenant_id'" in content

@pytest.mark.unit
def test_migration_file_downgrade_drops_policy_and_disables_rls() -> None:
    content = _MIGRATION_PATH.read_text(encoding="utf-8")
    assert "DROP POLICY IF EXISTS tenant_isolation" in content
    assert "DISABLE ROW LEVEL SECURITY" in content
```

Razionale: senza Postgres in Docker non possiamo testare la policy effettivamente attiva. Verificare staticamente il contenuto del file di migration garantisce che eventuali edit accidentali (es. rimozione delle `op.execute(...)` durante un merge) vengano intercettati dal Test Gate prima del commit. Quando arriverà l'integration test, sostituiremo questi test statici con un test funzionale reale (rimozione tramite Errata di ADR-0019 se serve).

### Validazione end-to-end (offline SQL)

`alembic upgrade d6ab9ffde2a2:027a145f76a8 --sql` produce:

```sql
CREATE TABLE config_overrides (
    id BIGSERIAL NOT NULL,
    scope TEXT NOT NULL,
    scope_key TEXT,
    key TEXT NOT NULL,
    value_numeric NUMERIC(12, 4),
    value_text TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    tenant_id BIGINT DEFAULT 1 NOT NULL,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX idx_config_unique ON config_overrides (tenant_id, scope, scope_key, key);
ALTER TABLE config_overrides ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON config_overrides
    USING (tenant_id = current_setting('talos.tenant_id', true)::bigint);
```

Coerente con Allegato A in tutti i punti.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 23 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 11 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 63 passed in 0.26s |
| Migration offline | `uv run alembic upgrade d6ab9ffde2a2:027a145f76a8 --sql` | ✅ DDL + UNIQUE INDEX + RLS + POLICY coerenti |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (15):
- 9 invarianti strutturali (tablename, metadata, columns 8 voci, PK, NOT NULL su scope/key, nullable su altre, types, defaults)
- 1 test indice UNIQUE composito con ordine colonne corretto
- 2 test costruzione runtime (scope=global numeric, scope=asin)
- **3 test schema-aware sul file di migration** (ENABLE RLS, CREATE POLICY, downgrade)

**Rischi residui:**
- I test RLS sono **statici** (verifica contenuto file). Quando arriverà Postgres in Docker, vanno aggiunti `tests/integration/test_config_overrides_rls.py` con flusso `SET LOCAL talos.tenant_id = '1' → INSERT → SELECT` e verifica che `tenant_id = '2' → SELECT` non veda nulla.
- `value_numeric` e `value_text` sono **mutuamente esclusivi nell'intent** (uno popolato a seconda del tipo della chiave) ma l'Allegato A non vincola questo a livello DB. Validazione applicativa (futuro modulo `config/`).
- `scope` e `key` sono `TEXT` libero (Allegato A non dichiara CHECK). Valori validi `global`/`category`/`asin` per `scope` e `veto_roi_pct`/`referral_fee_pct` per `key` sono solo convenzione applicativa. Eventuale promozione a Postgres ENUM o CHECK constraint è errata corrige di ADR-0015 da discutere.
- Il `current_setting('talos.tenant_id', true)` con secondo argomento `true` evita errori se la variabile non è settata, ma una connessione applicativa che dimentica `SET LOCAL talos.tenant_id` riceverà stringa vuota → cast a `bigint` fallisce. Bootstrap della connessione (futuro CHG su engine/SessionLocal) deve garantire il `SET LOCAL`.
- `key` come nome colonna non è keyword Python ma è semanticamente vicino al `dict.keys()`. Nessun problema con SQLAlchemy/ruff/mypy oggi; se in futuro emergesse confusione, possibile rinomina in `config_key` via errata.

## Refs

- ADR: ADR-0015 (Allegato A — schema + RLS Zero-Trust + indice unique), ADR-0014 (mypy + ruff strict), ADR-0013 (struttura `models/`), ADR-0019 (test unit invarianti + schema-aware sui file migration)
- Predecessore: CHG-2026-04-30-011 (`listino_items` + FK)
- Successore atteso: prossima tabella Allegato A — probabilmente `vgp_results` (FK doppia: session_id + listino_item_id, modello con più colonne dell'Allegato A — il nucleo del decisore)
- Commit: `<pending>`
