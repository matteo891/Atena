# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-04-30 — commit `89fb471` (feat(persistence): UNIQUE(tenant_id, listino_hash) + find_session_by_hash). Tag: 3 milestone + 8 checkpoint. Catena CHG odierna: 001→...→**047**. **Tabelle Allegato A coperte: 10/10** ✓ + **426 test PASS** (372 unit/gov/golden + 54 integration). **Indice GitNexus** (1907 / 2203 — stale ~38 commit; reindex consigliato).
> **Sessione corrente:** TALOS — **🔒 IDEMPOTENCY APERTA**: migration Alembic `e965e1b81041` aggiunge UNIQUE INDEX `ux_sessions_tenant_hash` su `sessions(tenant_id, listino_hash)`. `find_session_by_hash(db, *, listino_hash, tenant_id=1) -> SessionSummary | None` per lookup pre-save deterministico. Stesso (tenant, hash) → IntegrityError (no più duplicate silenziose). Tenant diversi su stesso listino ammessi.

---

## Stato in Una Riga

Governance hardened (ADR 0001–0012) + vision TALOS `Frozen` dal 2026-04-29 + **stack hardened (ADR 0013–0021) dal 2026-04-30**. Tutte le aree precedentemente in gap sono ora coperte. Repo in stato di **purezza infrastrutturale**: zero codice applicativo, ADR cardine pronti per il bootstrap del primo modulo `src/talos/`.

**Repository:** https://github.com/matteo891/Atena (fork operativo del Leader; il repo originale `santacrocefrancesco00-ux/Atena` è del padre)
**Milestone tag corrente:** `milestone/stack-frozen-v0.9.0` (atteso post-CHG-2026-04-30-002) — restore point pre-codice
**Milestone precedente:** `milestone/vision-protocol-v0.6.0` su commit `55ea55f` (pre-esposizione)
**Codename progetto:** TALOS — *Scaler 500k*

---

## Appena Completato

