import time
from pathlib import Path

import requests


class StravaClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        access_token: str,
        expires_at: int,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.expires_at = expires_at

    def ensure_access_token(self) -> str:
        now = int(time.time())
        if self.access_token and self.expires_at > now:
            return self.access_token

        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        self.access_token = payload["access_token"]
        self.refresh_token = payload.get("refresh_token", self.refresh_token)
        self.expires_at = payload.get("expires_at", self.expires_at)
        return self.access_token

    def _auth_headers(self) -> dict[str, str]:
        token = self.ensure_access_token()
        return {"Authorization": f"Bearer {token}"}

    def upload_fit(
        self, path: Path, retries: int = 3, backoff_seconds: float = 1.0
    ) -> int:
        attempts = 0
        while True:
            attempts += 1
            with Path(path).open("rb") as handle:
                response = requests.post(
                    "https://www.strava.com/api/v3/uploads",
                    headers=self._auth_headers(),
                    data={"data_type": "fit"},
                    files={
                        "file": (Path(path).name, handle, "application/octet-stream")
                    },
                    timeout=30,
                )

            if response.status_code >= 500 and attempts < retries:
                time.sleep(backoff_seconds)
                continue

            response.raise_for_status()
            payload = response.json()
            return int(payload["id"])

    def poll_upload(
        self, upload_id: int, max_attempts: int = 10, poll_interval_seconds: float = 2.0
    ) -> dict:
        last_payload = {
            "status": "unknown",
            "error": "poll timeout",
            "activity_id": None,
        }
        for attempt in range(max_attempts):
            response = requests.get(
                f"https://www.strava.com/api/v3/uploads/{upload_id}",
                headers=self._auth_headers(),
                timeout=30,
            )
            if response.status_code >= 500:
                if attempt == max_attempts - 1:
                    response.raise_for_status()
                time.sleep(poll_interval_seconds)
                continue

            response.raise_for_status()
            payload = response.json()
            last_payload = payload
            if payload.get("error") is not None:
                return payload
            if payload.get("activity_id") is not None:
                return payload
            if str(payload.get("status", "")).lower() in {"ready", "complete"}:
                return payload
            if attempt < max_attempts - 1:
                time.sleep(poll_interval_seconds)

        return last_payload
