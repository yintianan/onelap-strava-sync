# OneLap HTTP Direct Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `python run_sync.py` run a real OneLap -> Strava sync flow via direct OneLap HTTP APIs (not placeholder backends).

**Architecture:** Keep current layering (`run_sync.py` -> `sync_engine` -> domain adapters). Replace placeholder OneLap dependency with a real HTTP-backed `OneLapClient`, and build runtime dependencies from validated `.env` settings. Keep sync orchestration in `sync_engine`, and keep API details inside adapter clients.

**Tech Stack:** Python 3.11+, `requests`, `python-dotenv`, `pytest`, `responses`.

---

## Preconditions

- Run in a dedicated worktree.
- Follow strict TDD for every task (RED -> GREEN -> REFACTOR).
- If API behavior is unclear while implementing, inspect `SyncOnelapToXoss.py` first and only then adjust adapter parsing.

### Task 1: Upgrade Settings Loader to Real `.env` Configuration

**Files:**
- Modify: `src/sync_onelap_strava/config.py`
- Modify: `tests/test_config.py`

**Step 1: Write the failing test**

```python
def test_load_settings_reads_env_and_cli_since(monkeypatch):
    monkeypatch.setenv("ONELAP_USERNAME", "u")
    monkeypatch.setenv("ONELAP_PASSWORD", "p")
    monkeypatch.setenv("STRAVA_CLIENT_ID", "id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "r")
    monkeypatch.setenv("STRAVA_ACCESS_TOKEN", "a")
    monkeypatch.setenv("STRAVA_EXPIRES_AT", "123")
    monkeypatch.setenv("DEFAULT_LOOKBACK_DAYS", "5")

    s = load_settings(cli_since=date(2026, 3, 1))
    assert s.default_lookback_days == 5
    assert s.onelap_username == "u"
    assert s.strava_client_id == "id"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py::test_load_settings_reads_env_and_cli_since -v`
Expected: FAIL (`AttributeError`/missing fields).

**Step 3: Write minimal implementation**

- Add required fields to `Settings`:
  - `onelap_username`, `onelap_password`
  - `strava_client_id`, `strava_client_secret`, `strava_refresh_token`, `strava_access_token`, `strava_expires_at`
  - `default_lookback_days`, `cli_since`
- Call `dotenv.load_dotenv()` inside `load_settings`.
- Parse `DEFAULT_LOOKBACK_DAYS` and `STRAVA_EXPIRES_AT` as int.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/sync_onelap_strava/config.py tests/test_config.py
git commit -m "feat: load runtime settings from .env for real sync"
```

### Task 2: Add OneLap HTTP Login Adapter

**Files:**
- Modify: `src/sync_onelap_strava/onelap_client.py`
- Create: `tests/test_onelap_http_login.py`

**Step 1: Write the failing test**

```python
@responses.activate
def test_onelap_login_stores_session_cookie():
    responses.add(
        responses.POST,
        "https://www.onelap.cn/login",
        json={"code": 0},
        headers={"Set-Cookie": "sid=abc; Path=/"},
        status=200,
    )
    client = OneLapClient(base_url="https://www.onelap.cn", username="u", password="p")
    client.login()
    assert client.session.cookies.get("sid") == "abc"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_onelap_http_login.py -v`
Expected: FAIL (constructor signature/login missing).

**Step 3: Write minimal implementation**

- Refactor `OneLapClient` into HTTP-backed adapter with:
  - `requests.Session`
  - `base_url`, `username`, `password`
  - `login()` method sending POST and checking success code/status.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_onelap_http_login.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/sync_onelap_strava/onelap_client.py tests/test_onelap_http_login.py
git commit -m "feat: add direct HTTP login for onelap client"
```

### Task 3: Implement OneLap Activity Listing and Since-Date Filtering

**Files:**
- Modify: `src/sync_onelap_strava/onelap_client.py`
- Modify: `tests/test_onelap_client.py`

**Step 1: Write the failing test**

```python
@responses.activate
def test_list_fit_activities_filters_since_date():
    responses.add(
        responses.GET,
        "https://www.onelap.cn/api/activities",
        json={"data": [
            {"id": "a1", "start_time": "2026-03-06T08:00:00Z", "fit_url": "/fit/a1.fit"},
            {"id": "a2", "start_time": "2026-03-08T08:00:00Z", "fit_url": "/fit/a2.fit"},
        ]},
        status=200,
    )
    c = OneLapClient(base_url="https://www.onelap.cn", username="u", password="p")
    items = c.list_fit_activities(since=date(2026, 3, 7), limit=50)
    assert [i.activity_id for i in items] == ["a2"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_onelap_client.py::test_list_fit_activities_filters_since_date -v`
Expected: FAIL (parsing/filter mismatch).

**Step 3: Write minimal implementation**

- In `list_fit_activities`:
  - call activity list endpoint
  - normalize each entry to `OneLapActivity(activity_id, start_time, fit_url)`
  - apply `since` filter by date
  - cap by `limit`.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_onelap_client.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/sync_onelap_strava/onelap_client.py tests/test_onelap_client.py
