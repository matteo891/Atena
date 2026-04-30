---
id: CHG-2026-04-30-023
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Pending
commit: TBD
adr_ref: ADR-0010, ADR-0009, ADR-0008, ADR-0003
---

## What

**Errata corrige di ADR-0010** (Self-Briefing Hardening): aggiunta esplicita di una verifica `git tag -l 'checkpoint/*' 'milestone/*'` allo Step 1 del Self-Briefing, attivata quando `docs/STATUS.md` afferma esistenza, proposta o assenza di un tag specifico. Lo scenario di mancata verifica si è materializzato oggi: STATUS marcava `checkpoint/2026-04-30-03` come "in attesa autorizzazione" mentre il tag esisteva già da 6 ore.

| File | Tipo | Cosa |
|---|---|---|
| `docs/decisions/ADR-0010-self-briefing-hardening.md` | modificato | Frontmatter `errata:` esteso; Step 1 della sequenza re-briefing arricchito con sub-bullet "verifica `git tag -l` se STATUS afferma stato di tag"; nuova riga in Test di Conformità; sezione `## Errata` aggiunta in coda; campo `Commits:` riallineato (da placeholder `[da aggiornare post-commit]` a `416ab87` + commit di questo errata) |
| `docs/changes/2026-04-30-023-errata-adr-0010-tag-verification.md` | nuovo | questo change document |

Niente codice. Modifiche di sola governance documentale (file `.md` sotto `docs/`). Test gate ADR-0011: test manuali documentati ammessi.

## Why

Sessione 2026-04-30 (questa): durante CHG-019→022 ho aggiornato ripetutamente STATUS.md scrivendo riga "CHECKPOINT-03 — Tag `checkpoint/2026-04-30-03` proposto, in attesa autorizzazione". Quando il Leader ha autorizzato la creazione, la verifica `git tag -l` ha mostrato che il tag esisteva già su `e563e59` (creato 15:50 post-CHG-018). STATUS era stale di 4 CHG.

**Causa radice:** ADR-0010 dichiara la sequenza canonica del Self-Briefing ma **non specifica esplicitamente** che lo Step 1 (lettura di STATUS.md) deve essere bilanciato da una verifica indipendente quando STATUS afferma fatti su risorse del repository (tag, branch, hash di commit pubblicati). La regola "ogni claim ancorato" di ADR-0010 (Regola 2) copre il **caso scrittore** (chi modifica STATUS deve agganciare ad ancore verificabili) ma non il **caso lettore** (chi rilegge STATUS deve confermare che le ancore puntino ancora alla realtà attuale).

In conseguenza: ADR-0008 Regola "STATUS prevale sulla memoria di Claude" si combina con assenza di verifica reciproca → STATUS stale può sopravvivere indefinitamente.

L'errata corrige inscrive la **verifica reciproca**: se STATUS dice "il tag X esiste / non esiste / è proposto", chi legge esegue `git tag -l X` (o l'equivalente per branch/hash) prima di agire. Costo: <1 secondo. Beneficio: chiude la classe di errori "STATUS stale propaga decisioni sbagliate".

ADR-0009 ammette **errata corrige** per "chiarimenti di convenzione interpretativa" — è esattamente questo caso: chiarimento operativo di Step 1 senza supersessione.

## How

### Modifiche puntuali al testo di ADR-0010

**Frontmatter:**

```yaml
errata:
  - date: 2026-04-30
    chg: CHG-2026-04-30-023
    summary: "Step 1 esteso con sub-bullet 'verifica reciproca STATUS↔git per claim su tag/branch/hash pubblicati', via `git tag -l` o equivalente. Test di Conformità arricchito con scenario corrispondente."
```

**Sezione "Sequenza di Re-Briefing — Fonte Unica":** sotto la riga `1. docs/STATUS.md` aggiungo un sub-bullet:

> Quando STATUS afferma esistenza, proposta, o assenza di un tag git, di un branch, o di un commit hash specifico, lo Step 1 include la verifica reciproca con il repository (`git tag -l '<pattern>'`, `git branch --list`, `git log <hash>`). Se la verifica diverge da STATUS, segnalarlo al Leader e correggere STATUS prima di agire — STATUS è fonte di verità sulla **storia documentata**, non sullo **stato git corrente** quando i due possono divergere.

**Sezione `## Test di Conformità`:** aggiunta una riga in tabella:

> | STATUS afferma tag/branch/hash, repo dice diversamente | Errore di rilettura, segnalare al Leader, correggere STATUS prima di agire |

**Sezione `## Errata` (nuova):** entry datata con sintesi della modifica e motivazione.

**Campo `Commits:`** — sostituito il placeholder `[da aggiornare post-commit]` con `416ab87` (commit originale di hardening v0.5.0) + commit di questo errata (TBD).

### Test di conformità (manuale, documentato — ADR-0011)

| Comando | Esito atteso | Esito |
|---|---|---|
| `head -16 docs/decisions/ADR-0010-self-briefing-hardening.md \| grep -A4 'errata:'` | mostra entry 2026-04-30 / CHG-023 | atteso ✅ |
| `grep -n 'verifica reciproca STATUS' docs/decisions/ADR-0010-self-briefing-hardening.md` | presente nel corpo | atteso ✅ |
| `grep -n '## Errata' docs/decisions/ADR-0010-self-briefing-hardening.md` | sezione presente in coda | atteso ✅ |
| `grep -E '^## ' docs/decisions/ADR-0010-self-briefing-hardening.md` | 6 sezioni canoniche + `## Errata` | atteso ✅ |
| Pre-commit hook (file ADR modificato → check sezioni) | PASS | atteso ✅ |

Niente test runtime: la modifica è documentale e non tocca codice eseguibile.

### Out-of-scope

- **Automazione della verifica reciproca** (es. test governance che fa `diff <git tag -l> <STATUS claims>`): valutata e scartata per questa fase. Costo di costruzione > beneficio attuale (3 checkpoint totali, basso volume).
- **Estensione retroattiva ad altri ADR** che potrebbero contenere riferimenti staling-prone: scope futuro se emergeranno casi simili.
- **Tooling dedicato alla freshness di STATUS** (es. script `check-status-freshness.sh`): scope se il problema si ripresenta dopo questa errata.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Verifica struttura ADR | `grep -E '^## ' docs/decisions/ADR-0010-self-briefing-hardening.md` | atteso ✅ |
| Pre-commit hook | (al commit reale) | atteso ✅ |
| Quality gate | `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/` | atteso ✅ (no codice toccato → invariato) |
| Test suite | `uv run pytest tests/unit tests/governance -q` | atteso ✅ 171 PASS (invariato) |

**Rischi residui:**
- La verifica `git tag -l` aggiunta è in linguaggio naturale, non meccanica. Se in futuro emergono altri pattern di stale data in STATUS (oltre tag/branch/hash), serve estendere la regola.
- `## Errata` sezione facoltativa: il pre-commit hook controlla solo le 6 sezioni canoniche obbligatorie, quindi non valida la struttura interna di `## Errata`. Coerenza affidata alla disciplina umana.

## Refs

- ADR: ADR-0010 (oggetto dell'errata), ADR-0009 (meccanismo errata corrige), ADR-0008 (regola "STATUS prevalente"), ADR-0003 (governa i tag — oggetto del fail)
- Predecessore: CHG-2026-04-30-022 (formula L11b — chiusura sessione applicativa); errore di rappresentazione emerso al passaggio successivo
- Successore atteso: applicazione della verifica reciproca al prossimo Self-Briefing
- Commit: TBD (in attesa di permesso esplicito Leader)