| Cosa | ADR | CHG | Commit |
|---|---|---|---|
| ADR 0001–0008 promulgati (governance fondativa) | 0001–0008 | [CHG-001](changes/2026-04-29-001-bootstrap-adr-fondativi.md) | `5959ebd`, `a796ce0` |
| Hardening governance v0.5.0 — ADR-0009/0010/0011 | 0009–0011 | [CHG-002](changes/2026-04-29-002-hardening-governance.md) | `416ab87` |
| Vision capture protocol — ADR-0012 + PROJECT-RAW.md template Draft | 0012 | [CHG-003](changes/2026-04-29-003-vision-capture-adr.md) | `7b7ef17` |
| Restore point `milestone/vision-protocol-v0.6.0` | 0003 | — | tag su `55ea55f` |
| **TALOS — Esposizione Round 1: trascrizione verbatim + 24 lacune** | 0012 | [CHG-004](changes/2026-04-29-004-talos-exposition-iterating.md) | `44d53e7` |
| **TALOS — Round 2 Q&A: 6 critiche chiuse, L11b condizionale aperta** | 0012 | [CHG-005](changes/2026-04-29-005-talos-iterating-round-2.md) | `b05ecbe` |
| **TALOS — Round 3: formula VGP, Keepa out-of-scope, L04b critica aperta, direttiva concisione → memory** | 0012 | [CHG-006](changes/2026-04-29-006-talos-iterating-round-3.md) | `7dee02b` |
| **TALOS — Round 4: chiusa L04b (normalizzazione min-max [0,1] dei tre termini VGP). 0 critiche residue.** | 0012 | [CHG-007](changes/2026-04-29-007-talos-iterating-round-4.md) | `0cd9f1f` |
| Backfill CHG-007 + fix repo URL al fork operativo `matteo891/Atena` | — | (parte di CHG-007) | `97f404f`, `2abe28e` |
| **TALOS — Round 5: sweep finale, chiuse tutte le 17 lacune residue. Vision pronta per Frozen.** | 0012 | [CHG-008](changes/2026-04-29-008-talos-iterating-round-5-sweep-finale.md) | `08beebf` |
| Backfill CHG-008 | — | (parte di CHG-008) | `8f7333d` |
| **TALOS — Round 6: `Frozen` dichiarato esplicitamente dal Leader. Vision congelata.** | 0012 | [CHG-009](changes/2026-04-29-009-talos-frozen-declaration.md) | `5f8d664` |
| Backfill CHG-009 | — | (parte di CHG-009) | `cb14561` |
| **Promulgazione cluster ADR di stack 0013–0021 (validazione bulk Opzione A)** | 0013–0021 | [CHG-2026-04-30-001](changes/2026-04-30-001-promulgazione-adr-stack-0013-0021.md) | `8cd06f7` |
| Backfill CHG-001 | — | (parte di CHG-001) | `fb8ff51` |
| **Integrazione tooling GitNexus condiviso (CLAUDE.md + AGENTS.md + skills + .gitignore)** | 0007 | [CHG-2026-04-30-002](changes/2026-04-30-002-integrazione-tooling-gitnexus.md) | `71c4c3b` |
| **Milestone tag `milestone/stack-frozen-v0.9.0`** | 0003 | (parte di CHG-002) | tag su `71c4c3b` |
| **Errata Corrige ADR-0006 + side-effect su ADR-0014/0020 (hooks v2: pre-commit-app wiring + bot reindex bypass)** | 0006, 0014, 0020 | [CHG-2026-04-30-003](changes/2026-04-30-003-errata-adr-0006-hooks-extension.md) | `b92fe87` |
| **Bootstrap codice minimale (pyproject.toml + src/talos scaffold + tests + pre-commit-app + setup-dev.sh + README)** | 0013, 0014, 0019, 0021, 0006 | [CHG-2026-04-30-004](changes/2026-04-30-004-bootstrap-codice-minimale.md) | `b7f78d4` |
| **CI base (`.github/workflows/ci.yml` — 3 job server-side: quality-gates + structure-check + governance-checks) + Errata Corrige ADR-0020 (rollout staging dei 4 workflow)** | 0020, 0006, 0009 | [CHG-2026-04-30-005](changes/2026-04-30-005-ci-base-github-actions.md) | `4684085` |
| **Primo modulo applicativo: `src/talos/observability/` con `configure_logging` reale + catalogo eventi canonici (10 voci) + 9 test unit/governance. structlog prima dep runtime.** | 0021, 0019, 0014 | [CHG-2026-04-30-006](changes/2026-04-30-006-observability-configure-logging.md) | `9298e70` |
| **Persistence skeleton: SQLAlchemy 2.0 + Alembic + psycopg deps; plugin `sqlalchemy[mypy]` attivo; `Base = DeclarativeBase` + struttura `migrations/`. No modelli, no Postgres ancora.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-007](changes/2026-04-30-007-persistence-skeleton.md) | `088b410` |
| **Tag `checkpoint/2026-04-30-01`** — 5 CHG significativi post stack-frozen | 0003 | (nessun CHG) | tag su `0f8f40a` |
| **Primo modello concreto: `AnalysisSession` (tabella `sessions`) — 7 colonne Allegato A + initial migration Alembic `9d9ebe778e40`. SQL offline coerente.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-008](changes/2026-04-30-008-sessions-model-initial-migration.md) | `4dcca3c` |
| **Seconda tabella: `AsinMaster` (anagrafica ASIN, 11 colonne Allegato A) + indice `idx_asin_brand_model` + Alembic revision `d4a7e3cefbb1`. 11 test unit. SQL offline coerente.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-009](changes/2026-04-30-009-asin-master-model.md) | `16a4f77` |
| **Errata Corrige ADR-0015: regola "DEFAULT in Allegato A → NOT NULL (nullable=False) nell'ORM"** ratificata dal Leader | 0015, 0009 | [CHG-2026-04-30-010](changes/2026-04-30-010-errata-adr-0015-default-implies-not-null.md) | `3a4414f` |
| **Terza tabella: `ListinoItem` (primo con FK → sessions ON DELETE CASCADE + relationship bidirezionale + indice + revision `d6ab9ffde2a2`). 12 test unit.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-011](changes/2026-04-30-011-listino-items-model-with-fk.md) | `02a8787` |
| **Quarta tabella: `ConfigOverride` (primo con RLS Zero-Trust + indice UNIQUE composito 4 col + revision `027a145f76a8`). 15 test unit.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-012](changes/2026-04-30-012-config-overrides-model-with-rls.md) | `2498326` |
| **Quinta tabella: `VgpResult` (nucleo decisore, 15 col, doppia FK CASCADE, indice `(session_id, vgp_score DESC)` + revision `c9527f017d5c`). 16 test unit.** | 0015, 0014, 0013, 0019, 0018 | [CHG-2026-04-30-013](changes/2026-04-30-013-vgp-results-model.md) | `047bb46` |
| **Tag `checkpoint/2026-04-30-02`** — 6 CHG significativi (sessions/asin_master/errata/listino_items/config_overrides/vgp_results) | 0003 | (nessun CHG) | tag su `37fdc7e` |
| **Sesta tabella: `CartItem` (carrello Tetris, 6 col, doppia FK CASCADE, locked_in R-04 + revision `fa6408788e73`). 13 test unit.** | 0015, 0014, 0013, 0019, 0018 | [CHG-2026-04-30-014](changes/2026-04-30-014-cart-items-model.md) | `9a587cc` |
| **Settima tabella: `PanchinaItem` (R-09 archivio, 4 col, doppia FK CASCADE + revision `618105641c27`). 10 test unit.** | 0015, 0014, 0013, 0019, 0018 | [CHG-2026-04-30-015](changes/2026-04-30-015-panchina-items-model.md) | `69cb614` |
| **Ottava tabella: `StoricoOrdine` (R-03 registro permanente, 8 col, FK SENZA CASCADE + RLS Zero-Trust + revision `a074ee67895c`). 17 test unit.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-016](changes/2026-04-30-016-storico-ordini-model-with-rls.md) | `0270e20` |
| **Nona tabella: `LockedInItem` (R-04 Manual Override, 6 col, standalone, RLS + revision `e7a92c0260fa`). 15 test unit.** | 0015, 0014, 0013, 0019, 0018 | [CHG-2026-04-30-017](changes/2026-04-30-017-locked-in-model-with-rls.md) | `099dd60` |
| **🎯 Decima e ultima tabella: `AuditLog` (registro append-only, 8 col incluso 2 JSONB, funzione PL/pgSQL `record_audit_log()` + 3 trigger AFTER su tabelle critiche + revision `6e03f2a4f5a3`). 19 test unit. SCHEMA ALLEGATO A COMPLETO 10/10** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-018](changes/2026-04-30-018-audit-log-model-with-triggers.md) | `18c32b6` |
| **`alembic upgrade head` reale verde su Postgres 16-alpine** (10 revision in catena, RLS attiva su 3 tabelle, funzione + 9 trigger creati, 6 FK CASCADE + 2 FK NO ACTION verbatim Allegato A) | 0015 | (no CHG — validazione runtime) | (container ephemeral `talos-pg-test`) |
| **`tests/integration/` inaugurata: 4 test RLS (`tenant_isolation` + FORCE + ruolo non-superuser) + 4 test audit trigger I/U/D con before/after JSONB. Env-var `TALOS_DB_URL` con skip module-level se assente. Pattern fixture transazionale + rollback.** | 0019, 0015, 0011 | [CHG-2026-04-30-019](changes/2026-04-30-019-integration-tests-postgres.md) | `35190c3` |
| **DB lifecycle: `engine.py` (factory + URL precedence + pool conditional) + `session.py` (`make_session_factory` + `session_scope` + `with_tenant` Zero-Trust). 11 test unit + 4 integration (commit/rollback + `current_setting` + RLS effettivo via role switch).** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-020](changes/2026-04-30-020-persistence-engine-session.md) | `ddb3229` |
| **DB bootstrap roles: `scripts/db_bootstrap.py` (idempotente, psycopg.sql injection-safe). Materializza la matrice ADR-0015: `talos_admin` (BYPASSRLS, DBA), `talos_app` (NOBYPASSRLS, pool app), `talos_audit` (read-only). FORCE RLS su 3 tabelle. 9 integration test (attributi, GRANT/REVOKE, idempotenza, login).** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-021](changes/2026-04-30-021-db-bootstrap-roles.md) | `aee694c` |
| **Refactor `persistence/engine.py`: legge `db_url` via `TalosSettings.db_url` (CHG-029 → primo consumatore reale del config layer). Quality gate verde 221 PASS invariati.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-030](changes/2026-04-30-030-engine-via-talos-settings.md) | `464e4f3` |
| **Tag `checkpoint/2026-04-30-05`** — 5 CHG significativi (cash_profit/roi + veto R-08 + e2e + config layer + engine via settings) | 0003 | (nessun CHG) | tag su `cf11e6c` |
| **Refactor `scripts/db_bootstrap.py` via `TalosSettings` (+4 campi: db_url_superuser + 3 password). Centralizzazione completa env var DB. 226 unit + 9 integration PASS su Postgres reale.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-031](changes/2026-04-30-031-db-bootstrap-via-talos-settings.md) | `877b8ea` |
| **F3 Compounding T+1 — `formulas/compounding.py`. Verbatim `Budget_T+1 = Budget_T + Somma(Cash_Profit)`. Chiude catena scalare F1→F2→F3 + ROI + Veto R-08. 9 test unit, 235 PASS.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-032](changes/2026-04-30-032-formulas-compounding-t1.md) | `eb04afb` |
| **Sentinella e2e estesa con rollup F3 (`test_value_chain.py` +2 test): rollup batch escluso vetati + chained T→T+1→T+2 streaming. Snapshot 1394.9957 EUR. 237 PASS.** | 0019, 0018 | [CHG-2026-04-30-033](changes/2026-04-30-033-chain-e2e-with-compounding.md) | `cc4070e` |
| **🎯 Milestone tag `milestone/first-formula-v1.0.0`** — catena scalare formule chiusa e blindata da sentinella | 0003 | (nessun CHG) | tag su `cc4070e` |
| **🚀 Frontiera applicativa attraversata: `formulas/fee_fba.py` con `fee_fba_manual` verbatim L11b. Funzione pura + R-01 NO SILENT DROPS via 2 ValueError. 8 test unit (snapshot tolerance + boundary scorporato==100 + monotonia + edge case).** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-022](changes/2026-04-30-022-formulas-fee-fba.md) | `750b70d` |
| **Errata corrige ADR-0010: Step 1 esteso con verifica reciproca STATUS↔git (`git tag -l`, `git branch`, `git log <hash>`) per claim su tag/branch/hash. Trigger reale: STATUS marcava CHECKPOINT-03 come "in attesa autorizzazione" mentre il tag esisteva già da 6 ore.** | 0010, 0009, 0008, 0003 | [CHG-2026-04-30-023](changes/2026-04-30-023-errata-adr-0010-tag-verification.md) | `d962445` |
| **Chiusura ISS-001 + errata ADR-0007/0010: Step 4 esige verifica empirica via `mcp__gitnexus__list_repos` prima di accettare claim documentali di indisponibilità. Rebuild GitNexus riuscito in 3.3s su Node v22 (root cause v24-specific). Indice fresh: 1646 nodes / 1929 edges / 4 flows.** | 0007, 0010, 0009, 0008 | [CHG-2026-04-30-024](changes/2026-04-30-024-chiusura-iss-001-gitnexus-rebuild.md) | `cea9494` |
| **F1 `formulas/cash_inflow.py`: `cash_inflow_eur(buy_box, fee_fba, referral_fee) = buy_box − fee_fba − buy_box·referral_fee` verbatim. Primo consumatore architetturale di `fee_fba_manual` (CHG-022 non più isolato). 11 test (3 snapshot + zero/negative-allowed + monotonia + 5 raises). Output negativo permesso by design (R-08 a valle). 182 unit/governance PASS.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-025](changes/2026-04-30-025-formulas-cash-inflow.md) | `2fb60a8` |
| **🚀 Frontiera vettoriale aperta: `vgp/normalize.py` con `min_max_normalize(series, kill_mask)` verbatim ADR-0018. numpy 2.4.4 + pandas 2.3.3 + pandas-stubs 3.0.0 introdotte come prime deps applicative pesanti. 13 test (10 snapshot + 3 property-based Hypothesis: range [0,1], min→0, max→1). 250 PASS, primo modulo Talos su `pd.Series`.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-034](changes/2026-04-30-034-vgp-normalize-min-max.md) | `7bd60dc` |
| **`vgp/score.py` con `compute_vgp_score(df, ...)`: formula VGP composita verbatim PROJECT-RAW sez. 6.3 (norm(ROI)·0.4 + norm(Velocity)·0.4 + norm(Cash_Profit)·0.2). R-05 KILL-SWITCH + R-08 VETO ROI applicati vettoriale via `where(~blocked, 0.0)`. Boundary R-08 inclusivo (ROI=0.08 passa). 17 test (15 snapshot + 2 property-based: vgp_score ∈ [0,1] attivo, kill→0). 267 PASS. Primo caller di `min_max_normalize`.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-035](changes/2026-04-30-035-vgp-score-formula-composita.md) | `5829bfe` |
| **🎯 Tag `checkpoint/2026-04-30-06`** — 5 CHG significativi post checkpoint-05 (CHG-031..035): config layer + catena scalare + cluster vettoriale `vgp/` completo | 0003 | (nessun CHG) | tag su `0812f5d` |
| **🚀 Cluster `tetris/` inaugurato: `tetris/allocator.py` con `allocate_tetris(vgp_df, budget, locked_in)` greedy. Pass 1 R-04 (locked-in priorità∞ + `InsufficientBudgetError` fail-fast). Pass 2 R-06 (VGP DESC, `continue` su over-budget letterale, `break` su saturation ≥ 0.999). `Cart` mutable + `CartItem` frozen + override colonne. 19 test (Cart + base + R-04 + R-06 + validation + ordering). 286 PASS.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-036](changes/2026-04-30-036-tetris-allocator-r04-r06.md) | `4747382` |
| **`tetris/panchina.py` con `build_panchina(vgp_df, cart)`: R-09 verbatim PROJECT-RAW riga 227 (ASIN idonei `vgp_score > 0` non allocati, ordinati VGP DESC). Cluster `tetris/` completo. 10 test (esclusione cart/zero-score, ordinamento, vuoti, realistic, validation). 296 PASS.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-037](changes/2026-04-30-037-tetris-panchina-r09.md) | `00a3c3f` |
| **`formulas/velocity.py`: F4.A `q_m=V_tot/(S_comp+1)` + F4 `qty_target=Q_m·days/30` + F5 `qty_final=Floor(qty/lot)·lot` (Samsung MVP lot=5) + `velocity_monthly=Q_m·30/days`. Costanti `DEFAULT_VELOCITY_TARGET_DAYS=15` (L05) e `DEFAULT_LOT_SIZE=5`. Sblocca orchestratore di sessione (tutti i building block scalari pronti). 29 test (default + per-funzione + composizione end-to-end). 325 PASS.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-038](changes/2026-04-30-038-formulas-velocity-quantity.md) | `f693abc` |
| **🎯 Orchestratore end-to-end `src/talos/orchestrator.py` con `run_session(SessionInput) -> SessionResult`. Compone enrichment (F1/F2/ROI/F4.A/F4/F5/velocity_monthly/kill_mask) → `compute_vgp_score` → sort → `allocate_tetris` → `build_panchina` → `compounding_t1`. Top-level (gap ADR risolto inline da Leader: opzione A ratificata). `SessionInput`/`SessionResult` frozen. 20 test end-to-end Samsung-like (smoke + R-05/R-08 + cart/panchina + budget_t1 + R-04 + validations + edge cases). 345 PASS.** | 0018, 0014, 0013, 0019 | [CHG-2026-04-30-039](changes/2026-04-30-039-orchestrator-session-end-to-end.md) | `6584d49` |
| **🚀 Milestone `milestone/pipeline-e2e-v1.1.0`** — pipeline applicativa end-to-end funzionale (run_session + tutti i building block) | 0003 | (nessun CHG) | tag su `6584d49` |
| **🎯 UI `src/talos/ui/dashboard.py` Streamlit mono-page MVP. streamlit>=1.40 introdotto. Sidebar parametri + CSV upload + run_session + metric/tabelle. Lancio: `uv run streamlit run src/talos/ui/dashboard.py`. Helper `parse_locked_in` esposto/testato. 8 test (smoke + parse). 353 PASS.** | 0016, 0014, 0013, 0019 | [CHG-2026-04-30-040](changes/2026-04-30-040-ui-streamlit-dashboard-mvp.md) | `da0a370` |
| **🛡️ Mini-golden `tests/golden/test_pipeline_samsung_mini.py` snapshot byte-exact `run_session` su 10 ASIN fissati (copertura R-04/R-05/R-08/F5 floor/saturazione/panchina). 13 test (cart asin/qty/total/saturation, panchina, budget_t1, vgp/veto/kill per ASIN, sentinelle regression). + bug fix `allocate_tetris` Pass 2: skip `qty_final<=0` (S010_TINY ex bug). 367 PASS (354 + 13 golden).** | 0019, 0018, 0014, 0013 | [CHG-2026-04-30-041](changes/2026-04-30-041-golden-test-samsung-mini-plus-fix-qty-zero.md) | `1615206` |
| **🎯 Tag `checkpoint/2026-04-30-07`** — 6 CHG significativi post checkpoint-06 (CHG-036..041): cluster `tetris/` + formulas/velocity + orchestrator + UI Streamlit + golden | 0003 | (nessun CHG) | tag su `f5698a4` |
| **🎯 Loop architetturale chiuso: `persistence/session_repository.py` con `save_session_result(db_session, *, session_input, result, tenant_id=1) -> int`. Mappa `SessionResult` su 5 tabelle Allegato A. `with_tenant` future-proof RLS. `listino_hash` deterministico sha256. Pattern Unit-of-Work. 9 test integration (header, listino_items, vgp_results, cart_items, panchina_items, hash, tenant, return type, locked_in). 397 PASS.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-042](changes/2026-04-30-042-persistence-session-repository.md) | `98ca62a` |
| **🎯 Loop UI→DB integrato: `ui/dashboard.py` con bottone "Salva sessione su DB". Helper `get_session_factory_or_none()` (graceful None) + `try_persist_session(factory, inp, result, tenant_id) -> (success, sid, error)`. `DEFAULT_TENANT_ID=1`. Persistenza condizionata a `TALOS_DB_URL` disponibile (graceful degrade). 5 test (2 unit smoke + 3 integration contro Postgres reale + 1 skipped fail-path scope futuro). 401 PASS.** | 0016, 0015, 0014, 0019 | [CHG-2026-04-30-043](changes/2026-04-30-043-dashboard-persistence-integration.md) | `316940b` |
| **🎯 Loop READ chiuso: `SessionSummary` (id/started_at/ended_at/budget_eur/velocity_target/listino_hash/n_cart_items/n_panchina_items) + `list_recent_sessions(db_session, *, limit=20, tenant_id=1)` con subquery `count()` aggregati + tiebreaker `id DESC` su `started_at`. UI: `fetch_recent_sessions_or_empty(factory, ...)` + `_render_history` con `st.expander("Storico Sessioni")` + `st.dataframe`. 8 test integration (empty/post-save/ordering+tiebreaker/limit/invalid/tenant filter/count/UI schema). 409 PASS.** | 0015, 0016, 0014, 0019 | [CHG-2026-04-30-044](changes/2026-04-30-044-list-recent-sessions-ui-history.md) | `d2a502a` |
| **🎯 CRUD-light chiuso: `LoadedSession` (summary + cart_rows + panchina_rows) + `load_session_by_id(db_session, sid, *, tenant_id=1) -> LoadedSession \| None` con JOIN single-query Cart/Panchina ←→ VgpResult per asin/score/roi. UI: `fetch_loaded_session_or_none` + `_render_loaded_session_detail` (metric + 2 tabelle) + UX `number_input` ID + bottone "Carica dettaglio". 8 test integration (id mancante/invalido/round-trip/cart match/panchina match/panchina order/tenant filter/locked preserve). 417 PASS.** | 0015, 0016, 0014, 0019 | [CHG-2026-04-30-045](changes/2026-04-30-045-load-session-by-id-ui-detail.md) | `9a55139` |
| **🛡️ Telemetria primo evento canonico vivente: `tetris.skipped_budget` emesso da `allocate_tetris` Pass 2 over-budget con `extra={asin, cost, budget_remaining}` (DEBUG level). Bug fix regex MULTILINE in `test_log_events_catalog` (era no-op per `continue`). Orchestrator: `continue` defensive → `raise RuntimeError` (R-01 strict). 3 test caplog. 420 PASS.** | 0021, 0019, 0018, 0014 | [CHG-2026-04-30-046](changes/2026-04-30-046-telemetry-tetris-skipped-budget.md) | `cdeae5e` |
| **🎯 Tag `checkpoint/2026-04-30-08`** — 5 CHG significativi post checkpoint-07 (CHG-042..046): persistence + UI persist + storico + dettaglio + telemetria | 0003 | (nessun CHG) | tag su `83b9cb7` |
| **🔒 Idempotency: migration `e965e1b81041` UNIQUE INDEX `ux_sessions_tenant_hash` su `sessions(tenant_id, listino_hash)` + `find_session_by_hash(db, *, listino_hash, tenant_id=1) -> SessionSummary \| None`. AnalysisSession ORM allineato con `__table_args__`. Stesso listino + stesso tenant → IntegrityError (era duplicate silenziose); tenant diversi su stesso listino ammessi. 6 test integration nuovi + 1 adattato. 426 PASS.** | 0015, 0014, 0013, 0019 | [CHG-2026-04-30-047](changes/2026-04-30-047-unique-sessions-tenant-hash-find-by-hash.md) | `89fb471` |

