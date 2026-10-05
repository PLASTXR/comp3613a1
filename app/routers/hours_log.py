from datetime import date

from fastapi import File, Form, Request, UploadFile
from starlette.responses import RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.hours_log import HoursLogRepository
from app.services.hours_log import HoursLogService
from app.utilities.evidence import delete_hours_evidence, save_hours_evidence
from app.utilities.flash import flash
from . import router


@router.post(
    "/app/volunteer-records/{volunteer_record_id}/hours",
    name="log_volunteer_hours",
)
async def log_volunteer_hours(
    request: Request,
    volunteer_record_id: int,
    user: AuthDep,
    db: SessionDep,
    volunteer_date: date = Form(),
    hours: int = Form(),
    description: str = Form(),
    evidence: UploadFile | None = File(default=None),
):
    repository = HoursLogRepository(db)
    service = HoursLogService(repository)
    evidence_path = None
    try:
        evidence_path = await save_hours_evidence(evidence)
        service.log_hours(
            volunteer_record_id=volunteer_record_id,
            student_id=user.id,
            volunteer_date=volunteer_date,
            hours=hours,
            description=description,
            evidence_attachment=evidence_path,
        )
        flash(request, "Hours submitted for verification.", "success")
    except ValueError as exc:
        if evidence_path is not None:
            delete_hours_evidence(evidence_path)
        flash(request, str(exc), "danger")
    return RedirectResponse(
        url=request.url_for("user_home_view"),
        status_code=303,
    )
    