---
id: ADR-0012
title: Project Vision Capture & Distillation
date: 2026-04-29
status: Active
deciders: Leader
category: process
supersedes: —
superseded_by: —
---

## Contesto

Il Leader sta per esporre la bozza concettuale del progetto. Senza un protocollo formale, questa esposizione rischia tre fallimenti:

1. **Drift fuori dalla governance.** Un file di "vision raw" creato in root senza ADR di copertura sarebbe immediatamente in zona Gap ADR (ADR-0008 Regola 5): qualsiasi futuro Claude che lo aprisse dovrebbe segnalare il gap e fermarsi. Il file diventerebbe un nodo orfano del grafo.

2. **Completamento silenzioso (allucinazione travestita da precisione).** Quando il Leader chiede una "spiegazione testuale puntuale e maniacale" di una bozza ancora vaga, la pressione di "essere maniacale" induce inferenze plausibili sui punti incerti. Questo viola ADR-0008 Regola 4 (degrado esplicito) e Regola 1 (verifica prima di affermare): le inferenze vengono presentate con la stessa confidenza dei fatti dichiarati dal Leader.

3. **Salto della validazione architetturale.** Il flusso ipotizzato dal Leader — "futuro Claude legge il raw, lo digerisce, scompone in task, li scrive in ROADMAP" — bypasserebbe ADR-0001: l'autorità architetturale resta nel Leader, non nell'IA. Senza un punto formale di ratifica, Claude finirebbe per fare decisioni architetturali implicite (cosa è in scope, cosa prima, cosa poi) senza ADR di copertura.

Serve un protocollo che chiuda questi tre rischi in un'unica decisione, mantenendo la fluidità del processo conversazionale Leader-Claude.

## Decisione

### Il File: `PROJECT-RAW.md`

Posizione fissa: **root del repository**. Coerente con `CLAUDE.md`, `ROADMAP.md`, `CHANGELOG.md`. Naming maiuscolo per coerenza con gli altri file di root.

Formato: markdown con frontmatter YAML.

### Stati del File

```
Draft → Iterating → Frozen → (post-Frozen, modifiche solo via Errata Corrige ADR-0009)
```

| Status | Significato | Chi può modificare | Come |
|---|---|---|---|
| `Draft` | Il Leader sta esponendo la bozza per la prima volta; il file è in stesura iniziale | Claude (sotto dettatura del Leader) | Edit diretto |
| `Iterating` | Bozza scritta, Claude pone domande di chiarimento, Leader risponde, Claude affina | Claude (sotto dettatura) e Leader | Edit diretto + sezione "Q&A Log" cresce |
| `Frozen` | Il Leader dichiara la vision sufficientemente chiara per essere fonte di intent autoritativa | Solo Leader (o Claude con autorizzazione esplicita per ogni modifica) | Errata Corrige (ADR-0009) per refusi; per cambi di sostanza, transizione a stato `Iterating` con motivazione documentata |

Il passaggio Frozen è dichiarato esplicitamente dal Leader (es. "freeze la vision"). Claude non può promuovere lo stato autonomamente.

### Frontmatter Obbligatorio

```yaml
---
status: Draft | Iterating | Frozen
owner: Leader
started: YYYY-MM-DD
last_iteration: YYYY-MM-DD
frozen_at: YYYY-MM-DD | —
qa_rounds: <numero round di domanda/risposta>
---
```

### Struttura del Documento

