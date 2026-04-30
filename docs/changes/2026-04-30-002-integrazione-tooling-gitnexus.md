---
id: CHG-2026-04-30-002
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: <pending>
adr_ref: ADR-0007, ADR-0006, ADR-0003
---

## What

Integrazione del tooling **GitNexus** condiviso nel repository (componente di ADR-0007), e creazione del milestone tag `milestone/stack-frozen-v0.9.0` come restore point pre-codice (ADR-0003).

Componenti:
- Blocco `<!-- gitnexus:start -->…end -->` in `CLAUDE.md` (auto-iniettato da `gitnexus init`) — già presente sul filesystem dalla sessione precedente, ora committato formalmente
- `AGENTS.md` come gemello multi-agent (Cursor / Cline / Aider)
- `.claude/skills/gitnexus/` — 6 skill condivise per uso operativo di GitNexus tramite Claude Code
- `.gitignore` esteso: esclude `settings.local.json` (machine-specific) e l'intera directory `.gitnexus/` (lock SQLite, WAL, `meta.json` con path assoluti machine-specific). Il bot CI di ADR-0020 userà `git add -f .gitnexus/` esplicito quando reindexerà post-merge — coerente con la fase governance corrente in cui non c'è un knowledge graph "vero" committato (ISS-001 aperta)
- `git rm --cached` su `.gitnexus/lbug` e `.gitnexus/lbug.wal` (lock SQLite tracciati per errore: `lbug.wal` era già stato cancellato fisicamente, `lbug` ancora modificato)
- `scripts/hooks/{pre-commit,commit-msg}` cambio modalità a `100755` (executable bit ripristinato; **comportamento immutato** — solo metadata file)

Chiusura della sessione 2026-04-30 con creazione tag `milestone/stack-frozen-v0.9.0` (decisione esplicita Leader, ADR-0003).

## Why

ADR-0007 governa l'integrazione di GitNexus come planimetria architetturale. La sessione precedente (interrotta) aveva eseguito `gitnexus init` localmente, che ha:
1. Aggiunto il blocco GitNexus a `CLAUDE.md`
2. Creato `AGENTS.md` come allineamento multi-agent
3. Popolato `.claude/skills/gitnexus/` con 6 skill operative

Senza questo CHG quei file rimarrebbero **untracked**, perdendo:
- Allineamento di ogni futuro Claude/agent al protocollo di uso obbligatorio di GitNexus prima di edit (sezione "Always Do" / "Never Do")
- Disponibilità delle skill operative (exploring, impact-analysis, debugging, refactoring, guide, cli) ai contributor che clonano il repo

Il `.gitignore` è necessario per non sporcare il working tree di chiunque cloni il repo con i lock SQLite di GitNexus quando il tool gira localmente.

I cambi `100644 → 100755` sugli hook scripts sono side-effect benigni (probabilmente di un rerun di `setup-hooks.sh` o di una toolchain): allineano i permessi a quanto è già il comportamento atteso (script eseguibili da git).

**Tag `milestone/stack-frozen-v0.9.0`:** decisione Leader esplicita. Restore point cruciale prima del bootstrap del primo modulo di codice. Il Leader sta clonando `Atena-Core` da questo stato di **purezza infrastrutturale** (zero codice applicativo, ADR cardine completi). Coerente con ADR-0003 (milestone per ADR completamente implementato — qui per il cluster 0013–0021).

## How

### File aggiunti / modificati

- `CLAUDE.md` — già modificato dalla sessione precedente con blocco GitNexus auto-iniettato; ora committato (diff: solo aggiunta in coda, nessuna modifica alla sezione governance esistente)
- `AGENTS.md` — nuovo file (untracked → tracked); contenuto identico al blocco GitNexus di CLAUDE.md, per agent diversi da Claude Code
- `.gitignore` — riscritto: 4 esclusioni runtime invece di `.gitnexus` totale; commenti esplicativi inline
- `.claude/skills/gitnexus/{gitnexus-cli,gitnexus-debugging,gitnexus-exploring,gitnexus-guide,gitnexus-impact-analysis,gitnexus-refactoring}/` — 6 directory skill (solo i file `SKILL.md` e annessi, nessuna config locale)
- `scripts/hooks/pre-commit` — chmod 100755 (no content diff)
- `scripts/hooks/commit-msg` — chmod 100755 (no content diff)
- `docs/STATUS.md` — backfill commit hash CHG-001 (`8cd06f7`), header `Ultimo aggiornamento` aggiornato

### File rimossi dal tracking (filesystem intatto)

