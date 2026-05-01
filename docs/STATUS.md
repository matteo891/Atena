# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-05-01 round 4 chiusura — **🎯 BLOCCO ASIN_RESOLVER 5/5 + MVP CFO TARGET RAGGIUNTO + milestone v1.3.0**. HEAD `caa6d29` (CHG-020 backfill); commit di chiusura sessione segue. Tag: **8 milestone** (`milestone/asin-resolver-v1.3.0`) + **14 checkpoint** (`checkpoint/2026-05-01-14`). **773 test PASS, 0 SKIPPED** (640 unit/gov/golden + 133 integration). Catena CHG 2026-05-01: 001..020 (7 significativi nel round 4). **Catalogo eventi canonici ADR-0021: 10/11 viventi**. **Indice GitNexus fresh** (4665 nodes / 6085 edges / 87 clusters / 16 flows — refreshed fine round 4 dopo CHG-014..020 che hanno aggiunto ~520 nodes / ~690 edges / 14 clusters). **Quota Keepa consumata sessione: ~9 token**. **MVP CFO TARGET RAGGIUNTO**: il CFO carica un listino fornitore "umano" (CSV `descrizione+prezzo`) e ottiene classifica VGP completa senza preprocessing manuale. Memory `project_session_handoff_2026-05-01-round4.md` puntatore di re-entry post-/clear.
> **Sessione corrente:** TALOS round 2 (modalità "macina" riautorizzata Leader 2026-05-01) — Leader ha ratificato **Path B** ("obiettivo prodotto funzionante") come MVP target. Sequenza in 3 fasi: **Fase 1 (mock-testabile, no setup) ✓ CHIUSA**, Fase 2 (installazioni di sistema in sospeso), Fase 3 (live adapters + 5 decisioni Leader pre-flight). **5 CHG di Fase 1 (006..010)**: tutto il valore architetturale producibile senza Tesseract/Chromium/Keepa key è in produzione. Zero nuove deps, zero nuovi eventi canonici. Sentinelle e2e mock-only ancorano il flusso per Fase 3.

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
| **🎯 UX duplicate-aware: dashboard `fetch_existing_session_for_listino(factory, listino_raw, *, tenant_id)` graceful + `_render_existing_session_warning` (warning con id/n_cart/n_panchina) + bottone "Apri sessione esistente" → `fetch_loaded_session_or_none`. Mutua esclusione warning vs bottone "Salva" (no IntegrityError visibile al CFO). 4 test integration. 430 PASS.** | 0016, 0015, 0014, 0019 | [CHG-2026-04-30-048](changes/2026-04-30-048-ui-duplicate-check-pre-save.md) | `82d274f` |
| **📡 Telemetria 3 eventi canonici: `compute_vgp_score` emette `vgp.veto_roi_failed` (asin/roi_pct/threshold) per riga vetata e `vgp.kill_switch_zero` (asin/match_status) per riga killed. `build_panchina` emette `panchina.archived` (asin/vgp_score) per riga. +kwargs `asin_col`/`match_status_col` opzionali in score.py (graceful skip). Catalogo ADR-0021 ora 4/10 eventi viventi (5 dormienti attivati con futuri moduli). 8 test caplog (5 vgp + 3 panchina). 438 PASS.** | 0021, 0019, 0018, 0014 | [CHG-2026-04-30-049](changes/2026-04-30-049-telemetry-vgp-panchina-events.md) | `ac3a0ef` |
| **🚀 Milestone `milestone/crud-and-telemetry-v1.2.0`** — restore point post CRUD-light + idempotency + UX duplicate-aware + telemetria 4/10 | 0003 | (nessun CHG) | tag su `6654795` |
| **🎛️ Configurabilità persistente: `config_repository.py` con `get/set_config_override_numeric` (UPSERT `pg_insert.on_conflict_do_update`). SCOPE_GLOBAL/CATEGORY/ASIN. UI: sidebar pre-carica soglia veto ROI da DB tenant + bottone "Salva soglia ROI come default tenant". Bug fix migration `e8b80f77961b`: `idx_config_unique` ricreato con `NULLS NOT DISTINCT` (Postgres 15+). L10 PROJECT-RAW Round 5 chiusa operativamente. 7 test integration (None on missing, roundtrip, UPSERT overwrites, filter tenant, float-to-decimal, invalid scope, default scope). 445 PASS.** | 0015, 0016, 0014, 0019 | [CHG-2026-04-30-050](changes/2026-04-30-050-config-overrides-runtime-veto-roi.md) | `1bdac33` |
| **🎯 Tag `checkpoint/2026-04-30-09`** — 4 CHG significativi post checkpoint-08 (CHG-047..050) + milestone v1.2.0 | 0003 | (nessun CHG) | tag su `894c291` |
| **🛒 Referral Fee per categoria (L12 chiusa): `list_category_referral_fees(db, *, tenant_id) -> dict[str, Decimal]` + UI expander "Referral Fee per categoria" con dataframe + form input categoria/fee + bottone Salva. `KEY_REFERRAL_FEE_PCT="referral_fee_pct"` costante. Refactor `continue` defensive → dict comprehension (governance). Merge in orchestrator scope post `io_/extract`. 7 test integration (empty/mapping/tenant filter/exclude keys/exclude global/UI floats/UI no factory). 452 PASS.** | 0015, 0016, 0014, 0019 | [CHG-2026-04-30-051](changes/2026-04-30-051-referral-fee-per-category.md) | `45b4757` |
| **🔄 CRUD-light READ completo: `load_session_full(db, session_id, *, tenant_id=1) -> SessionResult \| None`. Ricostruisce cart/panchina/budget_t1/enriched_df da DB (round-trip canonico, drift Decimal→float `< 1 EUR` su budget_t1 documentato). 13 colonne enriched_df persistite; `fee_fba_eur`/`cash_inflow_eur`/`q_m` ricalcolabili on-demand. 8 test integration round-trip. 460 PASS (380 + 80).** | 0015, 0014, 0019 | [CHG-2026-04-30-052](changes/2026-04-30-052-load-session-full-round-trip.md) | `4c710ea` |
| **🛒 L12 chiusa lato pipeline: `SessionInput.referral_fee_overrides: dict[str, float] \| None` + `_resolve_referral_fee(row, overrides)` lookup hierarchy (overrides[category_node] → fallback referral_fee_pct raw) + colonna `referral_fee_resolved` (audit trail). Behavioral change zero per caller esistenti (default None + listini senza category_node). Loop CFO→config_overrides→run_session chiuso (manca aggancio UI). 7 test unit. 467 PASS (387 + 80).** | 0018, 0014, 0019 | [CHG-2026-04-30-053](changes/2026-04-30-053-orchestrator-referral-fee-overrides.md) | `1178389` |
| **🗑️ Triade CRUD config_overrides chiusa: `delete_config_override(db, *, key, tenant_id, scope, scope_key) -> bool` (idempotente, pre-check tipizzato per evitare `Result.rowcount` sotto mypy strict). UI: `try_delete_veto_roi_threshold` + `try_delete_category_referral_fee` graceful + bottoni "Reset al default" e "Reset" affiancati ai "Salva" via `st.columns(2)`. CFO può tornare al default applicativo senza inserire valori. 8 test integration. 475 PASS (387 + 88).** | 0015, 0016, 0014, 0019 | [CHG-2026-04-30-054](changes/2026-04-30-054-delete-config-override-ui-reset.md) | `9a3b0c3` |
| **🔁 Loop CFO→DB→UI→orchestrator chiuso lato referral fee: `build_session_input(factory, listino_raw, ...) -> SessionInput` carica overrides per categoria via `fetch_category_referral_fees_or_empty` e li passa al `SessionInput`. `dashboard.main()` delega la costruzione dell'input. Senza `category_node` nel listino raw → fail-safe (override inerti = comportamento pre-CHG). 3 test integration. 478 PASS (387 + 91).** | 0016, 0018, 0014, 0019 | [CHG-2026-04-30-055](changes/2026-04-30-055-ui-build-session-input-with-overrides.md) | `d8f74c1` |
| **♻️ What-if `replay_session(loaded, *, locked_in_override, budget_override) -> SessionResult`. Riusa `loaded.enriched_df` (no re-enrichment), riapplica Tetris+panchina+compounding. Primo consumer reale di `load_session_full` (CHG-052). Default override: locked_in/budget originali. `veto_roi_threshold_override` out-of-scope V1. 6 test integration. 484 PASS (387 + 97).** | 0018, 0014, 0019 | [CHG-2026-04-30-056](changes/2026-04-30-056-replay-session-what-if.md) | `e7c2666` |
| **🔁 UI consumer di `replay_session`: `try_replay_session` graceful + sub-expander "What-if Re-allocate" dentro `_render_loaded_session_detail`. Number_input budget + text_input locked-in CSV + bottone Re-allocate → metric/tabelle nuove (no persist). 3 test integration (success, ID inesistente, R-04 over-budget). 487 PASS (387 + 100).** | 0016, 0018, 0014, 0019 | [CHG-2026-04-30-057](changes/2026-04-30-057-ui-replay-what-if.md) | `92bd63b` |
| **📡 Telemetria `session.replayed` (errata catalogo ADR-0021): orchestrator emette `_logger.debug` post-replay con `asin_count/locked_in_count/budget/budget_t1`. Catalogo 5/11 eventi viventi. 2 test caplog. 489 PASS (389 + 100).** | 0021, 0019, 0009, 0014 | [CHG-2026-04-30-058](changes/2026-04-30-058-telemetry-session-replayed.md) | `a40b825` |
| **🔀 UI compare side-by-side `compare_session_kpis(loaded, replayed) -> dict` helper puro + `_render_compare_view` due colonne con metric Budget/Saturazione (delta pp)/Budget T+1/Cart-Panchina counts (delta). Sostituisce "solo replay" di CHG-057 con confronto immediato. 5 test unit (struttura, saturation derivata, NaN placeholder, replayed usa Cart, no div/0). 494 PASS (394 + 100).** | 0016, 0014, 0019 | [CHG-2026-04-30-059](changes/2026-04-30-059-ui-compare-runs-side-by-side.md) | `3550027` |
| **🚀 `src/talos/io_/` inaugurato — `KeepaClient` skeleton (ADR-0017 canale 1). Adapter pattern (`KeepaApiAdapter` Protocol) + rate limit hard `pyrate-limiter` (R-01 fail-now via `KeepaRateLimitExceededError`) + retry esponenziale `tenacity` (5 attempts, 1..60s) + miss handling (`KeepaMissError` per buybox/bsr/fee_fba). `_LiveKeepaAdapter` skeleton lancia `NotImplementedError` esplicito (mapping CSV indici Keepa rinviato). Settings +`keepa_api_key`+`keepa_rate_limit_per_minute` (env `TALOS_KEEPA_*`). Deps `keepa>=1.4.0`, `tenacity>=8`, `pyrate-limiter>=3`. 16 test unit + 6 settings. 516 PASS (416 + 100).** | 0017, 0014, 0019, 0021 | [CHG-2026-05-01-001](changes/2026-05-01-001-keepa-client-skeleton.md) | `4bb7e9b` |
| **🌐 `AmazonScraper` skeleton (ADR-0017 canale 2). `BrowserPageProtocol` adapter pattern + selector fallback chain CSS→XPath (D2.a) da `selectors.yaml` versionato + UA Chrome desktop fisso (D2.b) + delay range exposto fresh context (D2.c) + `parse_eur` heuristica italiano/anglo + `SelectorMissError` R-01 + `_PlaywrightBrowserPage` skeleton (`NotImplementedError`, attesa CHG-005 + `playwright install chromium`). Deps `playwright>=1.40`, `pyyaml>=6` + dev `types-PyYAML`. 34 test unit (loader/parse_eur 14 parametrici/fallback/skeleton). 550 PASS (450 + 100).** | 0017, 0014, 0019, 0021 | [CHG-2026-05-01-002](changes/2026-05-01-002-amazon-scraper-skeleton.md) | `ba2421c` |
| **🔠 `OcrPipeline` skeleton (ADR-0017 canale 3). `TesseractAdapter` Protocol + soglia confidence configurabile (default 70 verbatim, env `TALOS_OCR_CONFIDENCE_THRESHOLD`) + `OcrStatus` StrEnum OK/AMBIGUOUS (R-01 NO SILENT DROPS) + `RawOcrData`/`OcrResult` dataclass + helper `otsu_threshold`/`binarize_otsu` pure-numpy (D3.b preprocessing minimo) + lang `ita+eng` (D3.a) + `_LiveTesseractAdapter` skeleton (`NotImplementedError`, attesa CHG-005 + `apt install tesseract-ocr-ita-eng`). Dep `pytesseract>=0.3.13` + mypy override `ignore_missing_imports`. Settings +`ocr_confidence_threshold` validator [0,100]. 22 test unit OCR + 6 settings. 578 PASS (478 + 100).** | 0017, 0014, 0019, 0021 | [CHG-2026-05-01-003](changes/2026-05-01-003-ocr-pipeline-skeleton.md) | `1da38b0` |
| **🔐 `TalosSettings.env_file=".env"` + `.env.example` template + `.gitignore` per secrets locali. Sblocca caricamento Keepa private API key (consegnata Leader 2026-05-01 round 4) senza export shell manuale e senza memoria persistente del progetto. Precedenza shell-env > .env (CI-friendly). Test fixture `_isolate_settings` con `monkeypatch.chdir(tmp_path)` per impedire inquinamento da .env reale. 3 nuovi test (loading .env / precedenza shell / no .env -> None). 690 PASS (568 + 122).** | 0014, 0017, 0019 | [CHG-2026-05-01-014](changes/2026-05-01-014-talos-settings-load-dotenv.md) | `0127f61` |
| **🚀 `_LiveKeepaAdapter` ratificato live (canale 1 ADR-0017). Decisioni Leader 2026-05-01 round 4 post-diagnostic empirico su B0CSTC2RDW: **A2** buybox hierarchy `BUY_BOX_SHIPPING → NEW → AMAZON` (NEW €549 coincide con scraper Buy Box €549 sul piano corrente che NON espone `BUY_BOX_SHIPPING`); **A** bsr da `data['SALES']`; **α''** `fee_fba_eur` SEMPRE None → caller usa `fee_fba_manual` L11b Frozen (Keepa `pickAndPackFee=€4.10` ≠ L11b totale ~€43.45 per Galaxy S24, sostituzione avrebbe rotto Cash_Profit/ROI/VGP). Lazy init `keepa.Keepa(api_key)` + lazy import + `domain="IT"`. Helper `_last_valid_value` filtra sentinel `-1`/NaN. Errori network/shape → `KeepaTransientError` chained. 4 test live (~4 token consumati). **693 PASS** (567 + 126).** | 0017, 0014, 0019, 0021 | [CHG-2026-05-01-015](changes/2026-05-01-015-keepa-live-adapter.md) | `bb5a9cd` |
| **🧭 `extract/asin_resolver.py` skeleton — apertura blocco "(descrizione, prezzo) → ASIN" (decisioni Leader 1=A/2=α'/3=i'/4=a/5=A round 4). `ResolutionCandidate` + `ResolutionResult` (frozen, default ambiguous=True conservativo) + `AsinResolverProtocol` + `compute_confidence(fuzzy_title_pct, delta_price_pct) -> float` (60/40 weighted, saturazione 0-100, ValueError out-of-range) + `is_ambiguous(threshold=70)`. NESSUN scarto silenzioso: tutti i match esposti UI con `confidence_pct`. Memory feedback `ambigui_con_confidence` salvata. Mock-testable, no live. 20 test unit (costanti, 8 confidence, 4 ambiguous, dataclass shape, Protocol). **713 PASS** (587 + 126).** | 0017, 0014, 0019 | [CHG-2026-05-01-016](changes/2026-05-01-016-asin-resolver-skeleton.md) | `b86baea` |
| **🌐 `io_/serp_search.py` SERP Amazon.it live — apertura canale risoluzione descrizione→ASIN (decisione 1=A). `SerpResult` frozen (asin/title/price_displayed/position) + `SerpBrowserProtocol` separato da `BrowserPageProtocol` (zero blast radius mock esistenti) + `AmazonSerpAdapter` Protocol + `_LiveAmazonSerpAdapter` con `browser_factory` lambda (riuso context Chromium). `_PlaywrightBrowserPage.evaluate` aggiunto (additivo). JS hardcoded itera `[data-component-type="s-search-result"]`, estrae data-asin/title/price. 17 test unit mock + **1 test live Amazon.it** "Galaxy S24" PASS in 2.83s (selettori 2026 ratificati). **727 PASS** (604 + 123). | 0017, 0014, 0019 | [CHG-2026-05-01-017](changes/2026-05-01-017-amazon-serp-search-live.md) | `467c713` |
| **🎯 `_LiveAsinResolver` composer end-to-end — chiusura motore applicativo asin_resolver (3/5 CHG blocco). Compone SERP top-N (CHG-017) + lookup_product Keepa-only (CHG-006/015) per verifica prezzo + `rapidfuzz.fuzz.token_set_ratio` (descrizione vs title) + `compute_confidence` (CHG-016). `lookup_callable` iniettato (disaccoppiamento + Keepa-only Pattern per quota optimization). R-01 UX-side ratificato: lookup fallito per candidato → `buybox=None` + nota in `notes`, candidato comunque esposto. Tie-break implicito: max-by-confidence con stable sort = top-1 SERP a parità. 12 test unit + **1 test live e2e** (Galaxy S24 256GB Onyx @ €549 → top-1 starts B0, fuzzy>30, confidence>50, ~3 token Keepa, PASS 7.29s). **740 PASS** (616 + 124). | 0017, 0014, 0019 | [CHG-2026-05-01-018](changes/2026-05-01-018-asin-resolver-live-composer.md) | `fd51e40` |
| **🗂️ `description_resolutions` cache + repository UPSERT idempotente (4/5 CHG asin_resolver). Decisioni Leader α=A NO RLS, β=A UNIQUE `(tenant_id, description_hash)`, γ=A NO trigger audit. ORM `DescriptionResolution` (BIGSERIAL + CHAR(64) hash + CHAR(10) asin + NUMERIC(5,2) confidence). Migration `1d67de49c197` + alembic upgrade head reale verde. `compute_description_hash(desc) -> str` (SHA-256 hex 64-char di `strip().lower()`). `find_resolution_by_hash` + `upsert_resolution` (`pg_insert.on_conflict_do_update` last-write-wins). **Bonus correttivo**: drift `idx_config_unique` ORM↔DB risolto (`postgresql_nulls_not_distinct=True` aggiunto al modello). 10 test integration. **749 PASS** (616 + 133). | 0015, 0017, 0014, 0019 | [CHG-2026-05-01-019](changes/2026-05-01-019-description-resolutions-cache.md) | `f3b67e4` |
| **🎯 UI Streamlit rifondata: flow "(descrizione, prezzo) → ASIN" — chiusura blocco asin_resolver 5/5 (decisione Leader δ=A convivenza). `src/talos/ui/listino_input.py` nuovo modulo helper puri (no Streamlit dep): `parse_descrizione_prezzo_csv` + `resolve_listino_with_cache` (cache hit + live fallback + UPSERT) + `build_listino_raw_from_resolved` (DataFrame 7-col compat) + `format_confidence_badge` (OK/DUB/AMB soglie 85/70). `dashboard.py`: + `_render_descrizione_prezzo_flow` (Streamlit multi-step: upload + resolve con `st.spinner` + tabella preview con `confidence_pct` esposto + bottone Conferma → DataFrame run_session). + `st.radio` mode default = nuovo flow; legacy CSV-strutturato resta come opzione (zero breaking CHG-040). 24 test unit mock-only + smoke import OK. **773 PASS** (640 + 133). **MVP CFO target raggiunto.** | 0016, 0017, 0014, 0019 | [CHG-2026-05-01-020](changes/2026-05-01-020-ui-descrizione-prezzo-flow.md) | `2886728` |
| **🧬 `SamsungExtractor` + R-05 KILL-SWITCH (ADR-0017 + ADR-0018). Inaugura `src/talos/extract/`. NLP regex + `rapidfuzz` (D4.a) per estrazione modello/RAM/ROM/colore/connettivita'/enterprise; whitelist YAML versionata `samsung_whitelist.yaml` (D4.b: 20 modelli 5G + 17 colori + RAM/ROM canonici); `match()` con weighted sum (D4.c: model=3, ram=2, rom=2, color=1, conn=1) e soglie SICURO/AMBIGUO/MISMATCH; **R-05 hard su model mismatch** -> caller forzera' VGP=0 + evento `extract.kill_switch` (CHG-005). Dep `rapidfuzz>=3,<4`. 31 test unit (whitelist + parse + match + R-05 + end-to-end). 609 PASS (509 + 100).** | 0017, 0018, 0014, 0019, 0021 | [CHG-2026-05-01-004](changes/2026-05-01-004-samsung-extractor.md) | `2140ab4` |
| **🎯 `asin_master_writer` UPSERT merge (D5) + telemetria 5 eventi canonici attivati. `AsinMasterInput` + `upsert_asin_master(db, *, data) -> str` con `pg_insert.on_conflict_do_update` (D5.a Postgres-native atomico) + merge `COALESCE(EXCLUDED.f, AsinMaster.f)` su nullable (D5.b: input non-null vince, null preserva) + `last_seen_at = NOW()` refresh + nessun trigger audit (D5.c). Telemetria attivata in 4 moduli skeleton (`KeepaClient`/`AmazonScraper`/`OcrPipeline`/`SamsungExtractor`) con `_logger.debug(event_name, extra={...})` ai siti di produzione. **Catalogo ADR-0021: 10/11 viventi** (era 5/11; resta dormiente solo `db.audit_log_write` replicato da trigger Postgres). 10 test caplog + 5 integration `asin_master`. 624 PASS (519 + 105). **Blocco `io_/extract` chiuso a livello primitive + telemetria; live adapters scope sessione dedicata.** | 0017, 0015, 0021, 0014, 0019 | [CHG-2026-05-01-005](changes/2026-05-01-005-asin-master-writer-and-telemetry.md) | `8316ee4` |
| **🚀 Fallback chain orchestratrice (Fase 1 Path B aperta): `src/talos/io_/fallback_chain.py` con `lookup_product(asin, *, keepa, scraper=None, page=None, ocr=None) -> ProductData`. Orchestra Keepa primario (3 `fetch_*` indipendenti, `KeepaMissError` → field=None + `notes` annotato) + AmazonScraper fallback opzionale su `buybox_eur`/`title` (invocato se entrambi `scraper` e `page` forniti); `KeepaRateLimitExceededError`/`KeepaTransientError` propagano (R-01 fail-fast). `OcrPipeline` parametro placeholder NON invocato in CHG-006 (test verifica meccanicamente). `ProductData` frozen + `sources: dict` audit trail field→canale + `notes: list` R-01 trail. Zero nuove deps, zero nuovi eventi canonici. Tutto mock-testabile senza setup di sistema (no Chromium / Tesseract / Keepa API key). 15 test unit (2 schema + 2 keepa-success + 2 keepa-miss + 2 propagation + 6 scraper-fallback + 1 asin propagation). **639 PASS** (534 + 105). | 0017, 0014, 0019 | [CHG-2026-05-01-006](changes/2026-05-01-006-fallback-chain-orchestratrice.md) | `0c9b93a` |
| **🔧 Quick win Fase 1: `SamsungExtractor.match(*, asin: str | None = None)` propaga l'asin reale al campo `extra["asin"]` di `extract.kill_switch` (catalogo ADR-0021). Backward compat strict (default None → sentinel `<n/a>` preservato come CHG-005). Pronto per Fase 3 integratore: `lookup_product` (CHG-006) saprà passare `product.asin` a `match()`. 2 test caplog nuovi + 1 asserzione aggiunta sul test esistente. **641 PASS** (536 + 105). | 0017, 0021, 0014, 0019 | [CHG-2026-05-01-007](changes/2026-05-01-007-samsung-extractor-asin-kwarg.md) | `45fac4b` |
| **🔗 Bridge `ProductData → AsinMasterInput` + sentinella e2e mock-only: `build_asin_master_input(product_data, *, brand, enterprise=False, samsung_entities=None, title_fallback=None, category_node=None) -> AsinMasterInput` chiude il loop "io_/ → extract/ → DB". Title precedence `product_data.title` > `title_fallback` > `ValueError` (R-01 NO SILENT DROPS, `AsinMaster.title` NOT NULL). `enterprise` caller prevale (dual-SKU Samsung non affidabile da NLP titolo). Sentinella e2e: `lookup_product` → `parse_title` → `build_asin_master_input` → `upsert_asin_master` → query DB (mock Keepa+Scraper, Postgres reale). Second-pass test verifica merge `COALESCE` D5.b preserva valori esistenti con `samsung_entities=None`. 8 test unit + 2 test integration. **651 PASS** (544 + 107). | 0017, 0015, 0014, 0019 | [CHG-2026-05-01-008](changes/2026-05-01-008-bridge-product-data-asin-master-input.md) | `1e57c10` |
| **📦 Bulk wrapper `lookup_products(asin_list, *, keepa, scraper=None, page=None, ocr=None) -> list[ProductData]` come list-comprehension su `lookup_product`. R-01 fail-fast su `KeepaRateLimitExceededError`/`KeepaTransientError`/errori live `page.goto`; `KeepaMissError` e `SelectorMissError` restano gestiti dentro `lookup_product` (field=None + notes). Empty list → no-op. Scraper+page condivisi fra chiamate (riuso context Chromium Fase 3). 4 test unit. **655 PASS** (548 + 107). | 0017, 0014, 0019 | [CHG-2026-05-01-009](changes/2026-05-01-009-lookup-products-bulk.md) | `1a9369d` |
| **🎯 Fase 1 Path B CHIUSA: `src/talos/extract/acquisition.py` con `acquire_and_persist(asin_list, *, db, keepa, brand, enterprise=False, scraper=None, page=None, extractor=None, title_fallbacks=None, category_node=None) -> list[str]`. Orchestratore Fase 1: `lookup_products` → (parse_title opzionale) → `build_asin_master_input` → `upsert_asin_master`. Pattern Unit-of-Work (caller commits). Empty list = no-op; ValueError fail-fast su title None senza fallback. 5 test integration sentinelle (empty / batch round-trip 3 ASIN Galaxy S24/A55/Z Fold5 / title_fallback usato / ValueError + rollback / no-extractor preserva nullable). **660 PASS** (548 + 112). | 0017, 0015, 0014, 0019 | [CHG-2026-05-01-010](changes/2026-05-01-010-acquire-and-persist-orchestrator.md) | `e425d14` |

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
| ~~CHG-048~~ | ~~UI pre-save duplicate check (find_session_by_hash integration)~~ | Chiuso 2026-04-30 — 430 PASS, UX duplicate-aware | — |
| ~~CHG-049~~ | ~~telemetria vgp.veto_roi_failed/kill_switch_zero/panchina.archived~~ | Chiuso 2026-04-30 — 438 PASS, catalogo 4/10 eventi viventi | — |
| ~~MILESTONE-1.2.0~~ | ~~`milestone/crud-and-telemetry-v1.2.0`~~ | Creato e pushato su `6654795`. Restore point CRUD+telemetria | — |
| ~~CHG-050~~ | ~~config_overrides runtime + UI persistente soglia ROI~~ | Chiuso 2026-04-30 — 445 PASS, configurabilità persistente | — |
| ~~CHG-051~~ | ~~Referral_Fee per categoria L12~~ | Chiuso 2026-04-30 — 452 PASS, lookup persistente per categoria | — |
| ~~CHG-052~~ | ~~load_session_full round-trip SessionResult~~ | Chiuso 2026-04-30 sera — 460 PASS, CRUD-light READ canonico | — |
| ~~CHG-053~~ | ~~orchestrator referral_fee_overrides + lookup hierarchy~~ | Chiuso 2026-04-30 sera — 467 PASS, L12 chiusa lato pipeline | — |
| ~~CHG-054~~ | ~~delete_config_override + UI Reset~~ | Chiuso 2026-04-30 sera — 475 PASS, triade CRUD config_overrides chiusa | — |
| ~~CHG-055~~ | ~~build_session_input wires overrides UI→orchestrator~~ | Chiuso 2026-04-30 sera — 478 PASS, loop CFO→DB→UI→orchestrator chiuso | — |
| ~~CHG-056~~ | ~~replay_session what-if su SessionResult ricaricato~~ | Chiuso 2026-04-30 sera — 484 PASS, primo consumer reale load_session_full | — |
| ~~CHECKPOINT-10~~ | ~~Tag `checkpoint/2026-04-30-10`~~ | Creato e pushato su `1c2631c`. Finestra: CHG-052..056 | — |
| ~~CHG-057~~ | ~~UI try_replay_session + sub-expander what-if~~ | Chiuso 2026-04-30 sera — 487 PASS, consumer visivo replay_session | — |
| ~~CHG-058~~ | ~~telemetria session.replayed (errata ADR-0021)~~ | Chiuso 2026-04-30 sera — 489 PASS, catalogo 5/11 viventi | — |
| ~~CHG-059~~ | ~~UI compare_session_kpis side-by-side originale/replay~~ | Chiuso 2026-04-30 sera — 494 PASS, pattern UX what-if comparison | — |
| ~~CHG-2026-05-01-001~~ | ~~KeepaClient skeleton (ADR-0017 canale 1)~~ | Chiuso 2026-05-01 — 516 PASS (+22), inaugura `src/talos/io_/`. Primo CHG del blocco `io_/extract` Samsung (4-5 attesi). | — |
| ~~CHG-2026-05-01-002~~ | ~~AmazonScraper skeleton (ADR-0017 canale 2)~~ | Chiuso 2026-05-01 — 550 PASS (+34), aggiunge scraping Playwright skeleton + `selectors.yaml` versionato. 2/5 blocco `io_/extract`. | — |
| ~~CHG-2026-05-01-003~~ | ~~OcrPipeline skeleton (ADR-0017 canale 3)~~ | Chiuso 2026-05-01 — 578 PASS (+28), aggiunge Tesseract OCR skeleton + Otsu pure-numpy. 3/5 blocco `io_/extract`. | — |
| ~~CHG-2026-05-01-004~~ | ~~SamsungExtractor + R-05 KILL-SWITCH (ADR-0017 + ADR-0018)~~ | Chiuso 2026-05-01 — 609 PASS (+31), inaugura `src/talos/extract/` + whitelist YAML + R-05 hard su model mismatch. 4/5 blocco `io_/extract`. |
| ~~CHG-2026-05-01-005~~ | ~~asin_master_writer UPSERT + telemetria 5 eventi attivati~~ | Chiuso 2026-05-01 — 624 PASS (+15), 10/11 catalogo viventi, blocco `io_/extract` chiuso 5/5 a livello primitive + telemetria. |
| ~~CHG-2026-05-01-006~~ | ~~Fallback chain orchestratrice `lookup_product` (Fase 1 Path B)~~ | Chiuso 2026-05-01 — 639 PASS (+15). Path B sequenza 3 fasi: Fase 1 mock-only ✓, Fase 2 installazioni di sistema (apt/playwright/keepa key) in sospeso, Fase 3 live adapters + 5 decisioni Leader pre-flight. |
| ~~CHG-2026-05-01-007~~ | ~~Quick win Fase 1: `SamsungExtractor.match(asin=...)` kwarg per telemetria R-05~~ | Chiuso 2026-05-01 — 641 PASS (+2). Backward compat strict, sentinel `<n/a>` preservato senza kwarg. |
| ~~CHG-2026-05-01-008~~ | ~~Bridge `ProductData → AsinMasterInput` + sentinella e2e mock-only~~ | Chiuso 2026-05-01 — 651 PASS (+10: +8 unit + +2 integration). Loop io_/→extract/→DB chiuso a livello primitive; sentinella ancora il flusso per Fase 3. |
| ~~CHG-2026-05-01-009~~ | ~~Bulk wrapper `lookup_products`~~ | Chiuso 2026-05-01 — 655 PASS (+4 unit). Helper sequenziale fail-fast per N ASIN; pronto per CHG-010 orchestratore. |
| ~~CHG-2026-05-01-010~~ | ~~Orchestratore Fase 1 `acquire_and_persist` — Fase 1 Path B chiusa~~ | Chiuso 2026-05-01 — 660 PASS (+5 integration). 🎯 Fase 1 Path B chiusa 5/5 (CHG-006..010). Pronto per checkpoint + Fase 2 (installazioni di sistema). |
| ~~CHECKPOINT-12~~ | ~~Tag `checkpoint/2026-05-01-12`~~ | Creato e pushato su `e7d42e4`. Finestra: CHG-006..010 (Fase 1 Path B chiusa). 660 PASS (era 624 a checkpoint-11, +36). |
| ~~CHG-2026-05-01-011~~ | ~~`_LiveTesseractAdapter` live + bug fix R-01 OcrPipeline (Fase 3 aperta 1/3)~~ | Chiuso 2026-05-01 — 663 PASS (+3 netto: +4 live integration, −1 legacy unit). Sbloccato da apt tesseract Leader. Bug fix `has_text` evita OK su rumore puro. |
| ~~CHG-2026-05-01-012~~ | ~~`_PlaywrightBrowserPage` live + decisioni Leader A/B/B (Fase 3 2/3)~~ | Chiuso 2026-05-01 — 660 PASS + 6 skipped (netto: −3 unit legacy, +6 integration skipped). Codice live ratificato; 6 test integration in attesa di `sudo playwright install-deps chromium` (system libs libnspr4/libnss3/etc.). |
| ~~CHG-2026-05-01-013~~ | ~~Scraper BSR multi-livello generalizzato (chiude gap Path B scraping-only)~~ | Chiuso 2026-05-01 — 681 PASS + 6 skipped (+21 unit). `BsrEntry(category, rank)` + `bsr_chain: list[BsrEntry]` ordinata specifico→ampio. Generalizza qualsiasi gerarchia Amazon. Path B scraping-only ~92-94% utilizzabile senza Keepa. |
| ~~TEST-DEBT-001~~ | ~~`sudo playwright install-deps chromium` (system libs libnspr4/libnss3/etc.)~~ | Chiuso 2026-05-01 — system libs installate Leader-side. 6 test live `test_live_playwright.py` ora PASS. + fix encoding `data:text/html;charset=utf-8,...` (Chromium leggeva data URL come latin1, € → â‚¬). |
| ~~TEST-DEBT-002~~ | ~~Test live `AmazonScraper.scrape_product` su HTML Amazon.it reale~~ | Chiuso 2026-05-01 — smoke 1-shot diagnostico su B0CSTC2RDW (Samsung S24 reale): 2 fix emersi e applicati: (1) rimosso selettore non-standard `:-soup-contains` (BeautifulSoup pseudo, non valido in Chromium); (2) selettori BSR allineati a layout Amazon.it 2025 (`table.a-keyvalue.prodDetTable tr td ul.a-unordered-list li`); (3) `_resolve_bsr_chain` simmetrico + sort `key=rank` asc (più basso = più specifico). Output live: title + buybox 549.00 EUR + bsr_chain[Cellulari(162), Elettronica(6182)] tutto OK. |
| ~~TEST-DEBT-003~~ | ~~Smoke test UI Streamlit live in browser~~ | Chiuso 2026-05-01 al ~80% — server Streamlit avviato OK su port 8502, `/_stcore/health` "ok", root HTTP 200, no traceback nei log. Validazione "% interazione utente reale" residua (CSV upload, click "Esegui", visualizzazione metric/tabelle) richiede browser reale dal Leader. |
| ~~CHG-2026-05-01-014~~ | ~~`TalosSettings.env_file=".env"` + .env.example + .gitignore secrets~~ | Chiuso 2026-05-01 round 4 — 690 PASS (+3). Sblocca caricamento Keepa key consegnata Leader. | — |
| ~~CHG-2026-05-01-015~~ | ~~`_LiveKeepaAdapter` live + decisioni A2/A/α''~~ | Chiuso 2026-05-01 round 4 — 693 PASS (+3 netto). Canale 1 Keepa live ratificato. ~4 token quota consumati. | — |
| ~~CHG-2026-05-01-016~~ | ~~`extract/asin_resolver.py` skeleton — apertura blocco descrizione→ASIN~~ | Chiuso 2026-05-01 round 4 — 713 PASS (+20). Mock-testable, decisioni Leader 1-5 ratificate. CHG-017+ live adapters. | — |
| ~~CHG-2026-05-01-017~~ | ~~`io_/serp_search.py` Amazon SERP scraping live~~ | Chiuso 2026-05-01 round 4 — 727 PASS (+18: 17 unit + 1 live Amazon.it). Selettori SERP 2026 ratificati live su "Galaxy S24". | — |
| ~~CHG-2026-05-01-018~~ | ~~`_LiveAsinResolver` composer end-to-end~~ | Chiuso 2026-05-01 round 4 — 740 PASS (+13: 12 unit + 1 live e2e). Galaxy S24 256GB @ €549 risolto live, ~3 token Keepa. 5° CHG significativo round 4 → checkpoint-14 creato. | — |
| ~~CHG-2026-05-01-019~~ | ~~`description_resolutions` cache + repository UPSERT (4/5 asin_resolver)~~ | Chiuso 2026-05-01 round 4 — 749 PASS (+10 integration). Decisioni α=A/β=A/γ=A ratificate Leader. Drift `idx_config_unique` ORM corretto come bonus. | — |
| ~~CHECKPOINT-14~~ | ~~Tag `checkpoint/2026-05-01-14`~~ | Creato e pushato su `162afed`. Finestra: CHG-014..018 (5 CHG round 4). | — |
| ~~CHG-2026-05-01-020~~ | ~~UI Streamlit rifondata: flow descrizione+prezzo (5/5 asin_resolver)~~ | Chiuso 2026-05-01 round 4 — 773 PASS (+24 unit). Decisione δ=A convivenza ratificata. **MVP CFO target raggiunto**. milestone v1.3.0 candidato. | — |
| ~~TEST-DEBT-004~~ | ~~Test live `_LiveKeepaAdapter` + mapping CSV indici Keepa~~ | Chiuso 2026-05-01 round 4 con CHG-015. Mapping ratificato post-diagnostic empirico (BUY_BOX_SHIPPING assente sul piano → NEW hierarchy; pickAndPackFee ≠ L11b → α'' fallback formula manuale). | — |
| POLICY-001 | Velocity F4.A: decisione Leader "quale livello `bsr_chain` usare" | Default attuale: `bsr_chain[0]` (più specifico) se `bsr` scalare miss da Keepa. Refactor formula per scegliere fra livelli = decisione Leader pendente. | — |
| ~~CHG-2026-05-01-005~~ | ~~asin_master_writer UPSERT merge + telemetria 5 eventi canonici attivati~~ | Chiuso 2026-05-01 — 624 PASS (+15), chiude blocco `io_/extract` 5/5 a livello primitive + telemetria. Catalogo ADR-0021 10/11 viventi. Live adapters scope sessione dedicata. | — |
| ~~CHECKPOINT-11~~ | ~~Tag `checkpoint/2026-05-01-11`~~ | Creato e pushato su `9338665` (sha tag `2dae62c`). Finestra: CHG-2026-05-01-001..005. | — |
| **NEXT** | **Prossimi step possibili** | Configurabilità aperta | (e) **lookup `Referral_Fee` per categoria** (estensione config_repository con `set/get_text` o numeric per categoria — pattern testato); (β) `upsert_session` decisione Leader semantica; (z) migrazione a `structlog.bind(session_id, tenant_id)` context tracing; (q) refactor UI multi-page ADR-0016; (r) **`io_/extract` Samsung** (Playwright + Tesseract + Keepa) — last big block; (s) golden Samsung 1000 ASIN; (y) `load_session_full`; chiusi: (a/a'/a''/b/b''/c/d/d'/f/g/h/i/j/k/l/m/n/p/t/u/v/x/α) |
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

