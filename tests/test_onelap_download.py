import responses
from datetime import date

from sync_onelap_strava.onelap_client import OneLapClient


@responses.activate
def test_download_fit_writes_file(tmp_path):
    responses.add(
        responses.GET,
        "http://u.onelap.cn/analysis/list",
        json={
            "data": [
                {
                    "id": "a2",
                    "start_time": "2026-03-08T08:00:00Z",
                    "fit_url": "/fit/a2.fit",
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://www.onelap.cn/fit/a2.fit",
        body=b"fit-bytes",
        status=200,
        content_type="application/octet-stream",
    )
    c = OneLapClient(base_url="https://www.onelap.cn", username="u", password="p")
    item = c.list_fit_activities(since=date(2026, 3, 1), limit=50)[0]
    path = c.download_fit(item.record_key, tmp_path)
    assert path.exists()
    assert path.read_bytes() == b"fit-bytes"


@responses.activate
def test_download_fit_uses_source_filename_priority(tmp_path):
    responses.add(
        responses.GET,
        "http://u.onelap.cn/analysis/list",
        json={
            "data": [
                {
                    "id": "a2",
                    "start_time": "2026-03-08T08:00:00Z",
                    "fitUrl": "/fit/from-fiturl.fit",
                    "fileKey": "MAGENE_REAL.fit",
                    "durl": "/fit/fallback.fit",
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://www.onelap.cn/fit/from-fiturl.fit",
        body=b"fit-bytes",
        status=200,
        content_type="application/octet-stream",
    )

    c = OneLapClient(base_url="https://www.onelap.cn", username="u", password="p")
    item = c.list_fit_activities(since=date(2026, 3, 1), limit=50)[0]
    path = c.download_fit(item.record_key, tmp_path)

    assert path.name == "MAGENE_REAL.fit"
