# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/lang/it/).

---

## [Unreleased]

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
