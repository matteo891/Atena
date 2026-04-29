---
id: CHG-2026-04-29-003
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Committed
commit: 7b7ef17
adr_ref: ADR-0012
---

## What — Cosa è cambiato

Promulgazione di **ADR-0012 — Project Vision Capture & Distillation** e creazione del file `PROJECT-RAW.md` (root, stato `Draft`) come template pronto per l'esposizione della bozza del progetto da parte del Leader.

**File creati:**
- `docs/decisions/ADR-0012-project-vision-capture.md` — ADR che definisce posizione, formato, stati, struttura, regole anti-allucinazione e pipeline operativa del file di vision raw.
- `PROJECT-RAW.md` (root) — template vuoto in stato `Draft`, 11 sezioni fisse, 16 lacune iniziali aperte, Q&A Log vuoto.

**File aggiornati:**
- `docs/decisions/INDEX.md` — registrazione di ADR-0012, grafo dipendenze esteso.
- `docs/decisions/FILE-ADR-MAP.md` — `PROJECT-RAW.md` mappato sotto ADR-0012.
- `ROADMAP.md` — nuovo obiettivo "Vision capture (PROJECT-RAW.md)".
- `CHANGELOG.md` — versione 0.6.0.
- `docs/STATUS.md` — stato corrente aggiornato; Step 0 confermato; nota al prossimo Claude estesa con il flusso vision.

## Why — Perché

**ADR di riferimento:** [ADR-0012](../decisions/ADR-0012-project-vision-capture.md).

**Motivazione del Leader.** Il Leader ha richiesto di poter esporre la bozza del progetto in una sessione futura, con Claude che la trascriva in modo "puntuale e maniacale" e poi la affinasse via domande, fino a un punto di "Frozen" da cui un nuovo Claude possa brieffarsi e proporre una scomposizione in task ROADMAP. Nel mio audit ho rilevato tre buchi nel piano originale (file fuori sistema, completamento silenzioso, salto della validazione architetturale) e ho proposto di promulgare ADR-0012 prima del file. Il Leader ha approvato esplicitamente: "facciamo come hai detto tu, ha tutto senso. […] fammi trovare l'md raw pronto miraccomando. quindi la prima [opzione: governance-first]".

L'autorizzazione al commit + push è stata data esplicitamente: "committa e pushamelo su github […] fammi trovare l'md raw pronto" (Leader 2026-04-29).

## How — Come

**Approccio tecnico.** Ho seguito la pipeline disciplinata definita in CHG-002:
1. Verifica Step 0 ADR-0010: `git config core.hooksPath` = `scripts/hooks` ✅
2. Scrittura del change document **prima** del commit (questo file)
3. Promulgazione ADR-0012 con tutte e 6 le sezioni obbligatorie
4. Creazione PROJECT-RAW.md template con 16 lacune iniziali esplicite e Q&A Log vuoto
5. Aggiornamento di INDEX, FILE-ADR-MAP, ROADMAP, CHANGELOG, STATUS
6. Test strutturali (manuali documentati, ADR-0011)
7. Commit con footer CHG-ID + ADR-0012, push immediato (ADR-0011)
8. Backfill hash + STATUS finale

**Decisioni di design su PROJECT-RAW.md:**
- **Path:** root (coerente con CLAUDE/CHANGELOG/ROADMAP).
- **Naming:** `PROJECT-RAW.md` maiuscolo (coerenza con altri file di root).
- **Formato:** markdown (non `.txt` originariamente proposto dal Leader; lo stesso Leader ha poi confermato `md` con "fammi trovare l'md raw pronto").
- **16 lacune iniziali esplicite:** ogni sezione ha già le sue lacune precompilate con la domanda concreta da porre al Leader. Quando il Leader esporrà, Claude le chiuderà una a una.

**File creati:**

| File | Tipo | Note |
|---|---|---|
| `docs/decisions/ADR-0012-project-vision-capture.md` | nuovo | Categoria `process`. Sezioni complete (Contesto, Decisione, Conseguenze, Test, Cross-References, Rollback). Cita ADR-0001/0008/0009/0010 |
| `PROJECT-RAW.md` | nuovo | Status `Draft`, 16 lacune iniziali, Q&A Log vuoto |
| `docs/changes/2026-04-29-003-vision-capture-adr.md` | nuovo | Questo documento |

