# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-04-29 — commit `416ab87`
> **Sessione corrente:** Hardening governance v0.5.0 — promulgazione ADR-0009/0010/0011, errata su ADR-0003 e CHG-001, hardening patch su ADR-0004, rinforzo hook.

---

## Stato in Una Riga

Governance hardened (ADR 0001–0011, hook rinforzati, errata + hardening patch operativi, push policy + branch policy + test validity codificate). Nessun codice applicativo presente. Sistema valutato a prova di bomba per la fase governance.

**Repository:** https://github.com/santacrocefrancesco00-ux/Atena
**Milestone tag corrente:** `milestone/ADR-0001-0008` su commit `a796ce0` (precedente al hardening)
**Milestone tag proposto:** `milestone/governance-hardening-v0.5.0` (richiede approvazione Leader, su commit di chiusura di CHG-2026-04-29-002)

---

## Appena Completato

| Cosa | ADR | CHG |
|---|---|---|
| ADR 0001–0008 promulgati (meta, test gate, restore points, cross-ref, commit convention, hooks, gitnexus, anti-allucinazione) | tutti | [CHG-2026-04-29-001](changes/2026-04-29-001-bootstrap-adr-fondativi.md) (commit `5959ebd`, milestone su `a796ce0`) |
| Git hooks attivi: pre-commit + commit-msg (versione bootstrap) | ADR-0006 | CHG-2026-04-29-001 |
| Navigazione bidirezionale: FILE-ADR-MAP, INDEX, CHG-ID convention | ADR-0001, 0004, 0005 | CHG-2026-04-29-001 |
| docs/STATUS.md creato | ADR-0008 | CHG-2026-04-29-001 |
| Repo GitHub creata e pushata (prima versione) | ADR-0003 | CHG-2026-04-29-001 |
| **Audit di hardening 2026-04-29 — 5 buchi seri + 9 sviste + 3 policy gap rilevati** | — | sessione di audit (questo CHG-002) |
| **ADR-0009 promulgato — Errata Corrige & Hardening Patch** | ADR-0009 | [CHG-2026-04-29-002](changes/2026-04-29-002-hardening-governance.md) |
| **ADR-0010 promulgato — Self-Briefing Hardening & STATUS Anchoring** (Step 0, freshness, anchoring, supersede sezione di ADR-0004) | ADR-0010 | CHG-2026-04-29-002 |
| **ADR-0011 promulgato — Operational Policies** (push immediato, branch policy, test manuali documentati per governance) | ADR-0011 | CHG-2026-04-29-002 |
| **Errata applicate:** ADR-0003 (`master` → `main`), CHG-2026-04-29-001 (numerazione 0001–0008), FILE-ADR-MAP (`.gitattributes` ora ADR-0006, STATUS.md ora ADR-0008+0010) | ADR-0009 | CHG-2026-04-29-002 |
| **Hardening patch applicata:** ADR-0004 sezione "Flusso di Re-Briefing" marcata superseduta da ADR-0010 | ADR-0009 | CHG-2026-04-29-002 |
| **Hook pre-commit:** aggiunta `## Test di Conformità` ai REQUIRED (B3) | ADR-0006 | CHG-2026-04-29-002 |
| **Hook commit-msg:** classifier staging (B2), verifica CHG-ID esistente (M7), ADR-NNNN obbligatorio (M6) | ADR-0006, ADR-0005 | CHG-2026-04-29-002 |
| **CLAUDE.md:** Step 0 self-briefing, sezione "Tipi di test ammessi", branch `main` correttto, push policy esplicita | ADR-0010, ADR-0011 | CHG-2026-04-29-002 |

---

## In Sospeso

| ID | Cosa | Priorità | Note |
|---|---|---|---|
| ISS-001 | `gitnexus analyze` non eseguibile sulla macchina del Leader (architettura processore incompatibile, exit code 5 su Node v24.15.0) | Rinviata — decisione Leader 2026-04-29 | Sarà eseguita da PC operativo del Leader in seguito. Self-briefing step 4 degrada con dichiarazione esplicita |
| ISS-002 | Stack tecnologico non ancora definito | Bloccante per fase codice | Il Leader fornirà le prime istruzioni dopo il fork sul PC operativo |

