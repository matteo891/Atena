# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-04-29 — commit `<pending CHG-007 backfill>`
> **Sessione corrente:** TALOS — Iterating **Round 4**: chiusa L04b (normalizzazione **min-max su [0,1]** dei tre termini VGP sul listino di sessione, prima dei pesi 40/40/20). **0 critiche residue**, **17 aperte** (13 importanti + 4 di forma; più L11b condizionale). Vision pronta per sweep finale → Frozen. Risolto anche side-finding: ricreati MEMORY.md + feedback_concisione_documentale.md (referenziati in CHG-006 ma assenti su filesystem — directory memory non versionata).

---

## Stato in Una Riga

Governance hardened (ADR 0001–0012) + vision in `Iterating` **Round 4** su **TALOS (Scaler 500k)**. **0 lacune critiche residue.** 17 importanti+forma da chiudere con sweep finale prima del Frozen. Dominio matematico del decisore VGP pienamente specificato (formula + normalizzazione).

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
| **TALOS — Round 3: formula VGP, Keepa out-of-scope, L04b critica aperta, direttiva concisione → memory** | 0012 | [CHG-006](changes/2026-04-29-006-talos-iterating-round-3.md) | `7dee02b` |
| **TALOS — Round 4: chiusa L04b (normalizzazione min-max [0,1] dei tre termini VGP). 0 critiche residue.** | 0012 | [CHG-007](changes/2026-04-29-007-talos-iterating-round-4.md) | `<pending backfill>` |

---

## In Sospeso

| ID | Cosa | Priorità | Note |
|---|---|---|---|
| ~~ESP-002~~ | ~~Round 2 Q&A~~ | Chiusa in Round 2 (CHG-005) | — |
| ~~ESP-003~~ | ~~Round 3 Q&A~~ | Chiusa parzialmente in Round 3 (CHG-006) — L04+L21 chiuse, aperta L04b | — |
| ~~ESP-004~~ | ~~Round 4: chiusura L04b~~ | Chiusa in Round 4 (CHG-007) — normalizzazione min-max [0,1] | — |
| **ESP-005** | **Sweep finale: 13 importanti + 4 di forma + L11b condizionale → Frozen** | Prossimo passo | Nessuna critica residua, dipende da disponibilità del Leader per il sweep |
| ISS-001 | `gitnexus analyze` non eseguibile (architettura processore) | Rinviata | Uso futuro da PC operativo Leader |
| ISS-002 | Stack tecnologico → ADR di stack | Bloccante per fase codice | Si sblocca dopo Frozen + scomposizione validata; vincoli già parzialmente dichiarati: Python 3.10+, PostgreSQL via Docker, Streamlit/Gradio (LACUNA L14), Numpy vettorizzato |

### Lacune critiche residue

Nessuna. Round 4 ha chiuso l'ultima (L04b).

### Decisioni architetturali ratificate (Round 2 + 3 + 4)

| # | Round | Decisione |
|---|---|---|
| **L04b** | **4** | **Normalizzazione min-max su [0,1] dei tre termini VGP sul listino di sessione, prima dei pesi 40/40/20** |
| L04 | 3 | Formula VGP: `(ROI*0.4) + (Velocità*0.4) + (Cash_Profit*0.2)` |
| L21 | 3 | Keepa: piano gestito esternamente dal Leader, Talos consuma le API |
| L06 | 2 | MVP Samsung-only + interface `BrandExtractor` modulare |
| L08 | 2 | Scraping `amazon.it` |
| L11 | 2 | Lookup Keepa primario + fallback formula manuale (L11b condizionale) |
| L12 | 2 | Lookup categoria + override manuale configurabile |
| L18 | 2 | Tesseract locale |
| L20 | 2 | Pytest + fixture byte-exact + grep R-01 + ruff/mypy strict |

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
- **`PROJECT-RAW.md` è in stato `Iterating` Round 4 (codename TALOS).** Leggerlo in pieno se la sessione tocca decisioni architetturali. **NON scrivere ROADMAP né promulgare ADR di stack** finché il Leader non dichiara `Frozen` e valida la scomposizione (pipeline ADR-0012 step [6]–[7]).
- **Regola "Lacune mai completate" (ADR-0012, vincolante).** Se nei round successivi emergono altre ambiguità, marcarle e non inferire — anche se sembrano minute.
- **Nessuna lacuna critica residua post Round 4.** L04 (formula VGP) e L04b (normalizzazione min-max [0,1]) sono entrambe chiuse. Resta da fare lo sweep delle 17 importanti+forma + L11b condizionale prima del Frozen.
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
| ESP-002 | Round 2 | Chiusa 2026-04-29 con CHG-005 | ADR-0012 | Chiusa |
| ESP-003 | Round 3: chiusura L04 + L21 | Chiusa 2026-04-29 con CHG-006; aperta nuova L04b critica | ADR-0012 | Chiusa parzialmente |
| ESP-004 | Round 4: chiusura L04b | Chiusa 2026-04-29 con CHG-007 — normalizzazione min-max [0,1] | ADR-0012 | Chiusa |
| ESP-005 | Sweep finale: 13 importanti + 4 di forma + L11b condizionale → Frozen | Prossimo passo del Leader | ADR-0012 | Prossima |
