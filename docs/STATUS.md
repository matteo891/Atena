# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-04-29 — commit `[da aggiornare post-commit CHG-003]`
> **Sessione corrente:** Vision capture protocol (CHG-003) — promulgazione ADR-0012 + creazione `PROJECT-RAW.md` template Draft. Pronto per esposizione bozza dal Leader.

---

## Stato in Una Riga

Governance hardened (ADR 0001–0011) e vision capture protocol attivo (ADR-0012). `PROJECT-RAW.md` esiste in root, status `Draft`, 16 lacune aperte da chiudere all'esposizione del Leader. Nessun codice applicativo presente.

**Repository:** https://github.com/santacrocefrancesco00-ux/Atena
**Milestone tag corrente:** `milestone/ADR-0001-0008` su commit `a796ce0`
**Milestone tag proposto (governance hardening):** `milestone/governance-hardening-v0.5.0` su commit `416ab87` (richiede approvazione Leader esplicita)

---

## Appena Completato

| Cosa | ADR | CHG | Commit |
|---|---|---|---|
| ADR 0001–0008 promulgati (governance fondativa) | 0001–0008 | [CHG-001](changes/2026-04-29-001-bootstrap-adr-fondativi.md) | `5959ebd`, `a796ce0` |
| Hardening governance v0.5.0 — fix audit (B1–B5, M1–M9, P1–P3); ADR-0009/0010/0011 | 0009–0011 | [CHG-002](changes/2026-04-29-002-hardening-governance.md) | `416ab87` (+ backfill `1235f13`) |
| **Vision capture protocol — ADR-0012 promulgato** | 0012 | [CHG-003](changes/2026-04-29-003-vision-capture-adr.md) | [commit corrente] |
| **`PROJECT-RAW.md` creato in root, status `Draft`, 16 lacune iniziali, Q&A Log vuoto** | 0012 | CHG-003 | [commit corrente] |
| **INDEX, FILE-ADR-MAP, ROADMAP, CHANGELOG aggiornati con ADR-0012** | 0012 | CHG-003 | [commit corrente] |

---

## In Sospeso

| ID | Cosa | Priorità | Note |
|---|---|---|---|
| ESP-001 | Esposizione della bozza del progetto da parte del Leader | **Prossimo passo immediato** | Il Leader si è assentato dopo aver ratificato CHG-003. `PROJECT-RAW.md` è pronto per ricevere la trascrizione |
| ISS-001 | `gitnexus analyze` non eseguibile (architettura processore incompatibile) | Rinviata — decisione Leader 2026-04-29 | Sarà eseguito da PC operativo del Leader |
| ISS-002 | Stack tecnologico non ancora definito | Bloccante per fase codice | Sarà popolato dalla scomposizione validata del PROJECT-RAW Frozen (ADR-0012 step [6]–[7]) |

---

## Prossima Azione

1. **Leader torna e espone la bozza.** Claude trascrive in `PROJECT-RAW.md`, marca lacune con `[LACUNA: ...]`, chiede chiarimenti round per round.
2. Status del file passa `Draft → Iterating` durante i round Q&A.
3. Quando il Leader dichiara "Frozen", Claude propone scomposizione testuale in chat (ADR di architettura + task ROADMAP), **senza scrivere niente di vincolante senza validazione**.
4. Leader valida proposta per proposta → Claude promulga ADR di stack / aggiorna ROADMAP.
5. Solo allora si può scrivere la prima linea di codice applicativo (sotto ADR di stack ratificato).

Tag opzionale prima dell'esposizione: il Leader può autorizzare `milestone/governance-hardening-v0.5.0` per cristallizzare lo stato pre-vision.

---

## Nota al Prossimo Claude

> Questo campo è il presidio principale contro le allucinazioni da contesto perso. Leggerlo come se qualcuno avesse lasciato un biglietto.

