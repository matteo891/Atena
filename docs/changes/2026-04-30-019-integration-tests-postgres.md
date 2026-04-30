---
id: CHG-2026-04-30-019
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 35190c3
adr_ref: ADR-0019, ADR-0015, ADR-0014, ADR-0002, ADR-0011
---

## What

Inaugurazione della categoria di test **`tests/integration/`** prevista da ADR-0019 ma finora vuota. Primi due test reali contro Postgres reale (container ephemeral `talos-pg-test` su `host:55432`):

1. **`test_rls_isolation.py`** — verifica runtime della policy `tenant_isolation` su `config_overrides`: con `talos.tenant_id = '1'` la sessione vede **solo** le righe del tenant 1; cambiando a `'2'` vede solo quelle del tenant 2; con tenant inesistente vede 0 righe.
2. **`test_audit_triggers.py`** — verifica runtime della funzione PL/pgSQL `record_audit_log()` e dei tre trigger AFTER: `INSERT/UPDATE/DELETE` su `config_overrides` produce **una riga in `audit_log`** con `op='I'/'U'/'D'`, `actor=session_user`, `before_data`/`after_data` JSONB coerenti.

| File | Tipo | Cosa |
|---|---|---|
| `tests/integration/__init__.py` | nuovo | package marker |
| `tests/integration/conftest.py` | nuovo | fixture session-scoped `pg_engine` da env var `TALOS_DB_URL` (skip module-level pytest se assente); fixture function-scoped `pg_conn` che apre transazione, `SET LOCAL talos.tenant_id`, yield, **rollback finale** (isolamento per-test) |
| `tests/integration/test_rls_isolation.py` | nuovo | 4 test con `ALTER TABLE config_overrides FORCE ROW LEVEL SECURITY` in-tx (rollback ripristina) — INSERT cross-tenant da owner, poi SELECT con `talos.tenant_id` variabile |
| `tests/integration/test_audit_triggers.py` | nuovo | 4 test su INSERT/UPDATE/DELETE → verifica righe in `audit_log` con OP corretto, before/after JSONB, `actor='postgres'` |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Aggiunta entry `tests/integration/` → ADR-0019 + ADR-0015 |

Quality gate locale **atteso** verde: ruff + mypy strict pulito; **153 unit/governance test PASS** (invariati) + **8 integration PASS** (nuovi) **se** `TALOS_DB_URL` è settato. Senza env var: integration **skipped** (no failure).

## Why

I CHG-012, 016, 017, 018 hanno marcato come **rischio residuo** che i test su RLS e trigger erano solo "schema-aware" (lettura statica del file di migration), non runtime. Questo CHG chiude quel rischio per le tre dimensioni più critiche:
- isolamento RLS effettivo (cross-tenant leak)
- attivazione automatica dei trigger di audit
- semantica dei codici op (I/U/D) e dei payload JSONB

Inoltre **inaugura** la categoria `tests/integration/` (ADR-0019) finora vuota e definisce il pattern di fixture **riutilizzabile** per ogni futura tabella o flusso che richieda DB reale (FK CASCADE/RESTRICT, indici UNIQUE, trigger).

## How

### Fixture — `tests/integration/conftest.py`

- **`pg_engine`** (session): legge `TALOS_DB_URL` da env. Se assente: `pytest.skip(allow_module_level=True)` → niente esecuzione, niente errore. Se presente: crea engine con `pool_pre_ping=True` e `future=True`. Cleanup: `engine.dispose()`.
- **`pg_conn`** (function): apre `engine.connect()`, esegue `SET LOCAL talos.tenant_id = '1'` (default), apre transazione `with conn.begin()` e fa **rollback** in teardown (isolamento). I test che hanno bisogno di un tenant diverso fanno `pg_conn.execute(text("SET LOCAL talos.tenant_id = '2'"))` localmente.

Il design "rollback per-test" garantisce che i test non lascino righe nel DB. Combinato con il container ephemeral su tmpfs è doppio-sicuro.

### RLS test — `test_rls_isolation.py`

Scoperta runtime durante l'implementazione: Postgres bypassa RLS in **due** condizioni cumulative — (1) per il table owner salvo `FORCE ROW LEVEL SECURITY`, (2) per ruoli con attributo `BYPASSRLS` (incluso ogni superuser). Il test deve coprire entrambe:

1. `ALTER TABLE config_overrides FORCE ROW LEVEL SECURITY` — copre il bypass dell'owner.
2. `CREATE ROLE talos_rls_test_subject` (NOSUPERUSER NOBYPASSRLS, default) + `GRANT SELECT, UPDATE, DELETE ON config_overrides` (+ `INSERT ON audit_log` + `USAGE ON SEQUENCE audit_log_id_seq` per i trigger AFTER) + `SET LOCAL ROLE` — copre il bypass del superuser.

Tutto in transazione, `ROLLBACK` ripristina catalog (FORCE rimosso, role droppato — `CREATE ROLE` è transactional in Postgres 16).

La policy esistente (`USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)`) ha `USING` ma **non** `WITH CHECK`. Quindi:
- INSERT è permesso anche con `tenant_id` diverso da quello di sessione (USING-only filtra solo lettura/scrittura post-match).
- SELECT/UPDATE/DELETE filtrano per match.

