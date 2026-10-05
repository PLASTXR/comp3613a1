from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar

from sqlalchemy import String, UniqueConstraint
from sqlmodel import Field, SQLModel


class StudentVolunteerApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class StudentVolunteerApplication(SQLModel, table=True):
    __tablename__: ClassVar[str] = "student_volunteer_application"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "volunteer_project_id",
            name="uq_student_project_application",
        ),
    )

    application_id: int | None = Field(default=None, primary_key=True)
    volunteer_project_id: int = Field(
        foreign_key="volunteer_project.volunteer_project_id"
    )
    student_id: int = Field(foreign_key="student.student_id")
    application_status: StudentVolunteerApplicationStatus = Field(
        default=StudentVolunteerApplicationStatus.PENDING,
        sa_type=String,
    )
    creation_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    student_motivation: str = Field(default="", max_length=255)
    admin_reviewer_id: int | None = Field(
        default=None,
        foreign_key="campus_volunteerism_centre_admin.admin_id",
    )
    review_date: datetime | None = None
