---
id: CHG-2026-04-30-024
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Draft
commit: [da aggiornare post-commit]
adr_ref: ADR-0007, ADR-0010, ADR-0009, ADR-0008
---

## What

**Chiusura ISS-001 + due errata corrige incrociate** per impedire la ricorrenza dell'errore di oggi: Step 4 del Self-Briefing dichiarato "GitNexus non disponibile" senza alcuna verifica empirica, basandosi solo sul claim stale di STATUS.md. Il rebuild dell'indice è riuscito al primo tentativo.

| File | Tipo | Cosa |
|---|---|---|
| `docs/decisions/ADR-0010-self-briefing-hardening.md` | modificato | Frontmatter `errata:` esteso con voce 2026-04-30 (CHG-024). Sezione "Sequenza di Re-Briefing" arricchita con paragrafo "Verifica reciproca STATUS ↔ runtime per claim di indisponibilità tooling". Test di Conformità: nuova riga "STATUS afferma indisponibilità tooling, runtime risponde". Sezione `## Errata` aggiornata. |
| `docs/decisions/ADR-0007-gitnexus-integration.md` | modificato | Frontmatter `errata:` introdotto. Sezione "Stato Attuale" aggiornata (indice operativo, 1646 nodes / 4 flows post-rebuild 2026-04-30). Test di Conformità: aggiunta riga "Step 4 verifica empirica via `mcp__gitnexus__list_repos`; auto-rebuild se `staleness.commitsBehind > 0` o `lastCommit ≠ HEAD`". Nuova sezione `## Errata`. |
| `docs/STATUS.md` | modificato | Chiusura ISS-001 (era "Rinviata", diventa "Risolta 2026-04-30"). Aggiornamento header `Ultimo aggiornamento`. Nuova entry in "Appena Completato". "Nota al Prossimo Claude" aggiornata: GitNexus operativo, indice fresh, regola di verifica empirica allo Step 4. |
| `AGENTS.md` | modificato | Auto-aggiornato dal linter del blocco `<!-- gitnexus:start/end -->` post-rebuild: `329 symbols / 354 relationships / 0 execution flows` → `1646 / 1929 / 4`. |
| `CLAUDE.md` | modificato | Idem ad `AGENTS.md` (stesso blocco generato). |

Nessun codice applicativo toccato. Test gate ADR-0011: test manuali documentati ammessi.

## Why

### Catena dell'errore (root cause)

1. **2026-04-29:** una sessione precedente ha tentato `gitnexus analyze` con Node v24.15.0 (allora installato sulla macchina). L'eseguibile è andato in segfault / exit code 5. Ha aperto **ISS-001** marcandola "Rinviata — architettura processore incompatibile".
2. **Tra 2026-04-29 e 2026-04-30:** Node v24.15.0 è stato disinstallato dalla toolchain locale. Oggi `~/.nvm/versions/node/` contiene solo `v20.20.2` e `v22.22.2`. Il default Node è ora v22.22.2.
3. **2026-04-30 (sessione corrente, prima del fix):** il Self-Briefing ha letto STATUS.md, visto ISS-001 attiva, e ha dichiarato Step 4 "GitNexus non disponibile" senza mai chiamare il server MCP né tentare il rebuild. Errore.
4. **Verifica empirica chiesta dal Leader:** `mcp__gitnexus__list_repos` ha risposto immediatamente. Indice esistente ma stale di 55 commit, fermo a `26a1273` (2026-04-29 17:28Z). Il rebuild via `npx -y gitnexus analyze` su Node v22 è completato in 3.3s con successo (output: `Repository indexed successfully — 1,646 nodes | 1,929 edges | 12 clusters | 4 flows`).

### Causa strutturale

Lo Step 4 del Self-Briefing è formulato in CLAUDE.md come:

> 4. **GitNexus query** — `mcp__gitnexus__query` per orientamento architetturale. Se non disponibile (ISS-001): dichiarare "GitNexus non disponibile" e proseguire senza.

Questa formulazione è **asimmetrica** rispetto allo Step 0:

