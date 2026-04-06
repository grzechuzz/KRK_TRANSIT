import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """
    Compute SHA-256 for a file.
    Returns hex digest.
    """

    p = Path(path)

    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
