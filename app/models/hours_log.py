from enum import Enum
from datetime import date

from sqlalchemy import String
from sqlmodel import Field, SQLModel


class HoursLogStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class HoursLog(SQLModel, table=True):
    __tablename__ = "hours_log"

    log_id: int | None = Field(default=None, primary_key=True)
    volunteer_record_id: int = Field(foreign_key="student_volunteer_record.volunteer_record_id")
    student_id: int = Field(foreign_key="student.student_id")
    log_date: date = Field(default_factory=date.today)
    hours: int = Field(gt=0)
    status: HoursLogStatus = Field(
        default=HoursLogStatus.PENDING,
        sa_type=String(16),
    )
    description: str
    evidence_attachment: str | None = None
    volunteer_date: date
    admin_verified_by_id: int | None = Field(
        default=None,
        foreign_key="campus_volunteerism_centre_admin.admin_id",
    )
    verified_date: date | None = None
    denial_reason: str | None = None
