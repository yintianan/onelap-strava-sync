# Strava OAuth Init Automation Design

## Goal

Enable "authorize once, then run fully automatic" Strava integration in this project by adding a local OAuth initialization flow that writes tokens to `.env`, and by persisting refreshed tokens back to `.env` during normal sync runs.

## Scope

In scope:
- Add CLI init command for Strava OAuth (`--strava-auth-init`)
- Auto-open browser and receive callback on localhost
- Exchange authorization code for tokens
- Validate that granted scope includes `activity:write`
- Persist `STRAVA_ACCESS_TOKEN`, `STRAVA_REFRESH_TOKEN`, `STRAVA_EXPIRES_AT` to `.env`
- Persist refreshed tokens after refresh flow in runtime client

Out of scope:
- Full secrets-manager/keychain migration
- Background daemon or web dashboard
- Eliminating the one-time user approval click (not possible with standard OAuth)

## Chosen Approach

Chosen: **Approach 1 (one-time local callback init + `.env` persistence)**.

Rationale:
- Matches current project config model (`.env` + `load_settings()`)
- Minimal moving parts and minimal migration risk
- Solves the real pain point (manual code/token copy every time)
- Keeps runtime behavior simple: existing sync command remains the daily entrypoint

## Architecture

### 1) CLI entrypoint

- Extend `run_sync.py` with `--strava-auth-init`.
- When set, run auth init flow and exit with success/failure code.
- Keep normal sync path unchanged for users who do not use this flag.

### 2) OAuth initialization module

Add `src/sync_onelap_strava/strava_oauth_init.py`:
- Build authorize URL with:
  - `response_type=code`
  - `approval_prompt=force`
  - `scope=read,activity:write`
  - localhost redirect URI
- Start temporary localhost callback HTTP server.
- Open browser to authorize URL.
- Parse callback query (`code`, `scope`).
- Validate `activity:write` exists in returned scope.
- Exchange code with Strava token endpoint (`grant_type=authorization_code`).
- Persist tokens to `.env` using shared updater helper.

### 3) `.env` persistence helper

Add helper module (proposed `src/sync_onelap_strava/env_store.py`):
- Update specific keys in `.env` without clobbering unrelated lines.
- Preserve existing keys and comments where possible.
- Add missing keys if absent.

Primary keys to maintain:
- `STRAVA_ACCESS_TOKEN`
- `STRAVA_REFRESH_TOKEN`
- `STRAVA_EXPIRES_AT`

### 4) Runtime token refresh persistence

In `src/sync_onelap_strava/strava_client.py`:
- Keep current refresh logic.
- After refresh success in `ensure_access_token()`, persist latest token fields to `.env`.
- If persistence fails: log explicit error, continue current run with in-memory token.

## Data Flow

### Auth init flow (`--strava-auth-init`)

1. Read `STRAVA_CLIENT_ID` + `STRAVA_CLIENT_SECRET` from `.env`
2. Start localhost callback server
3. Open browser authorization page
4. User authorizes once
5. Callback receives `code` and granted `scope`
6. Validate scope includes `activity:write`
7. Exchange code for tokens
8. Write tokens to `.env`
9. Exit 0 with success message

### Normal sync flow (`run_sync.py --since ...`)

1. Load settings from `.env`
2. Use `StravaClient.ensure_access_token()`
3. If expired, refresh with `refresh_token`
4. Persist refreshed fields to `.env`
5. Continue upload/poll workflow

## Error Handling

- Callback timeout -> actionable error: rerun `--strava-auth-init`
- Callback missing `code` -> fail fast with clear message
- Scope missing `activity:write` -> fail with explicit guidance to re-authorize
- Token exchange non-200 -> include status code + response body in error
- Port in use on localhost -> fallback to alternate port and print actual redirect URL
- `.env` write failure -> log clear warning and continue current run where safe

## Testing Strategy

1. URL builder tests
- Includes `approval_prompt=force`
- Includes `scope=read,activity:write`

2. Callback parsing tests
- Happy path returns code/scope
- Missing code fails

3. Scope validation tests
- Accept when `activity:write` present
- Reject otherwise

4. Token exchange tests (mocked HTTP)
- Success maps all required fields
- Failure surfaces body/status

5. `.env` writer tests
- Updates existing keys only
- Appends missing keys
- Preserves unrelated lines

6. Refresh persistence tests
- Refresh success persists new values
- Persistence failure logs warning but returns token

7. CLI tests
- `--strava-auth-init` success exits 0
- Missing client credentials exits non-zero with clear message

## Security Notes

- `.env` persistence is explicitly chosen for operational convenience.
- `.env` must remain untracked (`git` status currently confirms this behavior).
- Do not print full tokens in logs.
- Error messages should avoid leaking client secret.

## Success Criteria

- User runs one command to initialize OAuth once.
- No manual paste of authorization code into scripts after initialization.
- Daily sync can run unattended as long as refresh token remains valid.
- Scope-related failures are explicit and diagnosable from logs/output.
