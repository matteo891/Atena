---
id: CHG-2026-04-29-006
date: 2026-04-29
author: Claude (su autorizzazione Leader)
status: Committed
commit: 7dee02b
adr_ref: ADR-0012
---

## What

Round 3 Q&A su `PROJECT-RAW.md` (TALOS):
- **L04 chiusa** — formula VGP fornita: `(ROI*0.4) + (Vel*0.4) + (Cash_Profit*0.2)`.
- **L21 chiusa** — piano Keepa è out-of-scope (gestito esternamente dal Leader); Talos consuma le API ed estrae ogni dato utile.
- **L04b aperta (CRITICA)** — i tre termini hanno scale non comparabili (ROI ~0.15, Vel ~3, Cash_Profit ~80€); senza normalizzazione, i pesi dichiarati 40/40/20 non riflettono il contributo effettivo. Domanda aperta al Leader: accettare la formula così o normalizzare i tre termini su [0,1].
- **Direttiva concisione del Leader** salvata come memory feedback durevole; applicata da questo CHG in poi.

Conteggio lacune: 19 → 18 (chiuse 2, aperta 1, una nuova critica L04b).

## Why

ADR-0012 step [3]–[4]: Iterating Round 3. Risposte del Leader e nuova lacuna sollevata da Claude.

## How

Edit puntuali in `PROJECT-RAW.md`: header, sez. 4.1.4 (VGP), sez. 4.1.1 (Keepa chiuso), sez. 6.3 (formula VGP incisa + L04b inline), sez. 9 (tabella aperte/chiuse), sez. 10 (Round 3), cronologia, frontmatter `qa_rounds: 3`. Nuova memory `feedback_concisione_documentale.md` per la direttiva di stile.

## Tests

| Test | Esito |
|---|---|
| Frontmatter `qa_rounds: 3` | PASS atteso |
| Formula VGP presente in sez. 6.3 | PASS atteso |
| L04b nuova in tabella aperte | PASS atteso |
| Tabella aperte ha 18 voci | PASS atteso |
| Memory `feedback_concisione_documentale.md` esiste e linkata in MEMORY.md | PASS atteso |

## Refs

- ADR: ADR-0012
- Vision: `PROJECT-RAW.md`
- Memory: `feedback_concisione_documentale.md`
- Commit: `7dee02b`
