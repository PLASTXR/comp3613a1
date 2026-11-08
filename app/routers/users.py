from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request, status, Form
from app.dependencies import SessionDep
from app.services.volunteer_project import VolunteerProjectService
from . import api_router
from app.services.user_service import UserService
from app.repositories.user import UserRepository
from app.utilities.flash import flash
from app.schemas import UserResponse
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.volunteer_project import VolunteerProjectService


# API endpoint for listing users
@api_router.get("/users", response_model=list[UserResponse])
async def list_users(request: Request, db: SessionDep):
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    return user_service.get_all_users()

@api_router.get("/projects")
async def list_available_projects(request: Request, db: SessionDep):
    service = VolunteerProjectService(VolunteerProjectRepository(db))
    projects = service.search_public_projects(query=None, category=None)
    
    return [
        {
            "id": project.volunteer_project_id,
            "name": project.project_name,
            "status": project.status.value if hasattr(project.status, 'value') else project.status,
            "current_volunteers": project.current_volunteers,
            "max_volunteers": project.max_volunteers
        }
        for project, organization in projects
    ]