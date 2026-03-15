# OneLap to Strava Sync

[简体中文](README.zh.md)

Local one-command Python tool to export FIT files from OneLap and incrementally upload to Strava.

This project runs with direct OneLap HTTP + Strava HTTP adapters.

## Setup

1. Create and activate virtual environment.
2. Install dependencies:
   - `pip install -r requirements-dev.txt`
3. Copy `.env.example` to `.env` and fill required values.

Required `.env` keys for runtime:

- `ONELAP_USERNAME`
- `ONELAP_PASSWORD`
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REFRESH_TOKEN`
- `STRAVA_ACCESS_TOKEN`
- `STRAVA_EXPIRES_AT`
- `DEFAULT_LOOKBACK_DAYS`

## OneLap Account Setup

- One-time OneLap credential init: `onelap-sync --onelap-auth-init`
- Interactively prompts for username and password (password input is hidden).
- Saves `ONELAP_USERNAME` and `ONELAP_PASSWORD` to `.env`.

## OAuth First Run

1. Create Strava API app and get `client_id` + `client_secret`.
2. Complete an OAuth authorization flow to obtain `refresh_token`.
3. Save credentials in `.env`.

- One-time Strava auth init: `onelap-sync --strava-auth-init`
- This flow requests `read,activity:write` and writes tokens to `.env`.
- During normal runs, refreshed Strava tokens are automatically persisted back to `.env`.

## One-command Run

- OneLap HTTP prerequisites:
  - OneLap account can sign in at `https://www.onelap.cn`
  - Strava OAuth tokens are valid in `.env`
- Recommended global command install:
  - `pipx install onelap-strava-sync`
- Default lookback run:
  - `onelap-sync`
- Run with explicit start date:
  - `onelap-sync --since 2026-03-01`

### Download-only Mode

- Download FIT files from OneLap without uploading to Strava:
  - `onelap-sync --download-only --since 2026-03-01`
- In this mode, Strava keys are not required.
- Example output:
  - `2026-03-09T08:00:00Z  a2.fit`
  - `download-only fetched X -> downloaded Y -> failed Z`

## --since Usage

- Use ISO date format: `YYYY-MM-DD`
- Example: `onelap-sync --since 2026-03-01`

Repo-local fallback command: `python run_sync.py`

## Skills Distribution

- Runtime code remains in root source directories.
- Distribution-friendly skill artifacts are under `skills/onelap-strava-sync/`.
- Mapping between skill artifacts and runtime entrypoints: `docs/skills-mapping.md`.
- Developer maintenance guide: `CONTRIBUTING.md`.

## Troubleshooting

- If import errors happen, confirm dependencies are installed in the active virtual environment.
- If Strava upload fails with 5xx, rerun; retriable errors use bounded backoff.
- If sync reports failed uploads, check `logs/sync.log`; each failure line includes Strava `status` and `error` details.
- If OneLap risk control triggers, wait and rerun later.
- If OneLap HTTP returns 401, verify username/password in `.env`.
- If OneLap HTTP returns 4xx/5xx repeatedly, verify endpoint reachability and retry later.
