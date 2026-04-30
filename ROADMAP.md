# ROADMAP

Tracker operativo del progetto. Ogni voce deve essere tracciabile a un ADR validato e ratificato dal Leader.

> **Regola vincolante:** Nessuna modifica architetturale viene registrata in questo documento prima di essere stata ratificata dal Leader come ADR in `docs/decisions/`. La validazione GitNexus è opzionale fintanto che ISS-001 è aperta (vedi STATUS.md).

---

## Obiettivi Attuali

| # | Obiettivo | ADR di riferimento | Stato |
|---|-----------|-------------------|-------|
| 1 | Inizializzazione infrastruttura dogmatica | — | Completato |
| 2 | Promulgazione ADR fondativi (0001–0004) | ADR-0001–0004 | Completato |
| 3 | Promulgazione ADR enforcement + anti-allucinazione (0005–0008) | ADR-0005–0008 | Completato |
| 4 | Hardening governance v0.5.0 — fix audit (B1–B5, M1–M9, P1–P3) | ADR-0009, ADR-0010, ADR-0011 | Completato (commit `416ab87`) |
| 5 | Verdetto: sistema governance a prova di bomba per fase pre-codice | tutti 0001–0011 | Confermato — sistema in produzione |
| 6 | Vision capture protocol — ADR-0012 + PROJECT-RAW.md template `Draft` | ADR-0012 | Completato (CHG-2026-04-29-003) |
| 7 | Esposizione bozza dal Leader → riempimento PROJECT-RAW.md `Draft → Iterating → Frozen` | ADR-0012 | **Completato.** Round 1–6 (CHG-004…009). 26/26 lacune chiuse. **Vision `Frozen` dal 2026-04-29** |
| 8 | Step [6] ADR-0012: proposta scomposizione (Claude in chat) → validazione Leader → ADR di stack | ADR-0012 → ADR-0013…0021 | **Completato.** Validazione bulk Leader (Opzione A) 2026-04-30. 9 ADR di stack promulgati (CHG-2026-04-30-001) |
| 9 | Fork repo su PC operativo Leader + verifica `gitnexus analyze` (ISS-001) | ADR-0007 | Rinviato — bloccato da setup PC operativo |
| 10 | Clone `Atena-Core` (purezza infrastrutturale post `milestone/stack-frozen-v0.9.0`) | ADR-0003 | **In corso** — Leader cloning post-tag (HARD STOP attivo) |
| 11 | Bootstrap primo modulo applicativo (`pyproject.toml` + `src/talos/__init__.py` + `tests/conftest.py`) | ADR-0013, ADR-0014 | Bloccante: subordinato a riapertura esplicita Leader post HARD STOP |

---

## Implementazioni in Corso

_Nessuna implementazione di codice attiva. Sessione 2026-04-30: promulgazione cluster ADR di stack 0013–0021 + tooling GitNexus condiviso + tag `milestone/stack-frozen-v0.9.0`. **HARD STOP** attivo per consentire al Leader il clone di `Atena-Core` nello stato di purezza infrastrutturale._

---

## Meta-Blocchi Futuri

_Decisioni architetturali future da discutere e formalizzare tramite ADR prima dell'implementazione._

| # | Tema | ADR necessario | Note |
|---|------|---------------|------|
| ~~A~~ | ~~Stack tecnologico~~ | Coperto da ADR-0014/0015/0016/0017/0018/0021 (CHG-2026-04-30-001) | Chiuso |
| ~~B~~ | ~~Struttura directory codice applicativo~~ | Coperto da ADR-0013 (CHG-2026-04-30-001) | Chiuso |
| ~~C~~ | ~~CI/CD pipeline~~ | Coperto da ADR-0020 (CHG-2026-04-30-001) | Chiuso |
| D | Branch policy v2 (multi-branch / PR / branch protection) | Da promulgare | Rinviata da ADR-0011 + ADR-0020 (single-push MVP); rivedere all'introduzione di multi-developer |
| E | GitNexus operativo da PC del Leader | ADR-0007 (esistente, in attesa) | Eseguire `gitnexus analyze` post-fork; CI bot (ADR-0020) reindex automatizzato post-merge |
| F | Task operativi derivati dal PROJECT-RAW Frozen | Da promulgare individualmente | Popolati post-bootstrap del primo modulo applicativo |
| G | Cloud backup PostgreSQL (post-MVP) | Da promulgare | Out-of-scope MVP per ADR-0015; valutare resilienza off-site post-MVP |
| H | Metriche / OpenTelemetry (post-MVP) | Da promulgare | Out-of-scope MVP per ADR-0021 |
| I | Multi-brand timeline (post-MVP) | Task ROADMAP, non ADR | Pianificare entro 4 settimane post-MVP (decisione bulk 2026-04-30) |
| J | Documentazione utente (README operativo + user-guide CFO) | Task ROADMAP, non ADR | Da pianificare post-bootstrap (decisione bulk 2026-04-30) |

