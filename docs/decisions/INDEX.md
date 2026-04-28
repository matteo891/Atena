# ADR Index — Mappa Neurale

Grafo relazionale di tutti gli ADR ratificati. Aggiornare **prima** della ratifica di ogni nuovo ADR.

> **Regola vincolante (ADR-0001):** Nessun ADR è considerato `Active` fino a quando non è referenziato in questo indice con tutte le colonne compilate.

---

## Registro

| ID | Titolo | Status | Categoria | Data | Dipende da | Governa |
|---|---|---|---|---|---|---|
| [ADR-0001](ADR-0001-meta-architettura-adr.md) | Meta-Architettura ADR | Active | meta | 2026-04-29 | — | Tutti gli ADR |
| [ADR-0002](ADR-0002-test-gate-commit.md) | Test Gate Protocol | Active | process | 2026-04-29 | ADR-0001 | Ogni commit di codice |
| [ADR-0003](ADR-0003-restore-point-github.md) | Restore Point Strategy | Active | process | 2026-04-29 | ADR-0001, ADR-0002 | Tag GitHub, CHANGELOG |
| [ADR-0004](ADR-0004-cross-reference-documentation.md) | Cross-Reference Documentation | Active | process | 2026-04-29 | ADR-0001 | docs/changes/, CHANGELOG |
| [ADR-0005](ADR-0005-commit-message-convention.md) | Commit Message Convention | Active | process | 2026-04-29 | ADR-0001, ADR-0004 | Ogni commit message non-triviale |
| [ADR-0006](ADR-0006-git-hooks-enforcement.md) | Git Hooks Enforcement | Active | process | 2026-04-29 | ADR-0001, ADR-0002, ADR-0004, ADR-0005 | scripts/hooks/, enforcement meccanico |
| [ADR-0007](ADR-0007-gitnexus-integration.md) | GitNexus Planimetria Architetturale | Active | tooling | 2026-04-29 | ADR-0001, ADR-0004 | .gitnexus/, self-briefing step 1 |
| [ADR-0008](ADR-0008-anti-allucinazione.md) | Anti-Allucinazione Protocol | Active | process | 2026-04-29 | ADR-0001, ADR-0004, ADR-0007 | Ogni affermazione di Claude, docs/STATUS.md |

---

## Grafo delle Dipendenze

```
ADR-0001 [meta] — La Volontà
    ├── ADR-0002 [process] — Test Gate
    │       ├── ogni commit non-triviale
    │       └── ← enforcement: ADR-0006 (pre-commit)
    ├── ADR-0003 [process] — Restore Points
    │       ├── dipende da ADR-0002 (commit certificati)
    │       └── governa: tag GitHub, CHANGELOG
    ├── ADR-0004 [process] — Cross-Reference
    │       ├── governa: docs/changes/
    │       ├── governa: CHANGELOG.md
    │       └── ← enforcement: ADR-0006 (pre-commit)
    ├── ADR-0005 [process] — Commit Convention
    │       ├── dipende da ADR-0004 (CHG-ID references)
    │       └── ← enforcement: ADR-0006 (commit-msg)
    ├── ADR-0006 [process] — Git Hooks
    │       ├── enforce: ADR-0001 (struttura ADR)
    │       ├── enforce: ADR-0002 (change doc)
    │       ├── enforce: ADR-0004 (change doc)
    │       └── enforce: ADR-0005 (commit format)
    ├── ADR-0007 [tooling] — GitNexus
    │       ├── dipende da ADR-0004 (context per briefing)
    │       └── governa: .gitnexus/, self-briefing step 1 ⚠ ISS-001
    └── ADR-0008 [process] — Anti-Allucinazione
            ├── dipende da ADR-0004 (STATUS.md come change doc esteso)
            ├── governa: docs/STATUS.md
            └── governa: ogni affermazione tecnica di Claude
```

---

## Aree di Codice Coperte

| Area / Componente | ADR di Riferimento | Note |
|---|---|---|
| Workflow commit | ADR-0002 | Test gate obbligatorio |
| Commit message format | ADR-0005 | CHG-ID + ADR-ID nel footer |
| Tag e release GitHub | ADR-0003 | Checkpoint ogni 5 commit significativi |
| docs/changes/ | ADR-0004 | Change document per ogni modifica non-triviale |
| docs/decisions/ | ADR-0001 | Governance ADR |
| docs/decisions/INDEX.md | ADR-0001 | Questa mappa — aggiornare prima di ogni ratifica |
| docs/decisions/FILE-ADR-MAP.md | ADR-0001 | Indice inverso file→ADR |
| CHANGELOG.md | ADR-0003, ADR-0004, ADR-0005 | Checkpoint + change summary con link CHG |
| ROADMAP.md | ADR-0001 | Aggiornato ad ogni nuova decisione architetturale |
| scripts/hooks/ | ADR-0006 | pre-commit + commit-msg |
| scripts/setup-hooks.sh | ADR-0006 | Eseguire post-clone |
| .gitnexus/ | ADR-0007 | Database knowledge graph ⚠ ISS-001 |
| docs/STATUS.md | ADR-0008, ADR-0004 | Stato corrente — aggiornare a fine ogni sessione |

---

## Aree Senza Copertura ADR

> Le aree elencate qui non hanno ancora un ADR `Active`. Claude deve segnalare il gap prima di toccarle.

| Area | Gap | Prossima Azione |
|---|---|---|
| Stack tecnologico | Nessun ADR | Da definire dal Leader |
| CI/CD | Nessun ADR | Da definire dal Leader |
| Struttura directory codice applicativo | Nessun ADR | Dipende dallo stack; da definire con ADR architecture |

---

## Legenda Status

| Status | Significato |
|---|---|
| `Active` | In vigore, vincolante per Claude e il Leader |
| `Proposed` | In discussione, non ancora vincolante |
| `Deprecated` | Non più in vigore, mantenuto per storia |
| `Superseded` | Sostituito — vedere campo `superseded_by` nell'ADR |
