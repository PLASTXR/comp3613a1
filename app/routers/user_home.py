from datetime import date

from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from app.dependencies.session import SessionDep
from app.dependencies.auth import AuthDep
from app.repositories.hours_log import HoursLogRepository
from app.repositories.student_profile import StudentProfileRepository
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.hours_log import HoursLogService
from app.services.student_profile import StudentProfileService
from app.services.volunteer_project import VolunteerProjectService
from app.utilities.flash import flash
from . import router, templates


@router.get("/app", response_class=HTMLResponse)
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    query: str = "",
    sort_by: str = "newest",
):
    if user.role != "regular_user":
        raise HTTPException(status_code=403, detail="Student access is required.")
    repository = HoursLogRepository(db)
    service = HoursLogService(repository)
    try:
        active_records = service.get_active_records(
            user.id,
            query=query,
            sort_by=sort_by,
        )
        stats = service.get_active_project_stats(user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "user": user,
            "active_records": active_records,
            "stats": stats,
            "query": query,
            "sort_by": sort_by,
            "today": date.today(),
        },
    )


@router.post(
    "/app/volunteer-records/{volunteer_record_id}/resign",
    name="resign_from_project",
)
async def resign_from_project(
    request: Request,
    volunteer_record_id: int,
    user: AuthDep,
    db: SessionDep,
    reason: str = Form(default=""),
):
    if user.role != "regular_user":
        raise HTTPException(status_code=403, detail="Student access is required.")

    repository = VolunteerProjectRepository(db)
    service = VolunteerProjectService(repository)
    try:
        service.resign_student_from_project(
            student_id=user.id,
            volunteer_record_id=volunteer_record_id,
            reason=reason,
        )
        flash(request, "You have resigned from the project.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("user_home_view"),
        status_code=303,
    )


@router.get("/app/profile", response_class=HTMLResponse, name="profile_view")
async def profile_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    student = None
    if user.role == "regular_user" and user.id is not None:
        student = StudentProfileService(StudentProfileRepository(db)).get_student(
            user.id
        )
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": user, "student": student},
    )


@router.post(
    "/app/profile/picture",
    name="update_student_profile_picture",
)
async def update_student_profile_picture(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    image: UploadFile | None = File(default=None),
):
    if user.role != "regular_user":
        raise HTTPException(status_code=403, detail="Student access is required.")
    if user.id is None:
        raise HTTPException(status_code=400, detail="Student ID is missing.")

    service = StudentProfileService(StudentProfileRepository(db))
    try:
        await service.update_profile_picture(user.id, image)
        flash(request, "Profile picture updated.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("profile_view"),
        status_code=303,
    )


@router.get(
    "/students/{student_id}/profile-picture",
    name="student_profile_picture",
)
async def student_profile_picture(
    student_id: int,
    user: AuthDep,
    db: SessionDep,
):
    service = StudentProfileService(StudentProfileRepository(db))
    authorized = user.role == "admin" or (
        user.role == "regular_user" and user.id == student_id
    )
    if (
        not authorized
        and user.role == "volunteer_organization"
        and user.id is not None
    ):
        authorized = service.organization_can_view_picture(user.id, student_id)
    if not authorized:
        raise HTTPException(status_code=403, detail="Access is denied.")

    try:
        image_path = service.get_profile_picture_path(student_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path=image_path)