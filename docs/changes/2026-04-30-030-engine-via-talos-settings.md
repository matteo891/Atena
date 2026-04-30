---
id: CHG-2026-04-30-030
date: 2026-04-30
author: Claude (su autorizzazione Leader)
status: Committed
commit: 464e4f3
adr_ref: ADR-0015, ADR-0014, ADR-0013, ADR-0019
---

## What

Refactor `src/talos/persistence/engine.py` per leggere la URL del DB tramite il config layer `TalosSettings` (CHG-029) anziché `os.getenv("TALOS_DB_URL")` direttamente. Primo consumatore reale di `get_settings()` da codice applicativo: chiude esplicitamente il debito inscritto in CHG-029 ("Out-of-scope: Refactor `engine.py` / `db_bootstrap.py` per leggere via `TalosSettings` — scope futuro CHG").

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/persistence/engine.py` | modificato | `os.getenv("TALOS_DB_URL")` → `get_settings().db_url`; rimosso `import os`; aggiornato docstring (rimosso "CHG futuro") |
| `tests/unit/test_persistence_engine.py` | modificato | Aggiunto autouse fixture `_clear_settings_cache` (pattern già in `test_settings.py`); 4 test invariati nella semantica (env var fluiscono via TalosSettings) |
| `docs/decisions/FILE-ADR-MAP.md` | modificato | Riga 87: aggiornata nota da "env var `TALOS_DB_URL`" a "letta via `TalosSettings.db_url`"; aggiunto riferimento CHG-030 |

Quality gate **atteso** verde: ruff/format/mypy strict puliti; ~221 test PASS (invariato — i 4 test esistenti continuano a passare; nessun test nuovo).

## Why

CHG-029 ha inaugurato il config layer ma lo ha lasciato senza consumatori applicativi. `engine.py` continuava a leggere `os.getenv("TALOS_DB_URL")` direttamente, mantenendo due percorsi paralleli: settings (con validazione, cache, error explicit) e env-var-grezza. Il refactor:

1. **Chiude il debito esplicito di CHG-029** (riferito 2 volte nel suo "Out-of-scope" + "Successore atteso").
2. **Materializza il contratto di FILE-ADR-MAP riga 87**: la nota "(env var `TALOS_DB_URL`)" diventa stale al primo override via settings; la riallineo.
3. **Riduce la superficie di accesso a env var grezze**: meno punti dove `os.getenv` può divergere (typo, default differenti, semantica differente).
4. **Sblocca il prossimo step (c) — lookup `config_overrides` per soglia ROI runtime**: avere `engine` che gira via settings dà fiducia nel pattern prima di esporlo a soglia veto.

### Decisioni di design

1. **Mantenuta firma pubblica `create_app_engine(url=None) -> Engine`**: nessun caller reale (impact GitNexus = LOW, 0 d=1). Ma il principio "url esplicito ha priorità su default settings" è importante per testabilità (test possono bypassare settings con un argomento esplicito senza dover monkeypatchare l'env).
2. **`get_settings().db_url` invece di costruire `TalosSettings()` ad-hoc**: passa per il singleton `lru_cache`, coerente con il pattern di `test_settings.py`. Conseguenza: i test devono `cache_clear()` come fanno i test settings — autouse fixture identica.
3. **NON viene toccato `scripts/db_bootstrap.py`**: è uno script una-tantum che usa `os.getenv` per più var (admin password, superuser url) — refactor a base più ampia, scope separato.
4. **NON viene toccato `migrations/env.py`**: è un entrypoint Alembic specializzato (non importa `talos.*` per evitare dipendenze applicative al momento della migration). Resta su env var grezza.
5. **Errore identico al pre-refactor**: `RuntimeError` con stesso messaggio. Behaviour pubblico invariato: chi chiama `create_app_engine()` senza url né `TALOS_DB_URL` continua a vedere la stessa eccezione, stessa stringa.
6. **`from talos.config import get_settings`** invece di `from talos.config.settings import get_settings`: l'`__init__.py` ri-esporta entrambi i simboli; la forma corta è canonical.

## How

### `src/talos/persistence/engine.py` (after)

```python
from __future__ import annotations
from typing import TYPE_CHECKING, Any
from sqlalchemy import create_engine
from talos.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy import Engine


