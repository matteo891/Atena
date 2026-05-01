# CLAUDE.md — Motore Operativo del Progetto

## Rules of Engagement

Questo file definisce il contratto operativo vincolante tra l'IA e il progetto.

Claude opera come strumento subordinato al **Dogma Architetturale** stabilito dal Leader del progetto. Ogni decisione tecnica, ogni proposta di modifica, ogni suggerimento deve essere conforme alle Architectural Decision Records (ADR) ratificate e depositate in `docs/decisions/`. In assenza di un ADR specifico, Claude deve segnalare l'ambiguità e richiedere una decisione esplicita prima di procedere.

**Principi vincolanti:**
- L'autorità architetturale risiede negli ADR, non nell'IA.
- Claude non propone pattern, librerie o approcci che contraddicono un ADR attivo.
- In caso di conflitto tra una richiesta utente e un ADR, Claude segnala il conflitto esplicitamente.
- Nessuna modifica strutturale viene intrapresa senza tracciabilità documentale.

---

## Workflow

### Self-Briefing Obbligatorio

**All'inizio di ogni sessione**, prima di proporre o applicare qualsiasi modifica, Claude è OBBLIGATO a eseguire il Self-Briefing in questa sequenza esatta. Ogni passo saltato va dichiarato esplicitamente (ADR-0008, ADR-0010).

0. **Verifica enforcement attivo (ADR-0010, bloccante)** — Eseguire `git config core.hooksPath`. L'output deve essere esattamente `scripts/hooks`. In qualsiasi altro caso (output vuoto, valore diverso, errore): NON procedere; comunicare al Leader "Hook non attivi, eseguire `bash scripts/setup-hooks.sh`. Self-briefing sospeso." L'esenzione è ammessa solo se il Leader dichiara esplicitamente "sessione di sola lettura".
1. **`docs/STATUS.md`** — Leggere per primo. Stato corrente in < 60 secondi: cosa è fatto, cosa è in sospeso, issues noti, "Nota al Prossimo Claude". È la fonte di verità sullo stato del progetto. Verificare il blocco "Ultimo aggiornamento" (ADR-0010): se è stale rispetto al `git log`, segnalarlo.
2. **`docs/decisions/INDEX.md`** — Mappa neurale: ADR attivi, dipendenze, aree coperte e gap. **Non rileggere tutti gli ADR** — leggere solo quelli rilevanti all'area di lavoro della sessione.
3. **Ultimi 3 change documents in `docs/changes/`** — Contesto operativo recente.
4. **GitNexus query** — `mcp__gitnexus__query` per orientamento architetturale. Se non disponibile (ISS-001): dichiarare "GitNexus non disponibile" e proseguire senza.
5. **`ROADMAP.md`** — Solo se STATUS.md non è sufficiente per allinearsi agli obiettivi correnti.

Solo al termine del Self-Briefing Claude può rispondere a richieste operative. Qualsiasi proposta fatta senza Self-Briefing è da considerarsi non valida.

> La fonte unica e canonica della sequenza di re-briefing è ADR-0010 (sezione "Sequenza di Re-Briefing — Fonte Unica"). La sezione "Flusso di Re-Briefing" di ADR-0004 è marcata come obsoleta tramite hardening patch (ADR-0009) e NON va seguita.

### Ciclo di Modifica

```
Richiesta
    → Self-Briefing (Step 0 → 5)
    → Verifica ADR (gap segnalato al Leader se area non coperta)
    → Proposta
    → Validazione Leader
    → Implementazione
    → Scrittura change document (docs/changes/)
    → Test (automatici per codice applicativo; manuali documentati per governance — ADR-0011)
    → Esito PASS → Report al Leader → Attesa permesso esplicito
    → Commit
    → Push immediato a origin (ADR-0011, salvo eccezione esplicita Leader)
    → Aggiornamento hash in change document
    → Aggiornamento CHANGELOG / ROADMAP
    → Verifica soglia checkpoint (ogni 5 commit significativi → proposta tag GitHub)
    → Aggiornamento docs/STATUS.md (stesso commit — obbligatorio per sessioni con modifiche;
       header "Ultimo aggiornamento" + claim ancorati — ADR-0010)
```

---

## Protocolli Operativi

I seguenti protocolli sono vincolanti. Definiti negli ADR indicati.

### Test Gate — ADR-0002 + ADR-0011

Nessuna modifica non-triviale viene committata senza:
1. Un test che la copra con esito positivo
2. Report completo dell'esito al Leader (test eseguiti, copertura, rischi residui)
3. Permesso esplicito del Leader di procedere

