import logging
from datetime import date

from sqlalchemy import case, func, or_, update
from sqlmodel import Session, select

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


class VolunteerProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_student_volunteer_record(
        self,
        volunteer_record_id: int,
    ) -> StudentVolunteerRecord | None:
        return self.db.get(StudentVolunteerRecord, volunteer_record_id)

    def resign_student_volunteer_record(
        self,
        volunteer_record_id: int,
        student_id: int,
        volunteer_project_id: int,
        reason: str | None,
        resignation_date: date,
    ) -> bool:
        try:
            record_update = update(StudentVolunteerRecord).where(
                StudentVolunteerRecord.volunteer_record_id == volunteer_record_id,
                StudentVolunteerRecord.student_id == student_id,
                StudentVolunteerRecord.participation_status
                == ParticipationStatus.ACTIVE,
            ).values(
                participation_status=ParticipationStatus.RESIGNED,
                resignation_reason=reason,
                resignation_date=resignation_date,
            )
            result = self.db.exec(record_update)
            if result.rowcount != 1:
                self.db.rollback()
                return False

            project_update = update(VolunteerProject).where(
                VolunteerProject.volunteer_project_id == volunteer_project_id
            ).values(
                current_volunteers=case(
                    (
                        VolunteerProject.current_volunteers > 0,
                        VolunteerProject.current_volunteers - 1,
                    ),
                    else_=0,
                )
            )
            project_result = self.db.exec(project_update)
            if project_result.rowcount != 1:
                self.db.rollback()
                return False

            self.db.commit()
            return True
        except Exception:
            logger.exception(
                "Failed to resign student %s from volunteer project %s",
                student_id,
                volunteer_project_id,
            )
            self.db.rollback()
            raise

    def count_volunteers(self) -> int:
        statement = select(
            func.count(func.distinct(StudentVolunteerRecord.student_id))
        )
        return int(self.db.exec(statement).one())

    def count_projects(self) -> int:
        statement = select(func.count()).select_from(VolunteerProject)
        return int(self.db.exec(statement).one())

    def count_organizations(self) -> int:
        statement = select(func.count()).select_from(VolunteerOrganization)
        return int(self.db.exec(statement).one())

    def get_organization_by_user_id(
        self,
        user_id: int,
    ) -> VolunteerOrganization | None:
        statement = select(VolunteerOrganization).where(
            VolunteerOrganization.user_id == user_id
        )
        return self.db.exec(statement).first()

    def get_organization_listings(
        self,
        organization_id: int,
    ) -> list[VolunteerProject]:
        statement = (
            select(VolunteerProject)
            .where(VolunteerProject.volunteer_organization_id == organization_id)
            .order_by(VolunteerProject.created_at.desc())
        )
        return list(self.db.exec(statement).all())

    def get_organization_listing(
        self,
        organization_id: int,
        volunteer_project_id: int,
    ) -> VolunteerProject | None:
        statement = select(VolunteerProject).where(
            VolunteerProject.volunteer_organization_id == organization_id,
            VolunteerProject.volunteer_project_id == volunteer_project_id,
        )
        return self.db.exec(statement).first()

    def listing_has_applications_or_volunteer_records(
        self,
        volunteer_project_id: int,
    ) -> bool:
        application_statement = (
            select(func.count())
            .select_from(StudentVolunteerApplication)
            .where(
                StudentVolunteerApplication.volunteer_project_id
                == volunteer_project_id
            )
        )
        record_statement = (
            select(func.count())
            .select_from(StudentVolunteerRecord)
            .where(
                StudentVolunteerRecord.volunteer_project_id == volunteer_project_id
            )
        )
        return (
            self.db.exec(application_statement).one() > 0
            or self.db.exec(record_statement).one() > 0
        )

    def get_projects_with_applications_or_volunteer_records(
        self,
        organization_id: int,
    ) -> set[int]:
        application_statement = (
            select(StudentVolunteerApplication.volunteer_project_id)
            .join(
                VolunteerProject,
                StudentVolunteerApplication.volunteer_project_id
                == VolunteerProject.volunteer_project_id,
            )
            .where(VolunteerProject.volunteer_organization_id == organization_id)
            .distinct()
        )
        record_statement = (
            select(StudentVolunteerRecord.volunteer_project_id)
            .join(
                VolunteerProject,
                StudentVolunteerRecord.volunteer_project_id
                == VolunteerProject.volunteer_project_id,
            )
            .where(VolunteerProject.volunteer_organization_id == organization_id)
            .distinct()
        )
        return set(self.db.exec(application_statement).all()) | set(
            self.db.exec(record_statement).all()
        )

    def delete_organization_listing(self, project: VolunteerProject) -> None:
        try:
            self.db.delete(project)
            self.db.commit()
        except Exception:
            logger.exception(
                "Failed to delete volunteer project listing %s",
                project.volunteer_project_id,
            )
            self.db.rollback()
            raise

    def count_pending_organization_applications(self, organization_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(StudentVolunteerApplication)
            .join(
                VolunteerProject,
                StudentVolunteerApplication.volunteer_project_id
                == VolunteerProject.volunteer_project_id,
            )
            .where(
                VolunteerProject.volunteer_organization_id == organization_id,
                StudentVolunteerApplication.application_status
                == StudentVolunteerApplicationStatus.PENDING,
            )
        )
        return int(self.db.exec(statement).one())

    def count_pending_applications_by_project(
        self,
        organization_id: int,
    ) -> dict[int, int]:
        statement = (
            select(
                StudentVolunteerApplication.volunteer_project_id,
                func.count(StudentVolunteerApplication.application_id),
            )
            .join(
                VolunteerProject,
                StudentVolunteerApplication.volunteer_project_id
                == VolunteerProject.volunteer_project_id,
            )
            .where(
                VolunteerProject.volunteer_organization_id == organization_id,
                StudentVolunteerApplication.application_status
                == StudentVolunteerApplicationStatus.PENDING,
            )
            .group_by(StudentVolunteerApplication.volunteer_project_id)
        )
        return {
            project_id: int(application_count)
            for project_id, application_count in self.db.exec(statement).all()
        }

    def get_organization_total_hours(self, organization_id: int) -> int:
        statement = (
            select(
                func.coalesce(
                    func.sum(
                        StudentVolunteerRecord.verified_hours
                        + StudentVolunteerRecord.unverified_hours
                    ),
                    0,
                )
            )
            .select_from(StudentVolunteerRecord)
            .join(
                VolunteerProject,
                StudentVolunteerRecord.volunteer_project_id
                == VolunteerProject.volunteer_project_id,
            )
            .where(VolunteerProject.volunteer_organization_id == organization_id)
        )
        return int(self.db.exec(statement).one())

    def get_recent_organization_applications(
        self,
        organization_id: int,
        limit: int | None = 4,
    ) -> list[tuple[StudentVolunteerApplication, Student, User, VolunteerProject]]:
        statement = (
            select(
                StudentVolunteerApplication,
                Student,
                User,
                VolunteerProject,
            )
            .join(
                VolunteerProject,
                StudentVolunteerApplication.volunteer_project_id
                == VolunteerProject.volunteer_project_id,
            )
            .join(
                Student,
                StudentVolunteerApplication.student_id == Student.student_id,
            )
            .join(User, Student.student_id == User.id)
            .where(VolunteerProject.volunteer_organization_id == organization_id)
            .order_by(StudentVolunteerApplication.creation_date.desc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.exec(statement).all())

    def create_organization_listing(
        self,
        project: VolunteerProject,
    ) -> VolunteerProject:
        try:
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            return project
        except Exception as exc:
            logger.exception("Failed to create volunteer project listing")
            self.db.rollback()
            raise

    def search_approved(
        self,
        query: str | None,
        category: str | None,
    ) -> list[tuple[VolunteerProject, VolunteerOrganization]]:
        statement = (
            select(VolunteerProject, VolunteerOrganization)
            .join(
                VolunteerOrganization,
                VolunteerProject.volunteer_organization_id
                == VolunteerOrganization.volunteer_organization_id,
            )
            .where(
                VolunteerProject.status == VolunteerProjectStatus.APPROVED,
                or_(
                    VolunteerProject.end_date.is_(None),
                    VolunteerProject.end_date >= date.today(),
                ),
            )
        )
        if category:
            statement = statement.where(
                or_(
                    VolunteerProject.primary_category.ilike(category),
                    VolunteerProject.secondary_category.ilike(category),
                )
            )
        if query:
            search_term = f"%{query}%"
            statement = statement.where(
                or_(
                    VolunteerProject.project_name.ilike(search_term),
                    VolunteerProject.short_listing_summary.ilike(search_term),
                    VolunteerProject.description.ilike(search_term),
                    VolunteerProject.location.ilike(search_term),
                    VolunteerOrganization.organization_name.ilike(search_term),
                )
            )
        statement = statement.order_by(VolunteerProject.created_at.desc())
        return list(self.db.exec(statement).all())

    def get_recent_approved(
        self,
        limit: int = 3,
    ) -> list[tuple[VolunteerProject, VolunteerOrganization]]:
        statement = (
            select(VolunteerProject, VolunteerOrganization)
            .join(
                VolunteerOrganization,
                VolunteerProject.volunteer_organization_id
                == VolunteerOrganization.volunteer_organization_id,
            )
            .where(
                VolunteerProject.status == VolunteerProjectStatus.APPROVED,
                or_(
                    VolunteerProject.end_date.is_(None),
                    VolunteerProject.end_date >= date.today(),
                ),
            )
            .order_by(VolunteerProject.created_at.desc())
            .limit(limit)
        )
        return list(self.db.exec(statement).all())

    def get_public_project_by_id(
        self,
        volunteer_project_id: int,
        include_expired: bool = False,
    ) -> tuple[VolunteerProject, VolunteerOrganization] | None:
        statement = (
            select(VolunteerProject, VolunteerOrganization)
            .join(
                VolunteerOrganization,
                VolunteerProject.volunteer_organization_id
                == VolunteerOrganization.volunteer_organization_id,
            )
            .where(
                VolunteerProject.volunteer_project_id == volunteer_project_id,
                VolunteerProject.status == VolunteerProjectStatus.APPROVED,
            )
        )
        if not include_expired:
            statement = statement.where(
                or_(
                    VolunteerProject.end_date.is_(None),
                    VolunteerProject.end_date >= date.today(),
                )
            )
        return self.db.exec(statement).first()