---

## Log delle Validazioni

| Data | Modifica | ADR | Validato da |
|------|----------|-----|-------------|
| 2026-04-29 | Inizializzazione infrastruttura | — | Leader |
| 2026-04-29 | Promulgazione ADR fondativi 0001–0004 + protocolli operativi | ADR-0001–0004 | Leader |
| 2026-04-29 | Promulgazione ADR 0005–0008 + git hooks + enforcement + anti-allucinazione | ADR-0005–0008 | Leader |
| 2026-04-29 | Hardening governance v0.5.0 — ADR-0009/0010/0011 + errata + hardening patch + hook rinforzati | ADR-0009, ADR-0010, ADR-0011 | Leader (CHG-2026-04-29-002, commit `416ab87`) |
| 2026-04-29 | Vision capture protocol — ADR-0012 + PROJECT-RAW.md template Draft | ADR-0012 | Leader (CHG-2026-04-29-003) |
| 2026-04-29 | TALOS — prima esposizione bozza, trascrizione verbatim, 24 lacune (Iterating Round 1) | ADR-0012 | Leader (CHG-2026-04-29-004) |
| 2026-04-29 | TALOS — Round 2 Q&A: chiuse 6 critiche (Tesseract, scraping, Keepa primario, Referral lookup+override, criteri completamento, Samsung-only modulare); aperta L11b. 19 aperte (2 critiche residue) | ADR-0012 | Leader (CHG-2026-04-29-005) |
| 2026-04-29 | TALOS — Round 3 Q&A: chiuse L04 (formula VGP) + L21 (Keepa out-of-scope); aperta L04b critica (normalizzazione scale). 18 aperte (1 critica). Direttiva concisione registrata come memory | ADR-0012 | Leader (CHG-2026-04-29-006) |
| 2026-04-29 | TALOS — Round 4 Q&A: chiusa L04b (normalizzazione min-max [0,1] dei tre termini VGP). 17 aperte, **0 critiche residue**. Vision pronta per sweep finale → Frozen | ADR-0012 | Leader (CHG-2026-04-29-007) |
| 2026-04-29 | Transizione fork: origin riallineato da `santacrocefrancesco00-ux/Atena` (repo padre, non scrivibile dal Leader operativo) a `matteo891/Atena` (fork operativo) | — | Leader (commit `2abe28e`) |
| 2026-04-29 | TALOS — Round 5 Q&A: sweep finale, chiuse tutte le 17 residue in un colpo (default + L02=(a) + L14=Streamlit + formula Fee_FBA verbatim per L11b). **0 aperte, 26/26 chiuse**. In attesa dichiarazione esplicita Frozen | ADR-0012 | Leader (CHG-2026-04-29-008) |
| 2026-04-29 | **TALOS — Round 6: `Frozen` dichiarato esplicitamente dal Leader (*"dichiaro frozen"*). Vision congelata. Sblocco step [6] ADR-0012** | ADR-0012 | Leader (CHG-2026-04-29-009) |
| 2026-04-30 | **Promulgazione cluster ADR di stack 0013–0021 (validazione bulk Opzione A): src-layout + uv, Python 3.11 + mypy, PostgreSQL Zero-Trust + SQLAlchemy 2.0, Streamlit + caching, Keepa+Playwright+Tesseract fallback chain, VGP+Tetris vettoriale Numpy, pytest + golden Samsung + Hypothesis limitato, GitHub Actions + GitNexus reindex bot, structlog + R-01 dinamico** | ADR-0013–0021 | Leader (CHG-2026-04-30-001) |
| 2026-04-30 | Integrazione tooling GitNexus condiviso nel repo (CLAUDE.md/AGENTS.md gemelli + skills committate + .gitignore esclusione runtime + git rm --cached lock SQLite) | ADR-0007 | Leader (CHG-2026-04-30-002) |
| 2026-04-30 | Milestone tag `milestone/stack-frozen-v0.9.0` — restore point pre-codice (purezza infrastrutturale, fonte di clone per `Atena-Core`) | ADR-0003 | Leader (post CHG-2026-04-30-002) |
| 2026-04-30 | Errata Corrige ADR-0006 (Git Hooks Enforcement) + side-effect su ADR-0014/0020: hooks v2 con pre-commit-app wiring (graceful skip se assente) e bypass cumulativo `commit-msg` per il bot reindex GitNexus (`[skip ci]` + author `github-actions[bot]`) | ADR-0006, ADR-0014, ADR-0020, ADR-0009 | Leader (CHG-2026-04-30-003) |
