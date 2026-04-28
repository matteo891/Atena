---
id: ADR-0007
title: GitNexus come Planimetria Architetturale
date: 2026-04-29
status: Active
deciders: Leader
category: tooling
supersedes: —
superseded_by: —
---

## Contesto

Il self-briefing basato solo su file markdown ha un limite: è O(codebase). Man mano che il progetto cresce, rileggere tutto per capire dove mettere le mani diventa insostenibile. GitNexus costruisce un knowledge graph del codice sorgente (simboli, dipendenze, flussi di esecuzione, relazioni tra moduli) e lo rende interrogabile via MCP. Questo grafo è la **planimetria** del progetto: permette briefing rapidi su "cosa tocca X", "da dove arriva Y", "se modifico Z cosa si rompe".

## Decisione

### Quando Eseguire `gitnexus analyze`

| Trigger | Azione | Priorità |
|---|---|---|
| Prima sessione su un clone nuovo | Eseguire `gitnexus analyze` | Obbligatoria |
| Fine sessione con modifiche a file sorgente | Claude propone `gitnexus analyze` | Obbligatoria |
| Inizio sessione se l'ultimo analyze è > 1 sessione fa | Claude esegue `gitnexus analyze` nel self-briefing | Obbligatoria |
| Aggiunta/rimozione di moduli o directory sorgente | Claude propone `gitnexus analyze` | Obbligatoria |
| Sessione di sola documentazione | Non necessario | — |

### Utilizzo nel Self-Briefing (Step 1 — CLAUDE.md)

```
mcp__gitnexus__query(query="stato architetturale corrente", goal="orientamento rapido")
```

Per sessioni di modifica su un componente specifico, aggiungere:
```
mcp__gitnexus__impact(name="ComponenteTarget")   ← cosa si rompe se tocco X
mcp__gitnexus__context(name="SimboloSpecifico")  ← 360° su un simbolo
```

### Integrazione con ADR e FILE-ADR-MAP

Dopo ogni `gitnexus analyze`, verificare che:
1. I file indicati nel campo "Governa" degli ADR `Active` esistano ancora nel grafo
2. I flussi di esecuzione descritti negli ADR corrispondano a quelli effettivi
3. `docs/decisions/FILE-ADR-MAP.md` sia aggiornata con i nuovi componenti emersi dall'analisi

GitNexus è la fonte di verità per "il codice è così"; gli ADR sono la fonte di verità per "il codice deve essere così". La divergenza tra i due è un segnale di ADR stale o di violazione architetturale.

### Configurazione

Il database GitNexus risiede in `.gitnexus/` (già presente nel repository). Per indicizzare:

```bash
gitnexus analyze
```

Il server MCP GitNexus (`mcp__gitnexus__*`) è già configurato nell'ambiente Claude Code. Funziona solo dopo che il database è stato popolato da `gitnexus analyze`.

### Stato Attuale

Al momento della promulgazione di questo ADR (2026-04-29), `gitnexus analyze` non è ancora stato eseguito. Il database è vuoto. Il self-briefing degrada al fallback manuale (ADR + change docs + CHANGELOG) finché non viene eseguita la prima analisi.

**Azione richiesta al Leader:** autorizzare l'esecuzione di `gitnexus analyze` nella prossima sessione operativa.

## Conseguenze

- Il self-briefing scende da O(codebase) a O(query) dopo ogni `gitnexus analyze`
- Le modifiche ad alto impatto vengono rilevate prima del commit via `mcp__gitnexus__impact`
- Il grafo diventa stale se non aggiornato dopo sessioni con modifiche al codice
- Senza `gitnexus analyze`, il self-briefing funziona ma è più lento (fallback manuale)

## Test di Conformità

- Dopo `gitnexus analyze`: `mcp__gitnexus__query(query="test")` deve restituire risultati
- Il grafo deve essere aggiornato entro la fine di ogni sessione con modifiche al codice sorgente

## Cross-References

- ADR correlati: ADR-0001 (meta), ADR-0004 (cross-reference doc)
- Governa: utilizzo del server MCP GitNexus, `.gitnexus/`, self-briefing step 1
- Impatta: velocità del self-briefing, impact analysis pre-modifica, `FILE-ADR-MAP.md`
- Test: `mcp__gitnexus__query` restituisce risultati post-analyze
- Commits: [da aggiornare post-commit]

## Rollback

Se GitNexus non è disponibile o produce risultati inaffidabili, il self-briefing degrada a:
1. `INDEX.md` — mappa neurale ADR
2. `docs/changes/` — ultimi 3 change documents
3. `CHANGELOG.md` — storia condensata
4. Lettura diretta dei file sorgente pertinenti

Il sistema è resiliente per design: GitNexus è un acceleratore, non un single point of failure.
