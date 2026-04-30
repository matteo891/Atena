---
id: CHG-2026-04-30-003
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: b92fe87
adr_ref: ADR-0006, ADR-0014, ADR-0020, ADR-0009
---

## What

**Errata Corrige di ADR-0006** (Git Hooks Enforcement) per allineare il testo dell'ADR + i due hook eseguibili alle estensioni già ratificate da ADR-0014 e ADR-0020 nella validazione bulk del 2026-04-30 (CHG-2026-04-30-001), ma fino a oggi rimaste "side-decision sotto-dichiarate". Conseguenti errata su ADR-0014 e ADR-0020 per allineare il loro testo allo stato corrente del repository.

Modifiche:

| File | Tipo | Cambio |
|---|---|---|
| `scripts/hooks/pre-commit` | implementazione | Tracciamento `HAS_PYTHON_STAGED`; nuova **Verifica 3** post-checks governance: se file Python/pyproject/uv.lock in staging, invoca `scripts/hooks/pre-commit-app` se eseguibile. Graceful skip se assente. |
| `scripts/hooks/commit-msg` | implementazione | Nuovo bypass cumulativo: marker `[skip ci]` **+** author email `github-actions[bot]@users.noreply.github.com` → exit 0. Marker da solo non basta. |
| `docs/decisions/ADR-0006-git-hooks-enforcement.md` | errata corrige | Frontmatter `errata:` esteso. Sezione "Hook 1: pre-commit" estesa con `Verifica 3`. Sezione "Hook 2: commit-msg" estesa con nota "Esenzioni bypass". Sezione `## Errata` aggiunta in coda. |
| `docs/decisions/ADR-0014-stack-linguaggio-quality-gates.md` | errata corrige | Frase "ADR-0006 verrà aggiornato... entrerà in vigore alla prima introduzione di codice Python" sostituita con stato corrente ("è stato aggiornato in CHG-003... graceful skip se assente"). Frontmatter `errata:` esteso. Sezione `## Errata` aggiunta. |
| `docs/decisions/ADR-0020-cicd-github-actions.md` | errata corrige | Frase "Hook governance va aggiornato... applicata alla prima introduzione di codice CI" sostituita con stato corrente + dettaglio bypass cumulativo. Frontmatter `errata:` esteso. Sezione `## Errata` aggiunta. |

