from sync_onelap_strava.sync_engine import SyncSummary


def test_cli_accepts_since_argument_and_prints_summary(capsys):
    class FakeEngine:
        def run_once(self, since_date=None, limit=50):
            assert str(since_date) == "2026-03-01"
            return SyncSummary(fetched=5, deduped=2, success=2, failed=1)

    from run_sync import run_cli

    exit_code = run_cli(["--since", "2026-03-01"], engine=FakeEngine())
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "fetched 5 -> deduped 2 -> success 2 -> failed 1" in out
