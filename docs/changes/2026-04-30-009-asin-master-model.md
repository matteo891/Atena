---
id: CHG-2026-04-30-009
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Seconda tabella dell'Allegato A**: `AsinMaster` (tabella `asin_master`) — anagrafica ASIN, lookup table standalone (no FK). Genera la **revision Alembic** `d4a7e3cefbb1_create_asin_master.py`, in catena alla revision `9d9ebe778e40` di CHG-008. Migration validata offline via `alembic upgrade head --sql`.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/asin_master.py` | nuovo | `class AsinMaster(Base)` con 11 colonne dell'Allegato A: `asin` CHAR(10) PK, `title` Text NOT NULL, `brand` Text NOT NULL, `model`/`connectivity`/`color_family`/`category_node` Text NULL, `rom_gb`/`ram_gb` Integer NULL, `enterprise` Boolean DEFAULT false, `last_seen_at` TIMESTAMP TZ DEFAULT NOW. `__table_args__ = (Index("idx_asin_brand_model", "brand", "model"),)` |
| `migrations/versions/d4a7e3cefbb1_create_asin_master.py` | nuovo | `op.create_table("asin_master", ...)` + `op.create_index("idx_asin_brand_model", ...)`. Catena: `Revises: 9d9ebe778e40` |
| `tests/unit/test_asin_master_model.py` | nuovo | 11 test invarianti: tablename, registrazione metadata, set 11 colonne, PK CHAR(10), title/brand NOT NULL, model/conn/color/cat nullable, rom/ram Integer nullable, enterprise Boolean default false NOT NULL, last_seen_at TIMESTAMP TZ NOT NULL, indice `idx_asin_brand_model`, costruzione runtime |
| `src/talos/persistence/models/__init__.py` | modificato | Re-export anche `AsinMaster` |
| `src/talos/persistence/__init__.py` | modificato | Re-export anche `AsinMaster` |

Quality gate locale verde: **36 test PASS**, mypy strict pulito su 9 source file, `alembic upgrade head --sql` produce DDL coerente con Allegato A (sezione "Tests" sotto).

## Why

ADR-0015 Allegato A elenca 10 tabelle. Ordine di introduzione: dopo `sessions` (CHG-008), la tabella più semplice è `asin_master`:
- **Standalone** (no FK in/out).
- Popolata in seguito da Keepa (ADR-0017) — lookup table di anagrafica.
- Indice secondario (`brand`, `model`) coerente con il caso d'uso `SamsungExtractor.find_by_brand_model("Samsung", "S24")`.

Beneficio operativo:
1. Sblocca i lookup ASIN → titolo/brand/modello senza dover fare join con tabelle non ancora esistenti.
2. La FK opzionale `listino_items.asin → asin_master.asin` (prossimo CHG) è ora possibile.
3. Pattern "tabella con indice secondario" introdotto: il test verifica `idx_asin_brand_model`, garantisce che non venga rimosso silenziosamente.

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `asin` | `CHAR(10) PRIMARY KEY` | `Mapped[str] = mapped_column(CHAR(10), primary_key=True)` |
| `title` | `TEXT NOT NULL` | `Mapped[str] = mapped_column(Text, nullable=False)` |
| `brand` | `TEXT NOT NULL` | `Mapped[str] = mapped_column(Text, nullable=False)` |
| `model` | `TEXT` | `Mapped[str \| None] = mapped_column(Text, nullable=True)` |
| `rom_gb` | `INT` | `Mapped[int \| None] = mapped_column(Integer, nullable=True)` |
| `ram_gb` | `INT` | `Mapped[int \| None] = mapped_column(Integer, nullable=True)` |
| `connectivity` | `TEXT` | `Mapped[str \| None]` |
| `color_family` | `TEXT` | `Mapped[str \| None]` |
| `enterprise` | `BOOLEAN DEFAULT FALSE` | `Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)` |
| `category_node` | `TEXT` | `Mapped[str \| None]` |
| `last_seen_at` | `TIMESTAMPTZ DEFAULT NOW()` | `Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)` |

Indice secondario:
```python
__table_args__ = (Index("idx_asin_brand_model", "brand", "model"),)
```

### Convenzione "`DEFAULT` implica `NOT NULL`" — coerenza con CHG-008

