# Download-Only Mode Design

## Context

Current CLI (`run_sync.py`) always builds both OneLap and Strava clients and always runs full sync flow (download + upload). User needs a temporary CLI mode that downloads FIT files from OneLap only and does not upload to Strava.

## Goals

- Add a CLI switch to run OneLap download only.
- In download-only mode, avoid Strava config requirements and Strava API calls.
- Print one line per FIT with timestamp and filename.
- Keep existing sync behavior unchanged when switch is not used.

## Non-Goals

- No new standalone script.
- No broad refactor of `SyncEngine`.
- No persisted download dedupe state.

## Chosen Approach

Use CLI-level branching in `run_sync.py`.

- Add `--download-only` flag.
- Keep existing `SyncEngine` upload workflow untouched.
- Implement a small download-only path in CLI layer:
  - Load settings
  - Validate only OneLap required keys
  - Build `OneLapClient`
  - List activities since date
  - Download each FIT
  - Print per-item lines and summary

Why this approach:

- Minimal risk to existing tested sync path.
- Meets requirement with smallest surface-area change.
- Keeps responsibilities clear: sync orchestration remains in `SyncEngine`; new mode is CLI execution mode.

## CLI Design

New argument:

- `--download-only` (boolean flag)

Execution rules:

- If absent: keep current behavior.
- If present:
  - Do not create or validate `StravaClient`.
  - Do not read/write `state.json` for dedupe.
  - Download all listed FIT items for requested date range.

## Data Flow (Download-Only)

1. Parse `--since` -> `since_value`.
2. Load settings via `load_settings`.
3. Validate OneLap config only (`ONELAP_USERNAME`, `ONELAP_PASSWORD`).
4. Build `OneLapClient`.
5. Fetch activities: `list_fit_activities(since, limit=50)`.
6. For each activity:
   - `download_fit(activity_id, downloads/)`
   - Print one line with activity start time + filename.
7. Print final summary.

## Output Format

Per successfully downloaded FIT, print one line:

`<start_time>  <activity_id>.fit`

On per-item failure:

`<start_time>  <activity_id>.fit  FAILED: <error>`

Final summary line:

`download-only fetched X -> downloaded Y -> failed Z`

## Error Handling

- Fatal errors (invalid args, missing required OneLap settings, list fetch failure, unexpected setup/runtime failure):
  - Print `fatal: ...`
  - Return non-zero exit code (`1`)
- Per-item download failures:
  - Count as failed
  - Continue remaining items
  - Still return `0` if run completes without fatal error

## Testing Strategy

Update/add tests with minimal scope:

- `tests/test_cli.py`
  - verify `--download-only` path can run without Strava settings
- New `tests/test_cli_download_only.py`
  - success case prints one line per FIT (time + filename) and summary
  - partial failure case prints FAILED line and correct counters
  - missing OneLap settings returns non-zero
- Run full suite to ensure existing sync mode remains unchanged.

## Risks and Mitigations

- Risk: accidental behavior change in normal sync mode.
  - Mitigation: isolate logic behind `--download-only`; keep existing path untouched; run full tests.
- Risk: noisy output format inconsistency.
  - Mitigation: assert exact per-line format in tests.

## Acceptance Criteria

- `python run_sync.py --download-only --since 2026-03-01`:
  - downloads FIT files without any Strava upload calls
  - does not require Strava env keys
  - prints one line per FIT with start time and filename
  - prints final summary line
- Existing sync command behavior and tests remain green.
