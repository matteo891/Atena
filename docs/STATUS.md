# STATUS — Stato Corrente del Progetto

> **Leggere per primo nel self-briefing (Step 1, dopo Step 0 di verifica hook) — max 60 secondi per il re-entry.**
> Aggiornare alla fine di ogni sessione con modifiche, nello stesso commit (ADR-0008 Regola 7 + ADR-0010).

> **Ultimo aggiornamento:** 2026-04-29 — commit `5f8d664`
> **Sessione corrente:** TALOS — **`Frozen` dichiarato esplicitamente dal Leader** (Round 6, verbatim: *"dichiaro frozen"*). La vision è congelata: `frontmatter.status: Frozen`, `frozen_at: 2026-04-29`. Sblocco dello step [6] di ADR-0012: Claude può proporre in chat la scomposizione in ADR di stack + task ROADMAP, soggetta a validazione del Leader.

---

## Stato in Una Riga

Governance hardened (ADR 0001–0012) + **vision TALOS `Frozen` dal 2026-04-29** (26/26 lacune chiuse). Sblocco step [6] ADR-0012: prossima azione = proposta di scomposizione in chat (Claude) → validazione Leader → ratifica ADR di stack + popolamento ROADMAP applicativo.

**Repository:** https://github.com/matteo891/Atena (fork operativo del Leader; il repo originale `santacrocefrancesco00-ux/Atena` è del padre)
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
| **TALOS — Round 4: chiusa L04b (normalizzazione min-max [0,1] dei tre termini VGP). 0 critiche residue.** | 0012 | [CHG-007](changes/2026-04-29-007-talos-iterating-round-4.md) | `0cd9f1f` |
| Backfill CHG-007 + fix repo URL al fork operativo `matteo891/Atena` | — | (parte di CHG-007) | `97f404f`, `2abe28e` |
| **TALOS — Round 5: sweep finale, chiuse tutte le 17 lacune residue. Vision pronta per Frozen.** | 0012 | [CHG-008](changes/2026-04-29-008-talos-iterating-round-5-sweep-finale.md) | `08beebf` |
| Backfill CHG-008 | — | (parte di CHG-008) | `8f7333d` |
| **TALOS — Round 6: `Frozen` dichiarato esplicitamente dal Leader. Vision congelata.** | 0012 | [CHG-009](changes/2026-04-29-009-talos-frozen-declaration.md) | `5f8d664` |

---

## In Sospeso

| ID | Cosa | Priorità | Note |
|---|---|---|---|
| ~~ESP-002~~ | ~~Round 2 Q&A~~ | Chiusa in Round 2 (CHG-005) | — |
| ~~ESP-003~~ | ~~Round 3 Q&A~~ | Chiusa parzialmente in Round 3 (CHG-006) — L04+L21 chiuse, aperta L04b | — |
| ~~ESP-004~~ | ~~Round 4: chiusura L04b~~ | Chiusa in Round 4 (CHG-007) — normalizzazione min-max [0,1] | — |
| ~~ESP-005~~ | ~~Sweep finale: 17 residue~~ | Chiusa in Round 5 (CHG-008) — tutte le 17 chiuse in un colpo | — |
| ~~ESP-006~~ | ~~Transizione `Iterating → Frozen`~~ | Chiusa in Round 6 (CHG-009) — Leader: *"dichiaro frozen"* | — |
| **ESP-007** | **Step [6] ADR-0012: proposta di scomposizione (Claude in chat) → validazione Leader → ratifica ADR di stack** | Prossimo passo | Sbloccato dal Frozen. Output atteso: pacchetto di ADR di stack proposti + task ROADMAP applicativo |
| **TAG-001** | **Proposta milestone tag GitHub `milestone/vision-frozen-v0.8.0`** | Suggerita | Restore point cruciale pre-scomposizione (ADR-0003); creazione subordinata ad autorizzazione Leader |
| ISS-001 | `gitnexus analyze` non eseguibile (architettura processore) | Rinviata | Uso futuro da PC operativo Leader |
| ISS-002 | Stack tecnologico → ADR di stack | Bloccante per fase codice | Si sblocca dopo Frozen + scomposizione validata; vincoli già parzialmente dichiarati: Python 3.10+, PostgreSQL via Docker, Streamlit/Gradio (LACUNA L14), Numpy vettorizzato |

