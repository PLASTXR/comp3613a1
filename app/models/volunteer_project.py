from datetime import date
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, String
from sqlmodel import Field, SQLModel


class VolunteerOrganization(SQLModel, table=True):
    __tablename__ = "volunteer_organization"

    volunteer_organization_id: int | None = Field(default=None, primary_key=True)
    password: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    organization_name: str = ""
    address: str = ""
    volunteer_projects: str = ""
    active_projects: str = ""

class VolunteerProjectStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    DENIED = "denied"

class VolunteerProject(SQLModel, table=True):
    __tablename__ = "volunteer_project"

    volunteer_project_id: int | None = Field(default=None, primary_key=True)
    volunteer_organization_id: int = Field(
        foreign_key="volunteer_organization.volunteer_organization_id"
    )
    primary_category: str = ""
    secondary_category: str = ""
    current_volunteers: int = 0
    max_volunteers: int = 0
    application_requirements: str = ""
    commitment_type: str = ""
    estimated_hours_per_session: int = 0
    availability: str = ""
    project_cover_image: str | None = None
    project_name: str
    start_date: date
    end_date: date | None = None
    description: str = ""
    location: str = ""
    status: VolunteerProjectStatus = Field(
        default=VolunteerProjectStatus.PENDING,
        sa_type=String(16),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
