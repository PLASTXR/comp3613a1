from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlmodel import Session

from app.models.volunteer_project import ProjectCoverImage

MAX_COVER_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_COVER_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
URL_PREFIX = "/project-covers/"


async def save_project_cover_image(
    project_cover_image: UploadFile | None, db: Session
) -> str | None:
    """Store the image in the database so it survives redeploys."""
    if project_cover_image is None:
        return None

    try:
        extension = Path(project_cover_image.filename or "").suffix.lower()
        if extension not in ALLOWED_COVER_IMAGE_EXTENSIONS:
            raise ValueError("Project cover image must be a JPG, PNG, JPEG, or WEBP file.")

        contents = await project_cover_image.read(MAX_COVER_IMAGE_BYTES + 1)
        if len(contents) > MAX_COVER_IMAGE_BYTES:
            raise ValueError("Project cover image files must be 5 MB or smaller.")

        filename = f"{uuid4().hex}{extension}"
        db.add(
            ProjectCoverImage(
                filename=filename,
                content_type=CONTENT_TYPES[extension],
                data=contents,
            )
        )
        db.commit()
        return f"{URL_PREFIX}{filename}"
    finally:
        await project_cover_image.close()


def get_cover_image(filename: str, db: Session) -> ProjectCoverImage | None:
    return db.get(ProjectCoverImage, filename)


def delete_cover_image(path: str, db: Session) -> None:
    if not path.startswith(URL_PREFIX):
        raise ValueError("The cover image path is outside the configured storage directory.")
    stored = db.get(ProjectCoverImage, Path(path).name)
    if stored is not None:
        db.delete(stored)
        db.commit()
