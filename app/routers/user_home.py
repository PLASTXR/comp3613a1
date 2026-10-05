from datetime import date

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import status
from app.dependencies.session import SessionDep
from app.dependencies.auth import AuthDep, IsUserLoggedIn, get_current_user, is_admin
from app.repositories.hours_log import HoursLogRepository
from app.services.hours_log import HoursLogService
from . import router, templates


@router.get("/app", response_class=HTMLResponse)
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    repository = HoursLogRepository(db)
    service = HoursLogService(repository)
    active_records = service.get_active_records(user.id)
    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "user": user,
            "active_records": active_records,
            "today": date.today(),
        },
    )


@router.get("/app/profile", response_class=HTMLResponse, name="profile_view")
async def profile_view(
    request: Request,
    user: AuthDep,
):
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": user},
    )