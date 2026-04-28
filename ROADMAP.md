# ROADMAP

Tracker operativo del progetto. Ogni voce deve essere tracciabile a un ADR validato tramite GitNexus.

> **Regola vincolante:** Nessuna modifica architetturale viene registrata in questo documento prima di essere stata validata attraverso il server MCP di GitNexus e ratificata dal Leader come ADR in `docs/decisions/`.

---

## Obiettivi Attuali

| # | Obiettivo | ADR di riferimento | Stato |
|---|-----------|-------------------|-------|
| 1 | Inizializzazione infrastruttura dogmatica | — | Completato |
| 2 | Promulgazione ADR fondativi (0001–0004) | ADR-0001–0004 | Completato |
| 3 | Promulgazione ADR enforcement + anti-allucinazione (0005–0008) | ADR-0005–0008 | Completato |
| 4 | Fix GitNexus ISS-001 (crash Node.js v24) | ADR-0007 | In attesa — fare prima di introdurre codice |

---

## Implementazioni in Corso

_Nessuna implementazione attiva al momento._

---

## Meta-Blocchi Futuri

_Decisioni architetturali future da discutere e formalizzare tramite ADR prima dell'implementazione._

| # | Tema | ADR necessario | Note |
|---|------|---------------|------|
| A | Fix GitNexus ISS-001 | ADR-0007 | `gitnexus analyze` crasha su Node.js v24 — fix probabile: nvm use 20 |
| B | Stack tecnologico | Da promulgare | Da definire dal Leader |
| C | CI/CD | Da promulgare | Da definire dal Leader |

---

## Log delle Validazioni

| Data | Modifica | ADR | Validato da |
|------|----------|-----|-------------|
| 2026-04-29 | Inizializzazione infrastruttura | — | Leader |
| 2026-04-29 | Promulgazione ADR fondativi 0001–0004 + protocolli operativi | ADR-0001–0004 | Leader |
| 2026-04-29 | Promulgazione ADR 0005–0008 + git hooks + enforcement + anti-allucinazione | ADR-0005–0008 | Leader |
