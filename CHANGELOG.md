# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/lang/it/).

---

## [Unreleased]

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
