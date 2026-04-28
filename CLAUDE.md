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

**All'inizio di ogni sessione**, prima di proporre o applicare qualsiasi modifica, Claude è OBBLIGATO a eseguire il Self-Briefing in questa sequenza esatta. Ogni passo saltato va dichiarato esplicitamente (ADR-0008).

1. **`docs/STATUS.md`** — Leggere per primo. Stato corrente in < 60 secondi: cosa è fatto, cosa è in sospeso, issues noti, "Nota al Prossimo Claude". È la fonte di verità sullo stato del progetto.
2. **`docs/decisions/INDEX.md`** — Mappa neurale: ADR attivi, dipendenze, aree coperte e gap. **Non rileggere tutti gli ADR** — leggere solo quelli rilevanti all'area di lavoro della sessione.
3. **Ultimi 3 change documents in `docs/changes/`** — Contesto operativo recente.
4. **GitNexus query** — `mcp__gitnexus__query` per orientamento architetturale. Se non disponibile (ISS-001): dichiarare "GitNexus non disponibile" e proseguire senza.
5. **`ROADMAP.md`** — Solo se STATUS.md non è sufficiente per allinearsi agli obiettivi correnti.

Solo al termine del Self-Briefing Claude può rispondere a richieste operative. Qualsiasi proposta fatta senza Self-Briefing è da considerarsi non valida.

### Ciclo di Modifica

```
Richiesta
    → Self-Briefing
    → Verifica ADR (gap segnalato al Leader se area non coperta)
    → Proposta
    → Validazione Leader
    → Implementazione
    → Scrittura change document (docs/changes/)
    → Test
    → Esito PASS → Report al Leader → Attesa permesso esplicito
    → Commit
    → Aggiornamento hash in change document
    → Aggiornamento CHANGELOG / ROADMAP
    → Verifica soglia checkpoint (ogni 5 commit significativi → proposta tag GitHub)
    → Aggiornamento docs/STATUS.md (stesso commit — obbligatorio per sessioni con modifiche)
```

---

## Protocolli Operativi

I seguenti protocolli sono vincolanti. Definiti negli ADR indicati.

### Test Gate — ADR-0002

Nessuna modifica non-triviale al codice viene committata senza:
1. Un test che la copra con esito positivo
2. Report completo dell'esito al Leader (test eseguiti, copertura, rischi residui)
3. Permesso esplicito del Leader di procedere

L'esenzione di emergenza richiede motivazione documentata nel commit message (`[EMERGENCY-NO-TEST]`) e nel change document.

### Restore Point — ADR-0003

Ogni 5 commit significativi su master, Claude propone la creazione di un tag GitHub (`checkpoint/YYYY-MM-DD-NN`). Dopo ogni ADR completamente implementato, si crea un milestone tag con GitHub Release. I tag sono immutabili.

### Cross-Reference — ADR-0004

Ogni modifica non-triviale genera un change document in `docs/changes/YYYY-MM-DD-NNN-slug.md` **prima** del commit. Il commit hash viene aggiunto al documento **immediatamente dopo** il commit. Sistema chiuso: nessun change document senza ADR di riferimento.

### Gap ADR

Se una richiesta riguarda un'area non coperta da un ADR `Active`, Claude **non procede** ma segnala il gap esplicitamente e richiede una decisione al Leader prima di qualsiasi implementazione.

---

## Anti-Allucinazione — ADR-0008

Regole hard. Non negoziabili. Testo completo in `docs/decisions/ADR-0008-anti-allucinazione.md`.

- **Mai descrivere un file senza averlo letto in questa sessione.**
- **Mai affermare che un file esiste senza Glob o Grep.**
- **Mai inventare hash di commit, path, nomi di funzioni, versioni di dipendenze.**
- **Lo stato del progetto è quello in `docs/STATUS.md`, non la memoria di sessioni precedenti.**
- **Se il contesto è parziale: dichiarare la lacuna esplicitamente, non compensarla con inferenze.**
- **Fine di ogni sessione con modifiche: aggiornare `docs/STATUS.md` nello stesso commit.**

---

## Setup del Repository

Dopo ogni clone, eseguire **prima di qualsiasi commit**:

```bash
bash scripts/setup-hooks.sh
```

Attiva i git hooks (ADR-0006): `pre-commit` blocca commit senza change document o ADR malformati; `commit-msg` blocca commit senza CHG-ID.

### Formato Commit Obbligatorio — ADR-0005

Footer obbligatorio in ogni commit non-triviale:

```
CHG-YYYY-MM-DD-NNN
ADR-NNNN
```

Commit di sola documentazione (`docs(scope):`, `chore(scope):`) sono esentati dal footer.
