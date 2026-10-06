from fastapi import Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.dependencies.auth import AdminDep
from app.dependencies.session import SessionDep
from app.repositories.admin_review import AdminReviewRepository
from app.services.admin_review import AdminReviewService
from app.utilities.flash import flash
from . import router, templates


def _admin_review_service(db: SessionDep) -> AdminReviewService:
    return AdminReviewService(AdminReviewRepository(db))


def _render_queue(
    request: Request,
    user: AdminDep,
    service: AdminReviewService,
    queue: str,
    title: str,
):
    try:
        records = service.get_queue(queue)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="admin_queue.html",
        context={
            "user": user,
            "queue": queue,
            "title": title,
            "records": records,
        },
    )


@router.get("/admin", response_class=HTMLResponse, name="admin_home_view")
async def admin_home_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    dashboard = _admin_review_service(db).get_dashboard_data()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "user": user,
            "dashboard": dashboard,
        },
    )


@router.get("/admin/listings", response_class=HTMLResponse, name="admin_all_listings")
async def admin_all_listings_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    return _render_queue(
        request,
        user,
        _admin_review_service(db),
        "listings",
        "Pending Project Listings",
    )


@router.get(
    "/admin/applications",
    response_class=HTMLResponse,
    name="admin_all_applications",
)
async def admin_all_applications_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    return _render_queue(
        request,
        user,
        _admin_review_service(db),
        "applications",
        "Pending Student Applications",
    )


@router.get("/admin/hours", response_class=HTMLResponse, name="admin_all_hours")
async def admin_all_hours_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    return _render_queue(
        request,
        user,
        _admin_review_service(db),
        "hours",
        "Pending Hour Logs",
    )


@router.get(
    "/admin/resignations",
    response_class=HTMLResponse,
    name="admin_all_resignations",
)
async def admin_all_resignations_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    return _render_queue(
        request,
        user,
        _admin_review_service(db),
        "resignations",
        "Student Resignations",
    )


@router.get(
    "/admin/listings/{project_id}",
    response_class=HTMLResponse,
    name="admin_listing_review_view",
)
async def admin_listing_review_view(
    request: Request,
    project_id: int,
    user: AdminDep,
    db: SessionDep,
):
    service = _admin_review_service(db)
    try:
        project, organization = service.get_project_review(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="admin_listing_review.html",
        context={
            "user": user,
            "project": project,
            "organization": organization,
        },
    )


@router.post(
    "/admin/listings/{project_id}/approve",
    name="admin_approve_listing",
)
async def admin_approve_listing(
    request: Request,
    project_id: int,
    user: AdminDep,
    db: SessionDep,
):
    try:
        _admin_review_service(db).review_project(project_id, approve=True)
        flash(request, "Project listing approved.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("admin_listing_review_view", project_id=project_id),
        status_code=303,
    )


@router.post(
    "/admin/listings/{project_id}/deny",
    name="admin_deny_listing",
)
async def admin_deny_listing(
    request: Request,
    project_id: int,
    user: AdminDep,
    db: SessionDep,
):
    try:
        _admin_review_service(db).review_project(project_id, approve=False)
        flash(request, "Project listing denied.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("admin_listing_review_view", project_id=project_id),
        status_code=303,
    )


@router.get(
    "/admin/applications/{application_id}",
    response_class=HTMLResponse,
    name="admin_application_review_view",
)
async def admin_application_review_view(
    request: Request,
    application_id: int,
    user: AdminDep,
    db: SessionDep,
):
    service = _admin_review_service(db)
    try:
        application, student, student_user, project, organization = (
            service.get_application_review(application_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="admin_application_review.html",
        context={
            "user": user,
            "application": application,
            "student": student,
            "student_user": student_user,
            "project": project,
            "organization": organization,
        },
    )


@router.post(
    "/admin/applications/{application_id}/accept",
    name="admin_accept_application",
)
async def admin_accept_application(
    request: Request,
    application_id: int,
    admin: AdminDep,
    db: SessionDep,
):
    try:
        _admin_review_service(db).review_application(
            application_id=application_id,
            admin_user_id=admin.id,
            approve=True,
        )
        flash(
            request,
            "Application accepted; the student is now an active volunteer.",
            "success",
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("admin_home_view"),
        status_code=303,
    )


@router.post(
    "/admin/applications/{application_id}/deny",
    name="admin_deny_application",
)
async def admin_deny_application(
    request: Request,
    application_id: int,
    admin: AdminDep,
    db: SessionDep,
):
    try:
        _admin_review_service(db).review_application(
            application_id=application_id,
            admin_user_id=admin.id,
            approve=False,
        )
        flash(request, "Application denied.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("admin_home_view"),
        status_code=303,
    )


@router.get(
    "/admin/hours/{log_id}",
    response_class=HTMLResponse,
    name="admin_hour_review_view",
)
async def admin_hour_review_view(
    request: Request,
    log_id: int,
    user: AdminDep,
    db: SessionDep,
):
    service = _admin_review_service(db)
    try:
        hours_log, student, student_user, record, project = (
            service.get_hour_review(log_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="admin_hour_review.html",
        context={
            "user": user,
            "hours_log": hours_log,
            "student": student,
            "student_user": student_user,
            "record": record,
            "project": project,
        },
    )


@router.get(
    "/admin/hours/{log_id}/evidence",
    name="admin_hour_evidence",
)
async def admin_hour_evidence(
    log_id: int,
    user: AdminDep,
    db: SessionDep,
):
    try:
        evidence_path, filename = _admin_review_service(db).get_hour_evidence(log_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path=evidence_path, filename=filename)


@router.post(
    "/admin/hours/{log_id}/approve",
    name="admin_approve_hours_log",
)
async def admin_approve_hours_log(
    request: Request,
    log_id: int,
    admin: AdminDep,
    db: SessionDep,
):
    try:
        _admin_review_service(db).approve_hours_log(
            log_id=log_id,
            admin_user_id=admin.id,
        )
        flash(
            request,
            "Hour log approved; credits were added to the student's account.",
            "success",
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("admin_hour_review_view", log_id=log_id),
        status_code=303,
    )


@router.post(
    "/admin/hours/{log_id}/deny",
    name="admin_deny_hours_log",
)
async def admin_deny_hours_log(
    request: Request,
    log_id: int,
    admin: AdminDep,
    db: SessionDep,
    denial_reason: str = Form(default=""),
):
    try:
        _admin_review_service(db).deny_hours_log(
            log_id=log_id,
            admin_user_id=admin.id,
            denial_reason=denial_reason,
        )
        flash(request, "Hour log denied.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("admin_hour_review_view", log_id=log_id),
        status_code=303,
    )