---

## In Sospeso

| ID | Cosa | Priorità | Note |
|---|---|---|---|
| ~~ESP-002~~ | ~~Round 2 Q&A~~ | Chiusa in Round 2 (CHG-005) | — |
| ~~ESP-003~~ | ~~Round 3 Q&A~~ | Chiusa parzialmente in Round 3 (CHG-006) — L04+L21 chiuse, aperta L04b | — |
| ~~ESP-004~~ | ~~Round 4: chiusura L04b~~ | Chiusa in Round 4 (CHG-007) — normalizzazione min-max [0,1] | — |
| ~~ESP-005~~ | ~~Sweep finale: 17 residue~~ | Chiusa in Round 5 (CHG-008) — tutte le 17 chiuse in un colpo | — |
| ~~ESP-006~~ | ~~Transizione `Iterating → Frozen`~~ | Chiusa in Round 6 (CHG-009) — Leader: *"dichiaro frozen"* | — |
| ~~ESP-007~~ | ~~Step [6] ADR-0012: scomposizione → ADR di stack~~ | Chiusa in CHG-2026-04-30-001 — promulgati 9 ADR di stack | — |
| ~~TAG-001~~ | ~~Milestone tag pre-scomposizione~~ | Sostituito da `milestone/stack-frozen-v0.9.0` (ADR-0003) post-CHG-002 | — |
| ~~HARD-STOP~~ | ~~Stop categorico post-tag~~ | Sciolto 2026-04-30 dal Leader ("rompi pure l'hard stop e continua") | — |
| ~~CHG-004~~ | ~~Bootstrap minimale codice~~ | Chiuso 2026-04-30 con commit `b7f78d4` — quality gate verde end-to-end | — |
| ~~CHG-005~~ | ~~CI base + Errata ADR-0020~~ | Chiuso 2026-04-30, run su HEAD verde in 22s | — |
| ~~CHG-006~~ | ~~observability configure_logging~~ | Chiuso 2026-04-30, run CI verde 21s | — |
| ~~CHG-007~~ | ~~persistence skeleton~~ | Chiuso 2026-04-30, CI verde | — |
| ~~CHECKPOINT~~ | ~~`checkpoint/2026-04-30-01`~~ | Creato e pushato su `0f8f40a` | — |
| ~~CHG-008~~ | ~~modello `sessions`~~ | Chiuso 2026-04-30 | — |
| ~~CHG-009~~ | ~~modello `asin_master`~~ | Chiuso 2026-04-30 | — |
| ~~OPEN-Q~~ | ~~Convenzione "DEFAULT → NOT NULL"~~ | Risolta dal Leader 2026-04-30 con risoluzione (a) — errata ADR-0015 in CHG-010 | — |
| ~~CHG-010~~ | ~~Errata Corrige ADR-0015~~ | Chiuso 2026-04-30 | — |
| ~~CHG-011~~ | ~~modello `listino_items`~~ | Chiuso 2026-04-30 | — |
| ~~CHG-012~~ | ~~modello `config_overrides`~~ | Chiuso 2026-04-30 | — |
| ~~CHG-013~~ | ~~modello `vgp_results`~~ | Chiuso 2026-04-30 | — |
| ~~CHECKPOINT-02~~ | ~~`checkpoint/2026-04-30-02`~~ | Creato e pushato su `37fdc7e` | — |
| ~~CHG-014~~ | ~~modello `cart_items`~~ | Chiuso 2026-04-30 | — |
| ~~CHG-015~~ | ~~modello `panchina_items`~~ | Chiuso 2026-04-30 | — |
| ~~CHG-016~~ | ~~modello `storico_ordini`~~ | Chiuso 2026-04-30 | — |
| ~~CHG-017~~ | ~~modello `locked_in`~~ | Chiuso 2026-04-30 | — |
| ~~CHG-018~~ | ~~modello `audit_log` + funzione PL/pgSQL + 3 trigger AFTER~~ | Chiuso 2026-04-30 — schema Allegato A 10/10 completo | — |
| ~~CHG-019~~ | ~~tests/integration/ con RLS + audit runtime~~ | Chiuso 2026-04-30 — 8 integration PASS su Postgres reale | — |
| ~~CHG-020~~ | ~~DB lifecycle: engine + session + with_tenant~~ | Chiuso 2026-04-30 — 11 unit + 4 integration verdi | — |
| ~~CHG-021~~ | ~~scripts/db_bootstrap.py: ruoli + FORCE RLS~~ | Chiuso 2026-04-30 — 9 integration verdi | — |
| ~~CHG-022~~ | ~~formulas/fee_fba.py: prima formula applicativa~~ | Chiuso 2026-04-30 — 8 test verdi | — |
| ~~CHG-023~~ | ~~Errata ADR-0010: verifica reciproca STATUS↔git~~ | Chiuso 2026-04-30 — modifica solo governance, no codice | — |
| ~~CHG-024~~ | ~~Chiusura ISS-001 + errata ADR-0007/0010: verifica empirica STATUS↔runtime tooling~~ | Chiuso 2026-04-30 — modifica solo governance + auto-aggiornamento blocco GitNexus in CLAUDE/AGENTS | — |
| ~~ISS-001~~ | ~~`gitnexus analyze` segfault su Node v24.15.0~~ | Risolta 2026-04-30 con CHG-024 — root cause Node v24-specific; risolto da downgrade a v22.22.2 (oggi default in nvm). Indice fresh, 1646/1929/4. | — |
| ~~CHG-025~~ | ~~F1 `formulas/cash_inflow.py`: primo consumatore di `fee_fba_manual`~~ | Chiuso 2026-04-30 — 11 test verdi, quality gate end-to-end PASS | — |
| ~~CHECKPOINT-04~~ | ~~Tag `checkpoint/2026-04-30-04`~~ | Creato e pushato su `3a5e2ed` (sha tag `2b74ddc`). Finestra: CHG-019..CHG-025 | — |
| ~~CHG-026~~ | ~~F2 `cash_profit_eur` + `roi` — sblocca gate Veto R-08~~ | Chiuso 2026-04-30 — 15 test verdi, quality gate end-to-end PASS. Catena F1→F2→ROI in piedi | — |
| ~~CHG-027~~ | ~~Veto R-08 scalare `vgp/veto.py` — inaugurazione `vgp/`~~ | Chiuso 2026-04-30 — 11 test verdi, primo filtro applicativo funzionale. `vgp/` non più vuota | — |
| ~~CHG-028~~ | ~~Catena e2e scalare: sentinella contratti tra anelli~~ | Chiuso 2026-04-30 — 6 test verdi (1 anchor + 5 parametrici). Zero codice nuovo, alta confidenza sull'integrazione | — |
| ~~CHG-029~~ | ~~Config layer pydantic-settings — sblocca L10~~ | Chiuso 2026-04-30 — 7 test verdi. Inaugurazione `config/`. Limite noto: pydantic-settings non protegge da typo env var (inscritto) | — |
| ~~CHG-030~~ | ~~refactor `engine.py` → `TalosSettings.db_url`~~ | Chiuso 2026-04-30 — primo consumatore reale del config layer; 221 PASS invariati | — |
| ~~CHG-031~~ | ~~refactor `scripts/db_bootstrap.py` via `TalosSettings`~~ | Chiuso 2026-04-30 — +4 campi settings; 226 unit + 9 integration PASS | — |
| ~~CHG-032~~ | ~~F3 Compounding T+1 (`compounding_t1`)~~ | Chiuso 2026-04-30 — chiude catena scalare formule; 235 PASS | — |
| ~~CHG-033~~ | ~~Sentinella e2e estesa con rollup F3~~ | Chiuso 2026-04-30 — 237 PASS, chiude formalmente il blocco | — |
| ~~MILESTONE~~ | ~~`milestone/first-formula-v1.0.0`~~ | Creato e pushato su `cc4070e`. Restore point catena scalare chiusa | — |
| ~~CHECKPOINT-03~~ | ~~Tag `checkpoint/2026-04-30-03`~~ | Già esistente su `e563e59` (post-CHG-018, creato 15:50) | — |
| ~~CHECKPOINT-05~~ | ~~Tag `checkpoint/2026-04-30-05`~~ | Creato e pushato su `cf11e6c`. Finestra: CHG-026..CHG-030 | — |
| ~~CHG-034~~ | ~~`vgp/normalize.py` min_max_normalize L04b + numpy/pandas deps~~ | Chiuso 2026-04-30 — 250 PASS, frontiera vettoriale aperta | — |
| ~~CHG-035~~ | ~~`vgp/score.py` compute_vgp_score formula composita + R-05 + R-08 vettoriale~~ | Chiuso 2026-04-30 — 267 PASS, prima monarchia VGP completa vettoriale | — |
| ~~CHECKPOINT-06~~ | ~~Tag `checkpoint/2026-04-30-06`~~ | Creato e pushato su `0812f5d`. Finestra: CHG-031..035 | — |
| ~~CHG-036~~ | ~~`tetris/allocator.py` Cart + R-04 + R-06 greedy~~ | Chiuso 2026-04-30 — 286 PASS, cluster tetris inaugurato | — |
| ~~CHG-037~~ | ~~`tetris/panchina.py` build_panchina R-09~~ | Chiuso 2026-04-30 — 296 PASS, cluster tetris completo | — |
| ~~CHG-038~~ | ~~`formulas/velocity.py` F4 + F4.A + F5 + velocity_monthly~~ | Chiuso 2026-04-30 — 325 PASS, building block scalari completi | — |
| ~~CHG-039~~ | ~~`src/talos/orchestrator.py` run_session end-to-end~~ | Chiuso 2026-04-30 — 345 PASS, pipeline funzionale + gap ADR risolto | — |
| ~~MILESTONE-1.1.0~~ | ~~`milestone/pipeline-e2e-v1.1.0`~~ | Creato e pushato su `6584d49`. Restore point pipeline applicativa end-to-end | — |
| ~~CHG-040~~ | ~~`src/talos/ui/dashboard.py` Streamlit MVP mono-page~~ | Chiuso 2026-04-30 — 353 PASS, strato visivo inaugurato | — |
| ~~CHG-041~~ | ~~mini-golden + fix allocator qty=0~~ | Chiuso 2026-04-30 — 367 PASS, pipeline blindata + bug regression sentinella | — |
| ~~CHECKPOINT-07~~ | ~~Tag `checkpoint/2026-04-30-07`~~ | Creato e pushato su `f5698a4`. Finestra: CHG-036..041 | — |
| ~~CHG-042~~ | ~~`persistence/session_repository.py` save_session_result~~ | Chiuso 2026-04-30 — 397 PASS, loop architetturale chiuso (memory→DB) | — |
| ~~CHG-043~~ | ~~dashboard integra save_session_result (bottone "Salva su DB")~~ | Chiuso 2026-04-30 — 401 PASS, loop UI→DB end-to-end | — |
| ~~CHG-044~~ | ~~list_recent_sessions + UI storico expander~~ | Chiuso 2026-04-30 — 409 PASS, loop READ chiuso | — |
| ~~CHG-045~~ | ~~load_session_by_id + UI dettaglio~~ | Chiuso 2026-04-30 — 417 PASS, CRUD-light persistenza completo | — |
| ~~CHG-046~~ | ~~telemetria tetris.skipped_budget + fix regex governance~~ | Chiuso 2026-04-30 — 420 PASS, primo evento canonico vivente | — |
| ~~CHECKPOINT-08~~ | ~~Tag `checkpoint/2026-04-30-08`~~ | Creato e pushato su `83b9cb7`. Finestra: CHG-042..046 | — |
| ~~CHG-047~~ | ~~UNIQUE listino_hash + find_session_by_hash~~ | Chiuso 2026-04-30 — 426 PASS, idempotency aperta | — |
| **NEXT** | **Prossimi step possibili** | Idempotency aperta | (α) **integrazione UI find_session_by_hash pre-save** (warning "questa sessione esiste gia'" con bottone "Forza nuovo" o "Apri esistente"); (β) **`upsert_session`** decisione Leader semantica (delete-recreate vs update-only vs error); (d') telemetria aggregata in `compute_vgp_score` (`vgp.veto_roi_failed`/`vgp.kill_switch_zero` count) + `panchina.archived`; (z) migrazione a `structlog.bind(...)` context tracing; (q) refactor UI multi-page ADR-0016; (r) `io_/extract` Samsung (Playwright + Tesseract + Keepa) — last big block; (s) golden Samsung 1000 ASIN; (c) lookup `config_overrides` runtime per soglia ROI; (e) lookup `Referral_Fee` per categoria; (y) `load_session_full`; chiusi: (a/a'/a''/b/b''/d/f/g/h/i/j/k/l/m/n/p/t/u/v/x) |
| ~~ISS-001~~ | ~~`gitnexus analyze` non eseguibile (architettura processore)~~ | Risolta in CHG-024 | Root cause vera: Node v24.15.0-specific segfault. Risolta da downgrade a v22.22.2. Indice operativo. |
| ~~ISS-002~~ | ~~Stack tecnologico → ADR di stack~~ | Chiusa in CHG-2026-04-30-001 — Python 3.11 + PostgreSQL 16 + SQLAlchemy 2.0 sync + Streamlit + Keepa/Playwright/Tesseract + structlog | — |

