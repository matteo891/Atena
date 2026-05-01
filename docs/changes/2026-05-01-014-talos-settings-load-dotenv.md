---
id: CHG-2026-05-01-014
date: 2026-05-01
author: Claude (su autorizzazione Leader, modalità "macina" round 4 — sblocco gestione secrets locali post arrivo Keepa private API key)
status: Draft
commit: TBD
adr_ref: ADR-0014, ADR-0017, ADR-0019
---

## What

`TalosSettings` ora legge automaticamente un `.env` locale nel
working directory tramite pydantic-settings. Sblocca la gestione
ergonomica dei secrets (Keepa API key, password DB, ecc.) senza
richiedere `export` manuale nella shell ad ogni avvio.

Modifica architettonica localizzata in `model_config`:

- Pre: `env_file=None` (commento: "nessun .env in repo: env da
  shell/CI/secrets") — pattern paranoid del CHG-029 originale.
- Post: `env_file=".env"` + `env_file_encoding="utf-8"` — pattern
  pydantic-settings standard. `.env` resta **gitignored** (questo
  CHG aggiunge `.env`, `.env.local`, `.env.*.local` a `.gitignore`).

Le env var dirette dalla shell/CI mantengono **precedenza** su `.env`
(comportamento by-default pydantic-settings, verificato da test).

| File | Tipo | Cosa |
|---|---|---|
| `src/talos/config/settings.py` | modificato | `model_config`: `env_file=None` -> `env_file=".env"`, `+env_file_encoding="utf-8"`. Commento aggiornato (precedenza shell/CI > .env). |
| `.gitignore` | modificato | + sezione "Secrets locali": `.env`, `.env.local`, `.env.*.local`. |
| `.env.example` | nuovo | Template committed con tutte le env var supportate (placeholder `CHANGE_ME`). DB / soglie applicative / Keepa / OCR. |
| `tests/unit/test_settings.py` | modificato | Fixture `_clear_settings_cache` -> `_isolate_settings`: aggiunge `monkeypatch.chdir(tmp_path)` per impedire che il `.env` reale del repo inquini i test "default None". + 3 nuovi test: caricamento da `.env` nel cwd / precedenza shell-env > .env / no .env + no env -> None. |

Quality gate **verde**: ruff/format/mypy strict puliti, pytest **27
PASS** su `test_settings.py` (era 24, +3). Suite intera invariata.

## Why

Il Leader ha consegnato la **private API access key Keepa**: serve
caricarla in modo sicuro per il prossimo CHG-015 (`_LiveKeepaAdapter`
live), senza:

1. Inserirla in **memoria persistente** (`~/.claude/projects/.../memory/`),
   che la esporrebbe in ogni sessione futura del progetto in chiaro.
2. Richiedere `export TALOS_KEEPA_API_KEY=...` manuale ad ogni nuova
   shell del Leader (UX scadente).

Il pattern `.env` locale + gitignore + pydantic-settings autoload e'
lo standard per Python/Pydantic e copre entrambi i requisiti:

- **Locale ergonomico**: il Leader scrive `.env` una sola volta, il
  file resta sulla sua macchina, viene letto automaticamente ad ogni
  istanziazione di `TalosSettings`.
- **Sicurezza**: `.env` aggiunto a `.gitignore` -> mai committed.
  `.env.example` committed funge da self-documentation per altri
  setup (futuri sviluppatori, CI bootstrap).
- **CI-friendly**: in CI le env var sono iniettate direttamente
  (GitHub Actions secrets, env: nel workflow); pydantic-settings
  da' precedenza alle env var shell rispetto al `.env` (verificato
  da test `test_shell_env_var_takes_precedence_over_dotenv`). Senza
  `.env` in CI -> default None -> module-import non fallisce -> i
  test integration che richiedono Keepa skippano module-level
  (pattern coerente con `TALOS_DB_URL`).

### Decisioni di design

1. **`env_file=".env"` (relativo al cwd)** invece di path assoluto:
   pattern standard pydantic-settings, permette diverso `.env` per
   diverso entry point (es. dashboard launchata da `src/`).
   Working dir tipico = root del repo (dove sta il `.env`).

2. **Precedenza shell-env > .env (default pydantic-settings)**: la
   CI/Docker passa env var via shell, deve poter override il `.env`
   se presente per errore. Comportamento testato esplicitamente.

