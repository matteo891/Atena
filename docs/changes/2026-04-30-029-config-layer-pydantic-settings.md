---
id: CHG-2026-04-30-029
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 0ae978a
adr_ref: ADR-0014, ADR-0013, ADR-0015, ADR-0018, ADR-0019
---

## What

**Inaugura `src/talos/config/`** — config layer centralizzato basato su `pydantic-settings`. Risolve L10 a livello tecnico (soglia ROI Veto R-08 configurabile via env var, persistita futura in `config_overrides`) e ancora `TALOS_DB_URL` come campo tipato anziché lookup grezzo via `os.getenv`.

Scope deliberatamente minimo: 2 campi (`db_url`, `roi_veto_threshold`), 1 validator. Le altre env var (password ruoli, `db_url_superuser`) restano lette direttamente dagli script una-tantum (CHG-021) finché non emerge un'esigenza di centralizzazione effettiva.

| File | Tipo | Cosa |
|---|---|---|
| `pyproject.toml` | modificato | dep `pydantic-settings>=2.14.0` (via `uv add`) |
| `uv.lock` | modificato | resolve `pydantic-settings` + transitive (pydantic, pydantic-core, annotated-types, python-dotenv, typing-inspection) |
| `src/talos/config/__init__.py` | nuovo | Re-export `TalosSettings`, `get_settings` |
| `src/talos/config/settings.py` | nuovo | `TalosSettings(BaseSettings)` con env_prefix `TALOS_` + 2 campi + validator soglia ROI; factory `get_settings()` con cache |
| `tests/unit/test_settings.py` | nuovo | 7 test (default values + override env var + validation [0,1] su threshold + cache + monkeypatch) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Entry `src/talos/config/settings.py` → ADR-0014, ADR-0019 |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; ~221 test PASS (214 + 7 nuovi).

## Why

Tre debiti concreti chiusi da questo CHG:

1. **L10 (tecnica)**: PROJECT-RAW.md dice *"soglia 8% configurabile dal cruscotto, persistita in DB come config"*. Senza un layer di config, il default `0.08` di `vgp/veto.py` è una **costante immutabile a runtime**. Con `TalosSettings.roi_veto_threshold`, la soglia diventa override-abile via env var `TALOS_ROI_VETO_THRESHOLD=0.10` — primo passo prima della persistenza in `config_overrides` (futura).
2. **`TALOS_DB_URL` non tipata**: `engine.py` (CHG-020) e `db_bootstrap.py` (CHG-021) leggono `os.getenv("TALOS_DB_URL")` direttamente. Funziona ma non è centralizzato; questo CHG ancora la variabile come campo `db_url: str | None`. Il refactor di `engine.py` per usare `TalosSettings` è scope futuro (non lo tocco qui per minimalità).
3. **Pattern config-layer assente**: FILE-ADR-MAP riga 87 governa `src/talos/config/` come "pydantic-settings + override layer", ma il modulo non esisteva. Inaugurarlo ora con il primo campo applicativo (soglia veto) chiude il debito strutturale.

### Decisioni di design

1. **`BaseSettings` con `env_prefix="TALOS_"`**: env var `TALOS_DB_URL`, `TALOS_ROI_VETO_THRESHOLD` automaticamente bound. Coerente con la convenzione già adottata.
2. **`db_url: str | None = None`**: opzionale per evitare che import-time fallisca in test/CI dove la DB non c'è. Errore esplicito nel call site quando serve davvero (pattern già in `engine.py`).
3. **`roi_veto_threshold: float = DEFAULT_ROI_VETO_THRESHOLD`**: il default punta alla costante R-08 verbatim di `vgp/veto.py` (0.08). **Sorgente di verità** è la costante; settings ne è override-abile.
4. **Validator `field_validator("roi_veto_threshold")`**: stesso vincolo di `is_vetoed_by_roi` — `(0, 1]`. Coerenza dei contratti tra strato config e strato applicativo.
5. **`extra="forbid"`**: kwarg Python sconosciuto al costruttore → `ValidationError`. **Limite noto:** pydantic-settings IGNORA le env var `TALOS_*` non riconosciute (non solleva errore: cerca solo le env var corrispondenti a campi noti). Quindi `extra="forbid"` non protegge da typo nelle env var (es. `TALOS_RIO_THRESHOLD`); protegge solo dal codice Python che istanzia `TalosSettings(typo_field="x")`. Decisione: accettato il limite, scritto esplicitamente in test.
6. **`get_settings()` con `lru_cache(maxsize=1)`**: factory singleton funzionale. Ogni call ritorna la stessa istanza; il primo call legge l'env. Per test che vogliono override → `get_settings.cache_clear()` + monkeypatch dell'env. Pattern Python idiomatic, alternativa a global state.
7. **Niente `.env` file di default**: l'env var arriva da ambient shell o da CI secrets (ADR-0020). Test usano monkeypatch.

