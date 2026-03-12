from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_skill_distribution_files_exist():
    skill_root = ROOT / "skills" / "onelap-strava-sync"
    assert skill_root.is_dir()
    assert (skill_root / "SKILL.md").is_file()
    assert (skill_root / "resources").is_dir()
    assert (skill_root / "resources" / "commands.md").is_file()


def test_skill_uses_english_slug_and_chinese_display_name():
    skill_root = ROOT / "skills" / "onelap-strava-sync"
    assert skill_root.name == "onelap-strava-sync"
    assert skill_root.name.isascii()
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    assert "中文名" in text


def test_skill_commands_cover_primary_cli_modes():
    text = (
        ROOT / "skills" / "onelap-strava-sync" / "resources" / "commands.md"
    ).read_text(encoding="utf-8")
    assert "python run_sync.py" in text
    assert "--since" in text
    assert "--download-only" in text
    assert "--strava-auth-init" in text


def test_skills_mapping_doc_links_to_root_entrypoints():
    mapping = (ROOT / "docs" / "skills-mapping.md").read_text(encoding="utf-8")
    assert "run_sync.py" in mapping
    assert "src/sync_onelap_strava" in mapping