3. **`.env.example` committed con placeholder `CHANGE_ME`**: pattern
   Twelve-Factor App standard. Self-documentation senza esporre
   secrets. Tutti i campi opzionali documentati.

4. **Isolamento test via `monkeypatch.chdir(tmp_path)`**: alternativa
   considerata e scartata = passare `_env_file=None` ai costruttori
   nei singoli test. Lo chdir e' meno invasivo (1 linea nel fixture
   autouse vs 7+ punti di edit). Side-effect zero perche' i test
   non leggono file relativi al cwd.

5. **Caricamento .env inerte fino a consumer reale**: la presenza
   di `keepa_api_key` valorizzata NON triggera side-effect runtime
   in CHG-014. `_LiveKeepaAdapter.query` lancia `NotImplementedError`
   esplicito (skeleton CHG-001), invariato. Il vero consumo attivo
   avverra' in CHG-015.

### Out-of-scope

- **`_LiveKeepaAdapter` implementazione live**: scope CHG-015. La
  key oggi viene caricata ma nessun adapter la usa ancora.
- **Validazione formato key**: nessun validator regex su
  `keepa_api_key`. Keepa documentazione non specifica un pattern
  rigido. Errore al primo call API.
- **Rotation della key esposta**: la key e' stata digitata dal
  Leader nel transcript della conversazione corrente. Il transcript
  e' archiviato sul disco di Claude Code (sessione locale, non
  pubblico), ma la best practice e' rotare la key dopo l'uso
  iniziale. Decisione Leader operativa.
- **Cifratura `.env`**: scope futuro se la macchina del Leader
  fosse condivisa o se serve commit-safe encrypted secrets
  (sops/age). Pattern attuale (file plaintext gitignored su disco
  locale dello sviluppatore) e' standard industry.
- **Schema validation CI** (verifica che `.env.example` resti
  sincronizzato con i campi di `TalosSettings`): scope futuro,
  test governance candidato.

## How

### `model_config` post-edit (highlight)

```python
model_config = SettingsConfigDict(
    env_prefix="TALOS_",
    # `.env` locale (gitignored) per ergonomia sviluppo locale: pydantic-settings
    # carica le var da .env nel cwd al boot. Le env var dirette dalla shell/CI
    # hanno PRECEDENZA su .env (pattern standard pydantic-settings) — la CI
    # continua a iniettare secrets via env senza file.
    env_file=".env",
    env_file_encoding="utf-8",
    extra="forbid",
    case_sensitive=False,
)
```

### Test isolation fixture (highlight)

```python
@pytest.fixture(autouse=True)
def _isolate_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Isola ogni test da `.env` locale del repo + reset singleton cache."""
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
```

### Test plan eseguito

3 nuovi test unit:

- `test_loads_keepa_key_from_dotenv_in_cwd`: scrive `.env` in
  `tmp_path`, chdir, verifica `TalosSettings().keepa_api_key ==
  "secret_from_env_file"`.
- `test_shell_env_var_takes_precedence_over_dotenv`: scrive `.env`
  con valore X, setenv valore Y, chdir, verifica precedenza shell.
- `test_no_dotenv_no_env_var_returns_none`: cwd vuoto + delenv,
  verifica `keepa_api_key is None` (CI senza secrets).

## Tests

| Step | Comando | Esito |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | tutti formattati |
| Type | `uv run mypy src/` | 0 issues (49 source files) |
| Unit settings (mirato) | `uv run pytest tests/unit/test_settings.py -q` | **27 PASS** (era 24, +3) |
| Unit + governance + golden | `uv run pytest tests/unit tests/governance tests/golden -q` | **568 PASS** (era 565, +3) |
| Integration | `TALOS_DB_URL=... uv run pytest tests/integration -q` | **122 PASS + 0 skipped** (invariato) |
| Verifica caricamento manuale | `uv run python -c "from talos.config.settings import TalosSettings; print(len(TalosSettings().keepa_api_key))"` | `64` (key 64 char caricata correttamente) |

**Rischi residui:**
- **`.env` non committato in CI**: comportamento intenzionale.
  Senza `.env` -> default None -> consumer fail-fast espliciti. Test
  integration che richiedono Keepa skippano module-level.
