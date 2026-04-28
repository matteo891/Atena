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

**All'inizio di ogni sessione**, prima di proporre o applicare qualsiasi modifica, Claude è OBBLIGATO a eseguire il Self-Briefing secondo questa sequenza:

1. **Scansione del Knowledge Graph** — Utilizzare il server MCP di GitNexus per interrogare il grafo della conoscenza del progetto e recuperare lo stato architetturale corrente.
2. **Lettura degli ADR attivi** — Leggere tutti i documenti presenti in `docs/decisions/` per verificare le decisioni ratificate e il loro stato.
3. **Verifica ROADMAP** — Leggere `ROADMAP.md` per allinearsi agli obiettivi correnti e alle implementazioni in corso.
4. **Verifica CHANGELOG** — Leggere `CHANGELOG.md` per comprendere la storia recente del progetto.

Solo al termine del Self-Briefing Claude può rispondere a richieste operative. Qualsiasi proposta fatta senza Self-Briefing è da considerarsi non valida.

### Ciclo di Modifica

```
Richiesta → Self-Briefing → Verifica ADR → Proposta → Validazione Leader → Implementazione → Aggiornamento CHANGELOG/ROADMAP
```