Nessun nuovo ADR promulgato (l'errata corrige è meccanismo formale di ADR-0009: non altera la sostanza, allinea il testo).

## Why

Le decisioni di estendere `pre-commit` (chiamata a `pre-commit-app` quando applicabile) e `commit-msg` (bypass bot reindex) sono già normative dal 2026-04-30 via ADR-0014 e ADR-0020 (CHG-2026-04-30-001, validazione bulk Opzione A). Tuttavia:

1. **Il testo di ADR-0006** continuava a descrivere solo le verifiche originali (change document, struttura ADR, formato commit), senza menzionare le estensioni ratificate altrove. Un futuro Claude che leggesse solo ADR-0006 avrebbe avuto un quadro incompleto.
2. **Gli hook eseguibili** non implementavano ancora le estensioni: erano allineati al testo originale di ADR-0006, non alle decisioni di ADR-0014/0020.
3. **ADR-0014 e ADR-0020** dichiaravano "side-decision sotto-dichiarata, applicata alla prima introduzione di [codice Python | codice CI]". Ora che siamo al varco del bootstrap codice, quella frase è obsoleta: l'integrazione **deve** essere fatta *prima* del primo commit Python, non concomitante (separare governance da applicativo, ADR-0004).

Conseguenze immediate:
- Il prossimo commit Python (CHG-2026-04-30-004 — Bootstrap minimale) troverà gli hook governance già pronti a gestirlo.
- Il workflow `gitnexus.yml` di ADR-0020, quando verrà introdotto, troverà il `commit-msg` già pronto a esentare i suoi commit `[skip ci]`.
- Lo `pre-commit-app` di ADR-0014 verrà introdotto nel CHG-4 di bootstrap; finché non esiste, il governance pre-commit fa graceful skip senza bloccare.

## How

### Modifiche a `scripts/hooks/pre-commit`

- Aggiunta variabile di stato `HAS_PYTHON_STAGED=0` inizializzata.
- Nel loop di classificazione dei file in staging, dopo le check ADR/non-triviali, regex aggiuntiva `(\.py$|^pyproject\.toml$|^uv\.lock$)` setta `HAS_PYTHON_STAGED=1`.
- Dopo la **Verifica 2** (Struttura ADR), nuova **Verifica 3**:
  - Se `HAS_PYTHON_STAGED == 1` e `scripts/hooks/pre-commit-app` esiste **ed è eseguibile**, lo invoca; un exit ≠ 0 dell'hook applicativo blocca il commit con diagnostica esplicita.
  - Se il file esiste ma non è eseguibile, log `WARNING` (non blocca; il setup-hooks dovrebbe averlo reso eseguibile).
  - Se il file non esiste, graceful skip. Questo permette di avere hooks governance già "pronti" prima che `pre-commit-app` sia stato creato in fase bootstrap.

### Modifiche a `scripts/hooks/commit-msg`

- Aggiunto bypass cumulativo dopo i bypass esistenti (merge, revert, EMERGENCY-NO-TEST):
  - Se il messaggio contiene `[skip ci]` **e** `$GIT_AUTHOR_EMAIL` (con fallback a `git config user.email`) corrisponde a `github-actions[bot]@users.noreply.github.com` (regex precisa per evitare falsi positivi), allora exit 0.
  - Marker `[skip ci]` da solo (commit umano) **non bypassa**: il `commit-msg` continua a richiedere CHG-ID + ADR-NNNN come per qualsiasi altro commit. Verificato in test manuale.

### Modifiche ad ADR-0006 (errata corrige)

- Frontmatter: aggiunta voce `errata:` con summary che cita ADR-0014 + ADR-0020 + CHG-003.
- Sezione "Hook 1: pre-commit" → aggiunta `Verifica 3` (chiamata pre-commit-app).
- Sezione "Hook 2: commit-msg" → aggiunta nota "Esenzioni bypass" (bot reindex).
- Sezione `## Errata` aggiunta in coda con descrizione + motivazione + dichiarazione "Sostanza alterata: No".

### Modifiche ad ADR-0014 (errata corrige)

- Frontmatter: aggiunta voce `errata:`.
- Sezione "Effetti collaterali noti" → frase "verrà aggiornato... alla prima introduzione" → "è stato aggiornato in CHG-003... graceful skip".
- Sezione `## Errata` aggiunta.

### Modifiche ad ADR-0020 (errata corrige)

- Frontmatter: aggiunta voce `errata:`.
- Sezione "Effetti collaterali noti" → frase "va aggiornato... applicata alla prima introduzione di codice CI" → stato corrente + dettaglio bypass cumulativo (precisazione su author email obbligatorio, non solo marker).
- Sezione `## Errata` aggiunta.

### Documenti governance aggiornati

- `docs/STATUS.md`: header `Ultimo aggiornamento` + nuova riga "Appena Completato" CHG-003 + Issues Noti ridotti.
- `ROADMAP.md`: log validazioni esteso con riga 2026-04-30 errata corrige.
- `CHANGELOG.md`: nuova versione `[0.9.1]` (patch — non bumpa minor perché non aggiunge nuova decisione, allinea hook a decisioni esistenti).

## Tests

Test manuali documentati (governance — ADR-0011). Modifiche solo a hook + ADR; nessun codice applicativo coinvolto.

| Test | Comando / Verifica | Esito |
|---|---|---|
| Syntax `pre-commit` | `bash -n scripts/hooks/pre-commit` | PASS |
| Syntax `commit-msg` | `bash -n scripts/hooks/commit-msg` | PASS |
| Bot bypass cumulativo | `GIT_AUTHOR_EMAIL="...github-actions[bot]@users.noreply.github.com" bash scripts/hooks/commit-msg <(echo "[skip ci] reindex")` | PASS (exit 0) |
| Human + `[skip ci]` non bypassa | `GIT_AUTHOR_EMAIL="me@example.com" bash scripts/hooks/commit-msg <(echo "feat(x): cosa [skip ci]")` | BLOCCATO (CHG-ID mancante) — comportamento atteso |
| `pre-commit` graceful skip senza pre-commit-app | (verifica testuale: `! test -f scripts/hooks/pre-commit-app && grep "graceful skip" scripts/hooks/pre-commit`) | PASS |
| ADR-0006 frontmatter `errata:` | `grep -A1 '^errata:' docs/decisions/ADR-0006-git-hooks-enforcement.md \| grep '2026-04-30'` | PASS |
| ADR-0006 sezione `## Errata` | `grep '^## Errata$' docs/decisions/ADR-0006-git-hooks-enforcement.md` | PASS |
| ADR-0014 frontmatter `errata:` | `grep -A1 '^errata:' docs/decisions/ADR-0014-stack-linguaggio-quality-gates.md \| grep '2026-04-30'` | PASS |
| ADR-0014 sezione `## Errata` | `grep '^## Errata$' docs/decisions/ADR-0014-stack-linguaggio-quality-gates.md` | PASS |
| ADR-0020 frontmatter `errata:` | `grep -A1 '^errata:' docs/decisions/ADR-0020-cicd-github-actions.md \| grep '2026-04-30'` | PASS |
| ADR-0020 sezione `## Errata` | `grep '^## Errata$' docs/decisions/ADR-0020-cicd-github-actions.md` | PASS |
| Decisione di sostanza non alterata | Lettura sezioni `## Decisione` di ADR-0006/0014/0020: contenuto normativo immutato (verifica manuale) | PASS |

**Copertura:** verifica strutturale + funzionale degli hook + verifica formale del rispetto di ADR-0009 (errata vs supersessione). Le condizioni richieste da ADR-0009 per qualificare come errata corrige sono tutte soddisfatte:
- Non altera la decisione presa: gli hook continuano a fare lo stesso lavoro di base; le estensioni sono già normative via ADR-0014/0020.
- Non altera le conseguenze: stesse barriere per commit non conformi, più due bypass formalmente già autorizzati.
- Non altera i test di conformità: tutti i casi originali in tabella ADR-0006 passano (verificati per costruzione, le branch nuove sono additive).

**Rischi residui:**
- Il `pre-commit-app` non esiste ancora; il graceful skip è disegnato esattamente per gestire questa condizione. Quando in CHG-4 verrà creato, sarà un file eseguibile in `scripts/hooks/pre-commit-app` e i futuri commit Python saranno automaticamente coperti senza ulteriori errata.
- Il bypass del bot è `cumulativo` per ridurre l'esposizione: un attaccante che committa con email `github-actions[bot]` ma marker mancante non bypassa, e viceversa. Resta un attaccante che mente sull'email — fuori scope di un hook locale (compete a branch protection + commit signing post-MVP).
- Errata Corrige NON è un veicolo per nuove decisioni: tutte le regole nuove sono già normative via ADR-0014 e ADR-0020. Questo CHG ne incide solo l'implementazione e il testo.

## Refs

- ADR: ADR-0006 (errata corrige primaria), ADR-0014 + ADR-0020 (errata corrige secondarie per stato), ADR-0009 (meccanismo)
- Predecessore: CHG-2026-04-30-002 (tooling GitNexus + tag stack-frozen)
- Successore atteso: CHG-2026-04-30-004 (Bootstrap minimale codice — `pyproject.toml`, `src/talos/__init__.py`, `tests/conftest.py`, `scripts/hooks/pre-commit-app`)
- Commit: `b92fe87`
- Issue: HARD-STOP risolto (Leader 2026-04-30 "rompi pure l'hard stop e continua")