Il file ha sezioni fisse (l'ordine è normativo). Una sezione vuota o ancora da raccogliere riporta `[LACUNA: domanda al Leader]` o `[da raccogliere]` — mai prosa inventata.

| # | Sezione | Contenuto |
|---|---|---|
| 1 | **Cosa è** | Definizione del progetto in una riga (elevator pitch) + paragrafo |
| 2 | **Perché** | Motivazione, problema, opportunità — solo dichiarato dal Leader |
| 3 | **Per chi** | Utenti target, stakeholder identificati |
| 4 | **Cosa fa** | Funzionalità chiave, comportamento atteso, scenari d'uso primari |
| 5 | **Cosa NON fa** | Out-of-scope espliciti dichiarati dal Leader |
| 6 | **Vincoli e requisiti** | Tecnici, di business, normativi, di tempo |
| 7 | **Successo misurabile** | Cosa significa "funziona" — criteri di completamento |
| 8 | **Rischi noti** | Cosa potrebbe rompere o invalidare il progetto |
| 9 | **Lacune Aperte** | Punti ancora vaghi, marker `[LACUNA: domanda]` con la domanda concreta da porre al Leader |
| 10 | **Q&A Log** | Cronologia delle domande di Claude e risposte del Leader durante `Iterating` |
| 11 | **Refs** | Riferimenti esterni (link, documenti, ispirazioni) |

### Regola Anti-Allucinazione: "Lacune Mai Completate"

**Vincolante e non negoziabile.** Quando una sezione o un punto specifico non è stato dichiarato dal Leader:

- **Proibito:** scrivere prosa plausibile, inferire da contesto, "completare" basandosi su pattern simili visti altrove.
- **Obbligatorio:** marcare il punto con `[LACUNA: <domanda concreta da porre al Leader>]` e aggiungerlo alla sezione 9.

Esempio:
- ❌ "Il progetto target una user base di sviluppatori italiani." (inferito)
- ✅ "Per chi: [LACUNA: il Leader ha menzionato 'utenti', ma non ha specificato segmenti, geografie, o livello di expertise. Domanda: chi sono concretamente gli utenti target?]"

Questa regola si rinforza specificamente sull'ordine "spiegazione puntuale e maniacale" del Leader: la maniacalità è sulla precisione di trascrizione e sulle domande sollevate, non sul completamento delle aree vuote.

### Pipeline Operativa: Raw → Decisione → ROADMAP

```
[1] Leader espone la bozza (oralmente, in chat)
       ↓
[2] Claude scrive PROJECT-RAW.md in stato Draft
       — trascrive ciò che è stato dichiarato
       — marca lacune con [LACUNA: ...]
       — colloca domande in sezione 9
       ↓
[3] Claude richiede al Leader: "ho N lacune, vuoi rispondere ora o per round?"
       ↓
[4] Iterating: round di Q&A, ogni risposta del Leader aggiorna il file
       — Q&A Log cresce
       — Lacune chiuse vengono spostate da sez. 9 a sez. corretta
       — Status frontmatter aggiornato
       ↓
[5] Leader dichiara "Frozen"
       — frontmatter status: Frozen, frozen_at compilato
       — sezione 9 deve essere vuota o contenere solo lacune accettate consapevolmente
       ↓
[6] Claude propone una scomposizione del Frozen in:
       — proposte di ADR di architettura (se ci sono decisioni da prendere)
       — proposte di task per ROADMAP (se ci sono solo lavori da tracciare)
       Nessuna scrittura diretta in ADR né in ROADMAP a questo step.
       ↓
[7] Leader valida proposta per proposta:
       — Per ogni decisione architetturale: ratifica → Claude promulga ADR
       — Per ogni task operativo: ratifica → Claude aggiorna ROADMAP
       — Decisioni dichiarate "rinviate": annotate in ROADMAP meta-blocchi futuri
       ↓
[8] Solo dopo validazione, gli ADR/ROADMAP riflettono il Frozen.
       PROJECT-RAW.md resta in stato Frozen come fonte di "intent" — non viene
       riscritto né tradotto: gli ADR sono la traduzione architetturale validata
       e autoritativa.
```

**Vincolo:** allo step [6], Claude non scrive in ROADMAP né promulga ADR. Produce **solo proposte testuali in chat**. La promulgazione/scrittura avviene allo step [7] sotto autorizzazione esplicita.

### Rapporto con Altri Documenti

| Documento | Autoritativo per | Conflict resolution |
|---|---|---|
| `PROJECT-RAW.md` (Frozen) | Intent del Leader, "perché esiste questo progetto" | Se ADR contraddice intent: ADR sbagliato, va superseduto |
| `docs/decisions/ADR-*.md` | Decisioni architetturali ratificate | Se RAW dichiara intent ma nessun ADR lo formalizza: gap, da chiudere |
| `ROADMAP.md` | Task operativi tracciati | Riflette lo stato di ADR ratificati; non contiene decisioni |
| `docs/STATUS.md` | Stato corrente operativo | Punta ai precedenti, non li sostituisce |

In caso di conflitto Frozen ↔ ADR: il Leader decide la riconciliazione (errata corrige sul RAW se la realtà ha cambiato l'intent; supersessione dell'ADR se l'intent è invariato e l'ADR era sbagliato).

### Modifica Post-Frozen

Dopo Frozen, il file segue le stesse regole degli ADR `Active`:
- **Refusi e incoerenze:** errata corrige (ADR-0009) — sezione `## Errata` aggiunta in coda al file con voce e CHG-ID.
- **Cambi di sostanza dell'intent:** transizione documentata a stato `Iterating` con CHG dedicato che spiega cosa è cambiato e perché. Frontmatter aggiornato. Eventuali ADR derivati vanno rivisti.

### Bootstrap

Alla promulgazione di questo ADR (CHG-2026-04-29-003), Claude crea:
- `PROJECT-RAW.md` in root, status `Draft`, sezioni fisse vuote con marker `[da raccogliere — il Leader esporrà la bozza nella prossima sessione conversazionale]`.
- Aggiornamento di `FILE-ADR-MAP.md`, `INDEX.md`, `ROADMAP.md`, `CHANGELOG.md`, `docs/STATUS.md`.

## Conseguenze

- L'esposizione della vision diventa un atto documentale tracciabile, non una conversazione effimera.
- Le lacune sono visibili, contate, e fungono da agenda implicita per i round di Iterating.
- Nessuna decisione architetturale entra in ADR o in ROADMAP senza passare per la validazione del Leader (step [7]).
- Il Frozen è un punto fisso che permette ai Claude futuri di brieffarsi rapidamente: STATUS → INDEX → PROJECT-RAW (Frozen) → ADR rilevanti → ultimi changes.
- Costo: il Leader deve esplicitamente "freezare" la vision; senza freeze, il file è materiale di lavoro non normativo.
- Beneficio: il "completamento silenzioso" diventa fisicamente tracciabile (ogni lacuna ha marker; ogni risposta è in Q&A Log; ogni round è contato in `qa_rounds`).

## Test di Conformità

| Scenario | Comportamento Atteso |
|---|---|
| `PROJECT-RAW.md` esiste in root | ✅ |
| File ha frontmatter con `status: Draft|Iterating|Frozen` | ✅ |
| Sezione mancante: contiene marker `[LACUNA: ...]` o `[da raccogliere]`, mai prosa | ✅ |
| Stato `Frozen` dichiarato senza autorizzazione esplicita del Leader | RIFIUTATO — Claude non promuove autonomamente |
| Modifica post-Frozen senza errata corrige o transizione a Iterating | RIFIUTATO — ADR-0009 |
| Scrittura in ROADMAP a partire dal Frozen senza step [7] | RIFIUTATO — viola ADR-0001 |
| Sezione "Q&A Log" non aggiornata dopo round di domande | RIFIUTATO — protocollo violato |

Verifica: a fine ogni sessione di Iterating, Claude rilegge PROJECT-RAW.md e conta le lacune; il numero deve essere monotonicamente decrescente fino al Frozen.

## Cross-References

- ADR correlati: ADR-0001 (autorità architetturale), ADR-0008 (anti-allucinazione, Regola 4 e 5), ADR-0009 (errata corrige post-Frozen), ADR-0010 (anchoring esteso al Q&A Log)
- Governa: `PROJECT-RAW.md`, pipeline raw → decisione → ROADMAP
- Impatta: `FILE-ADR-MAP.md`, `ROADMAP.md` (meta-blocchi futuri vengono popolati dallo step [7]), `docs/STATUS.md` (riferisce stato del file raw)
- Test: verifica strutturale + conteggio lacune; manuale a fine sessione
- Commits: [da aggiornare post-commit]

## Rollback

Se il protocollo si rivela troppo cerimoniale per la velocità della prima esposizione, il Leader può autorizzare per la sessione corrente uno stato "esposizione libera": Claude trascrive senza marker, ma alla fine della sessione il file viene normalizzato (lacune marcate, sezioni riallineate). Questa esenzione va documentata in change document e non costituisce supersessione dell'ADR.

In caso di abbandono del protocollo: ADR di supersessione che chiarisca cosa lo sostituisce; PROJECT-RAW.md può essere rinominato o rimosso solo con autorizzazione esplicita.