- **Working directory diverso da root**: se un caller futuro
  esegue da `src/` o sotto-directory, il `.env` non e' trovato
  (`env_file=".env"` e' relativo al cwd). Mitigazione: gli script
  ufficiali lanciano dal root (uv default). Pattern coerente con
  `alembic` che cerca `alembic.ini` nel cwd.
- **Shadow di `.env` con env var stale**: se il Leader modifica
  `.env` ma una shell ha gia' `export TALOS_KEEPA_API_KEY=...` in
  memoria, vince la shell. Pattern noto (precedenza by-design).
  `unset TALOS_KEEPA_API_KEY` per il refresh dal file.

## Test di Conformità

- **Path codice applicativo:** `src/talos/config/settings.py` ✓
  (area `config/` ADR-0013 consentita).
- **ADR-0014 vincoli rispettati:** mypy strict (49 source) +
  ruff strict (zero issue) + pytest pattern monkeypatch coerente.
- **ADR-0017 vincoli rispettati:** la key Keepa e' segnalata come
  opzionale con fail-fast al call site (skeleton invariato).
- **R-01 NO SILENT DROPS:** assenza di `.env` -> default None ->
  `KeepaClient` skeleton lancia `NotImplementedError` esplicito al
  primo `query()`. Nessun fallback silente.
- **Test unit:** ✓ 3 nuovi test mirati (ADR-0019).
- **Backward compat:** API `TalosSettings` invariata; tutti i test
  esistenti (24) continuano a passare grazie al fixture cwd
  isolation. Caller esterni (UI, scripts/db_bootstrap, etc.)
  acquisiscono ergonomia senza breaking change.
- **Sicurezza:** `.env` gitignored prima della creazione del file;
  `.env.example` committed con placeholder. La key reale resta
  esclusivamente sul disco locale del Leader.
- **No nuovi simboli senza ADR Primario:** modifica solo di
  `model_config` esistente -> ADR-0014 (config layer).
- **Impact analysis pre-edit:** GitNexus risk LOW (modifica
  parametro pydantic-settings interno; nessun breaking di
  signature). `acquire_and_persist`/`run_session`/`build_session_input`
  hanno `impactedCount=0` upstream applicativo.

## Impact

- **Sblocco operativo Keepa key**: la key consegnata dal Leader e'
  ora caricata via `.env` -> `TalosSettings.keepa_api_key`. Pronto
  per CHG-015 `_LiveKeepaAdapter` live (mapping CSV indici idx 18
  buy_box / idx 3 SALES root / fee_fba dal `data` field — decisione
  Leader pendente).
- **Pattern secrets standardizzato**: tutte le future env var
  TALOS_* possono usare `.env` senza richiedere ulteriori CHG.
  `.env.example` documenta i campi disponibili.
- **`pyproject.toml` invariato** (`pydantic-settings` gia' dep).
- **Catalogo eventi canonici ADR-0021**: invariato (10/11 viventi).
- **Test suite cresce di 3 unit** (568 PASS unit/gov/golden), zero
  cambi in integration / golden / governance.
- **Test isolation fixture rinforzato**: pattern `monkeypatch.chdir`
  + `cache_clear` riusabile per future suite che testano consumer
  di `TalosSettings` (es. scripts/db_bootstrap test).

## Refs

- ADR: ADR-0014 (config layer + quality gates), ADR-0017
  (canale Keepa, key opzionale al boot), ADR-0019 (test pattern
  unit con monkeypatch + tmp_path).
- Predecessori:
  - CHG-2026-04-30-029: introduzione `TalosSettings` con
    `env_file=None` (pattern paranoid no-.env).
  - CHG-2026-05-01-001: `keepa_api_key` field aggiunto a
    `TalosSettings` (skeleton).
- Successore atteso: CHG-2026-05-01-015 `_LiveKeepaAdapter`
  live (sblocca canale 1 fetch_buy_box / fetch_bsr / fetch_fee_fba
  reali, sblocca TEST-DEBT-004).
- Decisione Leader 2026-05-01 round 4: Keepa private API key
  consegnata + autorizzazione modalità "macina" round 4.
- Memory: nessuna nuova memory (la key NON va in memoria
  persistente; pattern `.env` documentato in change doc).
- Commit: TBD (backfill post-commit).