L'Allegato A di ADR-0015 specifica `BOOLEAN DEFAULT FALSE` e `TIMESTAMPTZ DEFAULT NOW()` **senza** `NOT NULL` esplicito. Tuttavia in CHG-008 ho applicato la convenzione "colonna con `server_default` valido → `nullable=False` nell'ORM" anche su `sessions.started_at`. Per **coerenza tra modelli**, la stessa convenzione è applicata qui a `enterprise` e `last_seen_at`.

**Razionale operativo:** `DEFAULT` rende impossibile in pratica un valore NULL (l'`INSERT` senza valore esplicito riceve il default). Marcare `nullable=False` nell'ORM è semantica più chiara e previene mismatch tra typing Python (`Mapped[bool]` non-Optional) e DB.

**Discrepanza dichiarata:** il testo letterale dell'Allegato A non prescrive `NOT NULL` su queste colonne. Possibili risoluzioni con il Leader:
- (a) **Errata Corrige di ADR-0015** che chiarisce esplicitamente "DEFAULT implica NOT NULL nell'Allegato A". Coerente con prassi di tutti i model.
- (b) **Errata corrige inversa di CHG-008** + di questo CHG: ripristinare `nullable=True` strict letterale. Più purista ma mette a rischio il typing Python (richiede `Mapped[bool | None]`, etc.).

Lascio aperta la decisione: chiedo al Leader di ratificare (a) o (b) come parte del prossimo step.

### Validazione end-to-end (offline SQL)

`alembic upgrade head --sql` produce:

```sql
CREATE TABLE asin_master (
    asin CHAR(10) NOT NULL,
    title TEXT NOT NULL,
    brand TEXT NOT NULL,
    model TEXT,
    rom_gb INTEGER,
    ram_gb INTEGER,
    connectivity TEXT,
    color_family TEXT,
    enterprise BOOLEAN DEFAULT false NOT NULL,
    category_node TEXT,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (asin)
);
CREATE INDEX idx_asin_brand_model ON asin_master (brand, model);
UPDATE alembic_version SET version_num='d4a7e3cefbb1' WHERE alembic_version.version_num = '9d9ebe778e40';
```

Allineato con l'Allegato A (con la convenzione documentata sopra).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 18 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 9 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 36 passed in 0.32s |
| Migration offline | `uv run alembic upgrade head --sql` | ✅ DDL `asin_master` + `idx_asin_brand_model` coerente con Allegato A |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (11): `test_table_name_matches_allegato_a`, `test_table_registered_in_base_metadata`, `test_columns_are_those_of_allegato_a`, `test_primary_key_is_asin_char_10`, `test_title_and_brand_not_null`, `test_optional_anagrafica_columns_nullable`, `test_rom_ram_int_nullable`, `test_enterprise_boolean_default_false_not_null`, `test_last_seen_at_timestamptz_default_now`, `test_index_idx_asin_brand_model_exists`, `test_construct_minimal_required_fields`.

**Rischi residui:**
- **Convenzione "DEFAULT → NOT NULL"** non ancora ratificata via errata corrige ADR-0015 (vedi sezione How). Non bloccante per il funzionamento — bloccante solo se il Leader vuole strict letterale all'Allegato A.
- **Nessun test integration con Postgres reale** — la migration è validata offline (SQL output). Quando arriverà Docker, sarà necessario `alembic upgrade head` (online) sulle migration combinate `9d9ebe778e40` + `d4a7e3cefbb1`.
- L'**indice `idx_asin_brand_model`** è su `(brand, model)` ma non è UNIQUE. Coerente con Allegato A (un brand+model può avere più ASIN per varianti color/storage).
- `category_node` resta `TEXT` libero. Quando ADR-0017 introdurrà il lookup `Referral_Fee per categoria`, potrebbe servire una FK a una `categories` table — out-of-scope dell'Allegato A ad oggi.

## Refs

- ADR: ADR-0015 (Allegato A — schema), ADR-0014 (mypy + ruff strict), ADR-0013 (struttura `models/`), ADR-0019 (test unit invarianti)
- Predecessore: CHG-2026-04-30-008 (sessions model + initial migration)
- Successore atteso: prossima tabella Allegato A — probabilmente `listino_items` (FK a `sessions(id)` + nullable FK a `asin_master(asin)`), primo modello con FK
- Commit: `<pending>`