**Tipi di test ammessi (ADR-0011):**
- **Codice applicativo:** test automatici con esito PASS — obbligatorio.
- **Governance e infrastruttura** (`docs/`, `scripts/hooks/`, `setup-hooks.sh`, `.gitattributes`, indici, ADR, change docs, CLAUDE/STATUS/CHANGELOG/ROADMAP): test manuali documentati ammessi (syntax check, verifica strutturale, ispezione di coerenza). Comando e esito vanno nel change document.

L'esenzione di emergenza richiede motivazione documentata nel commit message (`[EMERGENCY-NO-TEST]`) e nel change document.

### Push Policy — ADR-0011

Ogni commit certificato viene pushato a `origin` immediatamente. I tag annotati (checkpoint/milestone/manuale) vengono pushati esplicitamente. Eccezioni solo con autorizzazione esplicita del Leader.

### Branch Policy — ADR-0011

Fase governance corrente: single-branch su `main`. Nessun force push, nessun reset --hard su HEAD pubblicato, nessuna cancellazione di tag/branch remote senza autorizzazione esplicita. La policy sarà rivista all'introduzione del primo modulo applicativo.

### Restore Point — ADR-0003

Ogni 5 commit significativi su `main`, Claude propone la creazione di un tag GitHub (`checkpoint/YYYY-MM-DD-NN`). Dopo ogni ADR completamente implementato, si crea un milestone tag con GitHub Release. I tag sono immutabili.

### Cross-Reference — ADR-0004

Ogni modifica non-triviale genera un change document in `docs/changes/YYYY-MM-DD-NNN-slug.md` **prima** del commit. Il commit hash viene aggiunto al documento **immediatamente dopo** il commit. Sistema chiuso: nessun change document senza ADR di riferimento.

### Errata Corrige & Hardening Patch — ADR-0009

Per refusi e incoerenze testuali in ADR `Active` si usa **errata corrige** (modifica diretta + sezione `## Errata` aggiornata). Per sezioni rese obsolete da ADR posteriori si usa **hardening patch** (blocco "Sezione superseduta" sopra il testo). Le modifiche di sostanza richiedono comunque supersessione completa via nuovo ADR (regola originale ADR-0001).

### Gap ADR

Se una richiesta riguarda un'area non coperta da un ADR `Active`, Claude **non procede** ma segnala il gap esplicitamente e richiede una decisione al Leader prima di qualsiasi implementazione.

---

## Anti-Allucinazione — ADR-0008 + ADR-0010

Regole hard. Non negoziabili. Testo completo in `docs/decisions/ADR-0008-anti-allucinazione.md` e `ADR-0010-self-briefing-hardening.md`.

- **Mai descrivere un file senza averlo letto in questa sessione.**
- **Mai affermare che un file esiste senza Glob o Grep.**
- **Mai inventare hash di commit, path, nomi di funzioni, versioni di dipendenze.**
- **Lo stato del progetto è quello in `docs/STATUS.md`, non la memoria di sessioni precedenti.**
- **Ogni claim in STATUS.md deve avere un'ancora verificabile** (commit hash, path, ID di ADR/CHG/ISS, tag, output verificato).
- **Header `Ultimo aggiornamento` in STATUS.md sempre presente e fresco.**
- **Se il contesto è parziale: dichiarare la lacuna esplicitamente, non compensarla con inferenze.**
- **Fine di ogni sessione con modifiche: aggiornare `docs/STATUS.md` nello stesso commit.**

---

## Setup del Repository

Dopo ogni clone, eseguire **prima di qualsiasi commit**:

```bash
bash scripts/setup-hooks.sh
```

Attiva i git hooks (ADR-0006): `pre-commit` blocca commit senza change document o ADR malformati (sezioni obbligatorie incluso `## Test di Conformità`); `commit-msg` blocca commit senza CHG-ID/ADR-NNNN o con CHG-ID inesistente, e ricontrolla i file in staging anche per i prefissi `docs(`/`chore(`/`ci(`.

Lo Step 0 del Self-Briefing (ADR-0010) verifica meccanicamente che `git config core.hooksPath` = `scripts/hooks` prima di procedere.

### Formato Commit Obbligatorio — ADR-0005

Footer obbligatorio in ogni commit non-triviale:

```
CHG-YYYY-MM-DD-NNN
ADR-NNNN
```

Commit con prefisso `docs(scope):`, `chore(scope):`, `ci(scope):` sono esentati dal footer **solo se** in staging non c'è alcun file non-triviale (codice applicativo, hook, script, configurazione runtime). Se c'è anche un solo file non-triviale, il footer è obbligatorio (verificato meccanicamente dal `commit-msg` hook — CHG-2026-04-29-002, B2).

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Atena** (4143 symbols, 5393 relationships, 16 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Atena/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Atena/clusters` | All functional areas |
| `gitnexus://repo/Atena/processes` | All execution flows |
| `gitnexus://repo/Atena/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
