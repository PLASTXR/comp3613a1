import logging

from sqlmodel import Session, select

from app.models.hours_log import HoursLog
from app.models.student import ParticipationStatus, StudentVolunteerRecord
from app.models.volunteer_project import VolunteerOrganization, VolunteerProject

logger = logging.getLogger(__name__)

class HoursLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_volunteer_record(self, volunteer_record_id: int) -> StudentVolunteerRecord | None:
        statement = select(StudentVolunteerRecord).where(
            StudentVolunteerRecord.volunteer_record_id == volunteer_record_id
        )
        return self.db.exec(statement).one_or_none()

    def create_hours_log(self, hours_log: HoursLog) -> HoursLog:
        try:
            self.db.add(hours_log)
            self.db.commit()
            self.db.refresh(hours_log)
            return hours_log
        except Exception:
            logger.exception("An error occurred while saving a volunteer hours log.")
            self.db.rollback()
            raise

    def get_active_records(
        self,
        student_id: int,
    ) -> list[tuple[StudentVolunteerRecord, VolunteerProject, VolunteerOrganization]]:
        statement = (
            select(StudentVolunteerRecord, VolunteerProject, VolunteerOrganization)
            .join(
                VolunteerProject,
                StudentVolunteerRecord.volunteer_project_id
                == VolunteerProject.volunteer_project_id,
            )
            .join(
                VolunteerOrganization,
                VolunteerProject.volunteer_organization_id
                == VolunteerOrganization.volunteer_organization_id,
            )
            .where(
                StudentVolunteerRecord.student_id == student_id,
                StudentVolunteerRecord.participation_status == ParticipationStatus.ACTIVE,
            )
        )
        return list(self.db.exec(statement).all())
