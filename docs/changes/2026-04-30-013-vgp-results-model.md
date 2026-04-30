---
id: CHG-2026-04-30-013
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019, ADR-0018
---

## What

**Quinta tabella dell'Allegato A**: `VgpResult` (tabella `vgp_results`) — nucleo del decisore. **Primo modello con doppia FK** (`session_id`, `listino_item_id` entrambe ON DELETE CASCADE) + **primo indice composito con direzione `DESC`** sulla seconda colonna. Revision Alembic `c9527f017d5c` in catena (revises `027a145f76a8`). Migration validata offline.

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/models/vgp_result.py` | nuovo | `class VgpResult(Base)` con 15 colonne dell'Allegato A: `id` BigInt PK, `session_id`/`listino_item_id` BigInt FK NOT NULL ON DELETE CASCADE, `asin` CHAR(10) NOT NULL, 7 campi `Numeric` con precision/scale specifici (`roi_pct`/`8,4`, `velocity_monthly`/`12,4`, `cash_profit_eur`/`12,2`, `roi_norm`/`velocity_norm`/`cash_profit_norm`/`vgp_score` `6,4`), 2 flag `Boolean` (`veto_roi_passed`/R-08, `kill_switch_triggered`/R-05), 2 quantità `Integer` (`qty_target`, `qty_final` lotti R-06). `__table_args__ = (Index("idx_vgp_session_score", "session_id", text("vgp_score DESC")),)`. Relationship `session: Mapped[AnalysisSession]` + `listino_item: Mapped[ListinoItem]` |
| `migrations/versions/c9527f017d5c_create_vgp_results.py` | nuovo | `op.create_table` con 2 `sa.ForeignKey(..., ondelete="CASCADE")` + `op.create_index("idx_vgp_session_score", ..., ["session_id", sa.text("vgp_score DESC")])` |
| `tests/unit/test_vgp_result_model.py` | nuovo | 16 test invarianti: 14 strutturali (incluso 1 schema-aware sul file di migration per `vgp_score DESC`) + 2 relationship bidirezionali + 2 costruzioni runtime |
| `src/talos/persistence/models/analysis_session.py` | modificato | Aggiunta relationship `vgp_results: Mapped[list[VgpResult]] = relationship(back_populates="session", passive_deletes=True)`. Forward reference `VgpResult` in `TYPE_CHECKING` |
| `src/talos/persistence/models/listino_item.py` | modificato | Aggiunta relationship `vgp_results: Mapped[list[VgpResult]] = relationship(back_populates="listino_item", passive_deletes=True)`. Forward reference `VgpResult` in `TYPE_CHECKING` |
| `src/talos/persistence/models/__init__.py` | modificato | Re-export `VgpResult` |
| `src/talos/persistence/__init__.py` | modificato | Re-export `VgpResult` |

Quality gate locale verde: **79 test PASS** (era 63, +16), mypy strict pulito su 12 source file, `alembic upgrade --sql` produce DDL + 2 FK CASCADE + indice composito con `vgp_score DESC` coerenti.

## Why

ADR-0015 definisce `vgp_results` come la tabella più articolata dell'Allegato A: 15 colonne, doppia FK, indice tuning-aware. È **il nucleo del decisore VGP** (ADR-0018):
- I 3 termini grezzi (`roi_pct`, `velocity_monthly`, `cash_profit_eur`) sono il risultato di Formula F1/F2/F4 (ADR-0018 `formulas/`).
- I 3 normalizzati min-max [0,1] (`roi_norm`, `velocity_norm`, `cash_profit_norm`) sono il risultato di L04b / `vgp/normalize.py`.
- `vgp_score` è il risultato di `vgp/score.py`: `(roi_norm*0.4 + velocity_norm*0.4 + cash_profit_norm*0.2)`.
- I 2 flag (`veto_roi_passed`, `kill_switch_triggered`) sono il risultato di R-08 / R-05.
- `qty_target` / `qty_final` chiudono il loop applicativo: F4 → F5 (lotti di 5).

Beneficio del modello + indice composito:
1. Il pipeline `vgp/` di ADR-0018 può ora persistere il proprio output incrementalmente (ingest → normalize → score → veto/kill → qty).
2. L'indice `(session_id, vgp_score DESC)` supporta direttamente le query del **Tetris allocator** (ADR-0018 `tetris/allocator.py`): `SELECT * FROM vgp_results WHERE session_id = ? AND vgp_score IS NOT NULL ORDER BY vgp_score DESC LIMIT N` → index-scan.
3. La doppia FK CASCADE garantisce che cancellare una sessione (o una riga di listino) elimini in cascata i risultati VGP relativi senza orphan rows.

## How

### Mapping colonne Allegato A → SQLAlchemy 2.0

| Colonna | DDL Allegato A | SQLAlchemy 2.0 |
|---|---|---|
| `id` | `BIGSERIAL PRIMARY KEY` | `Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)` |
| `session_id` | `BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE` | `Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)` |
| `listino_item_id` | `BIGINT NOT NULL REFERENCES listino_items(id) ON DELETE CASCADE` | `Mapped[int] = mapped_column(BigInteger, ForeignKey("listino_items.id", ondelete="CASCADE"), nullable=False)` |
| `asin` | `CHAR(10) NOT NULL` | `Mapped[str] = mapped_column(CHAR(10), nullable=False)` |
| `roi_pct` | `NUMERIC(8,4)` | `Mapped[Decimal \| None] = mapped_column(Numeric(8, 4), nullable=True)` |
| `velocity_monthly` | `NUMERIC(12,4)` | `Mapped[Decimal \| None] = mapped_column(Numeric(12, 4), nullable=True)` |
| `cash_profit_eur` | `NUMERIC(12,2)` | `Mapped[Decimal \| None] = mapped_column(Numeric(12, 2), nullable=True)` |
| `roi_norm`/`velocity_norm`/`cash_profit_norm`/`vgp_score` | `NUMERIC(6,4)` | `Mapped[Decimal \| None] = mapped_column(Numeric(6, 4), nullable=True)` |
| `veto_roi_passed`/`kill_switch_triggered` | `BOOLEAN` | `Mapped[bool \| None] = mapped_column(Boolean, nullable=True)` |
| `qty_target`/`qty_final` | `INT` | `Mapped[int \| None] = mapped_column(Integer, nullable=True)` |

Tutte le colonne dei termini sono **nullable** perché vengono popolate **incrementalmente** dal pipeline VGP. La regola "DEFAULT → NOT NULL" (CHG-010) non si applica: nessuna di queste colonne ha un `DEFAULT` nell'Allegato A.

### Indice composito con `DESC`

```python
__table_args__ = (
    Index(
        "idx_vgp_session_score",
        "session_id",
        text("vgp_score DESC"),
    ),
)
```

In SQLAlchemy 2.0 la direzione di un indice si esprime via `text("col DESC")` o tramite `desc(col)` su una Column reference. Ho scelto `text(...)` per due ragioni:
1. È **string-driven** come il resto del `__table_args__` (consistenza).
2. Funziona anche **prima** che la classe sia istanziata (le colonne reference via `desc(SomeClass.col)` richiedono che `SomeClass` esista già — ma siamo dentro la sua definizione).

Test esplicito sul file di migration: `test_migration_index_uses_vgp_score_desc` cerca la stringa `"vgp_score DESC"` nella migration generata. Se qualcuno in futuro tentasse di rimuovere il `DESC` (compromettendo la performance del Tetris allocator), il test blocca.

### Relationship pattern: 2 padri, 1 figlio (many-to-one × 2)

`VgpResult` ha 2 FK → 2 relationship lato VgpResult:

```python
session: Mapped[AnalysisSession] = relationship(back_populates="vgp_results")
listino_item: Mapped[ListinoItem] = relationship(back_populates="vgp_results")
```

E 2 relationship inverse, una su `AnalysisSession` e una su `ListinoItem`:

```python
# In AnalysisSession
vgp_results: Mapped[list[VgpResult]] = relationship(
    back_populates="session",
    passive_deletes=True,
)

