# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/lang/it/).

---

## [Unreleased]

## [0.8.0] — 2026-04-29 — TALOS Vision `Frozen`

Pietra miliare del progetto. La vision di TALOS (Scaler 500k) è ufficialmente **`Frozen`** dopo 6 round di Iterating e 26 lacune chiuse. Sblocca lo step [6] di ADR-0012: proposta di scomposizione in ADR di stack.

### Changed
- `PROJECT-RAW.md`: `frontmatter.status: Iterating → Frozen`, `frozen_at: 2026-04-29`, `qa_rounds: 5 → 6`; header e pipeline note allineati; nuovo blocco Round 6 nel Q&A Log con dichiarazione verbatim del Leader; cronologia stati aggiornata ([CHG-2026-04-29-009](docs/changes/2026-04-29-009-talos-frozen-declaration.md))
- `docs/STATUS.md`: ESP-006 chiusa, ESP-007 (proposta scomposizione) aperta, TAG-001 (milestone tag) suggerito; Nota al Prossimo Claude allineata al regime post-Frozen (Errata Corrige obbligatoria per modifiche, niente edit diretti)
- `ROADMAP.md`: obiettivo #7 marcato Completato; #8 In corso

### Added
- `docs/changes/2026-04-29-009-talos-frozen-declaration.md`

## [0.7.4] — 2026-04-29 — TALOS Iterating Round 5 (sweep finale, 0 lacune aperte)

### Changed
- `PROJECT-RAW.md`: chiuse tutte le 17 lacune residue in un colpo (L01, L02, L03, L05, L07, L09, L09b, L10, L11b, L13, L14, L15, L16, L17, L19, L22, L24); default proposti accettati al 100% tranne L02 = Opzione (a) budget di sessione e L14 = Streamlit; **formula manuale Fee_FBA fornita verbatim dal Leader** e incisa in sez. 6.3 Formula 1 per L11b; tabelle 8.1/8.2 popolate con rischi+mitigazioni; refusi L09 (Veto ROI = R-08) e L09b (Tetris = R-06) corretti inline; `qa_rounds: 5`; **0 lacune aperte (26/26 chiuse)** ([CHG-2026-04-29-008](docs/changes/2026-04-29-008-talos-iterating-round-5-sweep-finale.md))
- `docs/STATUS.md`, `ROADMAP.md`: Round 5 registrato; ESP-005 chiusa, ESP-006 (transizione Frozen) aperta
- Vision pronta per dichiarazione esplicita di `Iterating → Frozen` da parte del Leader

### Added
- `docs/changes/2026-04-29-008-talos-iterating-round-5-sweep-finale.md`

## [0.7.3+1] — 2026-04-29 — Fork transition

### Changed
- `git remote origin` riallineato da `santacrocefrancesco00-ux/Atena` (repo del padre, non scrivibile dal Leader operativo `matteo891`) a `matteo891/Atena` (fork operativo)
- `docs/STATUS.md`: link al repository aggiornato di conseguenza (commit `2abe28e`)

## [0.7.3] — 2026-04-29 — TALOS Iterating Round 4 (normalizzazione VGP)

### Changed
- `PROJECT-RAW.md`: chiusa L04b (normalizzazione **min-max su [0,1]** dei tre termini VGP sul listino di sessione, prima dei pesi 40/40/20); `qa_rounds: 4`; **17 aperte, 0 critiche residue** ([CHG-2026-04-29-007](docs/changes/2026-04-29-007-talos-iterating-round-4.md))
- `docs/STATUS.md`, `ROADMAP.md`: Round 4 registrato; vision pronta per sweep finale → Frozen
- `memory/MEMORY.md` + `memory/feedback_concisione_documentale.md`: ricreati (erano referenziati in CHG-006 ma assenti su filesystem — directory memory `~/.claude/...` fuori dal repo, non versionata)

### Added
- `docs/changes/2026-04-29-007-talos-iterating-round-4.md`

## [0.7.2] — 2026-04-29 — TALOS Iterating Round 3 (formula VGP)

