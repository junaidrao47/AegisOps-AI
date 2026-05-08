from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

_filename_sanitize = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_filename(name: str) -> str:
    name = name.strip().replace("\\", "/")
    name = name.split("/")[-1]
    name = _filename_sanitize.sub("_", name)
    return name or "file"


def incident_dir(user_id: int, incident_id: int) -> Path:
    base = Path(settings.incident_storage_path)
    return base / str(user_id) / str(incident_id)


def save_upload(*, user_id: int, incident_id: int, kind: str, upload: UploadFile) -> tuple[str, int]:
    if upload.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_filename")

    target_dir = incident_dir(user_id, incident_id) / kind
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(upload.filename)
    path = target_dir / safe_name

    max_bytes = settings.max_upload_bytes
    size = 0

    with path.open("wb") as f:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                try:
                    f.close()
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file_too_large")
            f.write(chunk)

    # Ensure file handle closed by UploadFile
    try:
        upload.file.close()
    except Exception:
        pass

    return str(path), size


def read_text_file(storage_path: str, max_chars: int = 500_000) -> str:
    # Only for heuristics; avoid loading huge files.
    p = Path(storage_path)
    if not p.exists():
        raise FileNotFoundError(storage_path)
    with p.open("rb") as f:
        data = f.read(max_chars)
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode(errors="replace")
