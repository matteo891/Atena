---
id: CHG-2026-04-30-021
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: aee694c
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

**Bootstrap dei ruoli applicativi Zero-Trust** (ADR-0015 sezione "Ruoli"): script idempotente che crea `talos_admin/talos_app/talos_audit` con i privilegi corretti e attiva `FORCE ROW LEVEL SECURITY` sulle 3 tabelle con policy.

Sblocca `with_tenant(session, tenant_id, role='talos_app')` (CHG-020) **in produzione**: prima di questo CHG, `with_tenant` con `role='talos_app'` falliva con `role does not exist`. Dopo questo CHG, l'enforcement RLS è effettivo a livello pool applicativo, non solo nei test.

| File | Tipo | Cosa |
|---|---|---|
| `scripts/db_bootstrap.py` | nuovo | Script Python idempotente. Connessione superuser via env var `TALOS_DB_URL_SUPERUSER` (o `TALOS_DB_URL` come fallback). Password ruoli via `TALOS_ADMIN_PASSWORD`/`TALOS_APP_PASSWORD`/`TALOS_AUDIT_PASSWORD` (errore esplicito se mancanti). DDL via `psycopg.sql.SQL().format()` con `Identifier`/`Literal` (no string-interpolation manuale) |
| `tests/integration/test_db_bootstrap.py` | nuovo | subprocess.run dello script + verifica via SQL: ruoli esistono, attributi corretti (`NO BYPASSRLS` su app/audit, `BYPASSRLS` su admin), GRANT/REVOKE coerenti, FORCE RLS attivo, idempotenza (re-run senza errori), missing env var → exit non-zero |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Entry per `scripts/db_bootstrap.py` → ADR-0015 |

**Scelta di linguaggio:** Python (non bash + psql) perché (a) `psql` non è installato sull'host WSL del Leader; (b) `psycopg` è già dep del progetto; (c) `psycopg.sql.SQL().format()` con `Literal` previene injection sui valori password meglio di `psql -v`; (d) coerente con il resto del progetto Python-first.

Quality gate **atteso** verde: ruff/format/mypy strict puliti su `src/` + `scripts/` (esteso); test totali ~177 PASS (175 + 2 nuovi unit + N integration).

## Why

ADR-0015 dichiara la matrice ruoli ma **non** l'ha mai materializzata. Senza questo CHG:
1. `with_tenant(role='talos_app')` non funziona in prod → l'enforcement RLS è solo "in teoria".
2. Il pool applicativo dovrebbe usare `postgres` superuser → bypassa RLS, vanifica tutto Zero-Trust.
3. `audit_log` non è veramente append-only (REVOKE UPDATE/DELETE non applicato).

CHG-019 ha scoperto runtime che `BYPASSRLS` (default per superuser) supersede anche `FORCE ROW LEVEL SECURITY`. Quindi:
- `talos_admin`: **BYPASSRLS** (deve poter fare DDL/migration senza essere filtrato — ADR-0015 sezione "Ruoli" lo specifica).
- `talos_app`: **NOBYPASSRLS** (subject to RLS — questa è la lezione di CHG-019).
- `talos_audit`: **NOBYPASSRLS** (read-only, nessun bypass necessario).

Inoltre, le 3 tabelle con RLS sono state create dal superuser (Alembic gira come `postgres` finché non passa a `talos_admin`). Per fare in modo che `talos_app` (non-owner) E `talos_admin` siano filtrati uniformemente, la tabella deve avere `FORCE ROW LEVEL SECURITY` attiva — altrimenti il futuro proprietario `talos_admin` bypasserebbe RLS in quanto owner. (`talos_admin` ha comunque `BYPASSRLS` per Alembic, ma `talos_app` deve essere filtrato anche se in futuro la ownership passa a `talos_admin`).

## How

### `scripts/db_bootstrap.py` — design

**Idempotenza:** ogni operazione tollera lo stato finale già presente.
- `CREATE ROLE`: check su `pg_roles` → CREATE solo se assente.
- `ALTER ROLE`: sempre eseguito (riallinea password + attributi).
- `GRANT/REVOKE`: idempotenti by design in Postgres.
- `ALTER TABLE ... FORCE ROW LEVEL SECURITY`: idempotente.

