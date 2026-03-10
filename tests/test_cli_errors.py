def test_run_cli_returns_nonzero_on_missing_required_settings(monkeypatch):
    monkeypatch.delenv("ONELAP_USERNAME", raising=False)
    monkeypatch.delenv("ONELAP_PASSWORD", raising=False)
    monkeypatch.delenv("STRAVA_CLIENT_ID", raising=False)
    monkeypatch.delenv("STRAVA_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("STRAVA_REFRESH_TOKEN", raising=False)

    from run_sync import run_cli

    code = run_cli([])
    assert code != 0
