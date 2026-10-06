from enum import Enum

from datetime import date

from sqlmodel import Field, SQLModel


class ParticipationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    RESIGNED = "resigned"

class Student(SQLModel, table=True):
    __tablename__ = "student"

    student_id: int = Field(primary_key=True, foreign_key="user.id")
    contact_email: str = ""
    contact_phone: str = ""
    first_name: str = ""
    last_name: str = ""
    profile_picture_image: str | None = None
    credits: int = 0
    volunteer_projects: str = ""
    active_projects: str = ""
    campus_ID: str = ""
    degree: str = ""
    # STUDENT SNIPPET BEGIN: complete the non-negative leaderboard-hours field.
    total_verified_hours: int = Field(default=0, ge=0)
    # STUDENT SNIPPET END
    total_unverified_hours: int = 0


class StudentVolunteerRecord(SQLModel, table=True):
    __tablename__ = "student_volunteer_record"

    volunteer_record_id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.student_id")
    volunteer_project_id: int = Field(foreign_key="volunteer_project.volunteer_project_id")
    organization_name: str
    start_date: date
    end_date: date | None = None
    participation_status: ParticipationStatus = Field(default=ParticipationStatus.ACTIVE)
    resignation_reason: str | None = None
    resignation_date: date | None = None
    verified_hours: int = Field(default=0)
    unverified_hours: int = Field(default=0)