| Step | Verifica al re-entry | Tipo |
|---|---|---|
| Step 0 (hooks) | `git config core.hooksPath` obbligatoria, bloccante, meccanica | Empirica |
| Step 4 (GitNexus) | Lettura del flag ISS-001 in STATUS, nessuna prova runtime | **Documentale** |

Il claim di indisponibilità di un tool, scritto in STATUS in una sessione passata, sopravvive indefinitamente fino a quando qualcuno non lo rimuove esplicitamente. Nel frattempo Claude lo accetta come fatto e salta lo step. Questa è esattamente la stessa classe di errore che CHG-023 ha provato a chiudere per tag/branch/hash — ma CHG-023 era specifico al sottoinsieme git, non al tooling esterno.

### Generalizzazione (regola che si inscrive)

Ogni dichiarazione di indisponibilità tooling in STATUS richiede **verifica empirica al re-entry**, non può essere accettata dal contesto documentale. La regola si applica trasversalmente: GitNexus, MCP server vari, container, CI runner, ecc.

Per GitNexus in particolare, lo Step 4 deve eseguire `mcp__gitnexus__list_repos` (chiamata economica, no side-effect). Tre possibili outcome:

1. **Errore tecnico (server MCP non risponde, timeout, transport error):** allora e solo allora si dichiara "GitNexus non disponibile" — con citazione dell'errore come ancora.
2. **Risposta ma `staleness.commitsBehind > 0` o `lastCommit ≠ git rev-parse HEAD`:** indice stale → eseguire `npx -y gitnexus analyze` (o segnalare al Leader se la sessione lo proibisce). Se l'analyze fallisce, ALLORA documentare il fail come ancora.
3. **Risposta con `lastCommit == HEAD` e `staleness` assente:** indice fresh, Step 4 procede normalmente.

ADR-0009 ammette **errata corrige** per "chiarimento di convenzione interpretativa" — questo è il caso: chiarimento di Step 4 senza supersessione dell'ADR.

## How

### Modifiche puntuali

#### `docs/decisions/ADR-0010-self-briefing-hardening.md`

**Frontmatter `errata:`** — aggiungere voce 2026-04-30 / CHG-024:

```yaml
- date: 2026-04-30
  chg: CHG-2026-04-30-024
  summary: "Esteso il principio di verifica reciproca (CHG-023) alla classe 'claim di indisponibilità tooling'. Step 4 del Self-Briefing esige una chiamata MCP empirica (es. `mcp__gitnexus__list_repos`) prima di dichiarare il tool non disponibile; un claim documentale stale in STATUS non è sufficiente."
```

**Sezione "Sequenza di Re-Briefing — Fonte Unica":** dopo il paragrafo "Verifica reciproca STATUS ↔ git" aggiungere:

> **Verifica reciproca STATUS ↔ runtime tooling (errata 2026-04-30 / CHG-024).** Quando STATUS dichiara non disponibile uno strumento esterno (server MCP, container, runner CI, ecc.), Claude esegue una chiamata empirica economica al re-entry prima di accettare il claim. Esempi: per GitNexus, `mcp__gitnexus__list_repos`. Se la chiamata risponde, il claim documentale è obsoleto e va corretto via errata o nuovo CHG di chiusura della Issue. Se la chiamata fallisce, l'errore tecnico va citato come ancora del claim aggiornato. Solo errori effettivi giustificano il "tool non disponibile". Il principio sotteso (uguale a CHG-023): STATUS è fonte di verità sulla **storia documentata**, non sullo **stato runtime corrente** quando i due possono divergere.

**Sezione `## Test di Conformità`:** aggiunta riga:

> | STATUS afferma indisponibilità tooling, runtime risponde alla call empirica | Errore di rilettura: aggiornare STATUS (chiusura Issue o errata), procedere con lo step |

**Sezione `## Errata`:** aggiunta entry datata 2026-04-30 con sintesi e motivazione.

**Campo `Commits:`** — esteso con il commit di questo errata.

#### `docs/decisions/ADR-0007-gitnexus-integration.md`

