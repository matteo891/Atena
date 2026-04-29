# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-04-29 — commit `b05ecbe`
> **Sessione corrente:** TALOS — Iterating **Round 2**: chiuse 6 lacune critiche (L06, L08, L11, L12, L18, L20), 1 nuova condizionale (L11b). **19 aperte** (2 critiche residue: L04 formula VGP, L21 Keepa).

---

## Stato in Una Riga

Governance hardened (ADR 0001–0012) + vision in `Iterating` **Round 2** su **TALOS (Scaler 500k)** — Hedge Fund algoritmico per FBA Wholesale High-Ticket. 19 lacune da chiudere prima del Frozen (era 24 in Round 1; 6 chiuse, 1 nuova condizionale L11b). **Critica bloccante:** formula VGP Score non definita (L04).

**Repository:** https://github.com/santacrocefrancesco00-ux/Atena
**Milestone tag corrente:** `milestone/vision-protocol-v0.6.0` su commit `55ea55f` (restore point pre-esposizione)
**Codename progetto:** TALOS — *Scaler 500k*

---

## Appena Completato

| Cosa | ADR | CHG | Commit |
|---|---|---|---|
| ADR 0001–0008 promulgati (governance fondativa) | 0001–0008 | [CHG-001](changes/2026-04-29-001-bootstrap-adr-fondativi.md) | `5959ebd`, `a796ce0` |
| Hardening governance v0.5.0 — ADR-0009/0010/0011 | 0009–0011 | [CHG-002](changes/2026-04-29-002-hardening-governance.md) | `416ab87` |
| Vision capture protocol — ADR-0012 + PROJECT-RAW.md template Draft | 0012 | [CHG-003](changes/2026-04-29-003-vision-capture-adr.md) | `7b7ef17` |
| Restore point `milestone/vision-protocol-v0.6.0` | 0003 | — | tag su `55ea55f` |
| **TALOS — Esposizione Round 1: trascrizione verbatim + 24 lacune** | 0012 | [CHG-004](changes/2026-04-29-004-talos-exposition-iterating.md) | `44d53e7` |
| **TALOS — Round 2 Q&A: 6 critiche chiuse, L11b condizionale aperta** | 0012 | [CHG-005](changes/2026-04-29-005-talos-iterating-round-2.md) | `b05ecbe` |

---

## In Sospeso

| ID | Cosa | Priorità | Note |
|---|---|---|---|
| ~~ESP-002~~ | ~~Round 2 Q&A~~ | **Chiusa parzialmente in Round 2 (CHG-005)** | 6 critiche su 8 chiuse; restano L04 + L21 |
| **ESP-003** | **Round 3 Q&A: chiusura L04 (formula VGP) + L21 (Keepa) + sweep importanti+forma** | **Prossimo passo immediato** | L04 è bottleneck dell'MVP; Round 3 sblocca specificabilità + testabilità |
| ISS-001 | `gitnexus analyze` non eseguibile (architettura processore) | Rinviata | Uso futuro da PC operativo Leader |
| ISS-002 | Stack tecnologico → ADR di stack | Bloccante per fase codice | Si sblocca dopo Frozen + scomposizione validata; vincoli già parzialmente dichiarati: Python 3.10+, PostgreSQL via Docker, Streamlit/Gradio (LACUNA L14), Numpy vettorizzato |

### Le 2 lacune critiche residue (post Round 2)

| # | Lacuna | Sezione | Note |
|---|---|---|---|
| L04 | **Formula del VGP Score non definita** (monarca decisore) | 4.1.4 / 6.3 | Bottleneck assoluto: senza questa l'MVP non è specificabile né testabile |
| L21 | Keepa: subscription, campi, costo, rate limit | 4.1.1 | Collegata a L11/L11b: definisce se il lookup Fee_FBA è disponibile o se serve la formula manuale del Leader |

### Decisioni architetturali ratificate in Round 2

| # | Decisione | Origine |
|---|---|---|
| L06 | MVP Samsung-only + interface `BrandExtractor` modulare per estensione futura | Delega esplicita Leader → Claude |
| L08 | Scraping `amazon.it` (libreria specifica in ADR di stack) | Leader |
| L11 | Lookup primario Keepa + fallback formula manuale (→ L11b condizionale) | Leader |
| L12 | Lookup automatico per categoria + override manuale configurabile | Leader |
| L18 | Tesseract locale (open source, gratis, qualità media) | Leader |
| L20 | Pytest + fixture byte-exact + grep statico R-01 + ruff strict + mypy/pyright strict | Suggerimento Claude accettato |

