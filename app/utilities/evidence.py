from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

EVIDENCE_DIRECTORY = Path("uploads") / "hours"
MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
ALLOWED_EVIDENCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

async def save_hours_evidence(evidence: UploadFile | None) -> str | None:
    if evidence is None:
        return None

    try:
        if not (evidence.filename or "").strip():
            return None

        extension = Path(evidence.filename or "").suffix.lower()
        if extension not in ALLOWED_EVIDENCE_EXTENSIONS:
            raise ValueError("Evidence must be a JPG, PNG, or PDF file.")

        contents = await evidence.read(MAX_EVIDENCE_BYTES + 1)
        if len(contents) > MAX_EVIDENCE_BYTES:
            raise ValueError("Evidence files must be 5 MB or smaller.")

        EVIDENCE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        stored_path = EVIDENCE_DIRECTORY / f"{uuid4().hex}{extension}"
        stored_path.write_bytes(contents)
        return stored_path.as_posix()
    finally:
        await evidence.close()


def delete_hours_evidence(path: str) -> None:
    stored_path = Path(path).resolve()
    storage_root = EVIDENCE_DIRECTORY.resolve()
    if storage_root not in stored_path.parents:
        raise ValueError("The evidence path is outside the configured storage directory.")
    stored_path.unlink(missing_ok=True)


def resolve_hours_evidence(path: str) -> Path:
    stored_path = Path(path).resolve()
    storage_root = EVIDENCE_DIRECTORY.resolve()
    if storage_root not in stored_path.parents:
        raise ValueError("The evidence path is outside the configured storage directory.")
    if not stored_path.is_file():
        raise FileNotFoundError("The hour-log evidence file was not found.")
    return stored_path