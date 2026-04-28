---
id: CHG-YYYY-MM-DD-NNN
date: YYYY-MM-DD
author: Claude (su autorizzazione Leader)
status: Draft | Committed | Verified
commit: [hash — aggiornare immediatamente post-commit]
adr_ref: ADR-NNNN
---

## What — Cosa è cambiato

[Descrizione precisa della modifica. Cosa fa il codice adesso che prima non faceva, o cosa ha smesso di fare.]

## Why — Perché

[Riferimento ADR o motivazione esplicita del Leader. Mai lasciare questo campo vuoto o generico.]

**ADR di riferimento:** [ADR-NNNN](../decisions/ADR-NNNN-slug.md)

## How — Come

**File modificati:**

| File | Tipo di modifica | Note |
|---|---|---|
| `path/to/file.ext` | aggiunto / modificato / rimosso | descrizione breve |

**Approccio tecnico:**

[Descrizione dell'approccio scelto. Perché questo approccio e non altri. Eventuali trade-off consapevoli.]

## Tests

| Test | File | Esito | Note |
|---|---|---|---|
| `nome_test` | `path/to/test_file` | PASS / FAIL | — |

**Copertura stimata:** [es. "copre il path principale, non copre il caso X per motivo Y"]

**Rischi residui:** [casi limite noti non coperti dai test]

## Impact

[Componenti, funzioni o flussi che potrebbero essere influenzati indirettamente da questa modifica. Anche solo potenzialmente.]

## Refs

- ADR: [ADR-NNNN](../decisions/ADR-NNNN-slug.md)
- Commit: `[hash]`
- Checkpoint successivo: `[tag-name se applicabile]`
- Issue / Task: [se applicabile, altrimenti —]