### Changed
- `PROJECT-RAW.md`: chiuse L04 (formula VGP `(ROI*0.4)+(Vel*0.4)+(Cash_Profit*0.2)`) e L21 (Keepa out-of-scope per Talos); aperta L04b critica (normalizzazione scale) ([CHG-2026-04-29-006](docs/changes/2026-04-29-006-talos-iterating-round-3.md)); `qa_rounds: 3`; 18 aperte (1 critica L04b)
- `docs/STATUS.md`, `ROADMAP.md`: Round 3 registrato
- Direttiva del Leader sulla concisione documentale salvata come **memory feedback** durevole

### Added
- `docs/changes/2026-04-29-006-talos-iterating-round-3.md`
- `memory/feedback_concisione_documentale.md` (auto-memory)

## [0.7.1] — 2026-04-29 — TALOS Iterating Round 2

### Changed
- `PROJECT-RAW.md`: 6 lacune chiuse in Round 2 (L06 Samsung-only modulare, L08 scraping Amazon, L11 lookup Keepa primario, L12 Referral_Fee lookup+override, L18 Tesseract locale, L20 criteri di completamento misurabili accettati); 1 sub-lacuna nuova aperta (L11b formula manuale Fee_FBA); frontmatter `qa_rounds: 2`; sezione 9 ristrutturata in Aperte/Chiuse; Q&A Log esteso con Round 2 verbatim ([CHG-2026-04-29-005](docs/changes/2026-04-29-005-talos-iterating-round-2.md))
- `docs/STATUS.md`: Round 2 registrato, 19 lacune aperte (2 critiche L04/L21), prossima azione = Round 3
- `ROADMAP.md`: log validazioni esteso con Round 2

### Added
- `docs/changes/2026-04-29-005-talos-iterating-round-2.md` — change document Round 2

