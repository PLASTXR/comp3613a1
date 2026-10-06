from dataclasses import dataclass
from pathlib import Path

from app.models.hours_log import HoursLog
from app.models.student import Student, StudentVolunteerRecord
from app.models.student_application import StudentVolunteerApplication
from app.models.user import User
from app.models.volunteer_project import (
    VolunteerOrganization,
    VolunteerProject,
    VolunteerProjectStatus,
)
from app.repositories.admin_review import AdminReviewRepository
from app.utilities.evidence import resolve_hours_evidence


@dataclass(frozen=True)
class AdminReviewDashboard:
    pending_projects: list[tuple[VolunteerProject, VolunteerOrganization]]
    pending_applications: list[
        tuple[StudentVolunteerApplication, Student, User, VolunteerProject]
    ]
    pending_hours: list[tuple[HoursLog, Student, User, VolunteerProject]]
    recent_resignations: list[
        tuple[StudentVolunteerRecord, Student, User, VolunteerProject]
    ]


class AdminReviewService:
    def __init__(self, repository: AdminReviewRepository):
        self.repository = repository

    def get_dashboard_data(self) -> AdminReviewDashboard:
        return AdminReviewDashboard(
            pending_projects=self.repository.get_pending_projects(limit=4),
            pending_applications=self.repository.get_pending_applications(limit=4),
            pending_hours=self.repository.get_pending_hours(limit=4),
            recent_resignations=self.repository.get_resignations(limit=4),
        )

    def get_queue(self, queue: str) -> list:
        queue_methods = {
            "listings": self.repository.get_pending_projects,
            "applications": self.repository.get_pending_applications,
            "hours": self.repository.get_pending_hours,
            "resignations": self.repository.get_resignations,
        }
        method = queue_methods.get(queue)
        if method is None:
            raise ValueError("Unknown admin review queue.")
        return method()

    def get_project_review(
        self,
        project_id: int,
    ) -> tuple[VolunteerProject, VolunteerOrganization]:
        details = self.repository.get_project_review(project_id)
        if details is None:
            raise ValueError("Project listing not found.")
        return details

    def get_application_review(
        self,
        application_id: int,
    ) -> tuple[
        StudentVolunteerApplication,
        Student,
        User,
        VolunteerProject,
        VolunteerOrganization,
    ]:
        details = self.repository.get_application_review(application_id)
        if details is None:
            raise ValueError("Student application not found.")
        return details

    def get_hour_review(
        self,
        log_id: int,
    ) -> tuple[HoursLog, Student, User, StudentVolunteerRecord, VolunteerProject]:
        details = self.repository.get_hour_review(log_id)
        if details is None:
            raise ValueError("Hour log not found.")
        return details

    def get_hour_evidence(self, log_id: int) -> tuple[Path, str]:
        details = self.repository.get_hour_review(log_id)
        if details is None:
            raise ValueError("Hour log not found.")
        hours_log = details[0]
        if not hours_log.evidence_attachment:
            raise ValueError("This hour log has no attached evidence.")
        return (
            resolve_hours_evidence(hours_log.evidence_attachment),
            Path(hours_log.evidence_attachment).name,
        )

    def review_project(self, project_id: int, approve: bool) -> None:
        self.repository.review_project(
            project_id,
            VolunteerProjectStatus.APPROVED
            if approve
            else VolunteerProjectStatus.DENIED,
        )

    def review_application(
        self,
        application_id: int,
        admin_user_id: int | None,
        approve: bool,
    ) -> None:
        if admin_user_id is None:
            raise ValueError("Authenticated admin ID is missing.")
        self.repository.review_application(
            application_id=application_id,
            admin_user_id=admin_user_id,
            approve=approve,
        )

    def approve_hours_log(
        self,
        log_id: int,
        admin_user_id: int | None,
    ) -> None:
        if admin_user_id is None:
            raise ValueError("Authenticated admin ID is missing.")
        self.repository.review_hours_log(
            log_id=log_id,
            admin_user_id=admin_user_id,
            approve=True,
            denial_reason=None,
        )

    def deny_hours_log(
        self,
        log_id: int,
        admin_user_id: int | None,
        denial_reason: str | None,
    ) -> None:
        if admin_user_id is None:
            raise ValueError("Authenticated admin ID is missing.")
        clean_reason = denial_reason.strip() if denial_reason else ""
        if len(clean_reason) > 1000:
            raise ValueError("Denial reason must be 1000 characters or fewer.")
        self.repository.review_hours_log(
            log_id=log_id,
            admin_user_id=admin_user_id,
            approve=False,
            denial_reason=clean_reason or None,
        )
