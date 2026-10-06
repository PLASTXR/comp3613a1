"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.campus_admin import CampusVolunteerismCentreAdmin
from app.models.hours_log import HoursLog, HoursLogStatus
from app.models.reward import Redemption, RewardListing
from app.models.student_application import (
    StudentVolunteerApplication,
    StudentVolunteerApplicationStatus,
)
from app.models.student import ParticipationStatus, Student, StudentVolunteerRecord
from app.models.user import User
from app.models.volunteer_project import (
    ProjectCoverImage,
    VolunteerOrganization,
    VolunteerProject,
    VolunteerProjectStatus,
)

__all__ = [
    "CampusVolunteerismCentreAdmin",
    "HoursLog",
    "HoursLogStatus",
    "ParticipationStatus",
    "ProjectCoverImage",
    "Redemption",
    "RewardListing",
    "StudentVolunteerApplication",
    "StudentVolunteerApplicationStatus",
    "Student",
    "StudentVolunteerRecord",
    "User",
    "VolunteerOrganization",
    "VolunteerProject",
    "VolunteerProjectStatus",
]
