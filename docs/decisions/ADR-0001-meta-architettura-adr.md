---
id: ADR-0001
title: Meta-Architettura del Sistema ADR
date: 2026-04-29
status: Active
deciders: Leader
category: meta
supersedes: —
superseded_by: —
---

## Contesto

Il progetto necessita di un sistema di Architectural Decision Records capace di:
- Auto-documentarsi (ogni ADR segue le regole definite da questo ADR)
- Mantenere tracciabilità bidirezionale tra decisioni, codice, test e commit
- Sopravvivere a lunghe interruzioni e re-briefing minimali
- Minimizzare le allucinazioni dell'IA riducendo l'ambiguità contestuale

Questo ADR è la **volontà** del sistema: definisce come ogni altra decisione viene formalizzata, collegata e mantenuta. È auto-referenziale: segue il template che esso stesso definisce.

## Decisione

### Template Obbligatorio

Ogni ADR deve essere scritto secondo il template in `docs/decisions/TEMPLATE.md`. Nessun campo può essere omesso; i campi non applicabili usano il valore `—`.

### Naming Convention

```
ADR-NNNN-slug-descrittivo.md
```
- `NNNN`: numero sequenziale zero-paddato (0001, 0002, …)
- `slug`: titolo kebab-case, massimo 5 parole

### Categorie

| Categoria | Scopo |
|---|---|
| `meta` | Governance del sistema ADR stesso |
| `process` | Workflow operativi (test, commit, deploy) |
| `architecture` | Decisioni strutturali sul codice |
| `tooling` | Strumenti e integrazioni esterne |

### Ciclo di Vita degli Status

```
Proposed → Active → Deprecated
                  ↘ Superseded (da ADR-XXXX)
```

Un ADR `Active` non viene mai modificato retroattivamente. In caso di revisione si crea un nuovo ADR con `supersedes: ADR-NNNN`. L'ADR originale riceve `superseded_by: ADR-YYYY` e status `Superseded`.

### INDEX.md — Mappa Neurale

`docs/decisions/INDEX.md` è il grafo relazionale degli ADR. Ogni ADR aggiunto o modificato aggiorna INDEX.md **prima** di essere considerato ratificato, con:
- ID, titolo, status, categoria, data
- Dipendenze (ADR che questo ADR presuppone)
- Impatti (componenti o ADR che questo ADR governa)

### Cross-Reference Obbligatorio

Ogni ADR deve dichiarare esplicitamente nella sezione **Cross-References**:
- Gli ADR correlati (con ID)
- I file o componenti che governa
- I test che ne verificano la conformità
- I commit rilevanti (aggiornati a posteriori con hash)

### Regola di Non-Cancellazione

La cancellazione di un ADR è proibita. Si usa lo status `Deprecated` con motivazione, o `Superseded` con riferimento al successore.

## Conseguenze

- Claude non può proporre modifiche a componenti non coperti da un ADR `Active` senza prima segnalare il gap e richiedere una decisione al Leader.
- Ogni nuovo ADR aggiorna INDEX.md prima di essere operativo.
- Il sistema è chiuso e auto-consistente: ogni nodo punta ad altri nodi.

## Test di Conformità

- Ogni ADR in `docs/decisions/` è referenziato in `INDEX.md`.
- Ogni ADR contiene tutti i campi obbligatori del `TEMPLATE.md`.
- Nessun ADR ha status `Active` senza sezione Cross-References compilata.
- Verifica: revisione manuale pre-commit della struttura.

## Cross-References

- ADR correlati: nessuno (ADR fondativo, tutti gli altri dipendono da questo)
- Governa: tutti gli ADR, `docs/decisions/INDEX.md`, `docs/decisions/TEMPLATE.md`
- Impatta: `CLAUDE.md` (workflow), ogni futuro ADR
- Test: verifica strutturale manuale pre-commit
- Commits: [da aggiornare post-commit]

## Rollback

Non applicabile come ADR singolo. In caso di revisione fondamentale, creare ADR-XXXX che supersede ADR-0001 con motivazione esplicita del Leader.
