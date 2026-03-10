import argparse
from datetime import date

from sync_onelap_strava.dedupe_service import make_fingerprint
from sync_onelap_strava.state_store import JsonStateStore
from sync_onelap_strava.sync_engine import SyncEngine


def build_default_engine():
    class _NotConfiguredOnelap:
        def list_fit_activities(self, since, limit):
            return []

        def download_fit(self, activity_id, output_dir):
            raise RuntimeError("OneLap backend not configured")

    class _NotConfiguredStrava:
        def upload_fit(self, path):
            raise RuntimeError("Strava client not configured")

        def poll_upload(self, upload_id):
            raise RuntimeError("Strava client not configured")

    return SyncEngine(
        onelap_client=_NotConfiguredOnelap(),
        strava_client=_NotConfiguredStrava(),
        state_store=JsonStateStore("state.json"),
        make_fingerprint=make_fingerprint,
        download_dir="downloads",
    )


def run_cli(argv=None, engine=None):
    parser = argparse.ArgumentParser(description="Sync OneLap FIT files to Strava")
    parser.add_argument(
        "--since", type=str, default=None, help="ISO date like 2026-03-01"
    )
    args = parser.parse_args(argv)

    since_value = date.fromisoformat(args.since) if args.since else None
    app = engine or build_default_engine()
    summary = app.run_once(since_date=since_value)
    print(
        f"fetched {summary.fetched} -> deduped {summary.deduped} -> success {summary.success} -> failed {summary.failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