git commit -m "feat: list and filter onelap fit activities by since date"
```

### Task 4: Implement OneLap FIT Download

**Files:**
- Modify: `src/sync_onelap_strava/onelap_client.py`
- Create: `tests/test_onelap_download.py`

**Step 1: Write the failing test**

```python
@responses.activate
def test_download_fit_writes_file(tmp_path):
    responses.add(
        responses.GET,
        "https://www.onelap.cn/fit/a2.fit",
        body=b"fit-bytes",
        status=200,
        content_type="application/octet-stream",
    )
    c = OneLapClient(base_url="https://www.onelap.cn", username="u", password="p")
    path = c.download_fit("a2", tmp_path)
    assert path.exists()
    assert path.read_bytes() == b"fit-bytes"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_onelap_download.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Implement `download_fit(activity_id, output_dir)`:
  - resolve fit download URL from cached activity metadata
  - stream response to `<output_dir>/<activity_id>.fit`
  - return `Path`.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_onelap_download.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/sync_onelap_strava/onelap_client.py tests/test_onelap_download.py
git commit -m "feat: download fit files via onelap http adapter"
```

### Task 5: Wire Real Runtime Dependencies in CLI

**Files:**
- Modify: `run_sync.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
def test_build_default_engine_uses_real_clients(monkeypatch):
    monkeypatch.setenv("ONELAP_USERNAME", "u")
    monkeypatch.setenv("ONELAP_PASSWORD", "p")
    monkeypatch.setenv("STRAVA_CLIENT_ID", "id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "r")
    monkeypatch.setenv("STRAVA_ACCESS_TOKEN", "a")
    monkeypatch.setenv("STRAVA_EXPIRES_AT", "123")
    engine = build_default_engine()
    assert engine.onelap_client.__class__.__name__ == "OneLapClient"
    assert engine.strava_client.__class__.__name__ == "StravaClient"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_build_default_engine_uses_real_clients -v`
Expected: FAIL (placeholder classes still used).

**Step 3: Write minimal implementation**

- Update `run_sync.py`:
  - call `load_settings`
  - build real `OneLapClient` and `StravaClient`
  - keep `JsonStateStore` and `make_fingerprint`
  - ensure `build_default_engine()` no longer returns placeholder backends.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add run_sync.py tests/test_cli.py
git commit -m "feat: wire cli to real onelap and strava clients"
```

### Task 6: Add CLI Fatal Error Handling and Exit Codes

**Files:**
- Modify: `run_sync.py`
- Create: `tests/test_cli_errors.py`

**Step 1: Write the failing test**

```python
def test_run_cli_returns_nonzero_on_missing_required_settings(monkeypatch):
    monkeypatch.delenv("ONELAP_USERNAME", raising=False)
    code = run_cli([])
    assert code != 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_errors.py -v`
Expected: FAIL (currently always returns 0).

**Step 3: Write minimal implementation**

- Add settings validation (required keys).
- Convert fatal setup/runtime errors to non-zero exit code.
- Keep summary print for successful runs.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_cli_errors.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add run_sync.py tests/test_cli_errors.py
git commit -m "fix: return non-zero exit codes on fatal cli errors"
```

### Task 7: Validate Sync Engine Integration with Real Adapters (Mocked HTTP)

**Files:**
- Create: `tests/test_sync_http_integration.py`

**Step 1: Write the failing test**

```python
@responses.activate
def test_run_once_real_adapters_uploads_unsynced_only(tmp_path):
    # mock onelap list + fit download + strava upload/poll
    # run engine once
    # assert summary and state transitions
    ...
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sync_http_integration.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Only add smallest glue code needed after prior tasks.
- Avoid broad refactors.

**Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_sync_http_integration.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_sync_http_integration.py src/sync_onelap_strava/onelap_client.py run_sync.py
git commit -m "test: verify real-adapter sync flow with mocked http"
```

### Task 8: Update User Docs and Environment Template

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/reference/onelap-adapter-notes.md`

**Step 1: Write the failing doc test**

```python
def test_readme_documents_real_onelap_http_usage():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "OneLap HTTP" in text
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_e2e_dry_run.py::test_user_docs_and_env_example_exist -v`
Expected: FAIL or missing required wording/keys.

**Step 3: Write minimal implementation**

- Update README with:
  - required `.env` keys
  - real run prerequisites
  - common HTTP failure troubleshooting.
- Update `.env.example` to match runtime-required keys.
- Update adapter notes to document direct HTTP mode.

**Step 4: Run tests to verify pass**

Run: `python -m pytest -v`
Expected: PASS (all tests).

**Step 5: Commit**

```bash
git add README.md .env.example docs/reference/onelap-adapter-notes.md
git commit -m "docs: document direct onelap http runtime usage"
```

## Final Verification Checklist

- Run: `python -m pytest -v`
- Run: `python run_sync.py --help`
- Run: `python run_sync.py --since 2026-03-01` (with valid `.env`)
- Confirm:
  - summary format is correct
  - non-zero exit on fatal setup error
  - `state.json` only records successful uploads.
