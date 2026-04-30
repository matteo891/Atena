---
id: ADR-0007
title: GitNexus come Planimetria Architetturale
date: 2026-04-29
status: Active
deciders: Leader
category: tooling
supersedes: —
superseded_by: —
errata:
  - date: 2026-04-30
    chg: CHG-2026-04-30-024
    summary: "Sezione 'Stato Attuale' aggiornata: indice operativo dal 2026-04-30 dopo downgrade Node a v22 e rebuild riuscito (1646 nodes / 1929 edges / 12 clusters / 4 flows). ISS-001 chiusa. Test di Conformità arricchito: Step 4 esige verifica empirica via `mcp__gitnexus__list_repos`; auto-rebuild se l'indice è stale rispetto a HEAD; 'GitNexus non disponibile' è ammesso solo dopo errore tecnico effettivo, citato come ancora."
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

Al momento della promulgazione di questo ADR (2026-04-29), `gitnexus analyze` non era ancora stato eseguito. ISS-001 (segfault su Node v24.15.0) ha bloccato l'esecuzione fino al 2026-04-30. Dal 2026-04-30, dopo downgrade della toolchain Node a v22.22.2 (Node v24 disinstallato dalla macchina locale) e rebuild riuscito in 3.3s (`Repository indexed successfully — 1,646 nodes | 1,929 edges | 12 clusters | 4 flows`, CHG-2026-04-30-024), l'indice è operativo e referenziato come `lastCommit == git rev-parse HEAD`. ISS-001 è chiusa.

**Vincolo toolchain (errata 2026-04-30 / CHG-024):** l'esecuzione di `gitnexus analyze` deve avvenire su Node v22.22.2 (o versioni successive che non riproducano il segfault di v24.15.0). nvm con `node --version` fornisce la verifica.

## Conseguenze

- Il self-briefing scende da O(codebase) a O(query) dopo ogni `gitnexus analyze`
- Le modifiche ad alto impatto vengono rilevate prima del commit via `mcp__gitnexus__impact`
- Il grafo diventa stale se non aggiornato dopo sessioni con modifiche al codice
- Senza `gitnexus analyze`, il self-briefing funziona ma è più lento (fallback manuale)

## Test di Conformità

- Dopo `gitnexus analyze`: `mcp__gitnexus__query(query="test")` deve restituire risultati.
- Il grafo deve essere aggiornato entro la fine di ogni sessione con modifiche al codice sorgente.
- **Step 4 del Self-Briefing** (errata 2026-04-30 / CHG-024): `mcp__gitnexus__list_repos` deve essere chiamata empiricamente prima di accettare qualsiasi claim documentale di indisponibilità presente in STATUS.
- Output di `list_repos`: campo `staleness` assente e `lastCommit == git rev-parse HEAD`. Se diverge, eseguire `npx -y gitnexus analyze` (su Node v22) prima di proseguire con il Self-Briefing.
- Solo se la chiamata MCP fallisce con errore tecnico esplicito (transport error, server non risponde, timeout) è ammesso dichiarare "GitNexus non disponibile" — l'errore va citato verbatim come ancora nello STATUS.md.

## Cross-References

- ADR correlati: ADR-0001 (meta), ADR-0004 (cross-reference doc)
- Governa: utilizzo del server MCP GitNexus, `.gitnexus/`, self-briefing step 1
- Impatta: velocità del self-briefing, impact analysis pre-modifica, `FILE-ADR-MAP.md`
- Test: `mcp__gitnexus__query` restituisce risultati post-analyze
- Commits: introduzione (CHG-2026-04-29-001) + commit dell'errata CHG-2026-04-30-024 (chiusura ISS-001 + arricchimento Test di Conformità)

## Rollback

Se GitNexus non è disponibile o produce risultati inaffidabili, il self-briefing degrada a:
1. `INDEX.md` — mappa neurale ADR
2. `docs/changes/` — ultimi 3 change documents
3. `CHANGELOG.md` — storia condensata
4. Lettura diretta dei file sorgente pertinenti

Il sistema è resiliente per design: GitNexus è un acceleratore, non un single point of failure.

## Errata

### 2026-04-30 — CHG-2026-04-30-024

- **Tipo:** errata corrige (chiarimento di stato + arricchimento Test di Conformità).
- **Modifica:**
  - Sezione "Stato Attuale": riscritta. Il database non è più vuoto; l'indice è operativo dal 2026-04-30 post-rebuild su Node v22 (1646 nodes / 1929 edges / 12 clusters / 4 flows). ISS-001 chiusa.
  - Aggiunto vincolo toolchain: `gitnexus analyze` su Node v22.22.2 (Node v24.15.0 sconsigliato — segfault verificato e tracciato in ISS-001).
  - Sezione "Test di Conformità": aggiunte tre righe sul Step 4 del Self-Briefing — chiamata empirica obbligatoria via `mcp__gitnexus__list_repos`, condizioni di freshness (`lastCommit == HEAD` e `staleness` assente), regola di ammissibilità per "GitNexus non disponibile" (solo dopo errore tecnico effettivo citato verbatim).
  - Frontmatter `errata:` introdotto (mancava).
- **Motivo:** sessione 2026-04-30 ha dichiarato Step 4 "non disponibile" basandosi sul claim ISS-001 stale di STATUS, senza alcuna verifica empirica. La chiamata MCP è risposta immediatamente; il rebuild su Node v22 è completato in 3.3s. ISS-001 era documentale, non runtime. Questo errata inscrive nei Test di Conformità di ADR-0007 lo stesso principio inscritto in ADR-0010 errata 2026-04-30 / CHG-024 (verifica reciproca STATUS↔runtime tooling), specializzato su GitNexus.