def create_app_engine(url: str | None = None) -> Engine:
    """..."""
    resolved = url or get_settings().db_url
    if not resolved:
        msg = ("TALOS_DB_URL non settato e nessun url esplicito ...")
        raise RuntimeError(msg)
    kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
    if not resolved.startswith("sqlite"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    return create_engine(resolved, **kwargs)
```

### `tests/unit/test_persistence_engine.py` (after)

Aggiunto autouse fixture identico a `test_settings.py`:

```python
@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
```

I 4 test esistenti restano invariati nella semantica:
- `test_explicit_url_takes_priority_over_env`: il monkeypatch fluisce comunque attraverso `TalosSettings.db_url`; l'argomento esplicito ha priorità a livello di `create_app_engine`.
- `test_env_fallback_when_no_explicit_url`: `monkeypatch.setenv` → `TalosSettings()` legge → `get_settings().db_url` valore atteso.
- `test_raises_when_no_url_anywhere`: `monkeypatch.delenv` → `db_url is None` → `RuntimeError` come prima.
- `test_engine_can_connect_to_sqlite_memory`: smoke test puro, non tocca env.

### Out-of-scope

- **Refactor `scripts/db_bootstrap.py`**: 4+ env var distinte (admin/app/audit password + superuser url); CHG separato.
- **Refactor `migrations/env.py`**: scope diverso (Alembic isolato); valutare quando emergerà esigenza concreta.
- **Lookup `config_overrides` runtime per soglia ROI**: scope futuro (prossimo step naturale).
- **Cache invalidation strategy oltre `cache_clear()`**: il singleton resta module-level; basta per i casi attuali.

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | atteso ✅ |
| Format | `uv run ruff format --check src/ tests/` | atteso ✅ |
| Type | `uv run mypy src/` | atteso ✅ (28 source files invariati) |
| Unit + governance | `uv run pytest tests/unit tests/governance -q` | atteso ✅ ~221 PASS (invariato — 4 test esistenti continuano a passare) |

**Rischi residui:**

- I test fanno affidamento su `get_settings.cache_clear()` autouse. Se in futuro un test dimentica il fixture o aggiunge un caller che non lo usa, il singleton può "leakare" valori tra test (la prima istanza vince). Mitigazione: pattern già documentato in `test_settings.py`; estendibile a una fixture di scope `session` se cresce il numero di test che toccano settings.
- `migrations/env.py` e `scripts/db_bootstrap.py` ora **divergono** dal pattern di `engine.py` (env-var-diretta vs settings). Coscientemente accettato: scope CHG-030 era chirurgico. Da consolidare in CHG futuri se cresce la pressione di centralizzazione.
- Ciclo di import: `talos.persistence.engine` ora importa `talos.config`. `talos.config.settings` importa `talos.vgp` (per `DEFAULT_ROI_VETO_THRESHOLD`). Nessun ciclo: `vgp` non importa `persistence`. Verificato.

## Refs

- ADR: ADR-0015 (persistence stack — engine factory), ADR-0014 (mypy/ruff strict), ADR-0013 (struttura `config/`/`persistence/`), ADR-0019 (test pattern unit)
- Predecessore: CHG-2026-04-30-029 (config layer pydantic-settings) — questo CHG è il "Successore atteso" inscritto
- Vision: PROJECT-RAW.md L10 (configurabilità) — questo CHG aggiunge il primo nodo applicativo che fluisce via settings
- Successore atteso: refactor `scripts/db_bootstrap.py` per centralizzazione completa; lookup `config_overrides` runtime per soglia ROI
- Commit: `464e4f3`
