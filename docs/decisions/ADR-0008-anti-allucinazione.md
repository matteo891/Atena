---
id: ADR-0008
title: Anti-Allucinazione Protocol
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

Le allucinazioni di un LLM in contesto di sviluppo software sono silenziose e costose: Claude può inventare nomi di funzioni, path di file, comportamenti di API, stati del codice — presentandoli con la stessa confidenza di fatti verificati. La perdita di contesto tra sessioni amplifica il rischio: Claude può ricordare una versione precedente del codice come se fosse quella attuale. In un contesto dove "un errore costa carissimo", ogni affermazione non verificata è un rischio sistemico.

Questo ADR definisce le **regole hard** che rendono le allucinazioni sistematicamente impossibili e il re-briefing veloce e affidabile.

## Decisione

### Regola 1 — Verifica Prima di Affermare (No Assumption)

Claude non descrive il contenuto di un file senza averlo letto in **questa sessione**. Non afferma che un file esiste senza averlo verificato con Glob o Grep. Non descrive il comportamento di una funzione senza averla letta.

**Regola pratica:** "Se non ho letto il file in questa sessione, dico esplicitamente 'devo verificare' e lo leggo prima di rispondere."

### Regola 2 — Coordinate Non Inventabili

Claude non inventa mai le seguenti coordinate. Sono **sempre** verificate da fonte primaria:

| Coordinate | Fonte primaria |
|---|---|
| Hash di commit | `git log` |
| Path di file | Glob o Grep |
| Nomi di funzioni/classi/metodi | Grep o GitNexus |
| Versioni di dipendenze | file manifest (package.json, requirements.txt, etc.) |
| Output di comandi | eseguire il comando, non ricordarlo |
| Stato del progetto | `docs/STATUS.md` |

### Regola 3 — STATUS.md è la Fonte di Verità per lo Stato Corrente

Lo stato del progetto è quello descritto in `docs/STATUS.md`, non quello che Claude ricorda da sessioni precedenti. La memoria interna di Claude tra sessioni è inaffidabile. STATUS.md è autorevole.

Claude aggiorna `docs/STATUS.md` alla **fine di ogni sessione con modifiche**, nello stesso commit. La sezione "Nota al Prossimo Claude" porta forward esplicitamente i fatti non-ovvi che causano errori nelle sessioni successive.

### Regola 4 — Degrado Esplicito, Non Silenzioso

Se il self-briefing è parziale (GitNexus down, file non leggibili, sessione interrotta):
- Claude **dichiara esplicitamente** le lacune: "Non ho letto X — sto procedendo senza quella informazione"
- Non compensa le lacune con inferenze o interpolazioni
- Non finge di sapere ciò che non ha verificato

Il degrado silenzioso è proibito. Meglio un "non so, devo verificare" che un'affermazione sbagliata con aria di certezza.

### Regola 5 — ADR Prima di Agire su Qualsiasi Area

Prima di toccare qualsiasi file o componente, Claude verifica in `docs/decisions/FILE-ADR-MAP.md` quale ADR lo governa. Se l'area non è mappata → gap ADR → stop → segnala al Leader. Non si procede con un'interpretazione "plausibile" dell'ADR più vicino.

### Regola 6 — No Extrapolazione da ADR Parzialmente Letti

Se Claude ha letto 3 ADR su 8, non extrapola le regole degli altri 5. Li legge direttamente. INDEX.md dice quali ADR sono rilevanti per un'area specifica.

### Regola 7 — Obblighi Positivi di Fine Sessione

Alla fine di ogni sessione con modifiche, Claude deve:
1. Aggiornare `docs/STATUS.md` con lo stato corrente
2. Aggiornare il campo "Nota al Prossimo Claude" con i fatti non-ovvi emersi
3. Aggiornare "In Sospeso" con eventuali issues o lavori incompiuti
4. Verificare che `docs/changes/` abbia il change document per le modifiche della sessione
5. Includere l'aggiornamento di STATUS.md nello stesso commit delle modifiche

### Protocollo di Re-Entry Ottimale (< 60 secondi)

Sequenza obbligatoria:
1. `docs/STATUS.md` — stato corrente, issues noti, prossima azione
2. `docs/decisions/INDEX.md` — mappa neurale ADR (NON rileggere tutti gli ADR, solo quelli rilevanti all'area di lavoro)
3. Ultimi 3 file in `docs/changes/` — contesto operativo recente
4. GitNexus query — se disponibile; saltare con nota se non disponibile
5. `ROADMAP.md` — solo se passo 1 non è sufficiente per allineamento obiettivi

Regola: nessun passo può essere saltato senza dichiarare esplicitamente la lacuna.

## Conseguenze

- Risposte leggermente più lente (Claude legge prima di rispondere), ma zero affermazioni inventate
- Il Leader può fidarsi di ogni affermazione tecnica di Claude come di un fatto verificato
- Le sessioni brevi sono safe: Claude dichiara esplicitamente i limiti del suo contesto
- Il re-entry dopo qualsiasi interruzione è sempre in < 60 secondi via STATUS.md

## Test di Conformità

| Scenario | Comportamento Corretto |
|---|---|
| Claude cita un file | Deve averlo letto in questa sessione |
| Claude cita una funzione | Deve averla verificata con Grep/GitNexus |
| Claude descrive lo stato del progetto | Deve corrispondere a STATUS.md |
| GitNexus non disponibile | Claude dichiara esplicitamente "GitNexus non disponibile" |
| Area senza ADR | Claude dichiara gap e non procede |
| Fine sessione con modifiche | STATUS.md aggiornato nello stesso commit |

## Cross-References

- ADR correlati: ADR-0001 (meta), ADR-0004 (cross-reference), ADR-0007 (GitNexus)
- Governa: ogni affermazione tecnica di Claude, aggiornamento STATUS.md, protocollo re-entry
- Impatta: `docs/STATUS.md`, self-briefing, tutte le sessioni operative
- Test: verifica comportamentale per ogni sessione
- Commits: [da aggiornare post-commit]

## Rollback

Non applicabile come ADR di codice. Se superseduto, il nuovo ADR deve essere più restrittivo, mai meno: in un contesto ad alto costo dell'errore, allentare le regole anti-allucinazione è proibito senza esplicita autorizzazione del Leader con motivazione documentata.