---

## Prossima Azione

1. **Leader risponde alle 8 lacune critiche** (e progressivamente alle altre 15). Suggerirei di iniziare da L04 (formula VGP) perché è il bottleneck dell'MVP.
2. Status del file aggiorna `qa_rounds` ad ogni round; Q&A Log cresce; tabella lacune scende verso 0.
3. Quando il Leader dichiara "Frozen", Claude propone in chat la scomposizione in proposte di ADR di architettura/stack + task ROADMAP.
4. Leader valida proposta per proposta → Claude promulga gli ADR ratificati e aggiorna ROADMAP.
5. Solo dopo: prima linea di codice TALOS sotto ADR di stack ratificato.

---

## Nota al Prossimo Claude

> Questo campo è il presidio principale contro le allucinazioni da contesto perso. Leggerlo come se qualcuno avesse lasciato un biglietto.

- **Step 0 del Self-Briefing è bloccante (ADR-0010).** Verifica `git config core.hooksPath` = `scripts/hooks` prima di tutto.
- **`PROJECT-RAW.md` è in stato `Iterating` Round 1 (codename TALOS).** Leggerlo in pieno se la sessione tocca decisioni architetturali. **NON scrivere ROADMAP né promulgare ADR di stack** finché il Leader non dichiara `Frozen` e valida la scomposizione (pipeline ADR-0012 step [6]–[7]).
- **Regola "Lacune mai completate" (ADR-0012, vincolante).** Il Leader ha dichiarato "nessuna lacuna aperta", ma 23 sono state marcate per disciplina. Se nei round successivi emergono altre ambiguità, marcarle e non inferire.
- **Lacuna critica bloccante:** L04 — la formula del **VGP Score** non è stata definita. È il "monarca decisore" del sistema. Senza VGP, MVP non è specificabile né testabile. PRIMA di qualsiasi proposta di scomposizione, L04 deve essere chiusa.
- **Refusi noti nelle Leggi di Talos (R-08 vs R-09):** il testo del Leader cita "Veto ROI (R-09)" mentre in tabella R-09 è Archiviazione e R-08 è Veto ROI. Marcato L09. Non interpretare in autonomia: chiedere conferma.
- **GitNexus rinviato (ISS-001).** Step 4 self-briefing degrada con dichiarazione esplicita.
- **Errata corrige post-Frozen (ADR-0009).** Quando PROJECT-RAW.md sarà Frozen, ogni modifica successiva alla vision passa per Errata Corrige o transizione documentata a `Iterating`.
- **Push immediato post-commit certificato (ADR-0011).**
- **Test manuali documentati ammessi per governance (ADR-0011), non per codice applicativo.**
- **Tutti gli ADR sono `Active`.** ADR-0004 è `Active¹` (hardening patch).
- **Header `Ultimo aggiornamento` di STATUS.md obbligatorio (ADR-0010).** Aggiornare data + commit hash post-commit. Ogni claim ancorato.

---

## Issues Noti

| ID | Descrizione | Workaround | ADR | Priorità |
|---|---|---|---|---|
| ISS-001 | `gitnexus analyze` segfault / exit code 5 su Node v24.15.0; architettura processore macchina locale incompatibile | Saltare step 4 GitNexus nel self-briefing con dichiarazione esplicita; uso futuro da PC operativo Leader | ADR-0007 | Rinviata |
| ISS-002 | Stack tecnologico → ADR di stack non promulgato | Si sblocca dopo Frozen di TALOS + scomposizione validata | ADR-0012 → ADR di stack | Bloccante per fase codice |
| ESP-001 | Esposizione bozza progetto | **Chiusa 2026-04-29 con CHG-004** — bozza esposta verbatim, status Iterating | ADR-0012 | Chiusa |
| ESP-002 | Round 2: chiusura delle 24 lacune di TALOS | **Chiusa parzialmente 2026-04-29 con CHG-005** — 6 critiche chiuse (L06, L08, L11, L12, L18, L20); 1 condizionale nuova (L11b) | ADR-0012 | Chiusa parzialmente |
| ESP-003 | Round 3: chiusura L04 (formula VGP) + L21 (Keepa) + sweep delle 13 importanti + 4 di forma | Prossimo passo del Leader; L04 è bottleneck dell'MVP | ADR-0012 | Prossima |
