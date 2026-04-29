---
id: CHG-2026-04-29-009
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Committed
commit: 5f8d664
adr_ref: ADR-0012
---

## What

Transizione formale del file `PROJECT-RAW.md` (vision TALOS) da **`Iterating`** a **`Frozen`** dopo dichiarazione esplicita del Leader.

**Risposta verbatim del Leader:** *"dichiaro frozen"*

Modifiche applicate:
- Frontmatter: `status: Iterating → Frozen`; `frozen_at: 2026-04-29`; `qa_rounds: 5 → 6`.
- Header del documento: nota di stato corrente aggiornata; pipeline ADR-0012 con `(qui)` spostato da `Iterating` a `Frozen`.
- Q&A Log: nuovo blocco **Round 6 — Dichiarazione `Frozen`** con risposta verbatim del Leader e tabella eventi (6.1 dichiarazione, 6.2 mutazione frontmatter, 6.3 sblocco step [6]).
- Cronologia Stati: nuova riga `Frozen` (2026-04-29).

Nessuna modifica al **contenuto** della vision (sezioni 1–11). Il Frozen non altera le decisioni, solo cristallizza lo stato.

## Why

ADR-0012 step [5] — la transizione `Iterating → Frozen` è un **atto formale del Leader**, non automatico anche con 0 lacune aperte. Questo CHG documenta l'atto.

Conseguenze immediate:
- **Sblocco step [6]** — Claude può ora proporre in chat la scomposizione della vision in ADR di stack + task ROADMAP applicativo, soggetta a validazione del Leader.
- **Regime di modifica post-Frozen (ADR-0012 + ADR-0009)** — ogni modifica successiva alla vision passa per:
  - **Errata Corrige** per refusi/incoerenze testuali (modifica diretta + sezione `## Errata`),
  - **Hardening Patch** per sezioni rese obsolete da ADR posteriori,
  - **Transizione documentata `Frozen → Iterating`** per modifiche di sostanza (nuovo round Q&A con motivazione esplicita del Leader).
  Niente edit diretti silenziosi.
- **Anti-allucinazione (ADR-0008 Regola 5)** — lo stato del progetto è ora ancorato a `Frozen` con commit specifico. Ogni futuro Self-Briefing deve riconoscere il Frozen come fatto compiuto, non come in-progress.

## How

### Edit puntuali in `PROJECT-RAW.md`

- **Frontmatter:** `status: Iterating → Frozen`; `frozen_at: — → 2026-04-29`; `qa_rounds: 5 → 6`.
- **Header (riga 14–24):** nota di stato corrente riscritta per riflettere il Frozen + regime di modifica post-Frozen (Errata Corrige / Hardening Patch / re-Iterating). Pipeline note aggiornata: `(qui)` spostato da `Iterating` a `Frozen`.
- **Sezione 10 (Q&A Log):** nuovo blocco `Round 6 — 2026-04-29 — Dichiarazione Frozen` con risposta verbatim del Leader e tabella 6.1/6.2/6.3.
- **Sezione "Cronologia Stati":** nuova riga `2026-04-29 | Frozen | Round 6: dichiarazione esplicita...`.

### Aggiornamenti negli altri documenti

- **`docs/STATUS.md`:**
  - Header `Ultimo aggiornamento` (commit hash da backfillare).
  - "Sessione corrente" e "Stato in Una Riga" riscritti per il Frozen.
  - "Appena Completato" — aggiunta riga CHG-009.
  - "In Sospeso" — ESP-006 chiusa, ESP-007 (proposta scomposizione) aperta, TAG-001 (milestone tag) suggerito.
  - "Nota al Prossimo Claude" — regime post-Frozen + sblocco step [6] + vincolo no-codice-prima-di-ADR-stack.
  - "Issues Noti" — ESP-006 chiusa, ESP-007 prossima.
- **`ROADMAP.md`:**
  - Obiettivo #7 marcato Completato (Round 6 inclusivo del Frozen).
  - Obiettivo #8 marcato In corso.
  - Log validazioni esteso con riga Round 6.
- **`CHANGELOG.md`:**
  - Nuova versione `[0.8.0]` in cima — pietra miliare del progetto. Bumpa minor (non patch) perché segna una transizione di fase, non un fix.

