---
id: CHG-2026-04-30-047
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

Chiude il debito **idempotency** introducendo un UNIQUE INDEX
`(tenant_id, listino_hash)` su `sessions` + `find_session_by_hash` per
lookup deterministico pre-save.

| File | Tipo | Cosa |
|---|---|---|
| `migrations/versions/e965e1b81041_add_unique_constraint_sessions_tenant_.py` | nuovo | Alembic revision: `op.create_index("ux_sessions_tenant_hash", "sessions", ["tenant_id", "listino_hash"], unique=True)` + downgrade simmetrico |
| `src/talos/persistence/models/analysis_session.py` | modificato | +`__table_args__ = (Index("ux_sessions_tenant_hash", ..., unique=True),)` per allineamento ORM↔DB |
| `src/talos/persistence/session_repository.py` | modificato | +`find_session_by_hash(db_session, *, listino_hash, tenant_id=1) -> SessionSummary \| None` con check lunghezza hash (64 hex) e filtro tenant |
| `src/talos/persistence/__init__.py` | modificato | +re-export `find_session_by_hash` |
| `tests/integration/test_session_repository.py` | modificato | `test_save_listino_hash_deterministic` adattato al nuovo contratto: stesso listino + tenant_id diversi (no conflict); helper `_listino_hash` testato in isolamento |
| `tests/integration/test_find_session_by_hash.py` | nuovo | 6 test (None su hash sconosciuto, ValueError su lunghezza errata, summary post-save, UNIQUE blocca duplicate, tenant diverso ammesso, filtro tenant_id) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | +entry migration `e965e1b81041` + entry `find_session_by_hash` |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **426 PASS**
(372 unit/governance/golden + 54 integration).

## Why

