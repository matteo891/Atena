---
id: ADR-0010
title: Self-Briefing Hardening & STATUS Anchoring
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
errata:
  - date: 2026-04-30
    chg: CHG-2026-04-30-023
    summary: "Step 1 esteso con verifica reciproca STATUS↔git per claim su tag/branch/hash pubblicati (`git tag -l '<pattern>'` o equivalente). Test di Conformità arricchito con scenario corrispondente. Chiarisce convenzione interpretativa: STATUS è fonte di verità sulla storia documentata, non sullo stato git corrente quando i due possono divergere."
  - date: 2026-04-30
    chg: CHG-2026-04-30-024
    summary: "Esteso il principio di verifica reciproca (CHG-023) alla classe 'claim di indisponibilità tooling'. Step 4 del Self-Briefing esige una chiamata MCP empirica (es. `mcp__gitnexus__list_repos`) prima di dichiarare il tool non disponibile; un claim documentale stale in STATUS non è sufficiente. Test di Conformità arricchito con scenario corrispondente."
---

## Contesto

L'audit di hardening 2026-04-29 ha rilevato tre vulnerabilità nel sistema di re-entry e nella fonte di verità di stato:

1. **Hook silenziosamente disattivati (B4).** Se il Leader o un futuro Claude clona la repo e dimentica `bash scripts/setup-hooks.sh`, l'intero sistema di enforcement meccanico (ADR-0006) è inerte. Nessun controllo segnala l'omissione: il prossimo commit passa senza change doc, senza CHG-ID, senza verifica della struttura ADR. Tutta la disciplina collassa silenziosamente.

2. **STATUS.md senza ancoraggio temporale (B5).** ADR-0008 dichiara `docs/STATUS.md` fonte di verità prevalente sulla memoria di Claude. Ma STATUS.md è scritto da Claude: una sua eventuale allucinazione si propaga indefinitamente nelle sessioni successive. Mancano: timestamp di ultimo aggiornamento, commit hash di riferimento, regola che vincoli ogni claim a un'ancora verificabile (path, hash, ID).

3. **Sequenza di re-briefing duplicata e divergente (B1).** ADR-0004 sezione "Flusso di Re-Briefing" elenca una sequenza che non include STATUS.md (creato dopo) e mette ROADMAP al posto 2. CLAUDE.md e ADR-0008 elencano la sequenza corretta (`STATUS → INDEX → ultimi 3 changes → GitNexus → ROADMAP solo se serve`). Un Claude che leggesse ADR-0004 in isolamento — come ADR-0008 stesso impone di fare per le aree rilevanti — seguirebbe la sequenza sbagliata.

Questi tre vincoli sono interconnessi: il self-briefing è il primo presidio anti-allucinazione, e ogni sua falla amplifica le altre. Vanno chiusi insieme.

## Decisione

### Step 0 del Self-Briefing — Verifica Enforcement Attivo

Prima dello step 1 (lettura di STATUS.md), Claude esegue una verifica **obbligatoria e bloccante**:

```bash
git config core.hooksPath
```

L'output atteso è esattamente `scripts/hooks`. In qualsiasi altro caso (output vuoto, valore diverso, errore di esecuzione), Claude:

1. **Non procede** con il self-briefing.
2. **Non risponde** a richieste operative.
3. Comunica al Leader: *"Hook non attivi. Eseguire `bash scripts/setup-hooks.sh` prima di qualsiasi commit. Self-briefing sospeso."*
4. Attende conferma esplicita del Leader prima di riprendere.

L'esenzione è ammessa solo se il Leader dichiara esplicitamente "sessione di sola lettura, nessun commit previsto". In quel caso Claude annota esplicitamente l'esenzione nella prima risposta della sessione.

### Sequenza di Re-Briefing — Fonte Unica

La sequenza canonica e unica del Self-Briefing è quella già definita in CLAUDE.md e ADR-0008, ora aggiornata con lo step 0:

