from sqlmodel import Session, select

from app.models.student_application import StudentVolunteerApplication
from app.models.student import Student
from app.models.volunteer_project import VolunteerProject

class StudentApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_for_student_and_project(
        self,
        student_id: int,
        volunteer_project_id: int,
    ) -> StudentVolunteerApplication | None:
        statement = (
            select(StudentVolunteerApplication)
            .where(
                StudentVolunteerApplication.student_id == student_id,
                StudentVolunteerApplication.volunteer_project_id == volunteer_project_id,
            )
        )
        return self.db.exec(statement).first()

    def create(
        self,
        application: StudentVolunteerApplication,
    ) -> StudentVolunteerApplication:
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application
    
    def get_project_by_id(self, volunteer_project_id: int) -> VolunteerProject | None: 
        return self.db.get(VolunteerProject, volunteer_project_id)

    def get_student_by_id(self, student_id: int) -> Student | None:
        return self.db.get(Student, student_id)
    
