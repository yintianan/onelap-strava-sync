# AGENTS.md - OneLap to Strava Sync

## Project Overview

Local CLI tool that exports FIT activity files from the OneLap fitness platform and incrementally uploads them to Strava. Uses direct HTTP adapters for both OneLap and Strava APIs (no browser automation or Selenium).

- **Package name**: `sync-onelap-strava` v0.1.0
- **Language**: Python >= 3.11
- **Build system**: setuptools via `pyproject.toml`
- **License**: MIT
- **CLI entry point**: `onelap-sync` (defined in `pyproject.toml` as `sync_onelap_strava.cli:main`)

## Quick Reference

```bash
# Setup
pip install -r requirements-dev.txt
pip install -e .
cp .env.example .env

# Run tests
python -m pytest -q

# CLI commands
onelap-sync                              # Default sync (lookback DEFAULT_LOOKBACK_DAYS)
onelap-sync --since 2026-03-01           # Sync from specific date
onelap-sync --download-only --since ...  # Download FIT only, no Strava upload
onelap-sync --onelap-auth-init           # Interactive OneLap credential setup
onelap-sync --strava-auth-init           # Interactive Strava OAuth setup
python run_sync.py                       # Repo-local fallback (wraps cli.py)
```

## Architecture

```
CLI (cli.py)
 |
 |-- --onelap-auth-init --> onelap_auth_init.py --> env_store.py --> .env
 |-- --strava-auth-init --> strava_oauth_init.py --> env_store.py --> .env
 |-- --download-only    --> OneLapClient.list_fit_activities + download_fit --> downloads/
 |-- (default sync)     --> SyncEngine.run_once
 |                           |
 |                           |-- OneLapClient.list_fit_activities(since, limit)
 |                           |-- OneLapClient.download_fit(record_key, download_dir)
 |                           |-- make_fingerprint(path, start_time, record_key)
 |                           |-- JsonStateStore.is_synced(fingerprint)
 |                           |-- StravaClient.upload_fit(path)
 |                           |-- StravaClient.poll_upload(upload_id)
 |                           |-- JsonStateStore.mark_synced(fingerprint, activity_id)
 |                           |
 |                           --> SyncSummary(fetched, deduped, success, failed)
 |
 config.py (Settings dataclass, loads from .env via python-dotenv)
 logging_setup.py (file + console logger to logs/sync.log)
```

## Source Modules

All runtime code lives under `src/sync_onelap_strava/`:

| Module | Responsibility |
|---|---|
| `__init__.py` | Exports `__version__ = "0.1.0"` |
| `cli.py` | Primary entry point. argparse with 4 flags. Orchestrates all modes. |
| `config.py` | `Settings` dataclass. `load_settings(cli_since)` loads from `.env` via `python-dotenv`. |
| `onelap_client.py` | `OneLapClient` class. Login (MD5 password hash), list activities, download FIT files. |
| `onelap_auth_init.py` | Interactive OneLap credential setup. Saves to `.env`. |
| `strava_client.py` | `StravaClient` class. Token refresh, FIT upload with retry, poll upload status. |
| `strava_oauth_init.py` | Strava OAuth helpers: build authorize URL, parse callback, exchange code for tokens. |
| `sync_engine.py` | `SyncEngine` class. Core sync loop: fetch -> dedupe -> upload -> record state. |
| `state_store.py` | `JsonStateStore` class. JSON-backed persistence (`state.json`) tracking synced activities. |
| `dedupe_service.py` | `make_fingerprint(path, start_time, record_key)` -> `"{record_key}\|{sha256}\|{start_time}"` |
| `env_store.py` | `upsert_env_values(env_path, values)` - upsert key-value pairs in `.env` files. |
| `logging_setup.py` | `configure_logging(log_file)` - file handler + console handler, INFO level. |

Auxiliary:
- `run_sync.py` (project root) - Compatibility wrapper that delegates to `cli.py`. Adds `src/` to `sys.path`.

## Key Classes and Data Flow

### OneLapClient

```python
class OneLapClient:
    def __init__(self, base_url: str, username: str, password: str)
    def login(self) -> bool                                          # POST /api/login (MD5 hashed password)
    def list_fit_activities(self, since: date, limit: int) -> list[OneLapActivity]  # GET http://u.onelap.cn/analysis/list
    def download_fit(self, record_key: str, output_dir: Path) -> Path               # Downloads FIT via cached URL
```

- Login sends MD5-hashed password to `{base_url}/api/login`.
- Activities are fetched from `http://u.onelap.cn/analysis/list` (note: different subdomain).
- On 401/HTML/login-redirect response, auto-retries with login (max 1 retry).
- Each activity is identified by `record_key` (derived from `fileKey`, `fitUrl`, or `durl` fields).
- FIT download uses temp file + SHA-256 dedup to avoid overwriting identical files.

### OneLapActivity (dataclass)

