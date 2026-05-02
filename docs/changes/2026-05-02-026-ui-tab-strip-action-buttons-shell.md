---
id: CHG-2026-05-02-026
date: 2026-05-02
adr_ref: ADR-0016, ADR-0019, ADR-0014
commit: TBD
---

## What

UI restyle FASE 1 step 2: tab strip Carrello / Panchina / Comparazione
Fornitori / Centrale Validazione + bottoni azione header shell
(Satura Cash / WhatsApp Ordini / Chiudi Ciclo) disabled con tooltip
"In arrivo". Riorganizza il rendering post-`run_session`: cart e
panchina ora sono tab dedicati invece di sezioni sequenziali.

| File | Cosa |
|---|---|
| `src/talos/ui/dashboard.py` | + helper `_render_action_buttons_shell()` (3 bottoni `st.button(disabled=True)` con tooltip "Disponibile in CHG-029+/ADR-0023+/ADR-0024 (proposed)"). + helper `_render_tabs_section(result, panchina_df)` con `st.tabs([🛒 Carrello, 🪑 Panchina, 🤝 Comparazione Fornitori, ✅ Centrale Validazione])`. Tab 1 = `_render_cart_table`. Tab 2 = `_render_panchina_table`. Tab 3 = `st.info` shell ADR-0022 proposed (Comparazione Fornitori). Tab 4 = `st.info` shell ADR-0023 proposed (Centrale Validazione). Sostituisce le 2 chiamate sequenziali (`_render_cart_table`, render panchina) con `_render_tabs_section`. CSS minimo `.talos-shell-info` (banner stile placeholder con icona ◇). |
| `tests/unit/test_dashboard_tabs_shell.py` | nuovo: 3 test smoke import `_render_action_buttons_shell` e `_render_tabs_section`. |

## Why

Decisione Leader 2026-05-02: replicare UX ScalerBot 500K. I 4 tab
permettono di organizzare il workflow CFO in passi coerenti
(Carrello/Panchina = stato corrente; Comparazione = scelta fornitore;
Validazione = approvazione manuale ordini). I 2 tab "Coming soon" sono
prerequisiti per integrazione Arsenale risk-filters (ADR-0022/0023/0024
proposed). I 3 bottoni shell preparano UX hooks per:

- **Satura Cash**: ADR-0022 Ghigliottina (re-allocate forzando profitto
  assoluto minimo invece di ROI%).
- **WhatsApp Ordini**: ADR ancora da proporre — fuori MVP CFO.
- **Chiudi Ciclo**: ADR ancora da proporre — workflow snapshot ciclo
  + reset budget post chiusura.

Tab disabled non sono nativi in Streamlit (`st.tabs` mostra tutti
cliccabili). Workaround: contenuto del tab è `st.info` placeholder
con riferimento all'ADR proposed che lo abiliterà.

## Tests

ruff/format/mypy strict OK. **TBD PASS** (TBD unit/gov/golden + 160 integration).

- 3 test smoke (import helpers, no Streamlit invoke real).
- Test esistenti `_render_cart_table` / `_render_panchina_table` invariati (helpers preservati signature-compatible).

## Test di Conformità

- ADR-0016 (UI): `st.tabs` nativo Streamlit + helpers puri firma
  `(result, panchina_df) -> None`. Zero blast radius su pipeline/DB.
- ADR-0019 (test strategy): smoke test sufficienti per UI-only.
- ADR-0014 (quality gates): ruff strict + mypy strict + format puliti.

## Refs

- ADR-0016, ADR-0019, ADR-0014.
- Predecessori: CHG-2026-05-02-025 (cycle overview), CHG-2026-05-02-012
  (portale Demetra).
- Mockup ScalerBot 500K (Leader 2026-05-02).
- Roadmap risk-filters: ADR-0022 Ghigliottina / ADR-0023 Stress Test /
  ADR-0024 Amazon Presence (proposed) — abiliteranno tab 3-4 reali.
- Commit: TBD.