```
0. Verifica `git config core.hooksPath` = scripts/hooks    [ADR-0010]
1. docs/STATUS.md                                           [ADR-0008]
2. docs/decisions/INDEX.md                                  [ADR-0001]
3. Ultimi 3 file in docs/changes/                           [ADR-0004]
4. GitNexus query (degrade esplicitamente se ISS-001)       [ADR-0007]
5. ROADMAP.md (solo se step 1 non è sufficiente)            [ADR-0008]
```

**Verifica reciproca STATUS ↔ git (errata 2026-04-30 / CHG-023).** Quando lo Step 1 incontra in STATUS un'affermazione su esistenza, proposta o assenza di un tag git, di un branch o di un commit hash specifico, esegue la verifica corrispondente sul repository (`git tag -l '<pattern>'`, `git branch --list`, `git log <hash>`) prima di agire. Se la verifica diverge da STATUS, segnalare al Leader e correggere STATUS prima di qualsiasi azione: STATUS è fonte di verità sulla **storia documentata**, non sullo **stato git corrente** quando i due possono divergere. Costo: <1 secondo. Beneficio: chiude la classe di errori "STATUS stale propaga decisioni sbagliate".

**Verifica reciproca STATUS ↔ runtime tooling (errata 2026-04-30 / CHG-024).** Quando STATUS dichiara non disponibile uno strumento esterno (server MCP, container, runner CI, indice GitNexus, ecc.), Claude esegue una chiamata empirica economica al re-entry **prima** di accettare il claim. Esempi: per GitNexus, `mcp__gitnexus__list_repos`. Tre outcome possibili:

1. **Errore tecnico** (transport error, timeout, server non risponde) → solo allora si dichiara "tool non disponibile", **citando l'errore esatto come ancora**.
2. **Risposta con indice/stato stale** (es. `staleness.commitsBehind > 0` o `lastCommit ≠ git rev-parse HEAD`) → eseguire il rebuild/refresh appropriato (es. `npx -y gitnexus analyze`); se il rebuild fallisce, allora documentare il fail come ancora.
3. **Risposta fresh** (es. `lastCommit == HEAD`, `staleness` assente) → il claim documentale di STATUS è obsoleto: aggiornare STATUS (chiusura Issue o errata) e procedere normalmente con lo step.

Solo errori effettivi giustificano "tool non disponibile". Un claim documentale di indisponibilità in STATUS, scritto in una sessione passata, non sopravvive alla verifica empirica del re-entry. Principio sotteso (uguale a CHG-023): STATUS è fonte di verità sulla **storia documentata**, non sullo **stato runtime corrente** quando i due possono divergere.

La sezione "Flusso di Re-Briefing" di ADR-0004 è marcata come **superseduta da questo ADR** tramite hardening patch (ADR-0009, applicata in CHG-2026-04-29-002). Il resto di ADR-0004 rimane normativo.

### STATUS.md — Anchoring & Freshness

`docs/STATUS.md` riceve due regole vincolanti aggiuntive che si sovrappongono all'obbligo di aggiornamento già definito in ADR-0008.

**Regola 1 — Header di Freshness Obbligatorio.**
STATUS.md deve aprire con un blocco di intestazione che include almeno:

```markdown
> **Ultimo aggiornamento:** YYYY-MM-DD — commit `<7-char-hash>`
> **Sessione corrente:** [breve descrizione, opzionale]
```

Il commit hash è quello dell'ultimo commit che ha modificato STATUS.md (aggiornato post-commit, come per i change document). Se STATUS.md non è ancora stato committato dopo una modifica, il blocco riporta `[da aggiornare post-commit]` al posto del hash.

**Regola 2 — Ogni Claim Ancorato.**
Ogni affermazione tecnica in STATUS.md deve avere almeno **un'ancora verificabile**, scelta tra:

- Commit hash (`5959ebd`, `a796ce0`)
- Path di file (`scripts/hooks/pre-commit`)
- ID di ADR / CHG / ISS (`ADR-0007`, `CHG-2026-04-29-001`, `ISS-001`)
- Tag git (`milestone/ADR-0001-0008`)
- Citazione esplicita di output verificato (`node --version` → `v24.15.0`)