```python
@dataclass
class OneLapActivity:
    activity_id: str       # From API id field
    start_time: str        # ISO format timestamp
    fit_url: str           # URL to download FIT file
    record_key: str        # Unique identity: "fileKey:{value}" or "fitUrl:{value}" or "durl:{value}"
    source_filename: str   # Original filename from API
```

### StravaClient

```python
class StravaClient:
    def __init__(self, client_id, client_secret, refresh_token, access_token, expires_at)
    def ensure_access_token(self) -> str          # Auto-refresh if expired, persists new tokens to .env
    def upload_fit(self, path, retries=3) -> int   # POST /api/v3/uploads, returns upload_id
    def poll_upload(self, upload_id, max_attempts=10) -> dict  # GET /api/v3/uploads/{id}, polls until ready
```

- Token refresh: POST `https://www.strava.com/oauth/token` with `grant_type=refresh_token`.
- After refresh, new tokens are auto-saved to `.env` via `upsert_env_values`.
- Upload: POST `https://www.strava.com/api/v3/uploads` with `data_type=fit`.
- 5xx errors: bounded retry with backoff (default 3 retries, 1s backoff).
- 4xx errors: raise `StravaPermanentError` with detail.
- Poll: GET upload status up to 10 times with 2s interval.

### SyncEngine

```python
class SyncEngine:
    def __init__(self, onelap_client, strava_client, state_store, make_fingerprint, download_dir)
    def run_once(self, since_date=None, limit=50) -> SyncSummary
```

Core sync loop in `run_once`:
1. Fetch activity list from OneLap (default: last 3 days).
2. For each activity: download FIT -> compute fingerprint -> check state store.
3. If already synced (fingerprint exists in `state.json`), increment `deduped` counter.
4. Otherwise: upload to Strava -> poll result.
5. If Strava returns "duplicate of" error, treat as deduped and record in state.
6. If upload succeeds, mark synced with Strava `activity_id`.
7. Return `SyncSummary(fetched, deduped, success, failed)`.

Special handling:
- `OnelapRiskControlError`: aborts sync immediately, returns `aborted_reason="risk-control"`.
- Strava duplicate detection: regex extracts activity ID from error message like `"duplicate of activity /activities/12345"`.

### SyncSummary (dataclass)

```python
@dataclass
class SyncSummary:
    fetched: int                    # Total activities fetched from OneLap
    deduped: int                    # Skipped (already synced or Strava duplicate)
    success: int                    # Successfully uploaded to Strava
    failed: int                     # Upload failures
    aborted_reason: str | None      # e.g. "risk-control"
```

### JsonStateStore

```python
class JsonStateStore:
    def __init__(self, path: Path)                                    # Default: "state.json"
    def is_synced(self, fingerprint: str) -> bool
    def mark_synced(self, fingerprint: str, strava_activity_id: int) -> None
    def last_success_sync_time(self) -> str | None
```

State file format (`state.json`):
```json
{
  "synced": {
    "fileKey:abc|sha256hash|2026-03-09T08:00:00Z": {
      "strava_activity_id": 12345,
      "synced_at": "2026-03-10T10:30:00+00:00"
    }
  }
}
```

### Fingerprint

```python
def make_fingerprint(path: Path, start_time: str, record_key: str) -> str:
    # Returns: "{record_key}|{sha256_of_file}|{start_time}"
```

File-level dedup: same `activity_id` with different FIT files produces different fingerprints.

## Environment Variables

Configured in `.env` (template: `.env.example`):

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ONELAP_USERNAME` | Yes (all modes) | - | OneLap account username |
| `ONELAP_PASSWORD` | Yes (all modes) | - | OneLap account password |
| `STRAVA_CLIENT_ID` | Yes (sync mode) | - | Strava API app client ID |
| `STRAVA_CLIENT_SECRET` | Yes (sync mode) | - | Strava API app client secret |
| `STRAVA_REFRESH_TOKEN` | Yes (sync mode) | - | Strava OAuth refresh token |
| `STRAVA_ACCESS_TOKEN` | Yes (sync mode) | - | Strava OAuth access token (auto-refreshed) |
| `STRAVA_EXPIRES_AT` | No | `0` | Token expiry Unix timestamp |
| `DEFAULT_LOOKBACK_DAYS` | No | `3` | Days to look back when `--since` not specified |

In `--download-only` mode, only `ONELAP_USERNAME` and `ONELAP_PASSWORD` are required.

## CLI Modes

The CLI (`cli.py:run_cli`) has 4 mutually exclusive modes:

1. **`--onelap-auth-init`**: Interactive OneLap credential setup. Prompts for username (visible) and password (hidden via `getpass`). Saves to `.env`.

2. **`--strava-auth-init`**: One-time Strava OAuth flow. Prints authorize URL, user pastes callback URL. Exchanges code for tokens, saves to `.env`. Requires `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` in `.env` first.

3. **`--download-only`**: Downloads FIT files from OneLap to `downloads/` directory without uploading to Strava. Can combine with `--since`.

4. **Default sync**: Full sync flow - fetch from OneLap, dedupe, upload to Strava. Uses `SyncEngine.run_once()`.

`--since` (ISO date `YYYY-MM-DD`) applies to both sync and download-only modes.

## File Layout

```
onelap-strava-sync/
  src/sync_onelap_strava/    # All runtime source code
  tests/                     # 21 test files, pytest-based
  docs/
    plans/                   # Design and implementation plan documents
    reference/               # onelap-adapter-notes.md
    skills-mapping.md        # Maps skill artifacts to source modules
  .env.example               # Template for environment variables
  .env                       # Actual config (gitignored)
  state.json                 # Sync state (gitignored)
  downloads/                 # Downloaded FIT files (gitignored)
  logs/sync.log              # Log output (gitignored)
  pyproject.toml             # Package metadata, pytest config, console script
  requirements.txt           # Runtime deps: requests>=2.32, python-dotenv>=1.0
  requirements-dev.txt       # Dev deps: adds pytest>=9.0, responses>=0.26
  run_sync.py                # Compatibility wrapper
  README.md                  # English documentation
  README.zh.md               # Chinese documentation
  CONTRIBUTING.md            # Developer maintenance guide