---

## Prossima Azione

1. Leader rivede e approva il commit di hardening v0.5.0 (CHG-2026-04-29-002).
2. Push immediato a `origin/main` (ADR-0011).
3. Creazione milestone tag `milestone/governance-hardening-v0.5.0` su commit di chiusura, con GitHub Release.
4. Fork del repo sul PC operativo del Leader; lì avviene `bash scripts/setup-hooks.sh` e si testa `gitnexus analyze` (ISS-001).
5. Ricezione delle prime istruzioni di stack/architettura → promulgazione ADR di stack tecnologico → prima linea di codice.

---

## Nota al Prossimo Claude

> Questo campo è il presidio principale contro le allucinazioni da contesto perso. Leggerlo come se qualcuno avesse lasciato un biglietto.

- **Step 0 del Self-Briefing è bloccante (ADR-0010).** Verifica `git config core.hooksPath` = `scripts/hooks` PRIMA di qualsiasi altra cosa. Se è vuoto o diverso, fermati, chiedi al Leader, non procedere. Nessuna eccezione salvo dichiarazione esplicita "sessione di sola lettura".
- **GitNexus è rinviato (ISS-001).** Architettura processore della macchina locale incompatibile. Sarà usato da PC operativo del Leader. Step 4 del self-briefing degrada con dichiarazione esplicita; nessun tentativo locale.
- **Il repo contiene solo governance hardened.** Nessun file sorgente applicativo esiste. Non assumere l'esistenza di alcun modulo, funzione o classe. Se cerchi codice applicativo e non lo trovi, è perché non è ancora stato scritto.
- **ADR-0004 ha una sezione obsoleta marcata.** La sezione "Flusso di Re-Briefing" è stata superseduta da ADR-0010 tramite hardening patch (ADR-0009). NON seguirla. La sequenza canonica è in ADR-0010 sezione "Sequenza di Re-Briefing — Fonte Unica" e in CLAUDE.md Self-Briefing.
- **Errata corrige e hardening patch sono ora un meccanismo formale (ADR-0009).** Per refusi: modifica diretta + sezione `## Errata`. Per sezioni obsolete: blocco "Superseduta" + sezione `## Errata`. Per cambi di sostanza: supersessione completa via nuovo ADR (ADR-0001 originale).
- **Push immediato post-commit certificato (ADR-0011).** Default. Eccezioni solo con autorizzazione esplicita del Leader.
- **Test manuali documentati ammessi per governance (ADR-0011), non per codice applicativo.** Tabella delle categorie ammesse in ADR-0011.
- **Tutti gli ADR sono `Active`.** ADR-0004 è `Active¹` con hardening patch su una sezione (vedi INDEX.md legenda). Nessuno è Deprecated o Superseded.
- **Header `Ultimo aggiornamento` di STATUS.md è obbligatorio (ADR-0010).** Aggiornare data + commit hash in coda al commit di sessione. Ogni claim in STATUS.md deve avere un'ancora verificabile.
- **Commit-msg hook ora richiede CHG-ID + ADR-NNNN + CHG-ID esistente come file.** Il bypass per prefisso `docs(`/`chore(`/`ci(` vale solo se in staging non c'è alcun file non-triviale.

---

## Issues Noti

| ID | Descrizione | Workaround | ADR | Priorità |
|---|---|---|---|---|
| ISS-001 | `gitnexus analyze` segfault / exit code 5 su Node v24.15.0; architettura processore macchina locale incompatibile | Saltare step 4 GitNexus nel self-briefing con dichiarazione esplicita; uso futuro da PC operativo Leader | ADR-0007 | Rinviata |
| ISS-002 | Stack tecnologico non ancora definito | Attendere prime istruzioni del Leader | — | Bloccante per fase codice |
