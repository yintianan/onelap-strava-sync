from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_importable():
    import sync_onelap_strava

    assert sync_onelap_strava is not None


def test_pyproject_exposes_onelap_sync_console_script():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" in pyproject
    assert 'onelap-sync = "sync_onelap_strava.cli:main"' in pyproject
