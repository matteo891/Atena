---
id: ADR-0004
title: Cross-Reference Documentation delle Modifiche
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

La perdita di contesto tra sessioni è il principale vettore di allucinazioni e debug difficile. Senza tracciabilità esplicita, ogni re-briefing riparte quasi da zero, con rischio di contraddire decisioni già prese o ripetere errori già corretti.

Ogni modifica non-triviale deve essere rintracciabile da tre angolazioni:
- **Cosa** è cambiato (diff leggibile da umano)
- **Perché** è cambiato (ADR o decisione del Leader)
- **Dove** è cambiato (file, componente, funzione)

## Decisione

### Struttura della Documentazione

Ogni modifica non-triviale genera un **change document** in `docs/changes/`:

```
docs/changes/YYYY-MM-DD-NNN-slug.md
```

- `YYYY-MM-DD`: data della modifica
- `NNN`: numero sequenziale della giornata (001, 002, …)
- `slug`: descrizione kebab-case, massimo 4 parole

Il documento segue il template in `docs/changes/TEMPLATE.md`.

### Campi Obbligatori del Change Document

| Campo | Contenuto |
|---|---|
| `what` | Descrizione precisa della modifica |
| `when` | Data + commit hash (aggiornato post-commit) |
| `why` | ADR di riferimento o motivazione esplicita del Leader |
| `how` | File modificati, approccio tecnico adottato |
| `tests` | Test scritti/aggiornati, loro esito |
| `impact` | Componenti potenzialmente impattati dalla modifica |
| `refs` | Link espliciti ad ADR, commit hash, issue/task |

### Ordine di Creazione

Il change document viene creato **prima del commit** (come parte della preparazione), aggiornato con il commit hash **immediatamente dopo** il commit.

### CHANGELOG.md

`CHANGELOG.md` è il sommario human-readable. Ogni change document contribuisce a una voce in CHANGELOG.md seguendo il formato [Keep a Changelog](https://keepachangelog.com/it/1.0.0/). Il CHANGELOG è aggiornato nella stessa sessione del change document.

### Integrazione GitNexus

Dopo ogni sessione con modifiche significative al codice sorgente, Claude esegue (o propone di eseguire) `gitnexus analyze` per aggiornare il grafo della conoscenza. Il grafo aggiornato è la planimetria architettuale: permette briefing rapidi e localizzazione precisa delle aree da toccare.

### Regola di Non-Ambiguità (Sistema Chiuso)

- Nessun change document senza riferimento ADR valido
- Nessun ADR senza lista di file/componenti impattati
- Nessun commit non-triviale senza change document

Il sistema è chiuso: ogni nodo punta a un altro nodo.

### Flusso di Re-Briefing

Il re-briefing ottimale dopo un'interruzione segue questa sequenza:
1. `INDEX.md` — mappa neurale degli ADR attivi
2. `ROADMAP.md` — obiettivi correnti
3. Ultimi 3 change document in `docs/changes/` — contesto recente
4. `CHANGELOG.md` — storia condensata
5. GitNexus query — planimetria del codice

## Conseguenze

- Il debug inizia sempre da `docs/changes/` → ADR → codice (mai dal contrario)
- Il tempo di re-briefing si riduce da "rileggere tutto" a "leggere 3 file"
- Le allucinazioni diminuiscono perché il contesto è sempre ricostruibile dal filesystem
- L'overhead per modifica è basso (1 file markdown) ma il ritorno informativo è alto

## Test di Conformità

- Ogni commit non-triviale ha un change document in `docs/changes/`
- Ogni change document ha un campo `why` con ADR di riferimento valido
- `CHANGELOG.md` è aggiornato con ogni change document
- Verifica: `ls docs/changes/` deve avere almeno un file per ogni N commit significativi

## Cross-References

- ADR correlati: ADR-0001 (meta-architettura), ADR-0002 (test gate), ADR-0003 (restore points)
- Governa: `docs/changes/`, `CHANGELOG.md`, processo di self-briefing
- Impatta: ogni file sorgente non-trivialmente modificato, `ROADMAP.md`
- Test: verifica strutturale manuale pre-sessione
- Commits: [da aggiornare post-commit]

## Rollback

Se un change document contiene informazioni errate, si corregge con un nuovo commit che aggiorna il documento stesso. La correzione è a sua volta un change document (campo `what`: "Correzione CHG-YYYY-MM-DD-NNN").
