from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

COVER_IMAGE_DIRECTORY = Path("uploads") / "project_covers"
MAX_COVER_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_COVER_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


async def save_project_cover_image(project_cover_image: UploadFile | None) -> str | None:
    if project_cover_image is None:
        return None

    try:
        extension = Path(project_cover_image.filename or "").suffix.lower()
        if extension not in ALLOWED_COVER_IMAGE_EXTENSIONS:
            raise ValueError("Project cover image must be a JPG, PNG, JPEG, or WEBP file.")

        contents = await project_cover_image.read(MAX_COVER_IMAGE_BYTES + 1)
        if len(contents) > MAX_COVER_IMAGE_BYTES:
            raise ValueError("Project cover image files must be 5 MB or smaller.")

        COVER_IMAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        stored_path = COVER_IMAGE_DIRECTORY / f"{uuid4().hex}{extension}"
        stored_path.write_bytes(contents)
        return f"/project-covers/{stored_path.name}"
    finally:
        await project_cover_image.close()
        
def delete_cover_image(path: str) -> None:
    storage_root = COVER_IMAGE_DIRECTORY.resolve()
    if not path.startswith("/project-covers/"):
        raise ValueError("The cover image path is outside the configured storage directory.")
    stored_path = (storage_root / Path(path).name).resolve()
    if storage_root not in stored_path.parents:
        raise ValueError("The cover image path is outside the configured storage directory.")
    stored_path.unlink(missing_ok=True)