# In ListinoItem
vgp_results: Mapped[list[VgpResult]] = relationship(
    back_populates="listino_item",
    passive_deletes=True,
)
```

SQLAlchemy disambigua automaticamente le 2 relationship verso `VgpResult` perché `back_populates` punta a 2 attributi diversi (`session` e `listino_item`). Niente `foreign_keys=` esplicito perché c'è una sola FK per coppia.

### Aderenza letterale all'Allegato A: nessun UNIQUE su `listino_item_id`

L'Allegato A non dichiara `UNIQUE(listino_item_id)`. Concettualmente per una stessa run di sessione ogni `listino_item` produce 0 o 1 risultato VGP, ma l'Allegato A è letterale: many-to-one. La relationship inversa è quindi `Mapped[list[VgpResult]]` (in pratica avrà 0 o 1 elementi). Errata corrige di ADR-0015 ammessa se in futuro si vuole irrigidire a 1:1.

### Validazione end-to-end (offline SQL)

`alembic upgrade 027a145f76a8:c9527f017d5c --sql` produce:

```sql
CREATE TABLE vgp_results (
    id BIGSERIAL NOT NULL,
    session_id BIGINT NOT NULL,
    listino_item_id BIGINT NOT NULL,
    asin CHAR(10) NOT NULL,
    roi_pct NUMERIC(8, 4),
    velocity_monthly NUMERIC(12, 4),
    cash_profit_eur NUMERIC(12, 2),
    roi_norm NUMERIC(6, 4),
    velocity_norm NUMERIC(6, 4),
    cash_profit_norm NUMERIC(6, 4),
    vgp_score NUMERIC(6, 4),
    veto_roi_passed BOOLEAN,
    kill_switch_triggered BOOLEAN,
    qty_target INTEGER,
    qty_final INTEGER,
    PRIMARY KEY (id),
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE,
    FOREIGN KEY(listino_item_id) REFERENCES listino_items (id) ON DELETE CASCADE
);
CREATE INDEX idx_vgp_session_score ON vgp_results (session_id, vgp_score DESC);
```

Coerente con Allegato A in tutti i punti — inclusa la direzione `DESC` sul secondo termine dell'indice.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 24 files already formatted |
| Type | `uv run mypy src/` | ✅ Success: no issues found in 12 source files |
| Test suite | `uv run pytest tests/unit tests/governance -q` | ✅ 79 passed in 0.35s |
| Migration offline | `uv run alembic upgrade 027a145f76a8:c9527f017d5c --sql` | ✅ DDL + 2 FK CASCADE + indice con `vgp_score DESC` coerenti |
| Pre-commit-app E2E | (hook governance al commit reale) | atteso PASS |

Nuovi test (16):
- 11 invarianti strutturali (tablename, metadata, 15 columns, PK, 2 FK CASCADE distinte, asin NOT NULL, precision/scale di 7 colonne Numeric, Boolean nullable, Integer nullable, indice non-unique con prima colonna `session_id`)
- 1 schema-aware sul file di migration per `vgp_score DESC`
- 2 relationship bidirezionali (`session` ↔ `vgp_results`, `listino_item` ↔ `vgp_results`)
- 2 costruzioni runtime (campi minimi, fine-pipeline VGP popolato)

**Rischi residui:**
- Il test `test_index_idx_vgp_session_score_exists` controlla solo che la prima espressione dell'indice sia `session_id`; la verifica del `DESC` sulla seconda è demandata al test schema-aware sulla migration (`test_migration_index_uses_vgp_score_desc`). SQLAlchemy `Index.expressions` restituisce `text()` come oggetto opaco; introspecting la direzione DESC senza parsing dell'AST è fragile. Il test schema-aware è la difesa più robusta.
- `vgp_score = 0` in DB è **ambiguo**: può significare "calcolato e azzerato" (R-05/R-08 falliti) oppure "non ancora calcolato". I flag booleani disambiguano: `kill_switch_triggered=True` o `veto_roi_passed=False` per il primo caso, `vgp_score IS NULL` per il secondo. Disciplina applicativa lato `vgp/score.py` (ADR-0018).
- L'indice **non copre** gli scan per altre dimensioni (es. "tutti i risultati con `kill_switch_triggered=True`"). Indici aggiuntivi possono essere proposti in futuro come errata di ADR-0015 quando emergono pattern di query specifici.
- Non c'è ancora un modello `VgpResult` con metodo "compute" o helper applicativi — è solo schema. La logica di calcolo arriverà con `vgp/normalize.py`/`vgp/score.py` di ADR-0018.

## Refs

- ADR: ADR-0015 (Allegato A — schema), ADR-0018 (consumatore: pipeline VGP popola e legge questi campi), ADR-0014 (mypy + ruff strict), ADR-0013 (struttura `models/`), ADR-0019 (test unit + schema-aware)
- Predecessore: CHG-2026-04-30-012 (`config_overrides` + RLS)
- Successore atteso: prossima tabella Allegato A — `cart_items` (carrello finale del Tetris) o `panchina_items` (R-09 archiviazione). Entrambe FK doppia analoga
- Commit: `<pending>`
