from fastapi import Form, HTTPException, Request
from starlette.responses import RedirectResponse

from app.dependencies.auth import AuthDep, IsUserLoggedIn, get_current_user
from app.dependencies.session import SessionDep
from app.repositories.student_application import StudentApplicationRepository
from app.services.student_application import StudentApplicationService
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.volunteer_project import VolunteerProjectService
from app.utilities.flash import flash
from . import router, templates


@router.get(
    "/projects/{volunteer_project_id}/apply",
    name="project_application_form",
)
async def project_application_form(
    request: Request,
    volunteer_project_id: int,
    db: SessionDep,
    user_logged_in: IsUserLoggedIn,
):
    project_repository = VolunteerProjectRepository(db)
    project_service = VolunteerProjectService(project_repository)
    details = project_service.get_public_project_details(volunteer_project_id)
    if details is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    user = await get_current_user(request, db) if user_logged_in else None
    project, organization = details
    can_apply = user is not None and user.role == "regular_user"
    already_volunteering = False
    if can_apply:
        application_service = StudentApplicationService(
            StudentApplicationRepository(db)
        )
        already_volunteering = application_service.is_accepted_or_active_volunteer(
            user.id,
            volunteer_project_id,
        )
    return templates.TemplateResponse(
        request=request,
        name="project_application.html",
        context={
            "project": project,
            "organization": organization,
            "user": user,
            "user_logged_in": user_logged_in,
            "can_apply": can_apply,
            "project_is_full": project.current_volunteers >= project.max_volunteers,
            "already_volunteering": already_volunteering,
        },
    )


@router.post(
    "/projects/{volunteer_project_id}/apply",
    name="submit_project_application",
)
async def submit_project_application(
    request: Request,
    volunteer_project_id: int,
    user: AuthDep,
    db: SessionDep,
    student_motivation: str = Form(max_length=255),
):
    repository = StudentApplicationRepository(db)
    service = StudentApplicationService(repository)
    try:
        service.submit_application(
            volunteer_project_id=volunteer_project_id,
            student_id=user.id,
            student_motivation=student_motivation,
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for(
                "project_application_form",
                volunteer_project_id=volunteer_project_id,
            ),
            status_code=303,
        )

    return RedirectResponse(
        url=request.url_for(
            "project_detail_view",
            volunteer_project_id=volunteer_project_id,
        ).include_query_params(application_submitted="1"),
        status_code=303,
    )
