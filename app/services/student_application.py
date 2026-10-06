from datetime import date

from app.models.student_application import StudentVolunteerApplication
from app.models.volunteer_project import VolunteerProjectStatus
from app.repositories.student_application import StudentApplicationRepository


class StudentApplicationService:
    def __init__(self, repository: StudentApplicationRepository):
        self.repository = repository

    def is_accepted_or_active_volunteer(
        self,
        student_id: int | None,
        volunteer_project_id: int,
    ) -> bool:
        if student_id is None:
            return False
        return self.repository.has_active_or_approved_participation(
            student_id=student_id,
            volunteer_project_id=volunteer_project_id,
        )

    def submit_application(
        self,
        student_id: int | None,
        volunteer_project_id: int,
        student_motivation: str,
    ) -> StudentVolunteerApplication:
        if student_id is None:
            raise ValueError("Student ID is required.")

        if self.repository.get_student_by_id(student_id) is None:
            raise ValueError("A student profile is required to apply.")

        if not student_motivation or not student_motivation.strip():
            raise ValueError("Student motivation is required.")

        motivation = student_motivation.strip()
        if len(motivation) > 255:
            raise ValueError("Motivation must be 255 characters or fewer.")

        project = self.repository.get_project_by_id(volunteer_project_id)
        if project is None:
            raise ValueError("Volunteer project not found.")

        if project.status != VolunteerProjectStatus.APPROVED:
            raise ValueError("Cannot apply to a project that is not approved.")

        if project.end_date is not None and project.end_date < date.today():
            raise ValueError("Cannot apply to an expired project.")

        if project.current_volunteers >= project.max_volunteers:
            raise ValueError("This project has reached its volunteer limit.")

        if self.is_accepted_or_active_volunteer(
            student_id=student_id,
            volunteer_project_id=volunteer_project_id,
        ):
            raise ValueError(
                "You are already accepted to volunteer for this project."
            )

        existing_application = self.repository.find_for_student_and_project(
            student_id=student_id,
            volunteer_project_id=volunteer_project_id,
        )
        if existing_application:
            raise ValueError("Student has already applied to this project.")

        return self.repository.create(
            StudentVolunteerApplication(
                student_id=student_id,
                volunteer_project_id=volunteer_project_id,
                student_motivation=motivation,
            )
        )