Senza `UNIQUE(tenant_id, listino_hash)`, ri-eseguire la stessa sessione
crea righe duplicate in `sessions` (CHG-042 documentato come "no
idempotency"). Il CFO che esegue 3 volte stesso listino vedeva 3 entry
nello storico (CHG-044), confondendo l'audit. La UNIQUE costringe il
caller a fare una scelta esplicita: re-execute o skip.

`find_session_by_hash` e' la primitiva di **lookup esplicito**: la UI
puo' chiamarla pre-save per controllare se il listino e' gia' stato
eseguito, e — se si — mostrare un warning prima di tentare un save che
fallirebbe per IntegrityError.

### Decisioni di design

1. **UNIQUE INDEX (non constraint)**: allineamento con altri indici
   schema (CHG-009 `idx_asin_brand_model`, CHG-013 `idx_vgp_session_score`,
   ecc.). Drop/rebuild snello in errata corrige future. Semantica
   identica per la query `INSERT ... ON CONFLICT`.
2. **`(tenant_id, listino_hash)` (composto, non solo `listino_hash`)**:
   tenant diversi possono avere lo stesso listino senza conflitto.
   Future-proof per multi-tenancy. Test `test_unique_index_allows_different_tenants`.
3. **Validazione `len(listino_hash) == 64`**: sha256 hex e' sempre 64
   char. Hash piu' corti/lunghi sono bug del caller; raise R-01.
4. **`find_session_by_hash` ritorna `SessionSummary` (no full LoadedSession)**:
   il caller tipico (UI pre-save) vuole sapere SE esiste e mostrare
   info riassuntive ("ultima esecuzione 2 ore fa, 5 cart, 12 panchina").
   Se vuole il dettaglio, chiama `load_session_by_id` con l'`id` ritornato.
5. **Niente `upsert_session` automatico in questo CHG**: l'`ON CONFLICT
   DO UPDATE` semantico richiede di decidere cosa fare con i child rows
   (delete-all + recreate vs lascia il vecchio). Scelta del Leader scope
   CHG futuro.
6. **`save_session_result` invariato (default raise IntegrityError su
   duplicate)**: l'aggiunta di un kwarg `replace_existing=False` e'
   scope CHG futuro. Il pattern attuale e' "explicit-fail": il caller
   chiama `find_session_by_hash` prima del save se vuole evitare il
   raise.
7. **Test esistente `test_save_listino_hash_deterministic` adattato**:
   stesso input → stesso hash testato via helper `_listino_hash`
   isolato + via 2 save con `tenant_id` diversi (entrambi ammessi).
   Listino diverso → hash diverso testato come prima.

### Out-of-scope

- **`upsert_session`** con `ON CONFLICT (tenant_id, listino_hash) DO
  UPDATE`: scope CHG futuro. Decisione Leader: che semantica deve avere?
  - (a) Delete child rows + recreate (idempotent rerun)
  - (b) Update solo `ended_at`/timestamps (lascia child del primo run)
  - (c) Solo error (status quo)
- **UI: warning pre-save "questa sessione esiste gia'"**: scope CHG
  successivo che integra `find_session_by_hash` nella dashboard
  prima del bottone "Salva".
- **Migrazione retroattiva di sessioni duplicate esistenti**: il
  container ephemeral non ne ha, ma in produzione (post-MVP) servira'
  uno script di cleanup.

## How

### Migration `e965e1b81041` (highlight)

```python
def upgrade() -> None:
    op.create_index(
        "ux_sessions_tenant_hash",
        "sessions",
        ["tenant_id", "listino_hash"],
        unique=True,
    )

def downgrade() -> None:
    op.drop_index("ux_sessions_tenant_hash", table_name="sessions")
```

### `find_session_by_hash` (highlight)

```python
def find_session_by_hash(
    db_session: Session, *, listino_hash: str, tenant_id: int = 1,
) -> SessionSummary | None:
    if len(listino_hash) != 64:
        raise ValueError(...)
    with with_tenant(db_session, tenant_id):
        stmt = select(AnalysisSession).where(
            AnalysisSession.tenant_id == tenant_id,
            AnalysisSession.listino_hash == listino_hash,
        )
        asession = db_session.scalar(stmt)
        if asession is None:
            return None
        # count child rows + return SessionSummary
        ...
```

### Test plan

- 6 nuovi (`test_find_session_by_hash.py`):
  1. `test_find_returns_none_for_unknown_hash`
  2. `test_find_invalid_hash_length_raises`
  3. `test_find_returns_summary_after_save`
  4. `test_unique_index_blocks_duplicate_save` — IntegrityError verificato
  5. `test_unique_index_allows_different_tenants`
  6. `test_find_filters_by_tenant_id`
- 1 adattato (`test_session_repository.py`):
  - `test_save_listino_hash_deterministic` ora usa tenant_id diversi
    per i 2 save + testa `_listino_hash` helper isolato.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | ✅ All checks passed |
| Format | `uv run ruff format --check src/ tests/` | ✅ 86 files already formatted |
| Type | `uv run mypy src/` | ✅ 39 source files, 0 issues |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | ✅ **372 PASS** |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | ✅ **54 PASS** (48 + 6) |
| Migration | `alembic upgrade head` | ✅ applied `e965e1b81041` |

**Rischi residui:**
- **Sessioni duplicate pre-CHG** in DB di produzione: la migration
  fallirebbe se esistessero gia' duplicate. Container ephemeral non li
  ha; produzione richiede script di cleanup pre-migration. Documentato.
- **`save_session_result` raise IntegrityError**: il caller (UI) cattura
  e mostra `st.error`. Pattern coerente con `try_persist_session` di
  CHG-043 (gia' wrap exception → tuple).
- **`find_session_by_hash` non usato dalla UI ancora**: scope CHG
  successivo. Per ora helper testato e disponibile.

## Impact

**Idempotency aperta**: il pattern "esegui due volte stesso listino →
duplicate silenziose" e' ora **bloccato** dal vincolo. Future PR che
costruiranno `upsert_session` o "ricarica sessione precedente" hanno
una primitiva pulita su cui basarsi (`find_session_by_hash`).

`gitnexus_detect_changes` rilevera' al prossimo `gitnexus analyze` la
nuova migration + `find_session_by_hash`.

## Refs

- ADR: ADR-0015 (persistenza + Allegato A schema), ADR-0014
  (mypy/ruff strict), ADR-0019 (test integration pattern)
- Predecessori: CHG-2026-04-30-008 (sessions table iniziale),
  CHG-2026-04-30-042 (save_session_result), CHG-2026-04-30-044
  (list_recent_sessions)
- Successore atteso: `upsert_session` con `ON CONFLICT DO UPDATE` (decisione
  Leader semantica); UI integration `find_session_by_hash` pre-save +
  warning duplicate
- Commit: `[pending]`