```

## Test Suite

21 test files under `tests/`, using `pytest` + `responses` (HTTP mocking):

| Test File | Coverage |
|---|---|
| `test_cli.py` | CLI argument parsing, all 4 modes |
| `test_cli_download_only.py` | Download-only mode E2E |
| `test_cli_errors.py` | Error handling in CLI |
| `test_config.py` | Settings loading, defaults |
| `test_dedupe_service.py` | Fingerprint generation |
| `test_e2e_dry_run.py` | End-to-end dry run integration |
| `test_env_store.py` | `.env` file upsert logic |
| `test_import_smoke.py` | Import smoke test |
| `test_logging_output.py` | Logging configuration |
| `test_onelap_auth_init.py` | OneLap auth init flow |
| `test_onelap_client.py` | OneLap client: login, list, parse |
| `test_onelap_download.py` | FIT file download, dedup, naming |
| `test_onelap_http_login.py` | HTTP login specifics |
| `test_retry_and_failures.py` | Retry logic, failure scenarios |
| `test_skill_repository_structure.py` | Skill repo layout (external dependency) |
| `test_state_store.py` | JSON state persistence |
| `test_strava_oauth.py` | OAuth URL building, code exchange |
| `test_strava_upload.py` | Strava upload + poll |
| `test_sync_engine.py` | Core sync engine logic |
| `test_sync_http_integration.py` | HTTP integration tests |

Run tests: `python -m pytest -q`

Note: `test_skill_repository_structure.py` tests reference an external Windows path and will fail on non-Windows systems or when that repo is not present. This is expected.

## Error Handling Patterns

- **OneLap 401/login redirect**: Auto-retries with login (max 1 retry) in `_fetch_activities_payload`.
- **OneLap risk control**: Raises `OnelapRiskControlError`, `SyncEngine` aborts with `aborted_reason="risk-control"`.
- **Strava 5xx**: Bounded retry with configurable backoff (default: 3 retries, 1s). Raises `StravaRetriableError` if exhausted.
- **Strava 4xx**: Raises `StravaPermanentError` with response detail.
- **Strava "duplicate of"**: Treated as deduped, recorded in state to prevent repeated retries.
- **Missing settings**: `ValueError` with list of missing keys.
- **Fatal errors**: Logged to `logs/sync.log` and printed to console, exit code 1.

## API Endpoints

### OneLap
- Login: `POST https://www.onelap.cn/api/login` (form data: `account`, `password` as MD5 hex)
- Activity list: `GET http://u.onelap.cn/analysis/list` (uses session cookies)
- FIT download: `GET {fit_url}` (URL from activity list response)

### Strava
- Token refresh: `POST https://www.strava.com/oauth/token`
- Authorize: `GET https://www.strava.com/oauth/authorize` (scope: `read,activity:write`)
- Upload FIT: `POST https://www.strava.com/api/v3/uploads`
- Poll upload: `GET https://www.strava.com/api/v3/uploads/{upload_id}`

## Development Conventions

- Primary CLI implementation is in `src/sync_onelap_strava/cli.py`. `run_sync.py` is only a compatibility wrapper.
- When changing CLI flags or behavior, update: `cli.py`, `run_sync.py`, `README.md`, `README.zh.md`, `CONTRIBUTING.md`, relevant tests.
- Skill distribution is maintained in a separate repository (not part of this codebase).
- All runtime business logic stays under `src/sync_onelap_strava/`.
- Dependencies are minimal by design: only `requests` and `python-dotenv` at runtime.
- Tests use `responses` library for HTTP mocking, no real network calls.
- Gitignored artifacts: `.env`, `state.json`, `downloads/`, `logs/`, `__pycache__/`, `*.egg-info/`.

## Gitignored Runtime Artifacts

| Path | Content |
|---|---|
| `.env` | Secrets and configuration |
| `state.json` | Sync state (which activities have been synced) |
| `downloads/` | Downloaded FIT files |
| `logs/sync.log` | Runtime logs |