### Lacune critiche residue
- **L04** Formula del VGP Score (bottleneck dell'MVP)
- **L21** Keepa: subscription, campi, costo, rate limit (collegata a L11/L11b)

## [0.7.0] — 2026-04-29 — TALOS Vision Exposition (Round 1)

### Added
- **Codename del progetto: TALOS (Scaler 500k)** — Hedge Fund algoritmico automatizzato applicato al modello FBA Wholesale High-Ticket
- `docs/changes/2026-04-29-004-talos-exposition-iterating.md` — change document della prima esposizione

### Changed
- `PROJECT-RAW.md`: trascrizione verbatim integrale della bozza esposta dal Leader, mappatura 14+1 sezioni → 11 sezioni template, 24 lacune raccolte (8 critiche, 12 importanti, 4 di forma); status `Draft → Iterating`; frontmatter aggiornato (`qa_rounds: 1`, `codename: TALOS`, `tagline: "Scaler 500k"`)
- `docs/STATUS.md`: stato corrente = Iterating Round 1 completato, Round 2 (chiusura lacune critiche) in attesa Leader
- `ROADMAP.md`: obiettivo #7 in corso — esposizione completata, lacune mappate

### Lacune critiche da risolvere prima del Frozen
- **L04** Formula del VGP Score (non definita)
- **L08** Lookup Amazon (scraping vs PA-API)
- **L11/L12** Sorgente Fee_FBA e Referral_Fee
- **L18** Tecnologia OCR/Vision per file non-strutturati
- **L20** Criteri di completamento misurabili
- **L21** Keepa: subscription, campi, costo, rate limit
- **L06** Estrattore Samsung-only: scope MVP e roadmap

## [0.6.0] — 2026-04-29 — Vision Capture Protocol

### Added
- `ADR-0012`: Project Vision Capture & Distillation — protocollo formale per esporre, affinare e congelare la bozza concettuale del progetto via `PROJECT-RAW.md` ([CHG-2026-04-29-003](docs/changes/2026-04-29-003-vision-capture-adr.md))
- `PROJECT-RAW.md` (root): template vuoto in stato `Draft`, 11 sezioni fisse, 16 lacune iniziali precompilate, Q&A Log vuoto, regola "lacune mai completate" applicata
- `docs/changes/2026-04-29-003-vision-capture-adr.md` — change document della promulgazione

### Changed
- `docs/decisions/INDEX.md`: aggiunto ADR-0012 al registro, grafo dipendenze esteso, `PROJECT-RAW.md` registrato in "Aree di Codice Coperte"
- `docs/decisions/FILE-ADR-MAP.md`: `PROJECT-RAW.md` mappato sotto ADR-0012; ROADMAP esteso con dipendenza secondaria ADR-0012
- `ROADMAP.md`: obiettivo #6 (vision capture protocol) completato; #7 (esposizione Leader → Iterating) in attesa; #8 (Frozen → scomposizione → ADR di stack) successivo; meta-blocco F aggiunto
- `docs/STATUS.md`: stato vision capture, prossima azione = esposizione bozza Leader

## [0.5.0] — 2026-04-29 — Governance Hardening

Audit completo del sistema di governance richiesto dal Leader. Rilevati 5 buchi seri (B1–B5), 9 sviste minori (M1–M9) e 3 policy mancanti (P1–P3). Risolti integralmente in questo release.

### Added
- `ADR-0009`: Errata Corrige & Hardening Patch — meccanismo formale per correggere refusi e marcare sezioni obsolete senza supersessione completa ([CHG-2026-04-29-002](docs/changes/2026-04-29-002-hardening-governance.md))
- `ADR-0010`: Self-Briefing Hardening & STATUS Anchoring — Step 0 di verifica `core.hooksPath` (bloccante), header `Ultimo aggiornamento` in STATUS.md, regola di anchoring per ogni claim, fonte unica della sequenza di re-briefing ([CHG-2026-04-29-002](docs/changes/2026-04-29-002-hardening-governance.md))
- `ADR-0011`: Operational Policies — push immediato post-commit, branch policy fase governance, definizione formale di test manuali documentati per file di governance/infrastruttura ([CHG-2026-04-29-002](docs/changes/2026-04-29-002-hardening-governance.md))
- `docs/changes/2026-04-29-002-hardening-governance.md` — change document del hardening
- Frontmatter ADR esteso con campi opzionali `errata:` e `hardening_patches:` (append-only)
- Sezione `## Errata` in coda agli ADR modificati

### Changed
- `scripts/hooks/pre-commit`: aggiunta `## Test di Conformità` alla lista delle sezioni obbligatorie per nuovi ADR (B3)
- `scripts/hooks/commit-msg`: classifier dei file in staging anche per prefissi docs/chore/ci (B2); verifica esistenza fisica del change document referenziato dal CHG-ID (M7); presenza obbligatoria di ADR-NNNN nel footer (M6)
- `docs/decisions/INDEX.md`: aggiunti ADR-0009/0010/0011, grafo dipendenze esteso, status `Active¹` per ADR-0004 (con hardening patch), issues ISS-001/002 spostate qui per visibilità
- `docs/decisions/FILE-ADR-MAP.md`: aggiunto `docs/STATUS.md` (governato da ADR-0008 + ADR-0010), corretto `.gitattributes` (governato da ADR-0006, non più "triviale"), nuova sezione "Push, Branch, Tag" (M4, M5)
- `docs/STATUS.md`: header `Ultimo aggiornamento` + ancore verificabili su tutti i claim, aggiornamento integrale alla nuova realtà di governance
- `CLAUDE.md`: Self-Briefing con Step 0 bloccante, riferimento esplicito ad ADR-0010 come fonte unica della sequenza, sezione "Tipi di test ammessi" (ADR-0011), branch `main` (corretta), push policy esplicita
- `ROADMAP.md`: obiettivo "Hardening governance v0.5.0" completato; rinvio "Branch policy v2" alla fase codice applicativo

### Errata Corrige (ADR-0009)
- `ADR-0003`: tabella "Tipologie di Checkpoint" — `master` corretto in `main` (M1). Sezione `## Errata` aggiunta.
- `docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md`: numerazione "ADR 0001–0007" corretta in "ADR 0001–0008" (3 occorrenze); riferimento milestone tag corretto (M2). Sezione `## Errata` aggiunta.

### Hardening Patches (ADR-0009)
- `ADR-0004` sezione "Flusso di Re-Briefing": marcata superseduta da ADR-0010 con blocco di intestazione esplicito (B1). Status di ADR-0004 in INDEX.md aggiornato a `Active¹`. Sezione `## Errata` aggiunta.

## [0.4.0] — 2026-04-29

### Added
- `ADR-0008`: Anti-Allucinazione Protocol — regole hard contro invenzione di coordinate, degrado silenzioso, stato non verificato ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `docs/STATUS.md` — documento di stato vivo: re-entry in < 60 secondi, issues noti, "Nota al Prossimo Claude"

### Changed
- `CLAUDE.md`: Self-Briefing ottimizzato (STATUS.md come step 1), Anti-Allucinazione inline, Setup Repository, formato commit
- `docs/decisions/INDEX.md`: ADR-0008 aggiunto, ISS-001 segnalato, STATUS.md mappato
- `ROADMAP.md`: obiettivo #3 completato, #4 (fix GitNexus ISS-001) aggiunto, log aggiornato

## [0.3.0] — 2026-04-29

### Added
- `ADR-0005`: Commit Message Convention — footer con CHG-ID e ADR-ID in ogni commit non-triviale ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `ADR-0006`: Git Hooks Enforcement — pre-commit e commit-msg per enforcement meccanico dei protocolli ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `ADR-0007`: GitNexus come Planimetria Architetturale — knowledge graph del codice, briefing O(query) ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `docs/decisions/FILE-ADR-MAP.md` — indice inverso file → ADR per navigazione bidirezionale ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `scripts/hooks/pre-commit` — blocca commit senza change doc o ADR malformati/non-indicizzati ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `scripts/hooks/commit-msg` — blocca commit senza CHG-ID nel message ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `scripts/setup-hooks.sh` — script di attivazione hook, eseguire dopo ogni clone ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md))
- `docs/changes/2026-04-29-001-bootstrap-adr-fondativi.md` — primo change document del progetto

