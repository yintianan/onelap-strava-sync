import hashlib
from pathlib import Path


def make_fingerprint(path: Path, start_time: str, record_key: str) -> str:
    file_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"{record_key}|{file_hash}|{start_time}"