- `.gitnexus/lbug` — `git rm --cached` (rimosso dall'index; rimane sul filesystem perché è il lock SQLite di runtime di GitNexus)
- `.gitnexus/lbug.wal` — `git rm` (era già `D` nel working tree; ora rimosso anche dall'index)

### File esplicitamente NON committati

- `.claude/settings.local.json` — escluso da `.gitignore`; contiene preferenze permission machine-specific che non vanno nel repo

### Tag GitHub

```bash
git tag -a milestone/stack-frozen-v0.9.0 -m "Stack ADR cluster 0013-0021 promulgato; repo in stato di purezza infrastrutturale (zero codice applicativo); fonte di clone per Atena-Core."
git push origin milestone/stack-frozen-v0.9.0
```

Eseguito **dopo** il commit di questo CHG (ADR-0003 + ADR-0011 push immediato dei tag).

## Tests

Test manuali documentati (governance — ADR-0011). Modifiche sono di tooling/configurazione, nessun codice applicativo.

| Test | Comando / Verifica | Esito atteso |
|---|---|---|
| `CLAUDE.md` contiene blocco GitNexus | `grep '<!-- gitnexus:start -->' CLAUDE.md` | PASS |
| `AGENTS.md` esiste e contiene blocco GitNexus | `test -f AGENTS.md && grep -q '<!-- gitnexus:start -->' AGENTS.md` | PASS |
| `.gitignore` esclude `settings.local.json` | `grep -F '.claude/settings.local.json' .gitignore` | PASS |
| `.gitignore` esclude `.gitnexus/` (runtime locale) | `grep -E '^\.gitnexus/' .gitignore` | PASS |
| 6 skill GitNexus presenti | `ls .claude/skills/gitnexus/ \| wc -l` = 6 | PASS |
| `.gitnexus/lbug` non tracciato dopo `git rm --cached` | `git ls-files .gitnexus/lbug` (vuoto) | PASS |
| `.gitnexus/lbug.wal` non tracciato | `git ls-files .gitnexus/lbug.wal` (vuoto) | PASS |
| Hook eseguibili | `test -x scripts/hooks/pre-commit && test -x scripts/hooks/commit-msg` | PASS |
| Hook content invariato (solo chmod) | `git log --oneline -p scripts/hooks/ \| grep -c '^[+-]' < 10` (delta minima) | PASS |
| STATUS.md header aggiornato con `8cd06f7` | `head -10 docs/STATUS.md \| grep '8cd06f7'` | PASS |
| Tag `milestone/stack-frozen-v0.9.0` annotato | `git tag -l 'milestone/stack-frozen-v0.9.0' && git cat-file -t milestone/stack-frozen-v0.9.0` (tag) | PASS post-tag |
| Tag pushato a origin | `git ls-remote origin refs/tags/milestone/stack-frozen-v0.9.0` (output non vuoto) | PASS post-push |
| FILE-ADR-MAP.md include `AGENTS.md` + `.claude/skills/gitnexus/` | `grep -F 'AGENTS.md' docs/decisions/FILE-ADR-MAP.md && grep -F '.claude/skills/gitnexus' docs/decisions/FILE-ADR-MAP.md` | PASS |

**Copertura:** verifica strutturale completa dell'integrazione tooling. Comportamento operativo delle skill (es. invocazione `gitnexus_impact` da skill exploring) sarà verificato in fase d'uso quando GitNexus diventerà operativo da PC del Leader (ISS-001).

**Rischi residui:**
- ISS-001 ancora aperta (`gitnexus analyze` segfault sulla macchina locale): le skill esistono nel repo ma non sono testabili end-to-end finché il Leader non opera da PC compatibile.
- Il bot CI GitNexus (ADR-0020 `gitnexus.yml`) richiederà Errata Corrige di ADR-0006 per esentare i commit `[skip ci]` di `github-actions[bot]` dal `commit-msg` hook governance. Modifica side-decision sotto-dichiarata in ADR-0020, applicata alla prima introduzione di codice CI.
- Tag `milestone/stack-frozen-v0.9.0` è immutabile (ADR-0003); cambia solo via nuovo tag con suffisso (es. `-fix`).

## Refs

- ADR: ADR-0007 (GitNexus integration), ADR-0006 (governance hooks — chmod), ADR-0003 (milestone tag)
- Predecessore: CHG-2026-04-30-001 (promulgazione ADR di stack)
- Commit: `<pending>`
- Tag: `milestone/stack-frozen-v0.9.0` (post-CHG)
- Issue: HARD-STOP attiva post-tag (decisione Leader)