**File modificati:**

| File | Modifica |
|---|---|
| `docs/decisions/INDEX.md` | Aggiunta riga ADR-0012 nel registro; grafo dipendenze esteso; "Aree di Codice Coperte" aggiornata con `PROJECT-RAW.md` |
| `docs/decisions/FILE-ADR-MAP.md` | Nuova sezione "Vision e Intent" con `PROJECT-RAW.md` sotto ADR-0012 |
| `ROADMAP.md` | Obiettivo #8 aggiunto: "Vision capture e distillazione (PROJECT-RAW.md)"; meta-blocchi futuri rivisti |
| `CHANGELOG.md` | Versione 0.6.0 — vision capture protocol |
| `docs/STATUS.md` | "Appena Completato" esteso; "Prossima Azione" aggiornata (esposizione bozza dal Leader); "Nota al Prossimo Claude" estesa con la pipeline vision |

## Tests

| Test | Tipo | Esito | Note |
|---|---|---|---|
| Sintassi ADR-0012 — sezioni obbligatorie | Verifica strutturale (ADR-0011) | PASS atteso | grep `^## (Contesto|Decisione|Conseguenze|Test di Conformità|Cross-References|Rollback)` deve dare 6 |
| ADR-0012 in INDEX.md | Verifica strutturale | PASS atteso | grep `ADR-0012` deve dare ≥1 |
| `PROJECT-RAW.md` esiste e ha frontmatter `status: Draft` | Verifica strutturale | PASS atteso | Glob + grep `status: Draft` |
| `PROJECT-RAW.md` non contiene prosa inferita (solo `[LACUNA: …]` o `[da raccogliere]` nelle sezioni di contenuto) | Verifica strutturale | PASS — verificato manualmente in stesura | — |
| `FILE-ADR-MAP.md` cita `PROJECT-RAW.md` | Verifica strutturale | PASS atteso | grep |
| Tabella lacune in PROJECT-RAW.md ha 16 righe | Verifica strutturale | PASS — verificato manualmente | conteggio L01–L16 |
| Hook `pre-commit` accetta il commit (ADR-0012 ben formato + indicizzato + change doc presente) | Test runtime | da eseguire al commit | Se BLOCCATO, fix immediato |
| Hook `commit-msg` accetta CHG-2026-04-29-003 + ADR-0012 nel footer | Test runtime | da eseguire al commit | Idem |

**Copertura stimata:** copre la struttura del nuovo ADR e del nuovo file. La pipeline operativa di ADR-0012 (stato `Iterating`, transizione a `Frozen`, scomposizione validata) sarà testata runtime nelle prossime sessioni a partire dall'esposizione della bozza.

**Rischi residui:**
- Il Leader potrebbe trovare la struttura di PROJECT-RAW.md troppo rigida o troppo lasca. È modificabile via errata corrige (ADR-0009) prima del primo Iterating.
- Le 16 lacune precompilate potrebbero risultare presuntuose — il Leader potrebbe avere sezioni che non gli interessano. Vanno trattate come "default ragionevole", non come obbligo.

## Impact

- Il Leader ha un template pronto e governato in cui esporre la bozza al ritorno.
- Ogni futura sessione che tocca PROJECT-RAW.md ha disciplina chiara (chi può modificare cosa, in quale stato).
- Un futuro Claude può brieffarsi sul Frozen e proporre scomposizione senza saltare la validazione del Leader.
- Il rischio di "completamento silenzioso" è chiuso: marker `[LACUNA: ...]` obbligatori dove non c'è dichiarazione.
- Tre fonti distinte e non sovrapposte: PROJECT-RAW (intent), ADR (decisioni ratificate), ROADMAP (task tracciati).

## Refs

- ADR: [ADR-0012](../decisions/ADR-0012-project-vision-capture.md)
- Commit: `7b7ef17`
- Checkpoint successivo: nessun tag previsto per questo CHG (modifica di sola governance, non significativa ai fini del conteggio soglia-5 di ADR-0003)
- Issue / Task: ISS-002 ancora aperta — questa è la struttura per chiuderla, non la chiusura