**Connessione:**
- Legge `TALOS_DB_URL_SUPERUSER` (preferito, evita confusione con `TALOS_DB_URL` dell'app); fallback a `TALOS_DB_URL`.
- Strippa il prefisso `+psycopg` se presente (forma SQLAlchemy → forma psycopg).
- `autocommit=False` + commit esplicito a fine bootstrap.

**Password injection-safe:**
- `psycopg.sql.SQL().format(...)` con `sql.Literal(password)`: psycopg fa quoting corretto delle stringhe, anche con apici/backslash.
- `sql.Identifier(role_name)`: whitelist statica (`talos_admin/talos_app/talos_audit`), no input utente.

**Ruoli (matrice):**

| Ruolo | LOGIN | SUPERUSER | BYPASSRLS | CREATEDB | CREATEROLE |
|---|---|---|---|---|---|
| `talos_admin` | ✓ | NOSUPERUSER | **BYPASSRLS** | CREATEDB | CREATEROLE |
| `talos_app` | ✓ | NOSUPERUSER | **NOBYPASSRLS** | NOCREATEDB | NOCREATEROLE |
| `talos_audit` | ✓ | NOSUPERUSER | NOBYPASSRLS | NOCREATEDB | NOCREATEROLE |

**Privilegi:**

```sql
-- talos_app: CRUD su tabelle dati, INSERT-only su audit_log
GRANT CONNECT ON DATABASE <db> TO talos_app, talos_audit;
GRANT USAGE ON SCHEMA public TO talos_app, talos_audit;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    sessions, asin_master, listino_items, vgp_results,
    cart_items, panchina_items, storico_ordini, locked_in,
    config_overrides
TO talos_app;
GRANT INSERT ON audit_log TO talos_app;        -- solo INSERT
REVOKE UPDATE, DELETE ON audit_log FROM talos_app;  -- esplicito (sicurezza)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO talos_app;

-- talos_audit: SELECT-only, niente sequenze
GRANT SELECT ON ALL TABLES IN SCHEMA public TO talos_audit;

-- talos_admin: privilegi gestionali (no superuser → no shutdown DB, no DDL su pg_catalog)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO talos_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO talos_admin;
```

**FORCE RLS:**
```sql
ALTER TABLE config_overrides FORCE ROW LEVEL SECURITY;
ALTER TABLE locked_in        FORCE ROW LEVEL SECURITY;
ALTER TABLE storico_ordini   FORCE ROW LEVEL SECURITY;
```

**CLI:**
```bash
export TALOS_DB_URL_SUPERUSER='postgresql://postgres:test@localhost:55432/postgres'
export TALOS_ADMIN_PASSWORD='****'
export TALOS_APP_PASSWORD='****'
export TALOS_AUDIT_PASSWORD='****'
uv run python scripts/db_bootstrap.py
```

### Test integration — `tests/integration/test_db_bootstrap.py`

Lancia lo script via `subprocess.run` con env var di test (password fittizie + connessione al container `talos-pg-test`). Verifica via psycopg:

1. **Ruoli creati e attributi corretti**:
   - `talos_admin.rolbypassrls = true`, `rolcreatedb = true`, `rolcanlogin = true`, `rolsuper = false`
   - `talos_app.rolbypassrls = false`, `rolcanlogin = true`, `rolsuper = false`
   - `talos_audit.rolbypassrls = false`, `rolcanlogin = true`, `rolsuper = false`

2. **GRANT/REVOKE su `audit_log`**: `talos_app` ha INSERT, NON ha UPDATE/DELETE.

3. **GRANT/REVOKE su `config_overrides`**: `talos_app` ha SELECT/INSERT/UPDATE/DELETE.

4. **`talos_audit`**: SELECT su `audit_log`, niente INSERT.

5. **`talos_admin`**: SELECT su `audit_log`.

6. **FORCE RLS attivo** su `config_overrides`, `locked_in`, `storico_ordini` (`pg_class.relforcerowsecurity = true`).

7. **Idempotenza**: rieseguito subito dopo, nessun errore.

8. **Login funzionante**: `psycopg.connect(...)` con credenziali `talos_app/<pwd>` riesce.

9. **Missing env var fail**: se `TALOS_APP_PASSWORD` non è settato, lo script esce con exit code != 0 e messaggio chiaro.

**Cleanup post-test:** i ruoli sono globali al cluster; la fixture droppa i 3 ruoli alla fine (DROP OWNED + DROP ROLE) per non lasciare side-effect tra run.

### Out-of-scope

- **Distribuzione delle password** (Vault/secrets-manager): scope deployment.
- **Connection pool con set_session_authorization** (ADR-0015 sezione 67): da fare quando arriva `ui/`.
- **Backup script** (ADR-0015 punto 5 dei test di conformità): scope futuro.
- **Migrazione ownership tabelle a `talos_admin`**: lasciate sotto `postgres` per semplicità; FORCE RLS rende l'ownership irrilevante per il filtro RLS. In prod si valuterà una errata corrige.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/ scripts/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/ scripts/` | atteso ✅ |
| Type | `uv run mypy src/ scripts/db_bootstrap.py` | atteso ✅ |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ 163 PASS (invariato) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -v` | atteso ✅ 12 + N PASS |

**Rischi residui:**
- Lo script richiede privilegi superuser (CREATE ROLE). In prod, l'operatore deve avere accesso temporaneo come superuser.
- I ruoli creati persistono nel cluster Postgres. Cleanup post-test esplicito; in prod sono permanenti by design.
- `BYPASSRLS` su `talos_admin` è una scelta di compromesso: Alembic richiede di poter fare DDL e seed senza essere filtrato. Mitigazione: `talos_admin` non è il pool applicativo, è uno strumento DBA.
- Password in env var: chi può leggere l'environment del processo le vede. Mitigazione standard (Vault/secrets-manager) è scope deployment.
- `FORCE ROW LEVEL SECURITY` può rompere uno script di seeding scritto come `talos_admin`: mitigazione tramite `BYPASSRLS` sull'admin.

## Refs

- ADR: ADR-0015 (Allegato A — sezione "Ruoli" + matrice GRANT/REVOKE), ADR-0014 (mypy/ruff strict), ADR-0013 (struttura `scripts/`), ADR-0019 (test integration)
- Predecessore: CHG-2026-04-30-020 (DB lifecycle — `with_tenant(role=...)` ora è effettivamente utile in prod)
- Lezione applicata: CHG-2026-04-30-019 (NO BYPASSRLS su `talos_app`)
- Successore atteso: CHG-022 `config/` pydantic-settings (centralizza env var); primo vertical slice formula
- Commit: `aee694c`