### Lacune critiche residue

Nessuna. Round 4 ha chiuso l'ultima critica (L04b).

### Lacune aperte

Nessuna. Round 5 ha chiuso le 17 residue in un colpo.

### Decisioni architetturali ratificate (Round 2 + 3 + 4 + 5)

Tutte le 26 lacune sono chiuse. Per la lista completa vedi sezione 9 di `PROJECT-RAW.md`. Sintesi delle decisioni più strutturali:

| Tema | Decisione | Round |
|---|---|---|
| Formula VGP | `(ROI*0.4)+(Vel*0.4)+(Cash_Profit*0.2)` con normalizzazione min-max [0,1] sul listino di sessione | 3 + 4 |
| Estrattore | `SamsungExtractor` (MVP) con interface `BrandExtractor`; NLP+Regex come unico modulo a pipeline interna | 2 + 5 |
| Lookup Amazon | Scraping `amazon.it` via Playwright | 2 + 5 |
| Fee_FBA | Lookup Keepa primario; fallback formula manuale verbatim del Leader | 2 + 5 |
| Referral_Fee | Lookup categoria + override manuale configurabile | 2 |
| Keepa | Piano gestito esternamente; Talos consuma le API | 3 |
| OCR | Tesseract locale | 2 |
| UI | Streamlit (cruscotto militare con griglie e slider) | 5 |
| Stack Python | SQLAlchemy 2.0 sync + Alembic + Playwright + Tesseract + pytest + ruff strict + mypy strict | 2 + 5 |
| DB | PostgreSQL Zero-Trust (RLS + ruoli `talos_app`/`talos_admin` + no superuser pool app + audit log) | 5 |
| Velocity Target | Slider 7–30 gg, default 15, step 1 | 5 |
| Veto ROI | Soglia configurabile dal cruscotto, default 8% | 5 |
| Manual Override | Lock-in UI + tabella + Priorità=∞ nel Tetris | 5 |
| Storico ordini | Solo interno, alimentato dall'azione "ordina" | 5 |
| Output commercialista | Niente automatico, solo storico interno consultabile | 5 |
| Capitale `x` | Budget di sessione (Opzione a) | 5 |
| Stateless | Analisi di sessione senza dipendenza causale da sessioni precedenti | 5 |

