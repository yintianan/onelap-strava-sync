from sync_onelap_strava.dedupe_service import make_fingerprint


def test_fingerprint_uses_hash_and_start_time(tmp_path):
    fit_file = tmp_path / "a.fit"
    fit_file.write_bytes(b"fit-content")
    fp = make_fingerprint(fit_file, "2026-03-10T08:00:00Z")
    assert "|2026-03-10T08:00:00Z" in fp
    assert len(fp.split("|")[0]) == 64
