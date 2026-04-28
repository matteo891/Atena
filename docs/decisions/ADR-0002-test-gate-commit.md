---
id: ADR-0002
title: Test Gate Protocol
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

Nel contesto operativo del progetto, un errore introdotto senza rilevamento da test può propagarsi silenziosamente e causare danni difficilmente reversibili. Il costo di un errore in produzione è alto. La regola "nessun commit senza test" è un presidio fondamentale di qualità non negoziabile.

## Decisione

### Regola Fondamentale

Nessuna modifica **non-triviale** al codice può essere committata senza:
1. Un test che la copra esplicitamente
2. L'esito positivo del test (tutti i test della suite pertinente devono passare)
3. Il report dell'esito al Leader
4. Il **permesso esplicito del Leader** di procedere con il commit

### Definizione di Modifica Non-Triviale

Una modifica è **non-triviale** (soggetta a test gate) se riguarda:
- Logica applicativa: funzioni, classi, metodi, algoritmi
- Strutture dati o schemi (database, API, configurazioni runtime)
- Interfacce e contratti pubblici (API, eventi, tipi esportati)
- Dipendenze: aggiunta, rimozione o aggiornamento di librerie
- Script di build, CI/CD, infrastruttura

Una modifica è **triviale** (esentata da test gate) se riguarda:
- Solo whitespace, formattazione, typo in commenti
- Solo file di documentazione (`.md`, `.txt`, `docs/`)
- Solo variabili d'ambiente di sviluppo locale (non runtime)

### Flusso Obbligatorio

```
Implementazione
      ↓
Scrittura / aggiornamento test
      ↓
Esecuzione test
      ↓
   Esito? ──FAIL──→ Diagnosi e fix → torna a "Esecuzione test"
      ↓ PASS
Report esito completo al Leader
  (test eseguiti, copertura, rischi residui noti)
      ↓
Attesa permesso esplicito del Leader
      ↓
Commit (solo con permesso)
      ↓
Aggiornamento change document con hash commit
```

### Report Pre-Commit Obbligatorio

Prima di richiedere il permesso, Claude riporta al Leader:
- Elenco dei test eseguiti e loro esito (PASS / FAIL)
- Copertura stimata della modifica
- Eventuali rischi residui noti o casi limite non coperti

### Esenzione di Emergenza

In caso di emergenza documentata, il Leader può autorizzare un commit senza test con motivazione esplicita. Tale motivazione deve essere:
- Registrata nel commit message con prefisso `[EMERGENCY-NO-TEST]`
- Documentata nel change document (`docs/changes/`)
- Seguita da un commit di follow-up con i test mancanti (da creare entro la sessione successiva)

## Conseguenze

- I commit sono meno frequenti ma ogni commit è certificato
- Nessun "commit veloce" senza test, nemmeno per fix apparentemente banali
- Il Leader mantiene il controllo esplicito su ogni modifica committata
- La suite di test cresce organicamente con ogni modifica

## Test di Conformità

Questo ADR si auto-verifica: ogni commit nel repository deve avere almeno un test associato o una motivazione di esenzione documentata nel commit message e nel change document.

Verifica: `git log --oneline` — ogni commit non-documentale deve avere un change document corrispondente in `docs/changes/`.

## Cross-References

- ADR correlati: ADR-0001 (meta-architettura), ADR-0003 (restore points), ADR-0004 (cross-reference doc)
- Governa: ogni modifica al codice sorgente del progetto
- Impatta: `CLAUDE.md` (workflow), ogni file sorgente, `docs/changes/`
- Test: il test stesso è il presidio; la conformità è verificata per ogni commit
- Commits: [da aggiornare post-commit]

## Rollback

Se questo ADR viene superseduto, tutti i commit successivi alla supersessione devono documentare il nuovo protocollo nel CHANGELOG e nel relativo change document.