### Lacune critiche residue

Nessuna. Round 4 ha chiuso l'ultima critica (L04b).

### Lacune aperte

Nessuna. Round 5 ha chiuso le 17 residue in un colpo.

### Decisioni architetturali ratificate (Round 2 + 3 + 4 + 5)

Tutte le 26 lacune sono chiuse. Per la lista completa vedi sezione 9 di `PROJECT-RAW.md`. Sintesi delle decisioni più strutturali:

| Tema | Decisione | Round |
|---|---|---|
| Formula VGP | `(ROI*0.4)+(Vel*0.4)+(Cash_Profit*0.2)` con normalizzazione min-max [0,1] sul listino di sessione | 3 + 4 |
| Estrattore | `SamsungExtractor` (MVP) con interface `BrandExtractor`; NLP+Regex come unico modulo a pipeline interna | 2 + 5 |
| Lookup Amazon | Scraping `amazon.it` via Playwright | 2 + 5 |
| Fee_FBA | Lookup Keepa primario; fallback formula manuale verbatim del Leader | 2 + 5 |
| Referral_Fee | Lookup categoria + override manuale configurabile | 2 |
| Keepa | Piano gestito esternamente; Talos consuma le API | 3 |
| OCR | Tesseract locale | 2 |
| UI | Streamlit (cruscotto militare con griglie e slider) | 5 |
| Stack Python | SQLAlchemy 2.0 sync + Alembic + Playwright + Tesseract + pytest + ruff strict + mypy strict | 2 + 5 |
| DB | PostgreSQL Zero-Trust (RLS + ruoli `talos_app`/`talos_admin` + no superuser pool app + audit log) | 5 |
| Velocity Target | Slider 7–30 gg, default 15, step 1 | 5 |
| Veto ROI | Soglia configurabile dal cruscotto, default 8% | 5 |
| Manual Override | Lock-in UI + tabella + Priorità=∞ nel Tetris | 5 |
| Storico ordini | Solo interno, alimentato dall'azione "ordina" | 5 |
| Output commercialista | Niente automatico, solo storico interno consultabile | 5 |
| Capitale `x` | Budget di sessione (Opzione a) | 5 |
| Stateless | Analisi di sessione senza dipendenza causale da sessioni precedenti | 5 |

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
- **`PROJECT-RAW.md` è in stato `Frozen` dal 2026-04-29 (codename TALOS).** Da questo momento ogni modifica alla vision passa per **Errata Corrige** (ADR-0009) o **transizione documentata a `Iterating`** con motivazione esplicita del Leader. Niente edit diretti silenziosi.
- **Regola "Lacune mai completate" (ADR-0012, vincolante).** Continua ad applicarsi anche post-Frozen. Se emergono ambiguità durante la scomposizione, marcarle in chat e portarle al Leader, **non inferire**.
- **Step [6] ADR-0012 sbloccato.** Claude può ora proporre la scomposizione della vision in ADR di stack + task ROADMAP. La proposta avviene **in chat** (non come edit diretto dei file). Solo dopo validazione del Leader si promulgano gli ADR di stack ratificati.
- **NON scrivere il primo file di codice applicativo** finché almeno un ADR di stack non è ratificato (vincolo CLAUDE.md + ROADMAP obiettivo #10).
- **Repo origin:** `https://github.com/matteo891/Atena` (fork operativo del Leader). Il repo del padre `santacrocefrancesco00-ux/Atena` non è scrivibile da `matteo891`.
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
| ESP-005 | Round 5: sweep finale 17 lacune residue | Chiusa 2026-04-29 con CHG-008 — tutte chiuse in un colpo | ADR-0012 | Chiusa |
| ESP-006 | Transizione Iterating → Frozen | Chiusa 2026-04-29 con CHG-009 — Leader: "dichiaro frozen" | ADR-0012 | Chiusa |
| ESP-007 | Step [6] ADR-0012: proposta scomposizione → ADR di stack | Prossimo passo (Claude in chat) | ADR-0012 | Prossima |