---

## Prossima Azione

1. **HARD STOP sciolto.** Leader ha clonato `Atena-Core` post-tag e autorizzato la ripartenza ("rompi pure l'hard stop e continua").
2. **CHG-2026-04-30-003 promulgato:** Errata Corrige ADR-0006 + side-effect su ADR-0014/0020. Hooks v2 in vigore (pre-commit-app wiring + bot reindex bypass).
3. **CHG-2026-04-30-004 imminente:** Bootstrap minimale codice. Sequenza: (a) `pyproject.toml` (Python 3.11, ruff/mypy/pytest config), (b) `uv.lock` da `uv sync` (richiede toolchain), (c) `src/talos/__init__.py` con bootstrap structlog (ADR-0021), (d) `tests/conftest.py` skeleton, (e) `scripts/hooks/pre-commit-app` minimo. Test gate: smoke test `tests/unit/test_smoke.py` + governance test `tests/governance/test_no_root_imports.py`. Commit subordinato a permesso esplicito Leader.
4. Verifica fase codice: ogni nuovo file applicativo deve mappare a un ADR Primario in `docs/decisions/FILE-ADR-MAP.md` (sezione "Codice Applicativo"). Gap → bloccare e segnalare al Leader.

---

## Nota al Prossimo Claude

> Questo campo è il presidio principale contro le allucinazioni da contesto perso. Leggerlo come se qualcuno avesse lasciato un biglietto.

