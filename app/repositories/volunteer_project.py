from datetime import date

from sqlalchemy import or_
from sqlmodel import Session, select

from app.models.volunteer_project import VolunteerProject, VolunteerProjectStatus
from app.models.volunteer_project import VolunteerOrganization


class VolunteerProjectRepository:
    def __init__(self, db: Session):
        self.db = db

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
                or_(
                    VolunteerProject.end_date.is_(None),
                    VolunteerProject.end_date >= date.today(),
                ),
            )
        )
        return self.db.exec(statement).first()
