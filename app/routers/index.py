from fastapi import Request
from fastapi.responses import HTMLResponse

from app.dependencies.auth import IsUserLoggedIn, get_current_user
from app.dependencies.session import SessionDep
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.volunteer_project import VolunteerProjectService
from . import router, templates


@router.get("/", response_class=HTMLResponse, name="index_view")
async def index_view(
    request: Request,
    user_logged_in: IsUserLoggedIn,
    db: SessionDep,
):
    user = None
    if user_logged_in:
        user = await get_current_user(request, db)

    project_service = VolunteerProjectService(VolunteerProjectRepository(db))
    recent_projects = project_service.get_recent_public_projects()
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
            "user_logged_in": user_logged_in,
            "user": user,
            "recent_projects": recent_projects,
        },
    )
