import logging

from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from app.models.hours_log import HoursLog
from app.models.student import ParticipationStatus, Student, StudentVolunteerRecord
from app.models.volunteer_project import VolunteerOrganization, VolunteerProject

logger = logging.getLogger(__name__)

class HoursLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_student(self, student_id: int) -> Student | None:
        return self.db.get(Student, student_id)

    def get_active_project_stats(
        self,
        student_id: int,
    ) -> tuple[int, int, int]:
        active_project_count = self.db.exec(
            select(
                func.count(
                    func.distinct(StudentVolunteerRecord.volunteer_project_id)
                )
            ).where(
                StudentVolunteerRecord.student_id == student_id,
                StudentVolunteerRecord.participation_status
                == ParticipationStatus.ACTIVE,
            )
        ).one()
        hours_statement = select(
            func.coalesce(func.sum(HoursLog.hours), 0),
            func.coalesce(
                func.sum(
                    case(
                        (HoursLog.status == "pending", HoursLog.hours),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(HoursLog.student_id == student_id)
        total_hours, pending_hours = self.db.exec(hours_statement).one()
        return (
            int(active_project_count),
            int(total_hours),
            int(pending_hours),
        )

    def get_volunteer_record(self, volunteer_record_id: int) -> StudentVolunteerRecord | None:
        statement = select(StudentVolunteerRecord).where(
            StudentVolunteerRecord.volunteer_record_id == volunteer_record_id
        )
        return self.db.exec(statement).one_or_none()

    def create_hours_log(self, hours_log: HoursLog) -> HoursLog:
        try:
            record = self.db.get(
                StudentVolunteerRecord,
                hours_log.volunteer_record_id,
            )
            student = self.db.get(Student, hours_log.student_id)
            if record is None or student is None:
                raise ValueError("Hour log is missing its student participation.")
            record.unverified_hours += hours_log.hours
            student.total_unverified_hours += hours_log.hours
            self.db.add(hours_log)
            self.db.add(record)
            self.db.add(student)
            self.db.commit()
            self.db.refresh(hours_log)
            return hours_log
        except ValueError:
            self.db.rollback()
            raise
        except Exception:
            logger.exception("An error occurred while saving a volunteer hours log.")
            self.db.rollback()
            raise

    def get_active_records(
        self,
        student_id: int,
        query: str | None = None,
        sort_by: str = "newest",
    ) -> list[tuple[StudentVolunteerRecord, VolunteerProject, VolunteerOrganization]]:
        logged_hours = (
            select(func.coalesce(func.sum(HoursLog.hours), 0))
            .where(
                HoursLog.volunteer_record_id
                == StudentVolunteerRecord.volunteer_record_id
            )
            .correlate(StudentVolunteerRecord)
            .scalar_subquery()
        )
        sort_columns = {
            "newest": VolunteerProject.created_at.desc(),
            "hours": logged_hours.desc(),
            "volunteers": VolunteerProject.current_volunteers.desc(),
        }
        if sort_by not in sort_columns:
            raise ValueError("Unsupported active-project sort order.")

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
            .order_by(sort_columns[sort_by], VolunteerProject.project_name)
        )
        if query:
            search_term = f"%{query}%"
            statement = statement.where(
                or_(
                    VolunteerProject.project_name.ilike(search_term),
                    VolunteerOrganization.organization_name.ilike(search_term),
                    VolunteerProject.location.ilike(search_term),
                )
            )
        return list(self.db.exec(statement).all())
