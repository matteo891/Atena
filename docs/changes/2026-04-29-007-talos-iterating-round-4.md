---
id: CHG-2026-04-29-007
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Committed
commit: 0cd9f1f
adr_ref: ADR-0012
---

## What

Round 4 Q&A su `PROJECT-RAW.md` (TALOS):
- **L04b chiusa** — il Leader decide di **normalizzare i tre termini della formula VGP su [0,1]** prima di applicare i pesi 40/40/20. Citazione verbatim: *"la decisione è quella di normalizzare i tre termini. tutti i dati devono pesare e collaborare"*.
- **0 lacune critiche residue** — il dominio matematico del decisore VGP è pienamente specificato.
- Conteggio lacune: 18 → 17 aperte (chiusa 1, nessuna nuova). 0 critiche, 13 importanti, 4 di forma, + L11b condizionale.

Side-finding rilevato e risolto durante la sessione:
- Il file `MEMORY.md` e `feedback_concisione_documentale.md` referenziati in CHG-006 erano **assenti su filesystem** (la directory memory `~/.claude/projects/-home-matteo-Atena/memory/` è fuori dal repo, non versionata, ed era vuota). Ricreati in questa sessione per ripristinare la coerenza con CHG-006.

## Why

ADR-0012 step [3]–[4]: Iterating Round 4. Risposta del Leader sulla sub-lacuna critica L04b.

Razionale tecnico della normalizzazione min-max:
- Garantisce dominio [0,1] esatto per i tre termini → il contributo massimo possibile coincide con il peso dichiarato (0.4, 0.4, 0.2).
- Allinea i pesi dichiarati al contributo effettivo nel ranking (rimuove la dominanza di Cash_Profit_Assoluto per scala assoluta).
- Coerente con la natura **Stateless** di Talos: la normalizzazione si calcola sul listino della **singola sessione**, senza dipendenza da statistiche storiche cross-sessione.
- Min-max preferito a z-score per due motivi: (a) interpretabilità diretta (i pesi 40/40/20 sono i contributi massimi); (b) range esatto [0,1] vs distribuzione gaussiana centrata su 0 (non interpretabile come "peso" in senso classico).

## How

**Edit puntuali in `PROJECT-RAW.md`:**
- Frontmatter: `qa_rounds: 3 → 4`.
- Header: nuova riga Round 4 con la decisione + nota verbatim del Leader; conteggio aggiornato a "17 aperte, 0 critiche".
- Sezione 4.1.4: marker L04b da "aperta CRITICA" a "CHIUSA Round 4".
- Sezione 6.3 (Formula VGP): incisione della forma canonica con `norm(x)`, definizione min-max sul listino di sessione, edge case `max==min`, motivazione min-max vs z-score.
- Sezione 9: L04b rimossa dalla tabella Aperte e spostata in Chiuse (in cima); contatore aggiornato.
- Sezione 10: nuovo blocco Round 4 con tabella Q&A verbatim.
- Cronologia Stati: nuova riga Round 4.

**Aggiornamenti negli altri documenti:**
- `docs/STATUS.md`: header `Ultimo aggiornamento` (commit hash da backfillare), Stato in Una Riga, Appena Completato, In Sospeso (ESP-004 chiusa → ESP-005 aperta), tabella Decisioni ratificate, Nota al Prossimo Claude, Issues Noti.
- `ROADMAP.md`: obiettivo #7 aggiornato (4 round, 0 critiche), log validazioni esteso.
- `CHANGELOG.md`: nuova versione `[0.7.3]` in cima.

**Memory ricreata:**
- `~/.claude/projects/-home-matteo-Atena/memory/MEMORY.md` (indice).
- `~/.claude/projects/-home-matteo-Atena/memory/feedback_concisione_documentale.md` (direttiva di concisione del Leader, Round 3).

## Tests

Test manuali documentati (governance — ADR-0011).

| Test | Comando / Verifica | Esito |
|---|---|---|
| Frontmatter `qa_rounds: 4` | `grep '^qa_rounds:' PROJECT-RAW.md` | atteso PASS |
| Marker L04b "CHIUSA Round 4" presente | `grep -n 'L04b — CHIUSA Round 4' PROJECT-RAW.md` | atteso PASS |
| Formula VGP normalizzata presente | `grep -n 'norm(ROI_Percentuale)' PROJECT-RAW.md` | atteso PASS |
| Definizione min-max presente | `grep -n 'min-max' PROJECT-RAW.md` | atteso PASS |
| Tabella Aperte non contiene più L04b | `grep -A2 '### Lacune Aperte' PROJECT-RAW.md \| grep 'L04b'` (no match) | atteso PASS |
| Tabella Chiuse contiene L04b in cima | `grep -A2 '### Lacune Chiuse' PROJECT-RAW.md \| grep 'L04b'` | atteso PASS |
| Conteggio aperte = 17 | conteggio righe tabella Aperte | atteso PASS |
| Q&A Log Round 4 presente | `grep -n 'Round 4 — 2026-04-29' PROJECT-RAW.md` | atteso PASS |
| Cronologia Round 4 presente | `grep -n 'Round 4: chiusa L04b' PROJECT-RAW.md` | atteso PASS |
| STATUS.md header `Ultimo aggiornamento` presente | `head -10 docs/STATUS.md \| grep 'Ultimo aggiornamento'` | atteso PASS |
| ROADMAP log Round 4 presente | `grep 'Round 4 Q&A' ROADMAP.md` | atteso PASS |
| CHANGELOG `[0.7.3]` presente | `grep '\[0.7.3\]' CHANGELOG.md` | atteso PASS |
| `MEMORY.md` esiste | `test -f ~/.claude/projects/-home-matteo-Atena/memory/MEMORY.md` | atteso PASS |
| `feedback_concisione_documentale.md` esiste | `test -f ~/.claude/projects/-home-matteo-Atena/memory/feedback_concisione_documentale.md` | atteso PASS |

**Copertura:** verifica strutturale completa di Round 4. Validità della decisione (correttezza matematica della normalizzazione min-max sul listino di sessione) sarà testata in fase di implementazione, sotto ADR di stack/algoritmo.

**Rischi residui:**
- Edge case `max(x) == min(x)` su un termine — gestito per convenzione (termine vale 0). La gestione effettiva nel codice deve replicare questa convenzione esplicitamente con un test fixture dedicato.
- Outlier estremi possono comprimere la distribuzione del termine normalizzato. Mitigazione futura possibile via z-score o winsorization, da rivalutare solo se il problema emerge in fase di esercizio reale (non bloccante per Frozen).

## Refs

- ADR: ADR-0012
- Vision: `PROJECT-RAW.md`
- Memory: `feedback_concisione_documentale.md` (ricreata)
- Commit: `0cd9f1f`
- Issue: ESP-004 (chiusa con questo CHG) → ESP-005 (sweep finale aperta)