**Frontmatter `errata:`** — introdurre (mancava):

```yaml
errata:
  - date: 2026-04-30
    chg: CHG-2026-04-30-024
    summary: "Sezione 'Stato Attuale' aggiornata: indice operativo dal 2026-04-30 post-rebuild su Node v22. Test di Conformità arricchito: Step 4 esige verifica empirica via `mcp__gitnexus__list_repos`; auto-rebuild se l'indice è stale rispetto a HEAD."
```

**Sezione "Stato Attuale":** sostituire il paragrafo "Al momento della promulgazione…" con:

> Al momento della promulgazione di questo ADR (2026-04-29), `gitnexus analyze` non era ancora stato eseguito. ISS-001 (Node v24-specific) ne ha bloccato l'esecuzione fino al 2026-04-30. Dal 2026-04-30, dopo downgrade della toolchain Node a v22.22.2 e rebuild riuscito (`Repository indexed successfully — 1,646 nodes | 1,929 edges | 12 clusters | 4 flows`, CHG-2026-04-30-024), l'indice è operativo e referenziato come `lastCommit == git rev-parse HEAD`. ISS-001 è chiusa.

**Sezione `## Test di Conformità`:** aggiungere righe (mantenendo le esistenti):

> - Step 4 del Self-Briefing: `mcp__gitnexus__list_repos` deve rispondere (chiamata di verifica empirica obbligatoria, ADR-0010 errata 2026-04-30).
> - Output di `list_repos`: campo `staleness` assente e `lastCommit == git rev-parse HEAD`. Se diverge, eseguire `npx -y gitnexus analyze` prima di proseguire.
> - Se la chiamata MCP fallisce con errore tecnico esplicito, l'errore va citato come ancora nello STATUS.md; solo allora è ammesso "GitNexus non disponibile".

**Nuova sezione `## Errata`:** in coda, con la voce 2026-04-30.

#### `docs/STATUS.md`

- Header `Ultimo aggiornamento`: aggiornato a `2026-04-30 — commit <hash CHG-024>` (post-commit).
- "Sessione corrente": estesa con "+ chiusura ISS-001: GitNexus operativo dopo rebuild su Node v22 (CHG-024)".
- Sezione "Appena Completato": nuova riga in fondo con CHG-024.
- Sezione "In Sospeso": ISS-001 marcata `~~ISS-001~~` chiusa.
- Sezione "Issues Noti": riga ISS-001 aggiornata: "Risolta 2026-04-30 — root cause: Node v24.15.0-specific segfault; risolto da downgrade a Node v22.22.2 (oggi default in nvm). Indice riallineato a HEAD (CHG-024). 1646 nodes / 1929 edges / 4 execution flows."
- "Nota al Prossimo Claude": aggiunta voce: "Step 4 self-briefing: NON saltarlo per ISS dichiarate in STATUS; eseguire sempre `mcp__gitnexus__list_repos` empirica prima. Se `staleness.commitsBehind > 0`, eseguire `npx -y gitnexus analyze` su Node v22 (Node v24 sconsigliato — vedi ISS-001 risolta)."

#### `AGENTS.md` / `CLAUDE.md`

Già aggiornati dal linter del blocco `<!-- gitnexus:start/end -->` post-rebuild. Numeri verbatim dall'output di `analyze`: `1646 symbols, 1929 relationships, 4 execution flows`. Inclusi nello stesso commit.

### Test di conformità (manuale, documentato — ADR-0011)

