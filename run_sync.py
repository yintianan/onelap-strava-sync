import argparse
import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sync_onelap_strava.dedupe_service import make_fingerprint
from sync_onelap_strava.config import load_settings
from sync_onelap_strava.logging_setup import configure_logging
from sync_onelap_strava.onelap_client import OneLapClient
from sync_onelap_strava.state_store import JsonStateStore
from sync_onelap_strava.strava_client import StravaClient
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


def run_cli(argv=None, engine=None, log_file: Path | str = "logs/sync.log"):
    parser = argparse.ArgumentParser(description="Sync OneLap FIT files to Strava")
    parser.add_argument(
        "--since", type=str, default=None, help="ISO date like 2026-03-01"
    )
    args = parser.parse_args(argv)

    logger = configure_logging(log_file)
    try:
        since_value = date.fromisoformat(args.since) if args.since else None
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
