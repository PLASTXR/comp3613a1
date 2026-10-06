from datetime import date

from app.models.hours_log import HoursLog
from app.models.student import ParticipationStatus, StudentVolunteerRecord
from app.models.volunteer_project import VolunteerOrganization, VolunteerProject
from app.repositories.hours_log import HoursLogRepository

class HoursLogService:
    def __init__(self, repository: HoursLogRepository):
        self.repository = repository

    def log_hours(
        self,
        student_id: int | None,
        volunteer_record_id: int,
        volunteer_date: date,
        hours: int,
        description: str,
        evidence_attachment: str | None,
    ) -> HoursLog:
        if student_id is None:
            raise ValueError("You must be logged in to submit hours.")
        
        if hours <= 0:
            raise ValueError("Hours must be greater than zero.")
        
        if volunteer_date > date.today():
            raise ValueError("Volunteer date cannot be in the future.")
        
        if not description or not description.strip():
            raise ValueError("Description cannot be empty.")
        
        record = self.repository.get_volunteer_record(volunteer_record_id)
        
        if record is None:
            raise ValueError("Volunteer record not found.")
        
        if record.student_id != student_id:
            raise ValueError("You can only log hours for your own volunteer records.")
        
        if record.participation_status != ParticipationStatus.ACTIVE:
            raise ValueError("You can only log hours for active volunteer records.")
        
        within_window = record.start_date <= volunteer_date and (
            record.end_date is None or volunteer_date <= record.end_date
        )
        
        if not within_window:
            raise ValueError("Volunteer date must be within the volunteer record's start and end dates.")
        
        status = "pending"
        
        log = HoursLog(
            volunteer_record_id=volunteer_record_id,
            student_id=student_id,
            volunteer_date=volunteer_date,
            hours=hours,
            description=description,
            evidence_attachment=evidence_attachment,
            status=status,
        )

        return self.repository.create_hours_log(log)

    def get_active_records(
        self,
        student_id: int | None,
        query: str | None = None,
        sort_by: str = "newest",
    ) -> list[tuple[StudentVolunteerRecord, VolunteerProject, VolunteerOrganization]]:
        if student_id is None:
            return []
        if sort_by not in {"newest", "hours", "volunteers"}:
            raise ValueError("Unsupported active-project sort order.")
        clean_query = query.strip() if query else None
        return self.repository.get_active_records(
            student_id,
            query=clean_query or None,
            sort_by=sort_by,
        )

    def get_active_project_stats(self, student_id: int | None) -> dict[str, int]:
        if student_id is None:
            raise ValueError("Student ID is required.")
        student = self.repository.get_student(student_id)
        if student is None:
            raise ValueError("Student profile not found.")
        active_projects, total_hours, pending_hours = (
            self.repository.get_active_project_stats(student_id)
        )
        return {
            "active_projects": active_projects,
            "total_hours": total_hours,
            "pending_hours": pending_hours,
            "credits": student.credits,
        }
