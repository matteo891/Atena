---
id: ADR-0003
title: Restore Point Strategy su GitHub
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

Il costo di un errore in produzione è alto e la reversibilità è un requisito non negoziabile. Avere punti di ripristino garantiti e immutabili su GitHub permette di tornare a uno stato noto-sano in tempi minimi, senza dover ricostruire la storia git manualmente. I checkpoint su remote fungono anche da backup indipendente dal filesystem locale.

## Decisione

### Tipologie di Checkpoint

| Tipo | Trigger | Tag Format | GitHub Release |
|---|---|---|---|
| **Periodico** | Ogni 5 commit significativi su master | `checkpoint/YYYY-MM-DD-NN` | No |
| **Milestone** | ADR completamente implementato | `milestone/ADR-NNNN` | Sì, con note |
| **Manuale** | Richiesta esplicita del Leader | `manual/slug-descrittivo` | A discrezione del Leader |

`NN` nel tag periodico è un numero sequenziale per la giornata (01, 02, …).

### Definizione di "Commit Significativo"

Ai fini del conteggio soglia-5, sono **significativi** i commit che modificano codice sorgente, configurazioni runtime, o strutture dati. Sono **esclusi** dal conteggio: commit di sola documentazione, merge commit, commit di typo/whitespace.

### Procedura di Creazione Tag

```bash
# Tag annotato (sempre annotato, mai lightweight)
git tag -a <tag-name> -m "<descrizione breve dello stato>"
git push origin <tag-name>
```

Per i milestone tag, si crea anche una GitHub Release:
```bash
gh release create <tag-name> \
  --title "<titolo leggibile>" \
  --notes "<note di rilascio: cosa è stato implementato, ADR di riferimento>"
```

### Proposta Automatica di Checkpoint

Claude tiene il conteggio interno dei commit significativi dall'ultimo checkpoint. Al raggiungimento della soglia di 5, **propone proattivamente** la creazione del tag al Leader prima di procedere con il commit successivo.

### Immutabilità dei Tag

I tag di checkpoint sono **immutabili**:
- Non si forza mai il push su un tag esistente (`git push --force` su un tag è proibito)
- Non si elimina un tag di checkpoint
- In caso di errore nell'etichetta del tag, si crea `<tag-name>-corr` con nota esplicativa

### Registro Checkpoint in CHANGELOG.md

Ogni checkpoint viene registrato in `CHANGELOG.md` con:
- Tag name
- Commit hash di riferimento
- Data
- Motivazione / stato del progetto al momento del checkpoint

## Conseguenze

- La storia git è navigabile per "isole sicure" identificabili immediatamente
- Il rollback in caso di emergenza è eseguibile in meno di 5 minuti: `git checkout <tag-name>`
- I tag su GitHub sono backup indipendenti dalla branch locale e dal filesystem
- Il Leader ha visibilità chiara dei punti di ripristino disponibili

## Test di Conformità

- Verificare che ogni milestone tag abbia una GitHub Release associata: `gh release list`
- Verificare che i tag periodici esistano a intervalli di max 5 commit significativi: `git log --oneline` + `git tag -l "checkpoint/*"`
- Verificare l'immutabilità: nessun tag di checkpoint deve essere stato forzato (`git log --tags` non deve mostrare discontinuità)

## Cross-References

- ADR correlati: ADR-0001 (meta-architettura), ADR-0002 (test gate), ADR-0004 (cross-reference doc)
- Governa: strategia di tagging GitHub, gestione del remote
- Impatta: `CHANGELOG.md`, git history, GitHub repository
- Test: verifica strutturale manuale dei tag (vedi Test di Conformità)
- Commits: [da aggiornare post-commit]

## Rollback

I checkpoint sono per definizione il meccanismo di rollback primario del progetto.

```bash
# Ripristino a un checkpoint specifico (branch temporanea per ispezione)
git checkout -b recovery/<tag-name> <tag-name>

# Ripristino hard (solo su autorizzazione esplicita del Leader)
git reset --hard <tag-name>
```

In caso di rollback effettivo, documentare l'evento in `CHANGELOG.md` e in un change document dedicato.