### Changed
- `docs/decisions/INDEX.md` aggiornato con ADR-0005, 0006, 0007, grafo dipendenze esteso, aree coperte complete
- `CLAUDE.md` aggiornato con Setup Repository e commit format (ADR-0005, ADR-0006)

## [0.2.0] — 2026-04-29

### Added
- `ADR-0001`: Meta-Architettura del Sistema ADR — definisce template, naming, ciclo di vita e mappa neurale di tutti gli ADR.
- `ADR-0002`: Test Gate Protocol — nessun commit non-triviale senza test passante e permesso esplicito del Leader.
- `ADR-0003`: Restore Point Strategy su GitHub — checkpoint ogni 5 commit significativi, milestone tag per ogni ADR implementato.
- `ADR-0004`: Cross-Reference Documentation — change document obbligatorio per ogni modifica non-triviale in `docs/changes/`.
- `docs/decisions/TEMPLATE.md` — template riutilizzabile per nuovi ADR.
- `docs/decisions/INDEX.md` — mappa neurale relazionale di tutti gli ADR attivi.
- `docs/changes/TEMPLATE.md` — template per i change document.

### Changed
- `CLAUDE.md` aggiornato: Self-Briefing esteso con step 5 (change documents recenti), Ciclo di Modifica espanso con test gate e checkpoint, nuova sezione Protocolli Operativi.
- `ROADMAP.md` aggiornato: obiettivo #2 completato, meta-blocchi futuri strutturati con ADR necessari.

## [0.1.0] — 2026-04-29

### Added
- Inizializzazione dell'infrastruttura dogmatica base.
- Creazione di `CLAUDE.md` con le Rules of Engagement e il protocollo di Self-Briefing obbligatorio.
- Predisposizione della cassaforte delle leggi `docs/decisions/` (vuota, pronta per la promulgazione degli ADR).
- Creazione di `CHANGELOG.md` (questo file).
- Creazione di `ROADMAP.md` con struttura operativa e vincoli di validazione GitNexus.