- **Step 0 del Self-Briefing è bloccante (ADR-0010).** Verifica `git config core.hooksPath` = `scripts/hooks` PRIMA di qualsiasi altra cosa. Se è vuoto o diverso, fermati, chiedi al Leader, non procedere. Nessuna eccezione salvo dichiarazione esplicita "sessione di sola lettura".
- **`PROJECT-RAW.md` è il file di vision raw (ADR-0012).** Stato corrente: `Draft`, 16 lacune iniziali. Leggerlo come parte del briefing se la sessione tocca decisioni architetturali. Non scrivere ROADMAP / promulgare ADR di stack senza che il Leader abbia dichiarato `Frozen` e validato la scomposizione (pipeline step [6]–[7]).
- **Regola "Lacune mai completate" (ADR-0012, vincolante).** Se il Leader chiede una "spiegazione puntuale e maniacale" di una bozza vaga, NON inferire: marca `[LACUNA: <domanda concreta>]` e raccogli in sezione 9 di PROJECT-RAW.md. La maniacalità è sulla precisione di trascrizione, non sul completamento.
- **Stati di PROJECT-RAW.md.** `Draft` (esposizione iniziale, modifica diretta) → `Iterating` (round Q&A, modifica diretta + Q&A Log cresce) → `Frozen` (intent ratificato, modifiche solo via Errata Corrige ADR-0009 o transizione esplicita a `Iterating`). Solo il Leader promuove a `Frozen`.
- **GitNexus è rinviato (ISS-001).** Architettura processore della macchina locale incompatibile. Sarà usato da PC operativo del Leader. Step 4 del self-briefing degrada con dichiarazione esplicita; nessun tentativo locale.
- **Il repo contiene solo governance hardened + vision template.** Nessun file sorgente applicativo esiste. Non assumere l'esistenza di alcun modulo, funzione o classe.
- **ADR-0004 ha una sezione obsoleta marcata.** "Flusso di Re-Briefing" superseduta da ADR-0010 (hardening patch ADR-0009). NON seguirla. Sequenza canonica in ADR-0010 e in CLAUDE.md.
- **Errata corrige e hardening patch sono un meccanismo formale (ADR-0009).** Per refusi: modifica diretta + sezione `## Errata`. Per sezioni obsolete: blocco "Superseduta" + sezione `## Errata`. Per cambi di sostanza: supersessione completa.
- **Push immediato post-commit certificato (ADR-0011).** Default. Eccezioni solo con autorizzazione esplicita del Leader.
- **Test manuali documentati ammessi per governance (ADR-0011), non per codice applicativo.**
- **Tutti gli ADR sono `Active`.** ADR-0004 è `Active¹` (con hardening patch su una sezione). Nessuno è Deprecated o Superseded.
- **Header `Ultimo aggiornamento` di STATUS.md è obbligatorio (ADR-0010).** Aggiornare data + commit hash post-commit di sessione. Ogni claim in STATUS.md deve avere ancora verificabile.
- **Commit-msg hook ora richiede CHG-ID + ADR-NNNN + CHG-ID esistente come file.** Bypass per `docs(`/`chore(`/`ci(` solo se in staging non c'è file non-triviale.

---

## Issues Noti

| ID | Descrizione | Workaround | ADR | Priorità |
|---|---|---|---|---|
| ISS-001 | `gitnexus analyze` segfault / exit code 5 su Node v24.15.0; architettura processore macchina locale incompatibile | Saltare step 4 GitNexus nel self-briefing con dichiarazione esplicita; uso futuro da PC operativo Leader | ADR-0007 | Rinviata |
| ISS-002 | Stack tecnologico non ancora definito | Verrà popolato dalla scomposizione validata di PROJECT-RAW Frozen (ADR-0012) | ADR-0012 | Bloccante per fase codice |
| ESP-001 | Esposizione della bozza progetto attesa | `PROJECT-RAW.md` template Draft pronto a riceverla | ADR-0012 | Prossimo passo |
