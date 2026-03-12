from sync_onelap_strava.dedupe_service import make_fingerprint


def test_fingerprint_uses_record_key_hash_and_start_time(tmp_path):
    fit_file = tmp_path / "a.fit"
    fit_file.write_bytes(b"fit-content")
    fp = make_fingerprint(
        path=fit_file,
        start_time="2026-03-10T08:00:00Z",
        record_key="MAGENE_A.fit",
    )
    parts = fp.split("|")
    assert parts[0] == "MAGENE_A.fit"
    assert len(parts[1]) == 64
    assert parts[2] == "2026-03-10T08:00:00Z"
