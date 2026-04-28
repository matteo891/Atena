---
id: ADR-0005
title: Commit Message Convention
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

Senza una convenzione di commit message strutturata, `git log` è cieco rispetto al sistema ADR: non è possibile navigare da un commit al suo change document o alla decisione architetturale che lo ha motivato. La navigazione bidirezionale richiede che ogni commit non-triviale porti con sé i riferimenti espliciti ai documenti che lo governano.

## Decisione

### Formato Obbligatorio

```
<type>(<scope>): <descrizione imperativa, max 72 char>

[body opzionale — solo se il subject non è autoesplicativo, max 3 righe]

CHG-YYYY-MM-DD-NNN
ADR-NNNN
```

### Campi

| Campo | Obbligatorio | Valori ammessi | Esempio |
|---|---|---|---|
| `type` | Sì | `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci` | `feat` |
| `scope` | Consigliato | nome modulo/componente, kebab-case | `(auth)` |
| `descrizione` | Sì | imperativo, lowercase, niente punto finale | `add login validation` |
| `CHG-ID` | Sì (non-triviale) | `CHG-YYYY-MM-DD-NNN` | `CHG-2026-04-29-001` |
| `ADR-ID` | Sì (non-triviale) | `ADR-NNNN` | `ADR-0002` |

### Commit Triviali (Esentati da CHG-ID e ADR-ID)

I commit che modificano **solo** file `.md` o `docs/` usano il prefisso `docs` o `chore` e non richiedono footer:

```
docs(decisions): add ADR-0005 commit message convention
chore(hooks): fix pre-commit newline handling
```

### Esenzione di Emergenza (ADR-0002)

```
fix(auth): [EMERGENCY-NO-TEST] patch session token expiry

CHG-2026-04-29-002
ADR-0002
```

Il CHG-ID rimane obbligatorio anche in emergenza se il change document esiste.

### Convenzione CHANGELOG → Change Document

Ogni voce nel `CHANGELOG.md` per commit non-triviali include il link al change document:

```markdown
- Aggiunta validazione login ([CHG-2026-04-29-001](docs/changes/2026-04-29-001-login-validation.md))
```

Questo chiude il ciclo: CHANGELOG → change doc → ADR → commit.

## Conseguenze

- `git log --grep="CHG-"` restituisce tutti i commit non-triviali con change document associato
- Da qualsiasi commit è possibile risalire a: change doc → ADR → files coinvolti → test
- Il `commit-msg` hook (ADR-0006) verifica il formato meccanicamente
- La navigazione è completamente bidirezionale in ogni direzione del grafo

## Test di Conformità

- `git log --oneline | grep -v "^docs\|^chore\|^ci"` — tutti i risultati devono contenere `CHG-`
- Tentare un commit non-triviale con message mancante di CHG-ID: il hook deve bloccarlo
- Tentare un commit `docs(scope): ...` senza CHG-ID: deve passare

## Cross-References

- ADR correlati: ADR-0001 (meta), ADR-0002 (test gate), ADR-0004 (cross-reference doc), ADR-0006 (hooks)
- Governa: formato di ogni commit message non-triviale
- Impatta: `git log`, `CHANGELOG.md`, `docs/changes/`
- Test: commit-msg hook (ADR-0006)
- Commits: [da aggiornare post-commit]

## Rollback

Se la convenzione viene cambiata, i commit precedenti restano nel formato originale. La transizione è documentata nel nuovo ADR che supersede ADR-0005, con nota esplicita in `CHANGELOG.md`.