Affermazioni senza ancora sono proibite. Esempi di violazione:
- ❌ "Il sistema funziona bene su Mac." (senza path, hash, o output verificato)
- ✅ "GitNexus crasha con exit code 5 su Node v24.15.0 (ISS-001)."

La verifica è manuale a fine sessione: Claude rilegge STATUS.md prima del commit finale e marca eventuali claim non ancorati come gap, oppure li riformula con ancora.

### Aggiornamento STATUS.md a Fine Sessione (Rafforzamento ADR-0008)

L'obbligo di aggiornamento esistente in ADR-0008 Regola 7 è esteso con:

- Aggiornamento del campo `Ultimo aggiornamento` con la data corrente.
- Aggiornamento del campo `commit` post-commit con il nuovo hash.
- Verifica che la sezione "Nota al Prossimo Claude" sia coerente con i fatti emersi nella sessione, e che ogni nota abbia un'ancora.

### Esenzione di Sessione di Sola Lettura

Una sessione che non produce alcun commit (audit, esplorazione, briefing) **non** richiede aggiornamento di STATUS.md. Il blocco di freshness rimane invariato. Claude dichiara esplicitamente "Sessione di sola lettura — STATUS.md non aggiornato" nel report finale.

## Conseguenze

- Il rischio di "hook silenziosamente disattivati" è eliminato: ogni sessione comincia con una verifica meccanica del setup.
- STATUS.md diventa auto-verificabile: chi lo legge può controllare la freshness e tracciare ogni claim a un'ancora.
- La sequenza di re-briefing ha una fonte unica e non contraddittoria; ADR-0004 rimane Active ma con sezione obsoleta marcata.
- Costo: ~2 secondi extra a inizio sessione per la verifica step 0, e una passata di rilettura di STATUS.md a fine sessione per il check ancore.
- Le sessioni di sola lettura mantengono basso overhead grazie all'esenzione esplicita.

## Test di Conformità

| Scenario | Comportamento Atteso |
|---|---|
| Apertura sessione, hook attivi | Step 0 PASS, prosegue self-briefing |
| Apertura sessione, hook non attivi | Step 0 FAIL, sessione sospesa, messaggio al Leader |
| STATUS.md senza header `Ultimo aggiornamento` | Errore strutturale, da correggere prima del commit di sessione |
| STATUS.md con claim non ancorato | Errore di rilettura, riformulare o rimuovere |
| Sessione di sola lettura | Esenzione esplicita dichiarata, STATUS.md non modificato |
| Sezione "Flusso di Re-Briefing" di ADR-0004 letta in isolamento | Lettore vede il blocco "Superseduta da ADR-0010" e segue ADR-0010 |
| STATUS afferma stato di tag/branch/hash, repo dice diversamente (errata 2026-04-30 CHG-023) | Errore di rilettura: segnalare al Leader, correggere STATUS prima di agire |
| STATUS afferma indisponibilità tooling, runtime risponde alla call empirica (errata 2026-04-30 CHG-024) | Errore di rilettura: aggiornare STATUS (chiusura Issue o errata), procedere con lo step |

Verifica: pre-commit del commit di sessione, Claude rilegge STATUS.md ed elenca eventuali claim non ancorati al Leader.

## Cross-References

- ADR correlati: ADR-0001 (meta), ADR-0004 (subisce hardening patch), ADR-0006 (hooks), ADR-0008 (anti-allucinazione, esteso da questo ADR), ADR-0009 (meccanismo hardening patch)
- Governa: protocollo di self-briefing step 0, struttura di `docs/STATUS.md`, regole di anchoring
- Impatta: `CLAUDE.md` (workflow), `docs/STATUS.md`, ADR-0004 sezione "Flusso di Re-Briefing"
- Test: verifica meccanica step 0 + verifica manuale anchoring pre-commit
- Commits: `416ab87` (introduzione, CHG-2026-04-29-002) + `d962445` (errata CHG-2026-04-30-023, verifica STATUS↔git) + `cea9494` (errata CHG-2026-04-30-024, verifica STATUS↔runtime tooling)

