from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

PROFILE_PICTURE_DIRECTORY = Path("uploads") / "profile_pictures"
MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024
ALLOWED_PROFILE_PICTURE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


async def save_student_profile_picture(image: UploadFile | None) -> str:
    if image is None:
        raise ValueError("Choose a profile picture to upload.")

    try:
        extension = Path(image.filename or "").suffix.lower()
        if extension not in ALLOWED_PROFILE_PICTURE_EXTENSIONS:
            raise ValueError("Profile pictures must be JPG, PNG, or WEBP images.")

        contents = await image.read(MAX_PROFILE_PICTURE_BYTES + 1)
        if len(contents) > MAX_PROFILE_PICTURE_BYTES:
            raise ValueError("Profile pictures must be 5 MB or smaller.")
        if not _matches_image_format(contents, extension):
            raise ValueError("The uploaded file does not match its image format.")

        PROFILE_PICTURE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}{extension}"
        (PROFILE_PICTURE_DIRECTORY / filename).write_bytes(contents)
        return filename
    finally:
        await image.close()


def resolve_student_profile_picture(filename: str) -> Path:
    if Path(filename).name != filename:
        raise ValueError("Invalid profile picture path.")
    if Path(filename).suffix.lower() not in ALLOWED_PROFILE_PICTURE_EXTENSIONS:
        raise ValueError("Invalid profile picture format.")

    storage_root = PROFILE_PICTURE_DIRECTORY.resolve()
    image_path = (storage_root / filename).resolve()
    if image_path.parent != storage_root:
        raise ValueError("Profile picture is outside the configured storage directory.")
    if not image_path.is_file():
        raise FileNotFoundError("Profile picture file was not found.")
    return image_path


def delete_student_profile_picture(filename: str) -> None:
    if Path(filename).name != filename:
        raise ValueError("Invalid profile picture path.")
    if Path(filename).suffix.lower() not in ALLOWED_PROFILE_PICTURE_EXTENSIONS:
        raise ValueError("Invalid profile picture format.")
    storage_root = PROFILE_PICTURE_DIRECTORY.resolve()
    image_path = (storage_root / filename).resolve()
    if image_path.parent != storage_root:
        raise ValueError("Profile picture is outside the configured storage directory.")
    image_path.unlink(missing_ok=True)


def _matches_image_format(contents: bytes, extension: str) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return contents.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return contents.startswith(b"\x89PNG\r\n\x1a\n")
    return (
        extension == ".webp"
        and len(contents) >= 12
        and contents[:4] == b"RIFF"
        and contents[8:12] == b"WEBP"
    )
