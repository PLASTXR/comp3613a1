from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.models.student import ParticipationStatus, Student
from app.models.student_application import StudentVolunteerApplication
from app.models.user import User
from app.models.volunteer_project import (
    VolunteerOrganization,
    VolunteerProject,
    VolunteerProjectStatus,
)
from app.repositories.volunteer_project import VolunteerProjectRepository


class EndDateBeforeStartError(ValueError):
    pass


class OrganizationListingNotFoundError(ValueError):
    pass


class ListingHasAssociatedRecordsError(ValueError):
    pass


@dataclass(frozen=True)
class VolunteerOrganizationDashboard:
    organization: VolunteerOrganization
    listings: list[VolunteerProject]
    recent_listings: list[VolunteerProject]
    pending_applicant_counts: dict[int, int]
    protected_listing_ids: set[int]
    new_applicant_count: int
    total_hours: int
    recent_applicants: list[
        tuple[StudentVolunteerApplication, Student, User, VolunteerProject]
    ]
    new_listing_count: int


class VolunteerProjectService:
    def __init__(self, repository: VolunteerProjectRepository):
        self.repository = repository

    def resign_student_from_project(
        self,
        student_id: int | None,
        volunteer_record_id: int,
        reason: str | None,
    ) -> None:
        if student_id is None:
            raise ValueError("Student ID is required.")

        record = self.repository.get_student_volunteer_record(volunteer_record_id)
        if record is None:
            raise ValueError("Active project participation not found.")
        if record.student_id != student_id:
            raise ValueError("You can only resign from your own projects.")
        if record.participation_status != ParticipationStatus.ACTIVE:
            raise ValueError("This project participation is no longer active.")

        clean_reason = reason.strip() if reason else ""
        if not self.repository.resign_student_volunteer_record(
            volunteer_record_id=volunteer_record_id,
            student_id=student_id,
            volunteer_project_id=record.volunteer_project_id,
            reason=clean_reason or None,
            resignation_date=date.today(),
        ):
            raise ValueError("This project participation is no longer active.")

    def get_community_stats(self) -> dict[str, int]:
        return {
            "volunteer_count": self.repository.count_volunteers(),
            "project_count": self.repository.count_projects(),
            "organization_count": self.repository.count_organizations(),
        }

    def create_organization_listing(
        self,
        organization_user_id: int,
        project_name: str,
        primary_category: str,
        secondary_category: str,
        short_description: str,
        description: str,
        location: str,
        start_date: date,
        end_date: date | None,
        commitment_type: str,
        estimated_hours_per_session: int,
        availability: str,
        application_requirements: str,
        max_volunteers: int,
        project_cover_image: str | None,
    ) -> VolunteerProject:
        organization = self.repository.get_organization_by_user_id(organization_user_id)
        if organization is None or organization.volunteer_organization_id is None:
            raise ValueError("No organization profile found for this user.")

        project_name = project_name.strip()
        primary_category = primary_category.strip()
        secondary_category = secondary_category.strip()
        short_description = short_description.strip()
        description = description.strip()
        location = location.strip()
        commitment_type = commitment_type.strip()
        availability = availability.strip()
        application_requirements = application_requirements.strip()

        if start_date < date.today():
            raise ValueError("Start date cannot be in the past.")
        if end_date is not None and end_date < start_date:
            raise EndDateBeforeStartError(
                "End date cannot be earlier than start date."
            )

        if max_volunteers <= 0:
            raise ValueError("Maximum volunteers must be a positive integer.")

        if estimated_hours_per_session <= 0:
            raise ValueError("Estimated hours per session must be a positive integer.")

        if not project_name:
            raise ValueError("Project name is required.")

        if not primary_category:
            raise ValueError("Primary category is required.")

        if not description:
            raise ValueError("Description is required.")

        if not location:
            raise ValueError("Location is required.")

        if not commitment_type:
            raise ValueError("Commitment type is required.")

        if not availability:
            raise ValueError("Availability is required.")

        if not short_description:
            raise ValueError("Short description is required.")

        if short_description and len(short_description) > 200:
            raise ValueError("Short description must be 200 characters or fewer.")

        project = VolunteerProject(
            volunteer_organization_id=organization.volunteer_organization_id,
            project_name=project_name,
            primary_category=primary_category,
            secondary_category=secondary_category,
            short_listing_summary=short_description,
            description=description,
            location=location,
            start_date=start_date,
            end_date=end_date,
            commitment_type=commitment_type,
            estimated_hours_per_session=estimated_hours_per_session,
            availability=availability,
            application_requirements=application_requirements,
            max_volunteers=max_volunteers,
            project_cover_image=project_cover_image,
            status=VolunteerProjectStatus.PENDING,
        )
        return self.repository.create_organization_listing(project)

    def get_organization_dashboard(
        self,
        organization_user_id: int,
    ) -> VolunteerOrganizationDashboard:
        organization = self.repository.get_organization_by_user_id(
            organization_user_id
        )
        if organization is None or organization.volunteer_organization_id is None:
            raise ValueError("No organization profile found for this user.")
        listings = self.repository.get_organization_listings(
            organization.volunteer_organization_id
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        new_listing_count = 0
        for listing in listings:
            created_at = listing.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at >= cutoff:
                new_listing_count += 1
        return VolunteerOrganizationDashboard(
            organization=organization,
            listings=listings,
            recent_listings=listings[:4],
            pending_applicant_counts=self.repository.count_pending_applications_by_project(
                organization.volunteer_organization_id
            ),
            protected_listing_ids=self.repository.get_projects_with_applications_or_volunteer_records(
                organization.volunteer_organization_id
            ),
            new_applicant_count=self.repository.count_pending_organization_applications(
                organization.volunteer_organization_id
            ),
            total_hours=self.repository.get_organization_total_hours(
                organization.volunteer_organization_id
            ),
            recent_applicants=self.repository.get_recent_organization_applications(
                organization.volunteer_organization_id
            ),
            new_listing_count=new_listing_count,
        )

    def get_all_organization_listings(
        self,
        organization_user_id: int,
    ) -> tuple[list[VolunteerProject], dict[int, int], set[int]]:
        organization = self.repository.get_organization_by_user_id(
            organization_user_id
        )
        if organization is None or organization.volunteer_organization_id is None:
            raise ValueError("No organization profile found for this user.")
        organization_id = organization.volunteer_organization_id
        return (
            self.repository.get_organization_listings(organization_id),
            self.repository.count_pending_applications_by_project(organization_id),
            self.repository.get_projects_with_applications_or_volunteer_records(
                organization_id
            ),
        )

    def get_all_organization_applications(
        self,
        organization_user_id: int,
    ) -> list[tuple[StudentVolunteerApplication, Student, User, VolunteerProject]]:
        organization = self.repository.get_organization_by_user_id(
            organization_user_id
        )
        if organization is None or organization.volunteer_organization_id is None:
            raise ValueError("No organization profile found for this user.")
        return self.repository.get_recent_organization_applications(
            organization.volunteer_organization_id,
            limit=None,
        )

    def get_organization_listing(
        self,
        organization_user_id: int,
        volunteer_project_id: int,
    ) -> VolunteerProject | None:
        organization = self.repository.get_organization_by_user_id(
            organization_user_id
        )
        if organization is None or organization.volunteer_organization_id is None:
            raise ValueError("No organization profile found for this user.")
        return self.repository.get_organization_listing(
            organization.volunteer_organization_id,
            volunteer_project_id,
        )

    def delete_organization_listing(
        self,
        organization_user_id: int,
        volunteer_project_id: int,
    ) -> str | None:
        organization = self.repository.get_organization_by_user_id(
            organization_user_id
        )
        if organization is None or organization.volunteer_organization_id is None:
            raise ValueError("No organization profile found for this user.")
        project = self.repository.get_organization_listing(
            organization.volunteer_organization_id,
            volunteer_project_id,
        )
        if project is None:
            raise OrganizationListingNotFoundError("Listing not found.")
        if self.repository.listing_has_applications_or_volunteer_records(
            volunteer_project_id
        ):
            raise ListingHasAssociatedRecordsError(
                "This listing cannot be deleted because it has applications or volunteer records."
            )
        cover_image_path = project.project_cover_image
        self.repository.delete_organization_listing(project)
        return cover_image_path

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
        include_expired: bool = False,
    ) -> tuple[VolunteerProject, VolunteerOrganization] | None:
        return self.repository.get_public_project_by_id(
            volunteer_project_id,
            include_expired=include_expired,
        )