| # | Comando / Verifica | Esito atteso | Esito |
|---|---|---|---|
| 1 | `node --version` | `v22.22.2` | ✅ ancorato |
| 2 | `npx -y gitnexus --version` | `1.6.3` | ✅ ancorato |
| 3 | `npx -y gitnexus analyze` | `Repository indexed successfully — 1,646 nodes \| 1,929 edges \| 12 clusters \| 4 flows` | ✅ ancorato |
| 4 | `mcp__gitnexus__list_repos` | `lastCommit = 55a5ad5...`, `staleness` assente | ✅ ancorato |
| 5 | `git rev-parse HEAD` | `55a5ad5d960ad7d02c04658b4de12243539ddd73` | ✅ ancorato |
| 6 | `grep -E '^## ' docs/decisions/ADR-0010-self-briefing-hardening.md` | 6 sezioni canoniche + `## Errata` | atteso ✅ |
| 7 | `grep -E '^## ' docs/decisions/ADR-0007-gitnexus-integration.md` | 6 sezioni canoniche + `## Errata` | atteso ✅ |
| 8 | `grep -n 'verifica reciproca STATUS' docs/decisions/ADR-0010-self-briefing-hardening.md` | 2 occorrenze (CHG-023 + CHG-024) | atteso ✅ |
| 9 | `grep -n 'mcp__gitnexus__list_repos' docs/decisions/ADR-0007-gitnexus-integration.md` | presente in Test di Conformità | atteso ✅ |
| 10 | Pre-commit hook (file ADR + CHG modificati → check sezioni + footer) | PASS | atteso ✅ |
| 11 | `uv run pytest tests/unit tests/governance -q` | 171 PASS (invariato — no codice toccato) | atteso ✅ |

Niente test runtime: la modifica è documentale e non tocca codice eseguibile.

### Out-of-scope

- **Generalizzazione automatizzata** della verifica empirica al re-entry per ogni MCP server: la regola è inscritta in linguaggio naturale per ora. Tooling dedicato (es. `scripts/verify-mcp-availability.sh`) è scope futuro se il pattern si ripresenta su altri server.
- **Errata retroattiva** ad altri ADR che potrebbero contenere claim documentali stale: scope futuro caso per caso.
- **Risoluzione `embeddings: 0`** nell'indice GitNexus: non bloccante, scope futuro se serve ricerca semantica.
- **Test di governance automatizzato** che fa diff tra STATUS Issues "attive" e runtime MCP availability: valutato e scartato per questa fase (basso volume, costo > beneficio).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Verifica struttura ADR-0010 | `grep -E '^## ' docs/decisions/ADR-0010-self-briefing-hardening.md` | atteso ✅ |
| Verifica struttura ADR-0007 | `grep -E '^## ' docs/decisions/ADR-0007-gitnexus-integration.md` | atteso ✅ |
| Pre-commit hook | (al commit reale) | atteso ✅ |
| Quality gate | `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/` | atteso ✅ (no codice toccato → invariato) |
| Test suite | `uv run pytest tests/unit tests/governance -q` | atteso ✅ 171 PASS (invariato) |
| Verifica indice GitNexus post-commit | `mcp__gitnexus__list_repos` → `lastCommit == HEAD` | atteso ✅ (re-analyze post-commit per riallineare) |

**Rischi residui:**

- La regola di verifica empirica è in linguaggio naturale, non meccanica. Se in futuro emergono altri pattern di stale data in STATUS che la regola non copre (es. claim su versioni librerie, su path filesystem, su credenziali), serve estendere ulteriormente.
- L'indice GitNexus è fresh ora ma diventa stale a ogni nuovo commit. La regola di Step 4 prevede auto-rebuild ma non lo automatizza meccanicamente — affidata alla disciplina del Self-Briefing successivo.
- `## Errata` sezione facoltativa nel formato ADR (il pre-commit hook controlla solo le 6 sezioni canoniche obbligatorie). Coerenza interna affidata alla disciplina.

## Refs

- ADR: ADR-0007 (oggetto dell'errata #2), ADR-0010 (oggetto dell'errata #3 nel suo storico), ADR-0009 (meccanismo errata corrige), ADR-0008 (regola "STATUS prevalente")
- Predecessore: CHG-2026-04-30-023 (errata ADR-0010 per tag/branch/hash — questo CHG generalizza il principio alla classe tooling)
- Issue chiusa: ISS-001 (era "Rinviata" — root cause Node v24-specific, risolto da downgrade a v22)
- Successore atteso: prossima azione applicativa (F1 cash_inflow, config layer, o altro su autorizzazione Leader)
- Commit: [da aggiornare post-commit]
