---
id: ADR-0006
title: Git Hooks Enforcement
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

I protocolli definiti in ADR-0001, ADR-0002, ADR-0004 e ADR-0005 sono attualmente enforcement comportamentale: dipendono dalla disciplina di Claude e del Leader. Un singolo commit fatto senza rispettare i protocolli rompe silenziosamente l'integrità del sistema — e in un contesto dove "un errore costa carissimo", il rischio è inaccettabile. I git hooks trasformano l'enforcement da comportamentale a meccanico: il sistema fisicamente impedisce i commit non conformi.

## Decisione

### Hook 1: `pre-commit`

**File:** `scripts/hooks/pre-commit`
**Trigger:** prima della creazione di ogni commit

**Verifica 1 — Change Document (ADR-0002, ADR-0004):**
Se esistono file non-triviali in staging, controlla che esista almeno un change document in `docs/changes/` per la data corrente (escluso `TEMPLATE.md`). In assenza, il commit è bloccato con diagnostica.

**Verifica 2 — Struttura ADR (ADR-0001):**
Se esistono nuovi file ADR in staging (`docs/decisions/ADR-*.md`), controlla che contengano tutte le sezioni obbligatorie del template e che siano referenziati in `INDEX.md`. In assenza, il commit è bloccato con diagnostica.

**File non-triviali:** qualsiasi file che non sia `.md`, `docs/`, `.claude/`, `.gitnexus/`, `.gitignore`, `.gitattributes`.

### Hook 2: `commit-msg`

**File:** `scripts/hooks/commit-msg`
**Trigger:** dopo la scrittura del commit message, prima della creazione del commit

**Verifica — Formato ADR-0005:**
Se il commit message non inizia con `docs(`, `chore(`, `ci(` e non contiene `[EMERGENCY-NO-TEST]`, controlla la presenza di `CHG-YYYY-MM-DD-NNN` nel message. In assenza, il commit è bloccato con diagnostica.

### Attivazione (Obbligatoria ad ogni Clone)

```bash
bash scripts/setup-hooks.sh
```

Configura `git config core.hooksPath scripts/hooks` e imposta i permessi di esecuzione.

### File Tracciati dal Repository

```
scripts/
  hooks/
    pre-commit     ← hook bash (tracciato, executable bit gestito da git)
    commit-msg     ← hook bash (tracciato, executable bit gestito da git)
  setup-hooks.sh   ← script di attivazione (tracciato)
```

### Compatibilità Windows

Gli hook usano shebang `#!/bin/bash` e funzionano attraverso Git Bash (bundled con Git for Windows). Non sono necessarie dipendenze aggiuntive.

### Modifica degli Hook

Qualsiasi modifica agli hook è un commit non-triviale soggetto agli stessi hook che modifica. Il bootstrap (prima attivazione) è un'eccezione documentata nel change document `CHG-2026-04-29-001`.

## Conseguenze

- È fisicamente impossibile committare codice non-triviale senza change document
- È fisicamente impossibile committare ADR malformati o non indicizzati
- Il commit message malformato viene rifiutato prima della creazione del commit
- L'enforcement non dipende dalla memoria o disciplina di Claude o del Leader
- Ogni clone del repo richiede `bash scripts/setup-hooks.sh` per attivare i hook

## Test di Conformità

| Scenario | Comportamento Atteso |
|---|---|
| Commit file `.py` senza change doc oggi | BLOCCATO con diagnostica |
| Commit ADR senza sezione `## Contesto` | BLOCCATO con diagnostica |
| Commit ADR non presente in INDEX.md | BLOCCATO con diagnostica |
| Commit message senza CHG-ID (file non-triviali) | BLOCCATO con diagnostica |
| Commit `docs(scope): ...` senza CHG-ID | PASSA |
| Commit con `[EMERGENCY-NO-TEST]` | PASSA (esenzione ADR-0002) |
| Commit solo file `.md` | PASSA |

## Cross-References

- ADR correlati: ADR-0001 (struttura ADR), ADR-0002 (test gate), ADR-0004 (cross-reference), ADR-0005 (commit convention)
- Governa: `scripts/hooks/pre-commit`, `scripts/hooks/commit-msg`, `scripts/setup-hooks.sh`
- Impatta: workflow di commit per ogni sessione di Claude e del Leader
- Test: tabella "Test di Conformità" sopra (eseguire manualmente dopo setup)
- Commits: [da aggiornare post-commit]

## Rollback

Per disattivare i hook:
```bash
git config --unset core.hooksPath
```

Questo ripristina i hook standard di git (`.git/hooks/`, tipicamente vuota). I file in `scripts/hooks/` restano tracciati ma inattivi.