## How

### `src/talos/config/settings.py`

```python
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from talos.vgp import DEFAULT_ROI_VETO_THRESHOLD


class TalosSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TALOS_",
        env_file=None,
        extra="forbid",
        case_sensitive=False,
    )

    db_url: str | None = Field(default=None, description="...")
    roi_veto_threshold: float = Field(default=DEFAULT_ROI_VETO_THRESHOLD, ...)

    @field_validator("roi_veto_threshold")
    @classmethod
    def _check_threshold(cls, v: float) -> float:
        if not 0 < v <= 1: raise ValueError(...)
        return v


@lru_cache(maxsize=1)
def get_settings() -> TalosSettings:
    return TalosSettings()
```

### Test plan

7 test in `tests/unit/test_settings.py`:

1. `test_defaults_when_no_env` → `db_url is None`, `roi_veto_threshold == 0.08`.
2. `test_db_url_from_env` → `monkeypatch.setenv("TALOS_DB_URL", "postgresql://...")` + cache_clear → `settings.db_url == "..."`.
3. `test_roi_threshold_override_from_env` → `TALOS_ROI_VETO_THRESHOLD=0.10` → `settings.roi_veto_threshold == 0.10`.
4. `test_get_settings_returns_cached_instance` → due call a `get_settings()` ritornano la stessa istanza.
5. `test_threshold_zero_rejected` → `TALOS_ROI_VETO_THRESHOLD=0` → `ValidationError`.
6. `test_threshold_negative_rejected` → `TALOS_ROI_VETO_THRESHOLD=-0.05` → `ValidationError`.
7. `test_extra_kwarg_at_construction_rejected` → `TalosSettings(typo_field="x")` → `ValidationError` (extra=forbid sul costruttore; limite: non protegge da typo env var).

### Out-of-scope

- **Refactor `engine.py` / `db_bootstrap.py`** per leggere via `TalosSettings`: scope futuro CHG. Per ora i due script restano con `os.getenv` diretto.
- **Persistenza soglia in `config_overrides`** (lookup runtime DB → settings): scope futuro, richiede integrazione DB.
- **`.env` file in repo**: scope futuro se serve per developer experience locale (oggi: env shell + CI secrets).
- **Password ruoli (`TALOS_ADMIN_PASSWORD`, ecc.)** in settings: scope futuro, basso valore ora (sono usate solo da `db_bootstrap.py` una-tantum).
- **`db_url_superuser`**: idem.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (28 source files) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~221 PASS (214 + 7) |

**Rischi residui:**

- Doppia sorgente di verità per `roi_veto_threshold`: la costante in `vgp/veto.py` resta sorgente verbatim R-08; settings la prende come default. Se in futuro il Leader cambia il default (es. 10%) → cambia la costante in `vgp/veto.py` e settings lo eredita. Se invece settings diverge dalla costante (es. via env var), **il valore runtime è quello di settings** — la costante torna a essere solo "ancora documentale R-08". Questo è il comportamento desiderato (configurabilità L10), ma va ricordato.
- `extra="forbid"` non protegge da typo env var (limite di pydantic-settings: env var non riconosciute sono ignorate, non sollevano errore). Tooling esterno può fare l'audit (es. test governance che verifichi che ogni env var `TALOS_*` documentata sia usata da almeno un campo). Scope futuro.
- `lru_cache(maxsize=1)` è module-level: in test che vogliono multiple istanze serve `cache_clear()`. Alternativa Pydantic-style sarebbe creare l'istanza al call site senza singleton; scelgo singleton per efficienza (env var lette una sola volta).
- Aggiunta `pydantic-settings` aumenta la dep tree del progetto di ~5 pacchetti (pydantic, pydantic-core, annotated-types, python-dotenv, typing-inspection). Footprint accettabile per il valore.

## Refs

- ADR: ADR-0014 (stack quality gates — pydantic-settings dichiarato in roadmap), ADR-0013 (struttura `config/`), ADR-0015 (engine.py legge env var, ora ancorate in settings), ADR-0018 (soglia R-08 origine), ADR-0019 (test pattern unit)
- Predecessore: CHG-2026-04-30-027 (Veto R-08 con `DEFAULT_ROI_VETO_THRESHOLD`, ora override-able via settings)
- Vision: PROJECT-RAW.md L10 chiusa Round 5 — soglia 8% configurabile, persistita
- Successore atteso: refactor `engine.py` per usare `TalosSettings.db_url`; lookup `config_overrides` per soglia runtime override
- Commit: `0ae978a`