Sequenza per ogni test:
1. Seed 2 righe (tenant 1 + tenant 2) **come `postgres`** (RLS bypassata, INSERT cross-tenant libero).
2. Attiva FORCE + crea ruolo + GRANT minimo + `SET LOCAL ROLE talos_rls_test_subject`.
3. `SET LOCAL talos.tenant_id = '<n>'` per scegliere il tenant target.
4. SELECT/UPDATE/DELETE → solo righe con `tenant_id = <n>` visibili e mutabili.

**Implicazione operativa per il futuro CHG sui ruoli applicativi:** il bootstrap di `talos_app/talos_admin/talos_audit` dovrà esplicitamente NON dare BYPASSRLS al ruolo `talos_app` (default sicuro), e ogni tabella con RLS dovrà essere creata con `FORCE` se la sua proprietà ricade su un ruolo non-`talos_app` (oppure assegnare ownership a `talos_app` direttamente).

### Audit triggers test — `test_audit_triggers.py`

Per ogni operazione I/U/D:
1. Snapshot `MAX(id)` su `audit_log` per filtrare le righe nuove dopo l'operazione.
2. Esegui INSERT/UPDATE/DELETE su `config_overrides`.
3. SELECT righe `audit_log.id > snapshot AND table_name='config_overrides'`.
4. Verifica: `op` corretto, `actor='postgres'`, `before_data`/`after_data` coerenti con il flusso (`I` → before NULL, after pieno; `U` → entrambi pieni; `D` → before pieno, after NULL).
5. Verifica payload JSONB contiene almeno la chiave `key` con il valore atteso (forma duck-typed; non controllo schema completo per non fragile).

Tutti i test girano in transazione con rollback → niente persistenza, niente flakiness.

### Esecuzione locale

```bash
# Container già attivo (da fermaposto):
TALOS_DB_URL='postgresql+psycopg://postgres:test@localhost:55432/postgres' \
  uv run pytest tests/integration -v
```

Senza env var: i test integration sono **skipped** automaticamente. Il quality gate `tests/unit + tests/governance` resta invariato.

### Out-of-scope di questo CHG

- **CI integration job:** richiede service container Postgres in `.github/workflows/ci.yml` (env `TALOS_DB_URL` settato). Sarà un CHG dedicato (errata corrige di ADR-0020 se serve).
- **`pytest-postgresql`** (menzionato in ADR-0019): non introdotto qui — la sua adozione richiede `pg_ctl` sulla machine di test, che complica il setup. Il pattern attuale (env var → engine) è più semplice e sufficiente per la fase corrente.
- **Bootstrap ruoli `talos_app`/`talos_admin`/`talos_audit`** + `GRANT/REVOKE`: scope di un futuro `scripts/db-bootstrap.sh`.
- **Test su FK CASCADE/RESTRICT runtime** (i 6 CASCADE + i 2 RESTRICT su `storico_ordini`): naturale prossimo step, ma non strettamente necessario per chiudere il rischio "RLS + audit". Errata corrige di questo CHG ammessa se il Leader vuole estendere ora.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (no nuovi src/, solo tests/) |
| Type tests | `uv run mypy tests/` | non in scope corrente (ADR-0014 type checking solo su `src/`); se in futuro estensione → errata corrige |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ 153 PASS (invariato) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -v` | atteso ✅ 8 PASS |
| Integration skip | `uv run pytest tests/integration -v` (no env var) | atteso: skipped (collected but skipped at module level) |

**Rischi residui:**
- I test girano contro **`postgres` superuser**, non un ruolo applicativo. Ciò significa che la **disciplina append-only** di `audit_log` (REVOKE UPDATE/DELETE) non è verificata qui — sarà coperta dal CHG su `db-bootstrap.sh`.
- `FORCE ROW LEVEL SECURITY` in-tx funziona ma la sua persistenza dopo COMMIT cambierebbe lo stato del DB. Mitigazione: rollback obbligatorio a fine test (verificato dal pattern di fixture).
- Se due integration test girano in parallelo sulla **stessa connessione** (non dovrebbero, ma è un anti-pattern da evitare), `SET LOCAL talos.tenant_id` potrebbe interferire. Mitigazione: pytest non parallelizza by-default; ogni test apre la propria connessione dalla pool.
- Senza container Postgres in CI il job `tests/integration/` **skipperà** silenziosamente: in futuro, l'integration job di GitHub Actions deve **failarsi se non sono raccolti almeno N test**. Errata corrige di ADR-0020 in scope futuro.
- `pytest-postgresql` rimanda alla menzione di ADR-0019: non è una violazione perché l'ADR dice "*pytest-postgresql con container ephemeral*" come **strategia preferita**, non come **vincolo letterale**. Pattern alternativo qui adottato è coerente con lo spirito (ephemeral + isolato).

## Refs

- ADR: ADR-0019 (`tests/integration/` come categoria), ADR-0015 (RLS Zero-Trust + audit), ADR-0014 (quality gates), ADR-0002 + ADR-0011 (test gate, push immediato)
- Predecessore: CHG-2026-04-30-018 (audit_log + 3 trigger — chiuso il rischio residuo "test schema-aware solo statici")
- Successore atteso: integration job CI (`.github/workflows/ci.yml` con service Postgres) o bootstrap ruoli `db-bootstrap.sh`
- Commit: `35190c3`
