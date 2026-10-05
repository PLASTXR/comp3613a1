from datetime import date

from sqlmodel import Field, SQLModel


class HoursLog(SQLModel, table=True):
    __tablename__ = "hours_log"

    log_id: int | None = Field(default=None, primary_key=True)
    volunteer_record_id: int = Field(foreign_key="student_volunteer_record.volunteer_record_id")
    student_id: int = Field(foreign_key="student.student_id")
    log_date: date = Field(default_factory=date.today)
    hours: int = Field(gt=0)
    status: str = Field(default="pending")
    description: str
    evidence_attachment: str | None = None
    volunteer_date: date
    admin_verified_by_id: int | None = Field(
        default=None,
        foreign_key="campus_volunteerism_centre_admin.admin_id",
    )
    verified_date: date | None = None
    denial_reason: str | None = None
