import logging

from sqlmodel import Session, select, col

from app.models.student import Student
from app.models.student_application import StudentVolunteerApplication
from app.models.user import User
from app.models.volunteer_project import VolunteerOrganization, VolunteerProject

logger = logging.getLogger(__name__)


class StudentProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_student(self, student_id: int) -> Student | None:
        return self.db.get(Student, student_id)

    def get_top_students_by_verified_hours(self) -> list[tuple[Student, User]]:
        statement = (
            select(Student, User)
            .select_from(Student)
            .join_from(Student, User)
            .where(col(Student.total_verified_hours) > 0)
            .order_by(
                col(Student.total_verified_hours).desc(),
                col(Student.student_id),
            )
            .limit(10)
        )
        return list(self.db.exec(statement).all())

    def organization_has_student_applicant(
        self,
        organization_user_id: int,
        student_id: int,
    ) -> bool:
        statement = (
            select(StudentVolunteerApplication.application_id)
            .select_from(StudentVolunteerApplication)
            .join_from(StudentVolunteerApplication, VolunteerProject)
            .join_from(VolunteerProject, VolunteerOrganization)
            .where(
                StudentVolunteerApplication.student_id == student_id,
                VolunteerOrganization.user_id == organization_user_id,
            )
        )
        return self.db.exec(statement).first() is not None

    def set_profile_picture(self, student_id: int, filename: str) -> Student:
        student = self.get_student(student_id)
        if student is None:
            raise ValueError("Student profile not found.")

        student.profile_picture_image = filename
        try:
            self.db.add(student)
            self.db.commit()
            self.db.refresh(student)
            return student
        except Exception:
            logger.exception(
                "Failed to update profile picture for student %s",
                student_id,
            )
            self.db.rollback()
            raise
