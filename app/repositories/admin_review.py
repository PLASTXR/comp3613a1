import logging
from datetime import date, datetime, timezone

from sqlalchemy import literal_column, text
from sqlmodel import Session, select

from app.models.campus_admin import CampusVolunteerismCentreAdmin
from app.models.hours_log import HoursLog, HoursLogStatus
from app.models.student import (
    ParticipationStatus,
    Student,
    StudentVolunteerRecord,
)
from app.models.student_application import (
    StudentVolunteerApplication,
    StudentVolunteerApplicationStatus,
)
from app.models.user import User
from app.models.volunteer_project import (
    VolunteerOrganization,
    VolunteerProject,
    VolunteerProjectStatus,
)

logger = logging.getLogger(__name__)


class AdminReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_admin_profile(
        self,
        admin_user_id: int,
    ) -> CampusVolunteerismCentreAdmin | None:
        return self.db.get(CampusVolunteerismCentreAdmin, admin_user_id)

    def get_pending_projects(
        self,
        limit: int | None = None,
    ) -> list[tuple[VolunteerProject, VolunteerOrganization]]:
        statement = (
            select(VolunteerProject, VolunteerOrganization)
            .select_from(VolunteerProject)
            .join_from(VolunteerProject, VolunteerOrganization)
            .where(VolunteerProject.status == VolunteerProjectStatus.PENDING)
            .order_by(text("volunteer_project.created_at"))
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.exec(statement).all())

    def get_pending_applications(
        self,
        limit: int | None = None,
    ) -> list[tuple[StudentVolunteerApplication, Student, User, VolunteerProject]]:
        statement = (
            select(StudentVolunteerApplication, Student, User, VolunteerProject)
            .select_from(StudentVolunteerApplication)
            .join_from(StudentVolunteerApplication, Student)
            .join_from(Student, User)
            .join_from(StudentVolunteerApplication, VolunteerProject)
            .where(
                StudentVolunteerApplication.application_status
                == StudentVolunteerApplicationStatus.PENDING
            )
            .order_by(text("student_volunteer_application.creation_date"))
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.exec(statement).all())

    def get_pending_hours(
        self,
        limit: int | None = None,
    ) -> list[tuple[HoursLog, Student, User, VolunteerProject]]:
        statement = (
            select(HoursLog, Student, User, VolunteerProject)
            .select_from(HoursLog)
            .join_from(HoursLog, Student)
            .join_from(Student, User)
            .join_from(
                HoursLog,
                StudentVolunteerRecord,
                literal_column("hours_log.volunteer_record_id")
                == literal_column(
                    "student_volunteer_record.volunteer_record_id"
                ),
            )
            .join_from(StudentVolunteerRecord, VolunteerProject)
            .where(HoursLog.status == HoursLogStatus.PENDING)
            .order_by(text("hours_log.log_date"))
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.exec(statement).all())

    def get_resignations(
        self,
        limit: int | None = None,
    ) -> list[tuple[StudentVolunteerRecord, Student, User, VolunteerProject]]:
        statement = (
            select(StudentVolunteerRecord, Student, User, VolunteerProject)
            .select_from(StudentVolunteerRecord)
            .join_from(StudentVolunteerRecord, Student)
            .join_from(Student, User)
            .join_from(StudentVolunteerRecord, VolunteerProject)
            .where(
                StudentVolunteerRecord.participation_status
                == ParticipationStatus.RESIGNED
            )
            .order_by(text("student_volunteer_record.resignation_date DESC"))
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.exec(statement).all())

    def get_project_review(
        self,
        project_id: int,
    ) -> tuple[VolunteerProject, VolunteerOrganization] | None:
        statement = (
            select(VolunteerProject, VolunteerOrganization)
            .select_from(VolunteerProject)
            .join_from(VolunteerProject, VolunteerOrganization)
            .where(VolunteerProject.volunteer_project_id == project_id)
        )
        return self.db.exec(statement).first()

    def get_application_review(
        self,
        application_id: int,
    ) -> tuple[
        StudentVolunteerApplication,
        Student,
        User,
        VolunteerProject,
        VolunteerOrganization,
    ] | None:
        statement = (
            select(
                StudentVolunteerApplication,
                Student,
                User,
                VolunteerProject,
            )
            .select_from(StudentVolunteerApplication)
            .join_from(StudentVolunteerApplication, Student)
            .join_from(Student, User)
            .join_from(StudentVolunteerApplication, VolunteerProject)
            .where(
                StudentVolunteerApplication.application_id == application_id
            )
        )
        details = self.db.exec(statement).first()
        if details is None:
            return None
        application, student, user, project = details
        organization = self.db.get(
            VolunteerOrganization,
            project.volunteer_organization_id,
        )
        if organization is None:
            return None
        return application, student, user, project, organization

    def get_hour_review(
        self,
        log_id: int,
    ) -> tuple[HoursLog, Student, User, StudentVolunteerRecord, VolunteerProject] | None:
        statement = (
            select(HoursLog, Student, User, StudentVolunteerRecord)
            .select_from(HoursLog)
            .join_from(HoursLog, Student)
            .join_from(Student, User)
            .join_from(
                HoursLog,
                StudentVolunteerRecord,
                literal_column("hours_log.volunteer_record_id")
                == literal_column(
                    "student_volunteer_record.volunteer_record_id"
                ),
            )
            .where(HoursLog.log_id == log_id)
        )
        details = self.db.exec(statement).first()
        if details is None:
            return None
        hours_log, student, user, record = details
        project = self.db.get(VolunteerProject, record.volunteer_project_id)
        if project is None:
            return None
        return hours_log, student, user, record, project

    def review_project(
        self,
        project_id: int,
        status: VolunteerProjectStatus,
    ) -> None:
        try:
            project = self.db.exec(
                select(VolunteerProject)
                .where(VolunteerProject.volunteer_project_id == project_id)
                .with_for_update()
            ).one_or_none()
            if project is None:
                raise ValueError("Project listing not found.")
            if project.status != VolunteerProjectStatus.PENDING:
                raise ValueError("This project listing has already been reviewed.")
            project.status = status
            self.db.add(project)
            self.db.commit()
        except ValueError:
            self.db.rollback()
            raise
        except Exception:
            logger.exception("Failed to review volunteer project %s", project_id)
            self.db.rollback()
            raise

    def review_application(
        self,
        application_id: int,
        admin_user_id: int,
        approve: bool,
    ) -> None:
        try:
            admin = self.get_admin_profile(admin_user_id)
            if admin is None or admin.admin_id is None:
                raise ValueError("Admin profile not found. Run the seed command.")

            application = self.db.exec(
                select(StudentVolunteerApplication)
                .where(
                    StudentVolunteerApplication.application_id == application_id
                )
                .with_for_update()
            ).one_or_none()
            if application is None:
                raise ValueError("Student application not found.")
            if (
                application.application_status
                != StudentVolunteerApplicationStatus.PENDING
            ):
                raise ValueError("This application has already been reviewed.")

            project = self.db.exec(
                select(VolunteerProject)
                .where(
                    VolunteerProject.volunteer_project_id
                    == application.volunteer_project_id
                )
                .with_for_update()
            ).one_or_none()
            if project is None:
                raise ValueError("Project listing not found.")

            if approve:
                if project.status != VolunteerProjectStatus.APPROVED:
                    raise ValueError(
                        "Only approved project listings can accept volunteers."
                    )
                if project.current_volunteers >= project.max_volunteers:
                    raise ValueError("This project has reached its volunteer limit.")
                existing_record = self.db.exec(
                    select(StudentVolunteerRecord).where(
                        StudentVolunteerRecord.student_id == application.student_id,
                        StudentVolunteerRecord.volunteer_project_id
                        == application.volunteer_project_id,
                        StudentVolunteerRecord.participation_status
                        == ParticipationStatus.ACTIVE,
                    )
                ).first()
                if existing_record is not None:
                    raise ValueError(
                        "This student already has an active record for the project."
                    )
                organization = self.db.get(
                    VolunteerOrganization,
                    project.volunteer_organization_id,
                )
                if organization is None:
                    raise ValueError("Project organization profile not found.")
                if project.volunteer_project_id is None:
                    raise ValueError("Project listing has no assigned ID.")
                self.db.add(
                    StudentVolunteerRecord(
                        student_id=application.student_id,
                        volunteer_project_id=project.volunteer_project_id,
                        organization_name=organization.organization_name,
                        start_date=project.start_date,
                        end_date=project.end_date,
                        participation_status=ParticipationStatus.ACTIVE,
                    )
                )
                project.current_volunteers += 1
                application.application_status = (
                    StudentVolunteerApplicationStatus.APPROVED
                )
            else:
                application.application_status = (
                    StudentVolunteerApplicationStatus.DENIED
                )

            application.admin_reviewer_id = admin.admin_id
            application.review_date = datetime.now(timezone.utc)
            self.db.add(project)
            self.db.add(application)
            self.db.commit()
        except ValueError:
            self.db.rollback()
            raise
        except Exception:
            logger.exception(
                "Failed to review student application %s",
                application_id,
            )
            self.db.rollback()
            raise

    def review_hours_log(
        self,
        log_id: int,
        admin_user_id: int,
        approve: bool,
        denial_reason: str | None,
    ) -> None:
        try:
            admin = self.get_admin_profile(admin_user_id)
            if admin is None or admin.admin_id is None:
                raise ValueError("Admin profile not found. Run the seed command.")

            hours_log = self.db.exec(
                select(HoursLog)
                .where(HoursLog.log_id == log_id)
                .with_for_update()
            ).one_or_none()
            if hours_log is None:
                raise ValueError("Hour log not found.")
            if hours_log.status != HoursLogStatus.PENDING:
                raise ValueError("This hour log has already been reviewed.")

            record = self.db.get(
                StudentVolunteerRecord,
                hours_log.volunteer_record_id,
            )
            student = self.db.get(Student, hours_log.student_id)
            if record is None or student is None:
                raise ValueError("Hour log is missing its student participation.")
            if record.student_id != student.student_id:
                raise ValueError("Hour log does not match its student participation.")

            hours_log.status = (
                HoursLogStatus.APPROVED if approve else HoursLogStatus.DENIED
            )
            hours_log.admin_verified_by_id = admin.admin_id
            hours_log.verified_date = date.today() if approve else None
            hours_log.denial_reason = None if approve else denial_reason

            record.unverified_hours = max(0, record.unverified_hours - hours_log.hours)
            student.total_unverified_hours = max(
                0,
                student.total_unverified_hours - hours_log.hours,
            )
            if approve:
                record.verified_hours += hours_log.hours
                student.total_verified_hours += hours_log.hours
                student.credits += hours_log.hours * 25

            self.db.add(hours_log)
            self.db.add(record)
            self.db.add(student)
            self.db.commit()
        except ValueError:
            self.db.rollback()
            raise
        except Exception:
            logger.exception("Failed to review volunteer hour log %s", log_id)
            self.db.rollback()
            raise