## Rollback

Se lo step 0 si rivela troppo invasivo (falsi positivi, ambienti con configurazioni git non standard), si crea un ADR di supersessione che lo declassa a "consigliato ma non bloccante". Le regole di anchoring di STATUS.md sono indipendenti e possono essere mantenute o ritirate separatamente.

## Errata

### 2026-04-30 — CHG-2026-04-30-023

- **Tipo:** errata corrige (chiarimento di convenzione interpretativa).
- **Modifica:**
  - Sezione "Sequenza di Re-Briefing — Fonte Unica": aggiunta paragrafo "Verifica reciproca STATUS ↔ git" sotto la sequenza canonica. Lo Step 1 incorpora una verifica sul repository (`git tag -l '<pattern>'`, `git branch --list`, `git log <hash>`) ogni volta che STATUS afferma esistenza, proposta o assenza di un tag, branch o commit hash specifico.
  - Sezione "Test di Conformità": aggiunta riga "STATUS afferma stato di tag/branch/hash, repo dice diversamente → errore di rilettura, segnalare al Leader, correggere STATUS prima di agire".
  - Frontmatter `errata:` esteso con voce 2026-04-30.
  - Campo `Commits:` riallineato (sostituito placeholder con commit di hardening + commit dell'errata).
- **Motivo:** sessione 2026-04-30 (CHG-019..022) ha ripetutamente aggiornato STATUS con la riga "CHECKPOINT-03 proposto, in attesa autorizzazione" mentre il tag `checkpoint/2026-04-30-03` esisteva già da 6 ore (creato 15:50 post-CHG-018). La regola "ogni claim ancorato" di Regola 2 copre il **caso scrittore** ma non il **caso lettore**: chi rilegge STATUS deve confermare che le ancore puntino ancora alla realtà attuale. L'errata inscrive la verifica reciproca, chiudendo la classe di errori "STATUS stale propaga decisioni sbagliate".

### 2026-04-30 — CHG-2026-04-30-024

- **Tipo:** errata corrige (chiarimento di convenzione interpretativa — generalizzazione del principio di CHG-023).
- **Modifica:**
  - Sezione "Sequenza di Re-Briefing — Fonte Unica": aggiunto paragrafo "Verifica reciproca STATUS ↔ runtime tooling" dopo quello su STATUS↔git. Lo Step 4 (e per estensione ogni step che dipende da tooling esterno) incorpora una chiamata empirica economica (es. `mcp__gitnexus__list_repos`) prima di accettare un claim documentale di indisponibilità. Tre outcome canonici: errore tecnico → "non disponibile" ancorato all'errore; risposta stale → rebuild/refresh; risposta fresh → STATUS obsoleto, aggiornare e procedere.
  - Sezione "Test di Conformità": aggiunta riga "STATUS afferma indisponibilità tooling, runtime risponde alla call empirica → errore di rilettura, aggiornare STATUS, procedere con lo step".
  - Frontmatter `errata:` esteso con voce 2026-04-30 / CHG-024.
  - Campo `Commits:` esteso con il commit di questo errata.
- **Motivo:** sessione 2026-04-30 (questa) ha dichiarato Step 4 "GitNexus non disponibile" basandosi sul claim ISS-001 stale di STATUS, senza alcuna verifica empirica. Su sollecitazione del Leader la chiamata `mcp__gitnexus__list_repos` è risposta immediatamente; il rebuild via `npx -y gitnexus analyze` è completato in 3.3s su Node v22. ISS-001 era documentale, non runtime. Il principio di CHG-023 (verifica reciproca per tag/branch/hash) si generalizza naturalmente: ogni claim documentale di stato esterno richiede verifica empirica al re-entry. Step 0 (hooks via `git config core.hooksPath`) era già conforme; questo errata estende la simmetria allo Step 4 e a ogni futuro step dipendente da tooling esterno.
