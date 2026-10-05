from app.models.volunteer_project import VolunteerOrganization, VolunteerProject
from app.repositories.volunteer_project import VolunteerProjectRepository


class VolunteerProjectService:
    def __init__(self, repository: VolunteerProjectRepository):
        self.repository = repository

    def search_public_projects(
        self,
        query: str | None,
        category: str | None,
    ) -> list[tuple[VolunteerProject, VolunteerOrganization]]:
        clean_query = query.strip() if query else None
        clean_category = category.strip() if category else None

        return self.repository.search_approved(
            query=clean_query or None,
            category=clean_category or None,
        )

    def get_recent_public_projects(
        self,
        limit: int = 3,
    ) -> list[tuple[VolunteerProject, VolunteerOrganization]]:
        return self.repository.get_recent_approved(limit=limit)

    def get_public_project_details(
        self,
        volunteer_project_id: int,
    ) -> tuple[VolunteerProject, VolunteerOrganization] | None:
        return self.repository.get_public_project_by_id(volunteer_project_id)