### 🔄 Handoff sessione 2026-04-30 PM (post `45b4757` + handoff governance)

> **Per il prossimo Claude.** La sessione PM 2026-04-30 ha macinato **18 CHG consecutivi (034..051)**. Lo stato attuale e' radicalmente diverso da quello descritto sopra (pre-sessione). Leggi questo blocco **come priorita'** dopo Self-Briefing.

- **Stima MVP refresh (post CHG-051): ~88-92%** verso build CFO produttivo (era ~30-35% pre-sessione). Memory aggiornata: `memory/project_mvp_progress_estimate.md`.
- **Catena CHG-034..051**: vettoriale VGP + Tetris + formule + orchestrator + UI MVP + persistenza CRUD-light + idempotency + UX duplicate-aware + telemetria 4/10 + L10/L12 chiuse. Memory: `memory/project_session_handoff_2026-04-30-pm.md` (decisioni Leader, bug fix nascosti, prossimi step in priorita').
- **Decisione Leader CHG-039 (gap ADR orchestrator)**: ratificata **opzione A** = file top-level `src/talos/orchestrator.py` (no directory). NON aprire un `orchestrator/` cluster senza riautorizzazione.
- **Prossimo step strategico atteso**: **`io_/extract` Samsung** — ADR-0017 (Playwright + Tesseract + Keepa + NLP filter R-05). E' BIG, 4-5 CHG, **richiede sessione dedicata**. Non iniziarla come "9o CHG di una mega-sessione". Sblocca 4 eventi canonici dormienti del catalogo ADR-0021.
- **Alternative per scope contenuto** (in ordine di valore): (β) `upsert_session` decisione Leader semantica (delete-recreate vs update-only); (γ) integrazione orchestrator + Referral_Fee per categoria (post io_/extract); (y) `load_session_full`; (z) migrazione `structlog.bind` context tracing; (q) refactor UI multi-page ADR-0016.
- **Pattern operativi imparati durante la sessione (rispettare per coerenza)**:
  1. **Graceful degrade UI**: `fetch_*_or_none`/`fetch_*_or_empty` catturano `Exception` generico → `None`/`{}`.
  2. **Unit-of-Work**: i repository (`save_session_result`, `set_config_override_*`) NON committano. Caller via `session_scope`.
  3. **Stringhe letterali per eventi canonici** (es. `"tetris.skipped_budget"`): governance test fa grep, costanti importate non lasciano traccia.
  4. **CHAR(10) padding ASIN**: confronti su `vgp_result.asin` falliscono senza `.strip()`. Quirk Postgres documentato.
  5. **`_listino_hash` privato importato dalla UI**: deroga consapevole (UI + repository sono "di sessione").
- **3 bug fix nascosti durante la sessione (per allerta)**:
  1. CHG-041: `allocate_tetris` Pass 2 ora skippa `qty_final=0` (era no-op visivo). Sentinella in golden test.
  2. CHG-046: `test_log_events_catalog` regex `^\s*continue\b` aveva `re.MULTILINE` mancante. Bug latente da CHG-006.
  3. CHG-050: `idx_config_unique` UNIQUE NULL handling: migration `e8b80f77961b` ricrea con `NULLS NOT DISTINCT` (Postgres 15+).
- **Quality gate al termine sessione**: 380 unit/gov/golden + 72 integration = **452 PASS**, ruff/mypy strict puliti.
- **Tag**: 4 milestone (`stack-frozen-v0.9.0`, `first-formula-v1.0.0`, `pipeline-e2e-v1.1.0`, `crud-and-telemetry-v1.2.0`) + 9 checkpoint.
- **Indice GitNexus stale ~50 commit** al termine sessione → `npx -y gitnexus analyze` (Node v22) come prima azione operativa post-briefing.
- **Container Postgres**: `talos-pg-test` postgres:16-alpine host:55432 tmpfs. Migrations head: `e8b80f77961b`.
- **Memory utili da consultare**: `feedback_concisione_documentale.md`, `project_f1_referral_structure_confirmed.md`, `project_mvp_progress_estimate.md` (refresh PM), `project_session_handoff_2026-04-30-pm.md` (questa sessione).

### 🔄 Handoff sessione 2026-04-30 sera (post `3550027` — CHG-052..059 + checkpoint-10)

> **Per il prossimo Claude (post `/clear`).** La sessione sera 2026-04-30 ha macinato **8 CHG consecutivi (052..059)** in autorizzazione "macina" del Leader. Lo stato è ulteriormente avanzato rispetto al blocco PM sopra. Leggi questo blocco **insieme** al PM, in ordine: prima PM (catena 034..051), poi questo (catena 052..059).

- **Stima MVP refresh (post CHG-059): ~90-94%** verso build CFO produttivo. Memory: `project_mvp_progress_estimate.md` (aggiornato sera). Delta marginale rispetto al PM perché i loop UI/CRUD non aumentano il "% verso produzione reale", aumentano solo la qualità/usabilità del flusso esistente. **`io_/extract` resta il blocco strategico singolo (~19% MVP produttivo, 0% completato).**
- **Modalità "macina" del Leader era una clausola di sessione**: *"NON salvarla come memory feedback. Default ADR-0002 (permesso esplicito) resta valido nelle prossime sessioni."* → **default ADR-0002 reattivato dalla sessione successiva**. Permesso esplicito Leader prima di ogni commit.
- **Catena CHG-052..059** (memory: `project_session_handoff_2026-04-30-evening.md` — leggi PRIMA di proporre next):
  - **CHG-052** `4c710ea`: `load_session_full(db, sid, *, tenant_id)` round-trip canonico SessionResult da DB
  - **CHG-053** `1178389`: orchestrator `referral_fee_overrides` + `_resolve_referral_fee` lookup hierarchy (chiude L12 lato pipeline)
  - **CHG-054** `9a3b0c3`: `delete_config_override` + UI bottoni Reset (triade CRUD config_overrides chiusa)
  - **CHG-055** `d8f74c1`: `build_session_input(factory, listino_raw, ...)` UI wiring (loop CFO→DB→UI→orchestrator chiuso)
  - **CHG-056** `e7c2666`: `replay_session(loaded, *, locked_in_override, budget_override)` what-if (no re-enrichment)
  - **`checkpoint/2026-04-30-10`** su `1c2631c`
  - **CHG-057** `92bd63b`: UI `try_replay_session` + sub-expander "What-if Re-allocate"
  - **CHG-058** `a40b825`: telemetria `session.replayed` (errata catalogo ADR-0021, ora 5/11 viventi)
  - **CHG-059** `3550027`: UI `compare_session_kpis` side-by-side originale vs replay con delta
- **Quality gate baseline al re-entry (HEAD `2b8d99c` post-backfill)**:
  - **494 PASS** (394 unit/gov/golden + 100 integration)
  - ruff/format/mypy strict puliti, working tree clean, push aggiornato
  - Container Postgres `talos-pg-test` UP al close (8h). Se DOWN al re-entry: `docker run -d --rm --name talos-pg-test -e POSTGRES_PASSWORD=test -p 55432:5432 --tmpfs /var/lib/postgresql/data postgres:16-alpine && sleep 3 && TALOS_DB_URL='postgresql+psycopg://postgres:test@localhost:55432/postgres' uv run alembic upgrade head`
  - **Indice GitNexus stale ~22 commit** → `npx -y gitnexus analyze` Node v22 come prima azione operativa post-briefing
  - **Tag**: 4 milestone + 10 checkpoint
- **Pattern operativi NUOVI introdotti (rispettare per coerenza, dettagli in memory sera)**:
  1. **Drift Decimal→float documentato come tolerance**: Numeric(12,4) round-trip `<1 EUR` su budget. Test usano `abs(...) < tolerance`, no byte-exact.
  2. **Pre-check + execute** invece di `Result.rowcount` (mypy strict): `select(.id) → if None: return False; else: execute → return True`. Estendere a futuri DELETE.
  3. **`x or None`** normalizza dict vuoto a None esplicito (intent più chiaro).
  4. **NaN come placeholder type-safe**: `float("nan")` per campi non persistiti (vs `None` che richiede union types).
  5. **Lazy import** per spezzare cicli `persistence ↔ orchestrator ↔ tetris` (pattern coerente con orchestrator).
  6. **Helper UI puri testabili senza Streamlit**: ogni helper UI con logica derivativa = funzione pura + test unit (no `streamlit` import nei test).
  7. **Errata corrige additiva ammessa per cataloghi** (CHG-058 ADR-0021): aggiungere voce non altera semantica esistenti, no supersessione.
- **6 bug fix nascosti sera (per allerta, dettagli in memory sera)**:
  1. CHG-052 tolerance test inizialmente troppo strette (`1e-6` per drift `1e-5`).
  2. CHG-054 mypy `Result.rowcount` non tipato → refactor a pre-check.
  3. CHG-055 ruff FURB110: `x if x else None` → `x or None`.
  4. CHG-058 governance test catalogo: stringa letterale obbligatoria (no costante).
  5. CHG-059 mypy `sum(genexpr)` "expected bool" → loop esplicito + isinstance narrow.
  6. CHG-059 line length f-string >100 char → variabile separata.
- **Catalogo eventi canonici ADR-0021 (errata CHG-058)**: ora 5/11 viventi (`tetris.skipped_budget`, `vgp.veto_roi_failed`, `vgp.kill_switch_zero`, `panchina.archived`, `session.replayed`). 6 dormienti si attiveranno con i rispettivi moduli (`io_/extract` ne attiva 4: `extract.kill_switch`, `keepa.miss`, `keepa.rate_limit_hit`, `scrape.selector_fail`, `ocr.below_confidence`).
- **🚨 PROSSIMO BLOCCO STRATEGICO ATTESO: `io_/extract` Samsung (ADR-0017)** — sessione dedicata, 4-5 CHG. **5 decisioni di sostanza Leader pre-flight obbligatorie** (eccezione 2 ADR-0002), formula come opzioni A/B/C e attendi prima di toccare codice:
  1. **Keepa client** (`io_/keepa_client.py`): API key da `TalosSettings.keepa_api_key`? rate-limit strategy (token bucket vs rolling window)? retry/circuit breaker? cache locale (sqlite/parquet) + TTL?
  2. **Playwright** (`io_/scraper.py`): browser engine? user-agent rotation? cookie persistence? selector strategy con fallback chain (CSS → XPath → aria)? login Amazon (rischio TOS)?
  3. **Tesseract OCR** (`io_/ocr.py`): lingua (`-l ita+eng`)? image preprocessing (deskew, threshold, dpi)? soglia confidence per `ocr.below_confidence`? PDF Samsung via pdftoppm o tesseract diretto?
  4. **NLP filter R-05** (`extract/samsung.py`): regex set rule-based vs spaCy modello italiano vs custom? confidence soglia? `extract.kill_switch` event obbligatorio (catalogo ADR-0021).
  5. **`asin_master` populator** (`extract/asin_master_writer.py`): UPSERT `ON CONFLICT (asin) DO UPDATE` o pre-check? conflict resolution (overwrite/ignore/merge)? trigger audit (CHG-018)?
- **Memory aggiunta sera**: `project_session_handoff_2026-04-30-evening.md` (questa sessione, leggere DOPO il PM e PRIMA di proporre next).

### 🔄 Handoff sessione 2026-05-01 (post `847179a` — CHG-2026-05-01-001..005 + checkpoint-11 — blocco `io_/extract` chiuso 5/5 a livello primitive + telemetria)

> **Per il prossimo Claude (post `/clear`).** La sessione 2026-05-01 ha macinato **5 CHG consecutivi (001..005)** in autorizzazione "macina" del Leader (clausola di sessione, riautorizzata oltre mezzanotte da 2026-04-30 sera). Il blocco strategico `io_/extract` Samsung e' chiuso 5/5 **a livello primitive + telemetria**. I live adapters restano skeleton e richiedono sessione dedicata con setup di sistema. Leggere questo blocco **DOPO** PM e sera 2026-04-30 (ordine cronologico di catena).
>
> **CRITICO**: la **modalità "macina" NON persiste** automaticamente fra sessioni. La prossima sessione torna a default ADR-0002 (permesso esplicito Leader pre-commit) salvo riautorizzazione esplicita.

- **Stima MVP refresh (post checkpoint-11)**: due metriche distinte (memory `project_mvp_progress_estimate.md` aggiornata):
  - **Path A — CFO con CSV strutturato manuale**: **~95%** (tutto funziona end-to-end con CSV preparato a monte).
  - **Path B — CFO end-to-end con acquisizione automatica (PDF Samsung -> carrello)**: **~78%** (mancano i live adapters + fallback chain integratrice = ~22%).
  - **Stima media pesata onesta**: **~85%**. Quando il Leader chiede progresso, **chiedere quale Path e' il MVP target** prima di dichiarare un numero unico (decisione Leader pendente).
- **Catena CHG-2026-05-01-001..005** (memory: `project_session_handoff_2026-05-01.md` — leggi PRIMA di proporre next):
  - **CHG-001** `4bb7e9b`: `KeepaClient` skeleton + rate limit `pyrate-limiter` + retry `tenacity` + R-01 errori espliciti. Settings `keepa_api_key` + `keepa_rate_limit_per_minute`. Deps `keepa>=1.4`, `tenacity>=8`, `pyrate-limiter>=3`.
  - **CHG-002** `ba2421c`: `AmazonScraper` skeleton + `selectors.yaml` versionato + `parse_eur` italiano/anglo + CSS->XPath fallback (D2.a). `_PlaywrightBrowserPage` skeleton. Deps `playwright>=1.40`, `pyyaml>=6` + dev `types-PyYAML`.
  - **CHG-003** `1da38b0`: `OcrPipeline` skeleton + Otsu pure-numpy (D3.b) + soglia AMBIGUOUS configurabile + `OcrStatus` StrEnum + `_LiveTesseractAdapter` skeleton. Dep `pytesseract>=0.3.13` + mypy override `ignore_missing_imports`. Settings `ocr_confidence_threshold` validator [0,100].
  - **CHG-004** `2140ab4`: `SamsungExtractor` + R-05 KILL-SWITCH HARDWARE. Inaugura `src/talos/extract/`. NLP regex + `rapidfuzz` (D4.a) + `samsung_whitelist.yaml` (D4.b: 20 modelli 5G + 17 colori) + weighted sum confidence (D4.c). Dep `rapidfuzz>=3,<4`.
  - **CHG-005** `8316ee4`: `asin_master_writer` UPSERT merge (D5: `pg_insert.on_conflict_do_update` + `COALESCE` su nullable + `last_seen_at = NOW()` + no audit trigger). Telemetria 5 eventi canonici dormienti -> attivati ai siti di produzione nei 4 moduli skeleton (`keepa.miss`, `keepa.rate_limit_hit`, `scrape.selector_fail`, `ocr.below_confidence`, `extract.kill_switch`). **Catalogo ADR-0021 ora 10/11 viventi** (resta dormiente solo `db.audit_log_write` replicato da trigger Postgres).
  - **`checkpoint/2026-05-01-11`** su `9338665` (sha tag `2dae62c`).
- **Quality gate baseline al re-entry (HEAD `847179a` post-checkpoint commit)**:
  - **624 PASS** (519 unit/gov/golden + 105 integration)
  - ruff/format/mypy strict puliti, working tree clean, push aggiornato
  - Container Postgres `talos-pg-test` UP a fine sessione. Se DOWN al re-entry: `docker run -d --rm --name talos-pg-test -e POSTGRES_PASSWORD=test -p 55432:5432 --tmpfs /var/lib/postgresql/data postgres:16-alpine && sleep 3 && TALOS_DB_URL='postgresql+psycopg://postgres:test@localhost:55432/postgres' uv run alembic upgrade head`
  - **Indice GitNexus stale ~11 commit** -> `npx -y gitnexus analyze` (Node v22) come prima azione operativa post-briefing
  - **Tag**: 7 milestone + 11 checkpoint
- **Pattern operativi NUOVI introdotti (rispettare per coerenza)**:
  1. **Adapter Pattern + Protocol per ogni libreria esterna**: `KeepaApiAdapter`, `BrowserPageProtocol`, `TesseractAdapter`. Test mockano l'adapter; runtime usa skeleton `_LiveXxxAdapter` che lancia `NotImplementedError` con messaggio esplicito che cita CHG atteso + setup di sistema richiesto.
  2. **`_LiveXxxAdapter` skeleton come pattern R-01**: NO silent fallback. Lancia `NotImplementedError` con TODO esplicito.
  3. **TalosSettings cresce field-by-field per CHG**: ogni CHG che introduce config aggiunge un campo + validator. Coerente con CHG-029/030/031 (pattern preservato).
  4. **D5 merge con `COALESCE`**: pattern UPSERT per writer `INSERT ... ON CONFLICT DO UPDATE SET col = COALESCE(EXCLUDED.col, table.col)` per i campi nullable; NOT NULL = last-write-wins. Riusabile in altri writer futuri.
  5. **Sentinel `<no-html>`, `<image>`, `<n/a>` nei log telemetria**: quando un campo del catalogo non e' popolabile in CHG corrente, sentinel literal > campo mancante. Caller futuro puo' override con context completo.
  6. **Stringhe letterali per eventi canonici** (continua da CHG-046): `_logger.debug("event.name", extra={...})` con literal del catalogo (governance test grep). Costanti importate non lascerebbero traccia testuale.
- **6 bug fix nascosti durante la sessione (per allerta)**:
  1. CHG-001: `pyrate-limiter v4` API `try_acquire(name, blocking=False)` returns bool (non solleva BucketFullException). Adattato.
  2. CHG-001: scelta `Retrying` iteratore (parametri esposti via init constructor, zero-wait nei test) vs `@retry` decorator.
  3. CHG-002: ruff TC003 (move into TYPE_CHECKING) su `Callable`/`Decimal`. Risolto con block TYPE_CHECKING.
  4. CHG-003: governance test `test_no_silent_drops_under_src` su `ocr.py` ha rilevato `continue` (Otsu loop). Risolto menzionando `ocr.below_confidence` nel docstring.
  5. CHG-003: Otsu su immagine bimodale delta pura -> varianza costante in finestra [50..199]; il test aspettava `> 50` ma l'algoritmo prende il primo (50). Risolto con due test parametrici (delta puri + spread realistica).
  6. CHG-004: `_extract_rom` deve skippare i numeri seguiti da "RAM"; pattern `\d{2,4}\s?GB` + check `text[m.end():]`. Test end-to-end falliva con AMBIGUO se `amazon_title` non aveva keyword "RAM" (Amazon spesso la omette); workaround documentato (CHG futuro estendera' con dispatch "smaller=RAM larger=ROM").
- **Catalogo eventi canonici ADR-0021: 10/11 viventi** (era 5/11). Solo `db.audit_log_write` resta dormiente lato Python (replicato dai trigger PostgreSQL CHG-018, gia' attivo lato DB).
- **🚨 PROSSIMO BLOCCO STRATEGICO ATTESO: live adapters + fallback chain integratrice (sessione DEDICATA, fuori "macina")**. Il blocco `io_/extract` chiude a livello **primitive + telemetria**. La parte "live" richiede:
  1. **Setup di sistema preflight** (operazioni di sistema, NON banali):
     - `sudo apt install tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng` (binario di sistema)
     - `uv run playwright install chromium` (~150 MB Chromium)
     - Sandbox API key Keepa per ratificare mapping CSV indici (BUY_BOX_SHIPPING idx 18, SALES idx 3, fee_fba parsing dal `data` field)
  2. **5 decisioni Leader pre-flight** (eccezione 2 ADR-0002, formula come opzioni A/B/C):
     - `_LiveKeepaAdapter`: indici per `bsr` (`SALES` o `LISTING`?), parsing `fee_fba` dal piano subscription corrente, gestione missing fields
     - `_LiveTesseractAdapter`: dpi default `pdf2image`, concurrency limit per pagine PDF, encoding output (UTF-8 sicuro)
     - `_PlaywrightBrowserPage`: gestione cookie consenso GDPR Amazon, strategia stealth (anti-detection medium), timeout default per `goto`
     - **Fallback chain orchestratrice**: signature `lookup_product(asin, *, keepa, scraper, ocr) -> ProductData`, gestione `KeepaMissError -> SelectorMissError -> AMBIGUO + log`, integrazione con `SamsungExtractor.match` per filtro R-05, persistenza via `upsert_asin_master` (CHG-005)
     - **Golden fixtures**: dove salvare `tests/golden/html/amazon_*.html`, `tests/golden/pdf/listino_samsung_*.pdf`, `tests/golden/images/listino_*.png` + granularita' per ASIN
  3. **Estensione signature `SamsungExtractor.match(asin)`**: per popolare correttamente il campo `asin` dell'evento `extract.kill_switch` (in CHG-005 e' sentinel `<n/a>`).
- **Memory aggiunta in questa sessione**:
  - `project_io_extract_design_decisions.md` (D1-D5 default ratificate, aggiornata con stato "applicato" post-CHG-005)
  - `project_session_handoff_2026-05-01.md` (handoff completo, leggere DOPO PM e sera 2026-04-30)
  - `project_mvp_progress_estimate.md` (refresh con Path A/Path B distinti)

### 🔄 Handoff sessione 2026-05-01 round 4 (post `caa6d29` — **MVP CFO TARGET RAGGIUNTO** + blocco asin_resolver 5/5)

> **Per il prossimo Claude (post-`/clear`). RIPRENDI DA QUI.** La sessione round 4 ha macinato **7 CHG significativi (014..020)** in modalità "macina" ratificata Leader, post arrivo Keepa private API key. Blocco `asin_resolver` chiuso 5/5: il flusso "(descrizione, prezzo) → ASIN → classifica VGP" è end-to-end live. Memory dettagliata: `project_session_handoff_2026-05-01-round4.md` — leggi DOPO PM/sera/round 1/round 3 in ordine cronologico.

- **HEAD `caa6d29`**, branch `main`. **773 PASS, 0 SKIPPED** (640 + 133). Quality gate verde.
- **Tag round 4**: `checkpoint/2026-05-01-14` su `162afed` + 🚀 **`milestone/asin-resolver-v1.3.0`** su `caa6d29` (8° milestone, restore point blocco asin_resolver completo).
- **Catena CHG round 4**:
  - **CHG-014** `0127f61`: `TalosSettings.env_file=".env"` — sblocca caricamento Keepa key
  - **CHG-015** `bb5a9cd`: `_LiveKeepaAdapter` live — decisioni A2/A/α'' (BUY_BOX_SHIPPING assente sul piano, hierarchy NEW; pickAndPackFee ≠ L11b → α'' KeepaMiss sempre per preservare formula L11b Frozen)
  - **CHG-016** `b86baea`: `extract/asin_resolver.py` skeleton — tipi + Protocol + helper puri
  - **CHG-017** `467c713`: `io_/serp_search.py` SERP Amazon.it live — selettori `[data-component-type=s-search-result]` ratificati live
  - **CHG-018** `fd51e40`: `_LiveAsinResolver` composer — SERP top-N + lookup_product Keepa-only + rapidfuzz + compute_confidence. Test live e2e Galaxy S24 256GB Onyx PASS in 7.29s
  - **CHG-019** `f3b67e4`: `description_resolutions` cache (4° tabella post Allegato A) — α=A NO RLS / β=A UNIQUE tenant+hash / γ=A NO audit. Bonus: drift `idx_config_unique` ORM↔DB risolto
  - **CHG-020** `2886728`: UI rifondata — `st.radio` mode (δ=A convivenza) + `_render_descrizione_prezzo_flow` + helper puri `listino_input.py` testabili senza Streamlit
- **9 decisioni Leader ratificate round 4** (NON re-aprire senza istruzione esplicita): vedi memory `project_session_handoff_2026-05-01-round4.md` per dettaglio completo.
- **Quota Keepa consumata sessione**: ~9 token totali (4 test live keepa + 1 test live e2e + 2 diagnostic + ~2 verifiche).
- **Setup di sistema**: ✅ Tesseract / ✅ Chromium + libs / ✅ Keepa key in `.env` / ✅ Postgres `talos-pg-test` UP / ✅ Indice GitNexus refresh fine sessione.
- **MVP CFO TARGET RAGGIUNTO**: il CFO carica un listino fornitore "umano" (CSV `descrizione`+`prezzo`) → preview risoluzione con `confidence_pct` esposto per riga → conferma → classifica VGP completa con Cart/Panchina/Budget T+1. **Senza preprocessing manuale.**
- **Pattern operativi consolidati round 4**: mock-testable + 1 test live mirato post-adapter (lezione CHG-013); decisioni A/B/C con default proposto + ricalibratura empirica (es. fee_fba 3'→α''); R-01 multi-livello (tecnico + UX); helper puri in modulo separato + render Streamlit dedicato; lazy import per non penalizzare boot; `st.session_state` per stato multi-render; bonus correttivi durante CHG (drift `idx_config_unique`).
- **6 bug fix nascosti round 4** (per allerta — dettagli in memory): test_settings rotti da `.env` reale → fixture chdir; `BUY_BOX_SHIPPING` assente piano → A2 hierarchy; `pickAndPackFee` ≠ L11b → α'' policy; alembic spurio re-create → fix migration + ORM allineato; CHAR(10) overflow su asin test 11-char → 10-char; governance `keepa.miss` mancante in docstring → menzione esplicita.
- **Re-entry routine**:
  1. Self-Briefing standard (CLAUDE.md ADR-0010).
  2. Verificare container Postgres `talos-pg-test`. Se DOWN: `docker run -d --rm --name talos-pg-test -e POSTGRES_PASSWORD=test -p 55432:5432 --tmpfs /var/lib/postgresql/data postgres:16-alpine && sleep 3 && TALOS_DB_URL='postgresql+psycopg://postgres:test@localhost:55432/postgres' uv run alembic upgrade head`.
  3. ⚠️ **Modalità "macina" round 4 NON persiste**: prossima sessione = default ADR-0002.
  4. ⚠️ **Keepa key esposta nel transcript di questa sessione** (presente in `.env` locale gitignored). Best practice: rotala quando puoi (non urgente).
- **Aperti / scope futuro**: TEST-DEBT-003 smoke browser umano (~80% chiuso); POLICY-001 Velocity policy `bsr_chain`; override candidato manuale UI; `verified_buybox_eur` distinto da `cost_eur`; refactor multi-page Streamlit; telemetria `cache.hit/miss`/`asin_resolver.*`; cache TTL `description_resolutions`.

### 🔄 Handoff sessione 2026-05-01 round 3 (post `3b62bfd` — Fase 3 Path B 2/3 + smoke live)

> **Per il prossimo Claude (post `/clear`).** Riprendi da QUI. La sessione round 3 ha consolidato Fase 1 Path B (chiusa post CHG-010) e aperto Fase 3 Path B (2/3 live ratificati). Tutti i CHG sono in produzione, working tree clean, push aggiornato. **Memory dettagliata: `project_session_handoff_2026-05-01-round3.md`** — leggere DOPO PM/sera/round 1 in ordine cronologico.

- **HEAD `3b62bfd`**, branch `main`. **687 PASS, 0 SKIPPED** (565+122). Quality gate verde.
- **Tag `checkpoint/2026-05-01-13`** su `4691bd4` chiude round 3.
- **Catena CHG round 3**:
  - **CHG-006** `0c9b93a`: `lookup_product` fallback chain orchestratrice
  - **CHG-007** `45fac4b`: `SamsungExtractor.match(asin=...)` kwarg telemetria R-05
  - **CHG-008** `1e57c10`: `build_asin_master_input` bridge + sentinella e2e mock
  - **CHG-009** `1a9369d`: `lookup_products` bulk wrapper
  - **CHG-010** `e425d14`: `acquire_and_persist` orchestratore — **Fase 1 Path B chiusa**
  - **CHG-011** `001b066`: `_LiveTesseractAdapter` live + bug fix R-01 `OcrPipeline.has_text`
  - **CHG-012** `e553b5f`: `_PlaywrightBrowserPage` live + dep `playwright-stealth`
  - **CHG-013** `8ef6259`: scraper BSR multi-livello generalizzato (`BsrEntry` + `bsr_chain`)
  - 4 fix governance/post-live: `4691bd4` (data URL utf-8), `90e8600` (selettori BSR 2025 + sort)
- **Decisioni Leader ratificate**: Path B = MVP target; Cookie GDPR A; Stealth B medium (playwright-stealth 2.0.3); Timeout goto 60s; BSR generalizzato a qualsiasi gerarchia Amazon; sort `bsr_chain` per `rank` ascending = "specifico→ampio".
- **Setup di sistema completato Leader-side**:
  - ✅ Tesseract 5.3.4 (lingue ita+eng+osd)
  - ✅ Chromium binary `~/.cache/ms-playwright/chromium_headless_shell-1217/`
  - ✅ Chromium runtime libs (`libnspr4`/`libnss3`/etc.) — TEST-DEBT-001 chiuso
  - ❌ `TALOS_KEEPA_API_KEY` NOT_SET (Leader: in arrivo)
- **Test debt**: ~~001~~ ~~002~~ ~~003~~ chiusi (003 ~80%, residuo browser umano); 004 ⏳ Keepa key + POLICY-001 ⏳ Velocity bsr_chain.
- **5 bug emersi dai test live (i mock NON li avrebbero rilevati)**:
  1. `:-soup-contains` (BeautifulSoup) non valido in Chromium DOM → SyntaxError
  2. `data:text/html,...` interpretato come latin1 in Chromium → mojibake € → â‚¬
  3. Layout Amazon.it 2025: rank root + sub entrambi in `table.a-keyvalue.prodDetTable`, non in 2 sezioni separate
  4. Ordine HTML BSR: root prima di sub (richiesto sort `key=rank` asc)
  5. R-01 `OcrPipeline`: rumore puro → conf=95 con text vuoto → pre-fix dichiarava OK (fix `has_text` check)
- **Re-entry routine**:
  1. Self-Briefing standard (CLAUDE.md).
  2. Verificare container Postgres `talos-pg-test` (UP da 20h+; se DOWN, comando in handoff memory).
  3. ⚠️ **Modalità "macina" round 3 NON persiste**: prossima sessione = default ADR-0002 (permesso esplicito Leader pre-commit).
  4. Se Keepa key arriva: aprire CHG-014 `_LiveKeepaAdapter` (decisione Leader BSR Keepa idx 3 SALES vs altro pendente — default proposto SALES).
  5. Se Keepa NON arriva: Path B scraping-only e' utilizzabile live; prossimi candidati = POLICY-001 Velocity policy bsr_chain (½ sessione) oppure smoke browser umano UI Streamlit (validazione interazione utente reale, residuo TEST-DEBT-003).
- **Stima MVP onesta fine round 3**: Path A ~92% codice + ~88-90% validato; Path B ~95% codice + **~92-94% validato live**.

### 🔄 Aggiornamento sessione 2026-05-01 round 2 (Fase 1 Path B — fallback chain mock-only)

> **Per il prossimo Claude.** Round 2 della sessione 2026-05-01 (modalità "macina" riautorizzata Leader). Leader ha ratificato esplicitamente **Path B = MVP target** ("obiettivo prodotto funzionante"). Aperta **Fase 1 Path B**: tutto il valore architetturale producibile senza setup di sistema.

- **CHG-2026-05-01-006** `0c9b93a`: `src/talos/io_/fallback_chain.py` con `lookup_product(asin, *, keepa, scraper, page, ocr) -> ProductData`. Orchestra Keepa primario + Scraper fallback su buybox/title (OCR placeholder, non invocato in CHG-006). 15 test unit mock-only. **639 PASS**.
- **CHG-2026-05-01-007** `45fac4b`: `SamsungExtractor.match(*, asin: str | None = None)` kwarg propaga l'asin reale a `extract.kill_switch.extra["asin"]` (catalogo ADR-0021). Backward compat strict (default None → sentinel `<n/a>`). +2 test caplog. **641 PASS**.
- **CHG-2026-05-01-008** `1e57c10`: bridge `build_asin_master_input(product_data, *, brand, enterprise, samsung_entities, title_fallback, category_node) -> AsinMasterInput` + sentinella e2e mock-only. Loop "io_/ → extract/ → DB" chiuso a livello primitive. R-01 NO SILENT DROPS sul title (`ValueError` se entrambi None). +8 test unit + +2 integration. **651 PASS**.
- **CHG-2026-05-01-009** `1a9369d`: bulk wrapper `lookup_products(asin_list, ...)` list-comprehension su `lookup_product`. Fail-fast su rate-limit/transient. Empty list = no-op. +4 test unit. **655 PASS**.
- **CHG-2026-05-01-010** `e425d14`: 🎯 **Fase 1 Path B CHIUSA**. Orchestratore `acquire_and_persist(asin_list, *, db, keepa, brand, ...)` chiude il flusso `lookup_products` → parse_title → bridge → upsert. Pattern Unit-of-Work. 5 test integration sentinelle e2e. **660 PASS**.

**📊 Bilancio Fase 1 Path B (5 CHG, 006..010):**
- Tutto il valore architetturale producibile **senza setup di sistema** è in produzione.
- 660 PASS test totali (era 624 a checkpoint-11, +36).
- Loop completo: input N ASIN + Keepa client + opz. (Scraper, Page, Samsung extractor) → output N anagrafiche persistite su `asin_master` con merge `COALESCE` + audit trail (`sources`, `notes`).
- Sentinelle e2e mock-only ancorano il flusso per Fase 3 (i live adapter sostituiranno i mock via factory injection — codice applicativo invariato).
- Live adapter (`_LiveKeepaAdapter`, `_PlaywrightBrowserPage`, `_LiveTesseractAdapter`) restano skeleton (`NotImplementedError`).
- Catalogo eventi canonici ADR-0021: 10/11 viventi (invariato).
- Zero nuove deps applicative durante Fase 1.

**🚀 Prossimo blocco: Fase 2 Path B — installazioni di sistema (Leader pendente):**
- `sudo apt install tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng`
- `uv run playwright install chromium` (~150 MB)
- `TALOS_KEEPA_API_KEY` sandbox esportata in env
- 5 decisioni Leader pre-flight (formula come opzioni A/B/C, eccezione 2 ADR-0002): mapping CSV indici Keepa, dpi default OCR, GDPR cookie consent Playwright, fallback chain integrazione fine, golden fixtures location.
- **Sequenza Path B in 3 fasi (ratificata Leader 2026-05-01)**:
  - **Fase 1 — mock-only senza setup di sistema** (in corso): valore architetturale completo. Prossimo CHG candidato: estensione `SamsungExtractor.match(*, asin: str | None = None)` per popolare `extract.kill_switch.asin` reale (oggi sentinel `<n/a>`).
  - **Fase 2 — installazioni di sistema** (Leader pendente): `sudo apt install tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng` + `uv run playwright install chromium` (~150 MB) + sandbox `TALOS_KEEPA_API_KEY` esportata.
  - **Fase 3 — live adapters + integratore** (post Fase 2): completamento `_LiveKeepaAdapter` / `_PlaywrightBrowserPage` / `_LiveTesseractAdapter` + golden HTML/PDF/img + integration test live + 5 decisioni Leader pre-flight (mapping CSV indici Keepa, dpi default OCR, GDPR cookie consent, fallback chain integrazione fine, golden fixtures location). **Eccezione 2 ADR-0002**: decisioni formulate come opzioni A/B/C, attesa ratifica Leader prima di toccare codice live.
- **Indice GitNexus reindexato** a inizio sessione round 2 (Node v22.22.2): 3755 nodes / 4769 edges / 67 clusters / 8 flows. 2 warning innocui (`tests/golden/__init__.py` empty + `src/talos/ui/dashboard.py` parser glitch) — non bloccanti, candidati ISS futura.
- **Pattern operativi NUOVI introdotti in round 2 (rispettare per coerenza)**:
  1. **Composizione mock-testabile prima di live**: la fallback chain compone Protocol esistenti (KeepaApiAdapter / BrowserPageProtocol / TesseractAdapter). Test unit con mock di tutti i Protocol → zero dipendenza network/binari di sistema. Quando Fase 2 installa il setup, la chain non cambia: solo factory injection di `_LiveXxxAdapter`.
  2. **Parametri "placeholder signature compatibility"**: il parametro `ocr` di `lookup_product` e' accettato ma non invocato in CHG-006. Test meccanico verifica la non-invocazione (mock OCR che `AssertionError` se chiamato). Pattern utile per evolvere signature senza breaking change.
  3. **TypeVar PEP 484 modulo-level** (no PEP 695 `[T]`): Python 3.11 stack non supporta sintassi generic inline. Pattern `_T = TypeVar("_T")` modulo-level + annotazione esplicita `Callable[[str], _T]`.
- **Modalità "macina" round 2 NON persiste** automaticamente fra sessioni: prossima sessione torna a default ADR-0002 salvo riautorizzazione esplicita Leader.

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
