# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-04-30 — commit `02a8787` (CHG-011 listino_items + FK + relationship). Tag: `milestone/stack-frozen-v0.9.0` + `checkpoint/2026-04-30-01`. Catena CHG odierna: 001→002→003→004→005→006→007→008→009→010→011. Tabelle Allegato A coperte: 3/10 (`sessions`, `asin_master`, `listino_items`)
> **Sessione corrente:** TALOS — **Step [6] ADR-0012 completato.** Promulgazione del cluster ADR di stack 0013–0021 (9 ADR architettura/process: project structure, linguaggio, persistenza, UI, acquisizione dati, algoritmo VGP/Tetris, test strategy, CI/CD, logging). Validazione bulk Leader (Opzione A) + override puntuali ricevuti e incisi. Sblocco fase codice.

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
| **CHG-011** | **modello `listino_items` (primo con FK → sessions ON DELETE CASCADE + relationship bidirezionale)** | In commit | 48 test PASS, mypy 10 file. Pattern FK + relationship + cascade ratificato |
| **NEXT** | **Prossimo step Leader** | In attesa | Tabelle restanti Allegato A: `vgp_results` (FK doppia), `cart_items`, `panchina_items`, `storico_ordini` (RLS), `locked_in` (RLS), `config_overrides` (RLS), `audit_log` |
| ISS-001 | `gitnexus analyze` non eseguibile (architettura processore) | Rinviata | Uso futuro da PC operativo Leader |
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
- **`PROJECT-RAW.md` è in stato `Frozen` dal 2026-04-29 (codename TALOS).** Modifiche alla vision passano per **Errata Corrige** (ADR-0009) o transizione documentata a `Iterating` con motivazione esplicita del Leader.
- **Regola "Lacune mai completate" (ADR-0012, vincolante).** Continua ad applicarsi anche post-Frozen e post-stack-Frozen. Se emergono ambiguità durante la futura implementazione, marcarle in chat e portarle al Leader, **non inferire**.
- **Cluster ADR di stack 0013–0021 attivo (CHG-2026-04-30-001).** Ogni nuovo file applicativo deve mappare a un ADR Primario in FILE-ADR-MAP.md (sezione "Codice Applicativo"). Path consentiti: `src/talos/{io_,extract,vgp,tetris,formulas,persistence,ui,observability,config}` + `tests/{unit,integration,golden,governance}` + `migrations/`.
- **Repo origin:** `https://github.com/matteo891/Atena` (fork operativo del Leader). Il repo del padre `santacrocefrancesco00-ux/Atena` non è scrivibile da `matteo891`.
- **Refusi noti nelle Leggi di Talos (R-08 vs R-09):** il testo del Leader cita "Veto ROI (R-09)" mentre in tabella R-09 è Archiviazione e R-08 è Veto ROI. Marcato L09 (corretto inline in PROJECT-RAW sez. 4.1.9). Non interpretare in autonomia: chiedere conferma se rilevato altrove.
- **GitNexus rinviato (ISS-001).** Step 4 self-briefing degrada con dichiarazione esplicita.
- **Push immediato post-commit certificato (ADR-0011).**
- **Test manuali documentati ammessi per governance (ADR-0011), non per codice applicativo (richiede test automatici).**
- **Tutti gli ADR sono `Active`.** ADR-0004 è `Active¹` (hardening patch).
- **Header `Ultimo aggiornamento` di STATUS.md obbligatorio (ADR-0010).** Aggiornare data + commit hash post-commit. Ogni claim ancorato.

---

## Issues Noti

| ID | Descrizione | Workaround | ADR | Priorità |
|---|---|---|---|---|
| ISS-001 | `gitnexus analyze` segfault / exit code 5 su Node v24.15.0; architettura processore macchina locale incompatibile | Saltare step 4 GitNexus nel self-briefing con dichiarazione esplicita; uso futuro da PC operativo Leader | ADR-0007 | Rinviata |
| ~~ISS-002~~ | ~~Stack tecnologico non promulgato~~ | Chiusa 2026-04-30 con CHG-2026-04-30-001 — cluster ADR 0013–0021 promulgato | ADR-0013–0021 | Chiusa |
| ESP-001 | Esposizione bozza progetto | Chiusa 2026-04-29 con CHG-004 | ADR-0012 | Chiusa |
| ESP-002 | Round 2 | Chiusa 2026-04-29 con CHG-005 | ADR-0012 | Chiusa |
| ESP-003 | Round 3: chiusura L04 + L21 | Chiusa 2026-04-29 con CHG-006; aperta nuova L04b critica | ADR-0012 | Chiusa parzialmente |
| ESP-004 | Round 4: chiusura L04b | Chiusa 2026-04-29 con CHG-007 — normalizzazione min-max [0,1] | ADR-0012 | Chiusa |
| ESP-005 | Round 5: sweep finale 17 lacune residue | Chiusa 2026-04-29 con CHG-008 — tutte chiuse in un colpo | ADR-0012 | Chiusa |
| ESP-006 | Transizione Iterating → Frozen | Chiusa 2026-04-29 con CHG-009 — Leader: "dichiaro frozen" | ADR-0012 | Chiusa |
| ~~ESP-007~~ | ~~Step [6] ADR-0012: scomposizione → ADR di stack~~ | Chiusa 2026-04-30 con CHG-2026-04-30-001 — validazione bulk Leader (Opzione A) | ADR-0012 → ADR-0013–0021 | Chiusa |
| HARD-STOP | Pausa esplicita Leader post-tag stack-frozen | Attiva. Riapertura solo su istruzione esplicita Leader | — | Attiva |
