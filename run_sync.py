import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sync_onelap_strava.dedupe_service import make_fingerprint
from sync_onelap_strava.config import load_settings
from sync_onelap_strava.env_store import upsert_env_values
from sync_onelap_strava.logging_setup import configure_logging
from sync_onelap_strava.onelap_client import OneLapClient
from sync_onelap_strava.state_store import JsonStateStore
from sync_onelap_strava.strava_client import StravaClient
from sync_onelap_strava.strava_oauth_init import (
    build_authorize_url,
    ensure_required_scope,
    exchange_code_for_tokens,
    parse_callback_url,
)
from sync_onelap_strava.sync_engine import SyncEngine


def build_default_engine():
    settings = load_settings(cli_since=None)
    required_settings = {
        "ONELAP_USERNAME": settings.onelap_username,
        "ONELAP_PASSWORD": settings.onelap_password,
        "STRAVA_CLIENT_ID": settings.strava_client_id,
        "STRAVA_CLIENT_SECRET": settings.strava_client_secret,
        "STRAVA_REFRESH_TOKEN": settings.strava_refresh_token,
    }
    missing = [key for key, value in required_settings.items() if not value]
    if missing:
        raise ValueError(f"missing required settings: {', '.join(missing)}")

    onelap = OneLapClient(
        base_url="https://www.onelap.cn",
        username=settings.onelap_username or "",
        password=settings.onelap_password or "",
    )
    strava = StravaClient(
        client_id=settings.strava_client_id or "",
        client_secret=settings.strava_client_secret or "",
        refresh_token=settings.strava_refresh_token or "",
        access_token=settings.strava_access_token or "",
        expires_at=settings.strava_expires_at,
    )

    return SyncEngine(
        onelap_client=onelap,
        strava_client=strava,
        state_store=JsonStateStore("state.json"),
        make_fingerprint=make_fingerprint,
        download_dir="downloads",
    )


def _validate_onelap_settings(settings):
    required = {
        "ONELAP_USERNAME": settings.onelap_username,
        "ONELAP_PASSWORD": settings.onelap_password,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"missing required settings: {', '.join(missing)}")


def run_download_only(since_value):
    settings = load_settings(cli_since=since_value)
    _validate_onelap_settings(settings)

    onelap = OneLapClient(
        base_url="https://www.onelap.cn",
        username=settings.onelap_username or "",
        password=settings.onelap_password or "",
    )

    effective_since = since_value
    if effective_since is None:
        effective_since = date.today() - timedelta(days=settings.default_lookback_days)

    items = onelap.list_fit_activities(since=effective_since, limit=50)
    fetched = len(items)
    downloaded = 0
    failed = 0
    for item in items:
        filename = item.source_filename
        try:
            path = onelap.download_fit(item.record_key, Path("downloads"))
            print(f"{item.start_time}  {Path(path).name}")
            downloaded += 1
        except Exception as exc:
            print(f"{item.start_time}  {filename}  FAILED: {exc}")
            failed += 1

    print(
        f"download-only fetched {fetched} -> downloaded {downloaded} -> failed {failed}"
    )
    return 0


def run_strava_auth_init(client_id, client_secret, env_file):
    if not client_id or not client_secret:
        raise ValueError(
            "missing required settings: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET"
        )

    redirect_uri = "http://localhost:8765/callback"
    authorize_url = build_authorize_url(client_id=client_id, redirect_uri=redirect_uri)
    print("Open this URL in your browser and authorize:")
    print(authorize_url)
    callback_url = input("Paste the full callback URL: ").strip()

    code, scope = parse_callback_url(callback_url)
    ensure_required_scope(scope)
    payload = exchange_code_for_tokens(
        client_id=client_id,
        client_secret=client_secret,
        code=code,
    )
    upsert_env_values(
        Path(env_file),
        {
            "STRAVA_ACCESS_TOKEN": str(payload["access_token"]),
            "STRAVA_REFRESH_TOKEN": str(payload["refresh_token"]),
            "STRAVA_EXPIRES_AT": str(payload["expires_at"]),
        },
    )
    print("Strava tokens saved to .env")


def run_cli(argv=None, engine=None, log_file: Path | str = "logs/sync.log"):
    parser = argparse.ArgumentParser(description="Sync OneLap FIT files to Strava")
    parser.add_argument(
        "--since", type=str, default=None, help="ISO date like 2026-03-01"
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download FIT files from OneLap without uploading to Strava",
    )
    parser.add_argument(
        "--strava-auth-init",
        action="store_true",
        help="Run one-time Strava OAuth initialization and save tokens to .env",
    )
    args = parser.parse_args(argv)

    logger = configure_logging(log_file)
    try:
        if args.strava_auth_init:
            settings = load_settings(cli_since=None)
            run_strava_auth_init(
                settings.strava_client_id or "",
                settings.strava_client_secret or "",
                Path(".env"),
            )
            return 0

        since_value = date.fromisoformat(args.since) if args.since else None
        if args.download_only and engine is None:
            return run_download_only(since_value)
        app = engine or build_default_engine()
        summary = app.run_once(since_date=since_value)
    except Exception as exc:
        logger.error("fatal error: %s", exc)
        print(f"fatal: {exc}")
        return 1

    logger.info("summary success=%s failed=%s", summary.success, summary.failed)
    print(
        f"fetched {summary.fetched} -> deduped {summary.deduped} -> success {summary.success} -> failed {summary.failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
