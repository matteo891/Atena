---
id: CHG-2026-04-29-001
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Committed
commit: 5959ebd
adr_ref: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0008
---

## What — Cosa è cambiato

Inizializzazione completa del sistema di governance architetturale del progetto:
- Promulgazione di 7 ADR fondativi (ADR-0001 → ADR-0007)
- Creazione della mappa neurale (INDEX.md) e dell'indice inverso (FILE-ADR-MAP.md)
- Creazione dei template ADR e change document
- Implementazione degli hook git per enforcement meccanico (pre-commit, commit-msg)
- Aggiornamento di CLAUDE.md con protocolli operativi e ciclo di modifica esteso
- Creazione di questo change document (primo del progetto)

## Why — Perché

**ADR di riferimento:** Tutti gli ADR 0001–0007 sono stati ratificati dal Leader in questa sessione.

Il Leader ha stabilito i seguenti requisiti fondamentali:
- Test gate obbligatorio prima di ogni commit (ADR-0002)
- Restore points su GitHub ogni 5 commit significativi (ADR-0003)
- Cross-reference documentale per ogni modifica non-triviale (ADR-0004)
- Enforcement meccanico via git hooks per eliminare dipendenza dalla disciplina manuale (ADR-0006)
- Sistema a prova di bomba navigabile da qualsiasi punto (ADR-0001, ADR-0005, FILE-ADR-MAP)

## How — Come

**File creati:**

| File | Tipo | Note |
|---|---|---|
| `docs/decisions/ADR-0001-meta-architettura-adr.md` | nuovo | La Volontà — definisce il sistema ADR stesso |
| `docs/decisions/ADR-0002-test-gate-commit.md` | nuovo | Test obbligatorio + permesso Leader pre-commit |
| `docs/decisions/ADR-0003-restore-point-github.md` | nuovo | Tag GitHub ogni 5 commit significativi |
| `docs/decisions/ADR-0004-cross-reference-documentation.md` | nuovo | Change doc obbligatorio per ogni modifica |
| `docs/decisions/ADR-0005-commit-message-convention.md` | nuovo | Formato commit con CHG-ID e ADR-ID nel footer |
| `docs/decisions/ADR-0006-git-hooks-enforcement.md` | nuovo | Enforcement meccanico via pre-commit + commit-msg |
| `docs/decisions/ADR-0007-gitnexus-integration.md` | nuovo | GitNexus come planimetria architetturale |
| `docs/decisions/INDEX.md` | nuovo | Mappa neurale: grafo relazionale di tutti gli ADR |
| `docs/decisions/FILE-ADR-MAP.md` | nuovo | Indice inverso: file → ADR |
| `docs/decisions/TEMPLATE.md` | nuovo | Template riutilizzabile per nuovi ADR |
| `docs/changes/TEMPLATE.md` | nuovo | Template per change documents |
| `scripts/hooks/pre-commit` | nuovo | Hook: blocca commit senza change doc o ADR malformati |
| `scripts/hooks/commit-msg` | nuovo | Hook: blocca commit senza CHG-ID nel message |
| `scripts/setup-hooks.sh` | nuovo | Script di attivazione hook (eseguire post-clone) |
| `docs/decisions/ADR-0008-anti-allucinazione.md` | nuovo | Regole hard contro allucinazioni e degrado silenzioso |
| `docs/STATUS.md` | nuovo | Stato vivo del progetto — re-entry in < 60s, issues noti |

**File modificati:**

| File | Modifica |
|---|---|
| `CLAUDE.md` | Self-briefing esteso (step 5), Ciclo di Modifica espanso, Protocolli Operativi, Setup Repository |
| `ROADMAP.md` | Obiettivo #2 completato, meta-blocchi strutturati con ADR necessari |
| `CHANGELOG.md` | Versioni 0.2.0 e 0.3.0 documentate |

**Approccio tecnico:**
Sistema chiuso e auto-consistente: ogni nodo punta ad altri nodi. Gli hook git trasformano l'enforcement da comportamentale a meccanico. La navigazione è bidirezionale in ogni direzione del grafo (commit→CHG→ADR, file→ADR, ADR→INDEX, CHANGELOG→CHG).

## Tests

| Test | Tipo | Esito | Note |
|---|---|---|---|
| Struttura ADR (sezioni obbligatorie) | Verifica manuale | PASS | Tutti i 7 ADR hanno le 6 sezioni richieste |
| INDEX.md completo | Verifica manuale | PASS | Tutti i 7 ADR presenti con dipendenze |
| FILE-ADR-MAP.md copre tutti i file | Verifica manuale | PASS | Tutti i file di governance mappati |
| Hook pre-commit — sintassi bash | Verifica visiva | PASS | Nessun errore di sintassi evidente |
| Hook commit-msg — sintassi bash | Verifica visiva | PASS | Nessun errore di sintassi evidente |

**Nota:** Questi sono file di governance/infrastruttura, non codice applicativo. I test sono verifiche strutturali manuali, non suite automatizzate. I test automatici del codice applicativo saranno soggetti ad ADR-0002 quando il codice applicativo verrà introdotto.

**Copertura:** I change document e ADR di questa sessione sono auto-referenziali — documentano il sistema che li documenta. Non esiste copertura test più alta di questa.

## Impact

- Ogni futura sessione è governata da questo sistema
- I commit futuri non conformi vengono bloccati meccanicamente
- Il self-briefing è ora eseguibile in O(3 file) invece di O(codebase)
- GitNexus rimane da indicizzare (`gitnexus analyze`) — vedi ADR-0007

## Refs

- ADR: [ADR-0001](../decisions/ADR-0001-meta-architettura-adr.md) → [ADR-0007](../decisions/ADR-0007-gitnexus-integration.md)
- Commit: `5959ebd`
- Checkpoint successivo: `milestone/ADR-0001-0007` (primo milestone tag del progetto)
- Issue / Task: —
