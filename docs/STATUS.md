# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit.

---

## Stato in Una Riga

Infrastruttura di governance completata (ADR 0001–0008, git hooks attivi, navigazione bidirezionale). Nessun codice applicativo presente. In attesa delle prime istruzioni di progetto dal Leader.

---

## Appena Completato

| Cosa | ADR | CHG |
|---|---|---|
| ADR 0001–0008 promulgati (meta, test gate, restore points, cross-ref, commit convention, hooks, gitnexus, anti-allucinazione) | tutti | [CHG-2026-04-29-001](changes/2026-04-29-001-bootstrap-adr-fondativi.md) |
| Git hooks attivi: pre-commit + commit-msg | ADR-0006 | CHG-2026-04-29-001 |
| Navigazione bidirezionale: FILE-ADR-MAP, INDEX, CHG-ID convention | ADR-0001, 0004, 0005 | CHG-2026-04-29-001 |
| docs/STATUS.md creato (questo file) | ADR-0008 | CHG-2026-04-29-001 |
| Repo GitHub creata e pushata (prima versione) | ADR-0003 | CHG-2026-04-29-001 |

---

## In Sospeso

| ID | Cosa | Priorità | Note |
|---|---|---|---|
| ISS-001 | Fix GitNexus (`gitnexus analyze` crasha su Node.js v24) | Alta — fare prima di introdurre codice | Probabile fix: usare Node.js v20 LTS. Fino ad allora: self-briefing step GitNexus va saltato |
| ISS-002 | Stack tecnologico non ancora definito | — | Il Leader fornirà le prime istruzioni |

---

## Prossima Azione

1. Il Leader forka/clona la repo → eseguire `bash scripts/setup-hooks.sh`
2. Fix ISS-001 (GitNexus) — concordare con Leader
3. Ricevere le prime istruzioni di progetto → promulgare ADR di architettura

---

## Nota al Prossimo Claude

> Questo campo è il presidio principale contro le allucinazioni da contesto perso. Leggerlo come se qualcuno avesse lasciato un biglietto.

- **GitNexus è rotto (ISS-001)**: `gitnexus analyze` esce con codice 5 su Node.js v24.15.0. Non tentare — salta il self-briefing step GitNexus e usa il fallback: INDEX.md + ultimi change docs.
- **Il repo contiene solo governance**: nessun file sorgente applicativo esiste. Non assumere l'esistenza di alcun modulo, funzione o classe. Se cerchi codice applicativo e non lo trovi, è perché non è ancora stato scritto.
- **Gli hook sono configurati localmente**: `git config core.hooksPath scripts/hooks`. Dopo ogni clone, eseguire `bash scripts/setup-hooks.sh` prima di qualsiasi commit.
- **Tutti gli ADR sono `Active`**: ADR-0001 → ADR-0008. Nessuno è Deprecated o Superseded.
- **Primo milestone tag da creare**: dopo il commit iniziale su GitHub → `milestone/ADR-0001-0008`.

---

## Issues Noti

| ID | Descrizione | Workaround | ADR | Priorità |
|---|---|---|---|---|
| ISS-001 | `gitnexus analyze` segfault / exit code 5 su Node.js v24 | Saltare step GitNexus nel self-briefing | ADR-0007 | Alta |
