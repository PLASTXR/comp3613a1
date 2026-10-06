import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app.models.student import Student
from app.repositories.student_profile import StudentProfileRepository
from app.utilities.profilepicture import (
    delete_student_profile_picture,
    resolve_student_profile_picture,
    save_student_profile_picture,
)

logger = logging.getLogger(__name__)


class StudentProfileService:
    def __init__(self, repository: StudentProfileRepository):
        self.repository = repository

    def get_student(self, student_id: int) -> Student | None:
        return self.repository.get_student(student_id)

    def organization_can_view_picture(
        self,
        organization_user_id: int,
        student_id: int,
    ) -> bool:
        return self.repository.organization_has_student_applicant(
            organization_user_id=organization_user_id,
            student_id=student_id,
        )

    async def update_profile_picture(
        self,
        student_id: int,
        image: UploadFile | None,
    ) -> None:
        student = self.repository.get_student(student_id)
        if student is None:
            raise ValueError("Student profile not found.")

        old_filename = student.profile_picture_image
        new_filename = await save_student_profile_picture(image)
        try:
            self.repository.set_profile_picture(student_id, new_filename)
        except (SQLAlchemyError, ValueError):
            try:
                delete_student_profile_picture(new_filename)
            except OSError:
                logger.exception(
                    "Failed to remove uncommitted profile picture %s",
                    new_filename,
                )
            raise

        if old_filename and old_filename != new_filename:
            try:
                delete_student_profile_picture(old_filename)
            except (OSError, ValueError) as exc:
                logger.exception(
                    "Profile picture was updated, but the previous image "
                    "could not be removed: %s",
                    exc,
                )
                raise ValueError(
                    "Profile picture was uploaded, but the previous image "
                    "could not be removed."
                ) from exc

    def get_profile_picture_path(self, student_id: int) -> Path:
        student = self.repository.get_student(student_id)
        if student is None or not student.profile_picture_image:
            raise FileNotFoundError("Profile picture was not found.")
        return resolve_student_profile_picture(student.profile_picture_image)