### Tag GitHub proposto (non creato in questo commit)

Suggerimento operativo per il Leader: **creare un milestone tag annotato** subito dopo questo commit:

```
git tag -a milestone/vision-frozen-v0.8.0 -m "TALOS — Vision Frozen (26/26 lacune chiuse, 6 round di Iterating)"
git push origin milestone/vision-frozen-v0.8.0
```

Razionale (ADR-0003):
- Restore point cruciale prima dell'inizio della scomposizione (step [6]).
- Ogni ADR completamente implementato merita milestone tag — ADR-0012 ha completato il suo ciclo `Draft → Iterating → Frozen` con questa transizione.
- Coerente con il tag esistente `milestone/vision-protocol-v0.6.0` (su `55ea55f`) che marcò la promulgazione di ADR-0012 stesso.

Creazione subordinata ad autorizzazione Leader (push esplicito dei tag, ADR-0011).

## Tests

Test manuali documentati (governance — ADR-0011).

| Test | Comando / Verifica | Esito |
|---|---|---|
| Frontmatter `status: Frozen` | `grep '^status:' PROJECT-RAW.md` | atteso PASS |
| Frontmatter `frozen_at: 2026-04-29` | `grep '^frozen_at:' PROJECT-RAW.md` | atteso PASS |
| Frontmatter `qa_rounds: 6` | `grep '^qa_rounds:' PROJECT-RAW.md` | atteso PASS |
| Header riflette Frozen | `grep -A1 'Status corrente' PROJECT-RAW.md \| grep 'Frozen'` | atteso PASS |
| Pipeline note ha `(qui)` su Frozen | `grep 'Frozen (qui' PROJECT-RAW.md` | atteso PASS |
| Q&A Log Round 6 presente | `grep -c 'Round 6 — 2026-04-29' PROJECT-RAW.md` | atteso PASS |
| Citazione verbatim "dichiaro frozen" | `grep -F '"dichiaro frozen"' PROJECT-RAW.md` | atteso PASS |
| Cronologia Round 6 presente | `grep -c 'Round 6: dichiarazione esplicita' PROJECT-RAW.md` | atteso PASS |
| STATUS.md "Stato in Una Riga" cita Frozen | `grep 'Frozen dal 2026-04-29' docs/STATUS.md` | atteso PASS |
| STATUS.md ESP-007 aperta | `grep 'ESP-007' docs/STATUS.md` | atteso PASS |
| STATUS.md TAG-001 presente | `grep 'TAG-001' docs/STATUS.md` | atteso PASS |
| ROADMAP obiettivo #7 Completato | `grep -F '| 7 |' ROADMAP.md \| grep 'Completato'` | atteso PASS |
| ROADMAP log Round 6 presente | `grep -c 'Round 6.*Frozen' ROADMAP.md` | atteso PASS |
| CHANGELOG `[0.8.0]` presente | `grep -c '\[0.8.0\]' CHANGELOG.md` | atteso PASS |

**Copertura:** verifica strutturale completa della transizione. Validazione semantica del Frozen (assenza di edit accidentali alle sezioni 1–11) garantita dalla strategia di edit puntuale: solo frontmatter, header, sezione 10 (Round 6), cronologia. Nessuna sezione di vision toccata.

**Rischi residui:**
- Se in futuro emergono lacune non identificate durante l'Iterating, il regime post-Frozen impone Errata Corrige o ri-apertura formale a `Iterating`. Disciplina in capo al Leader e a Claude.
- L'eventuale milestone tag GitHub `milestone/vision-frozen-v0.8.0` è suggerito ma non creato in questo commit — la creazione resta atto separato del Leader.

## Refs

- ADR: ADR-0012 (step [5] completato), ADR-0003 (proposta milestone tag), ADR-0009 (regime post-Frozen)
- Vision: `PROJECT-RAW.md` — ora `Frozen`
- Predecessori: CHG-007 (Round 4), CHG-008 (Round 5)
- Commit: `5f8d664`
- Issue: ESP-006 (chiusa con questo CHG) → ESP-007 (proposta scomposizione aperta) + TAG-001 (suggerito)
