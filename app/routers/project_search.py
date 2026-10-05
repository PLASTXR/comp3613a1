from fastapi import HTTPException, Request
from starlette.responses import HTMLResponse

from app.dependencies.auth import IsUserLoggedIn, get_current_user
from app.dependencies.session import SessionDep
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.volunteer_project import VolunteerProjectService
from . import router, templates


@router.get("/projects", response_class=HTMLResponse, name="project_search_view")
async def project_search_view(
    request: Request,
    db: SessionDep,
    user_logged_in: IsUserLoggedIn,
    query: str | None = None,
    category: str | None = None,
):
    repository = VolunteerProjectRepository(db)
    service = VolunteerProjectService(repository)
    projects = service.search_public_projects(query=query, category=category)
    user = await get_current_user(request, db) if user_logged_in else None

    return templates.TemplateResponse(
        request=request,
        name="project_search.html",
        context={
            "projects": projects,
            "query": query or "",
            "category": category or "",
            "user": user,
            "user_logged_in": user_logged_in,
        },
    )


@router.get(
    "/projects/{volunteer_project_id}",
    response_class=HTMLResponse,
    name="project_detail_view",
)
async def project_detail_view(
    request: Request,
    volunteer_project_id: int,
    db: SessionDep,
    user_logged_in: IsUserLoggedIn,
):
    repository = VolunteerProjectRepository(db)
    service = VolunteerProjectService(repository)
    details = service.get_public_project_details(volunteer_project_id)
    if details is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    user = await get_current_user(request, db) if user_logged_in else None
    project, organization = details
    return templates.TemplateResponse(
        request=request,
        name="project_detail.html",
        context={
            "project": project,
            "organization": organization,
            "user": user,
            "user_logged_in": user_logged_in,
            "application_submitted": request.query_params.get(
                "application_submitted"
            )
            == "1",
        },
    )