- **Step 0 del Self-Briefing è bloccante (ADR-0010).** Verifica `git config core.hooksPath` = `scripts/hooks` prima di tutto.
- **Hooks v2 in vigore (CHG-2026-04-30-003).** Il `pre-commit` invoca `scripts/hooks/pre-commit-app` quando in staging ci sono `*.py`/`pyproject.toml`/`uv.lock` (graceful skip se l'hook applicativo non esiste); il `commit-msg` esenta i commit del bot `github-actions[bot]` con marker `[skip ci]` (esenzione cumulativa, marker da solo non basta).
- **🔓 Fermaposto Docker risolto (2026-04-30 sessione 19):** `docker ps` verde, gruppo attivo. Container `talos-pg-test` (postgres:16-alpine, host:55432, tmpfs) lanciato e validato; `alembic upgrade head` reale eseguito con successo (10 revision applicate, schema verbatim Allegato A). Container può essere fermato a fine sessione (`docker rm -f talos-pg-test`) — ephemeral, dati su tmpfs.
- **🔖 Scoperta runtime CHG-019 (rilevante per futuro `db-bootstrap.sh`):** la policy RLS `tenant_isolation` non era visibile testando da `postgres` neanche con `FORCE ROW LEVEL SECURITY`, perché `postgres` ha `BYPASSRLS` (superuser). I test usano `CREATE ROLE talos_rls_test_subject` (default NOSUPERUSER NOBYPASSRLS) + GRANT minimo + `SET LOCAL ROLE`. **Implicazione:** il bootstrap dei ruoli applicativi deve esplicitamente NON dare `BYPASSRLS` a `talos_app`, e ogni tabella con RLS deve avere `FORCE` se la ownership non è `talos_app`.
- **`TALOS_DB_URL` env var:** se assente, `tests/integration/` skippa silenziosamente module-level. CI integration job (futuro CHG) deve **failarsi se non vengono raccolti almeno N test** per evitare che lo skip diventi default.
- **`PROJECT-RAW.md` è in stato `Frozen` dal 2026-04-29 (codename TALOS).** Modifiche alla vision passano per **Errata Corrige** (ADR-0009) o transizione documentata a `Iterating` con motivazione esplicita del Leader.
- **Regola "Lacune mai completate" (ADR-0012, vincolante).** Continua ad applicarsi anche post-Frozen e post-stack-Frozen. Se emergono ambiguità durante la futura implementazione, marcarle in chat e portarle al Leader, **non inferire**.
- **Cluster ADR di stack 0013–0021 attivo (CHG-2026-04-30-001).** Ogni nuovo file applicativo deve mappare a un ADR Primario in FILE-ADR-MAP.md (sezione "Codice Applicativo"). Path consentiti: `src/talos/{io_,extract,vgp,tetris,formulas,persistence,ui,observability,config}` + `tests/{unit,integration,golden,governance}` + `migrations/`.
- **Repo origin:** `https://github.com/matteo891/Atena` (fork operativo del Leader). Il repo del padre `santacrocefrancesco00-ux/Atena` non è scrivibile da `matteo891`.
- **Refusi noti nelle Leggi di Talos (R-08 vs R-09):** il testo del Leader cita "Veto ROI (R-09)" mentre in tabella R-09 è Archiviazione e R-08 è Veto ROI. Marcato L09 (corretto inline in PROJECT-RAW sez. 4.1.9). Non interpretare in autonomia: chiedere conferma se rilevato altrove.
- **GitNexus operativo dal 2026-04-30 (ISS-001 risolta in CHG-024).** Step 4 self-briefing **non va saltato**: eseguire sempre `mcp__gitnexus__list_repos` empirica come prima azione dello step. Se `staleness.commitsBehind > 0` o `lastCommit ≠ git rev-parse HEAD`, eseguire `npx -y gitnexus analyze` su Node v22 (verificare prima `node --version` = `v22.x`; Node v24.15.0 segfault, vedi ISS-001 risolta). Solo errore tecnico effettivo (transport/timeout/server down) giustifica la dichiarazione "GitNexus non disponibile", citando l'errore verbatim come ancora.
- **Regola generale (ADR-0010 errata CHG-024):** ogni claim documentale di indisponibilità tooling in STATUS richiede verifica empirica al re-entry, non può essere accettato dal contesto. Vale per qualsiasi server MCP, container, runner CI futuro.
- **Push immediato post-commit certificato (ADR-0011).**
- **Test manuali documentati ammessi per governance (ADR-0011), non per codice applicativo (richiede test automatici).**
- **Tutti gli ADR sono `Active`.** ADR-0004 è `Active¹` (hardening patch).
- **Header `Ultimo aggiornamento` di STATUS.md obbligatorio (ADR-0010).** Aggiornare data + commit hash post-commit. Ogni claim ancorato.
- **Stima MVP 2026-04-30 (post `milestone/first-formula-v1.0.0`):** ~30-35% verso prima build USABILE dall'utente CFO finale. Fondamento tecnico ~95% (governance/schema/persistence/config/formule scalari); percorso utente ~5-10% (manca tutto il flusso "input listino → carrello → cruscotto"). Breakdown per area in `memory/project_mvp_progress_estimate.md`.
- **Ordine consigliato per il prossimo blocco strategico** (raccomandato in chat dal Claude precedente, non vincolante): vettoriale VGP (`vgp/normalize.py` + `vgp/score.py` Numpy/pandas) → Tetris allocator (`tetris/`) → orchestratore minimale headless (workflow integratore senza UI) → io_/extract (file readers + scraping Amazon Playwright + Keepa + OCR Tesseract) → UI Streamlit come ultimo strato. Razionale: costruire il "motore" su DataFrame sintetici (testabili in golden Samsung) prima dell'acquisizione reale, e prima di esporlo via UI.

---

## Issues Noti

| ID | Descrizione | Workaround | ADR | Priorità |
|---|---|---|---|---|
| ~~ISS-001~~ | ~~`gitnexus analyze` segfault / exit code 5 su Node v24.15.0~~ | Risolta 2026-04-30 (CHG-024) — root cause Node v24-specific (non architettura processore). Risolto da downgrade a Node v22.22.2 (oggi default in nvm). Indice operativo: `lastCommit == HEAD`, 1646 nodes / 1929 edges / 12 clusters / 4 flows. Vincolo: `gitnexus analyze` su Node v22 (Node v24 sconsigliato finché upstream non risolve). | ADR-0007 | Risolta |
| ~~ISS-002~~ | ~~Stack tecnologico non promulgato~~ | Chiusa 2026-04-30 con CHG-2026-04-30-001 — cluster ADR 0013–0021 promulgato | ADR-0013–0021 | Chiusa |
| ESP-001 | Esposizione bozza progetto | Chiusa 2026-04-29 con CHG-004 | ADR-0012 | Chiusa |
| ESP-002 | Round 2 | Chiusa 2026-04-29 con CHG-005 | ADR-0012 | Chiusa |
| ESP-003 | Round 3: chiusura L04 + L21 | Chiusa 2026-04-29 con CHG-006; aperta nuova L04b critica | ADR-0012 | Chiusa parzialmente |
| ESP-004 | Round 4: chiusura L04b | Chiusa 2026-04-29 con CHG-007 — normalizzazione min-max [0,1] | ADR-0012 | Chiusa |
| ESP-005 | Round 5: sweep finale 17 lacune residue | Chiusa 2026-04-29 con CHG-008 — tutte chiuse in un colpo | ADR-0012 | Chiusa |
| ESP-006 | Transizione Iterating → Frozen | Chiusa 2026-04-29 con CHG-009 — Leader: "dichiaro frozen" | ADR-0012 | Chiusa |
| ~~ESP-007~~ | ~~Step [6] ADR-0012: scomposizione → ADR di stack~~ | Chiusa 2026-04-30 con CHG-2026-04-30-001 — validazione bulk Leader (Opzione A) | ADR-0012 → ADR-0013–0021 | Chiusa |
| HARD-STOP | Pausa esplicita Leader post-tag stack-frozen | Attiva. Riapertura solo su istruzione esplicita Leader | — | Attiva |
