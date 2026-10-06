from datetime import date

from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse

from app.dependencies.auth import OrganizationDep
from app.dependencies.session import SessionDep
from app.models.volunteer_project import VolunteerProject, VolunteerProjectStatus
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.volunteer_project import (
    EndDateBeforeStartError,
    ListingHasAssociatedRecordsError,
    OrganizationListingNotFoundError,
    VolunteerProjectService,
)
from app.utilities.flash import flash
from app.utilities.coverimage import delete_cover_image, save_project_cover_image
from . import router, templates


def _listing_items(
    listings: list[VolunteerProject],
    pending_applicant_counts: dict[int, int],
    protected_listing_ids: set[int],
) -> list[tuple[VolunteerProject, str, int, bool]]:
    return [
        (
            listing,
            listing.status.value
            if isinstance(listing.status, VolunteerProjectStatus)
            else listing.status,
            pending_applicant_counts.get(listing.volunteer_project_id, 0),
            listing.volunteer_project_id in protected_listing_ids,
        )
        for listing in listings
    ]


@router.get(
    "/organization/listings",
    name="organization_listings_view",
    response_class=HTMLResponse,
)
async def organization_listings_view(
    request: Request,
    user: OrganizationDep,
    db: SessionDep,
):
    service = VolunteerProjectService(VolunteerProjectRepository(db))
    dashboard = service.get_organization_dashboard(user.id)
    organization = dashboard.organization
    all_listings = dashboard.listings
    listings = dashboard.recent_listings
    today = date.today()
    all_listing_items = _listing_items(
        all_listings,
        dashboard.pending_applicant_counts,
        dashboard.protected_listing_ids,
    )
    listing_items = _listing_items(
        listings,
        dashboard.pending_applicant_counts,
        dashboard.protected_listing_ids,
    )
    expiring_soon = [
        listing
        for listing in all_listings
        if listing.end_date is not None
        and 0 <= (listing.end_date - today).days <= 30
    ]
    return templates.TemplateResponse(
        request=request,
        name="organization_listings.html",
        context={
            "user": user,
            "organization": organization,
            "return_to": "dashboard",
            "listings": listings,
            "recent_applicants": dashboard.recent_applicants,
            "listing_items": listing_items,
            "pending_count": sum(
                status == "pending"
                for _, status, _, _ in all_listing_items
            ),
            "new_applicant_count": dashboard.new_applicant_count,
            "total_volunteers": sum(
                listing.current_volunteers for listing in all_listings
            ),
            "total_hours": dashboard.total_hours,
            "new_listing_count": dashboard.new_listing_count,
            "lifetime_listing_count": len(all_listings),
            "expiring_count": len(expiring_soon),
            "listing_submitted": request.query_params.get("submitted") == "1",
        },
    )


@router.get(
    "/organization/listings/all",
    name="organization_all_listings",
    response_class=HTMLResponse,
)
async def organization_all_listings(
    request: Request,
    user: OrganizationDep,
    db: SessionDep,
):
    service = VolunteerProjectService(VolunteerProjectRepository(db))
    listings, pending_applicant_counts, protected_listing_ids = (
        service.get_all_organization_listings(user.id)
    )
    return templates.TemplateResponse(
        request=request,
        name="organization_all_listings.html",
        context={
            "user": user,
            "return_to": "all",
            "listings": _listing_items(
                listings,
                pending_applicant_counts,
                protected_listing_ids,
            ),
        },
    )


@router.get(
    "/organization/applications",
    name="organization_applications_view",
    response_class=HTMLResponse,
)
async def organization_applications_view(
    request: Request,
    user: OrganizationDep,
    db: SessionDep,
):
    service = VolunteerProjectService(VolunteerProjectRepository(db))
    applicants = service.get_all_organization_applications(user.id)
    return templates.TemplateResponse(
        request=request,
        name="organization_all_applicants.html",
        context={
            "user": user,
            "applicants": applicants,
            "applicant_count": len(applicants),
        },
    )


@router.get(
    "/organization/listings/new",
    name="organization_listing_form",
    response_class=HTMLResponse,
)
async def organization_listing_form(
    request: Request,
    user: OrganizationDep,
):
    return templates.TemplateResponse(
        request=request,
        name="organization_listing_form.html",
        context={"user": user, "today": date.today(), "form_data": {}},
    )


@router.get(
    "/organization/listings/{volunteer_project_id}",
    name="organization_listing_detail",
    response_class=HTMLResponse,
)
async def organization_listing_detail(
    request: Request,
    volunteer_project_id: int,
    user: OrganizationDep,
    db: SessionDep,
):
    service = VolunteerProjectService(VolunteerProjectRepository(db))
    project = service.get_organization_listing(user.id, volunteer_project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    status_value = (
        project.status.value
        if isinstance(project.status, VolunteerProjectStatus)
        else project.status
    )
    return templates.TemplateResponse(
        request=request,
        name="organization_listing_detail.html",
        context={"user": user, "project": project, "status": status_value},
    )


@router.post(
    "/organization/listings/{volunteer_project_id}/delete",
    name="delete_organization_listing",
)
async def delete_organization_listing(
    request: Request,
    volunteer_project_id: int,
    user: OrganizationDep,
    db: SessionDep,
    return_to: str = Form(default="dashboard"),
):
    service = VolunteerProjectService(VolunteerProjectRepository(db))
    return_route = (
        "organization_all_listings"
        if return_to == "all"
        else "organization_listings_view"
    )
    try:
        cover_image_path = service.delete_organization_listing(
            user.id,
            volunteer_project_id,
        )
    except ListingHasAssociatedRecordsError as exc:
        flash(request, str(exc), "danger")
    except OrganizationListingNotFoundError as exc:
        flash(request, str(exc), "danger")
    else:
        if cover_image_path is not None:
            delete_cover_image(cover_image_path)
        flash(request, "Listing deleted.", "success")
    return RedirectResponse(
        url=request.url_for(return_route),
        status_code=303,
    )


@router.post(
    "/organization/listings",
    name="create_organization_listing",
)
async def create_organization_listing(
    request: Request,
    user: OrganizationDep,
    db: SessionDep,
    project_name: str = Form(),
    primary_category: str = Form(),
    secondary_category: str = Form(""),
    short_description: str = Form(),
    description: str = Form(),
    location: str = Form(),
    start_date: date = Form(),
    end_date_input: str = Form(default="", alias="end_date"),
    commitment_type: str = Form(),
    estimated_hours_per_session: int = Form(),
    availability: str = Form(),
    application_requirements: str = Form(""),
    max_volunteers: int = Form(),
    project_cover_image: UploadFile | None = File(default=None),
):
    repository = VolunteerProjectRepository(db)
    service = VolunteerProjectService(repository)
    cover_image_was_selected = bool(
        project_cover_image and project_cover_image.filename
    )
    form_data = {
        "project_name": project_name,
        "primary_category": primary_category,
        "secondary_category": secondary_category,
        "short_description": short_description,
        "description": description,
        "location": location,
        "start_date": start_date.isoformat(),
        "end_date": end_date_input,
        "commitment_type": commitment_type,
        "estimated_hours_per_session": estimated_hours_per_session,
        "availability": availability,
        "application_requirements": application_requirements,
        "max_volunteers": max_volunteers,
        "cover_image_cleared": cover_image_was_selected,
    }
    try:
        end_date = date.fromisoformat(end_date_input) if end_date_input else None
    except ValueError:
        flash(request, "Enter a valid end date.", "danger")
        form_data["end_date"] = ""
        return templates.TemplateResponse(
            request=request,
            name="organization_listing_form.html",
            context={"user": user, "today": date.today(), "form_data": form_data},
            status_code=422,
        )

    cover_image_path = None
    if project_cover_image and project_cover_image.filename:
        try:
            cover_image_path = await save_project_cover_image(project_cover_image)
        except ValueError as exc:
            flash(request, str(exc), "danger")
            return templates.TemplateResponse(
                request=request,
                name="organization_listing_form.html",
                context={"user": user, "today": date.today(), "form_data": form_data},
                status_code=422,
            )

    try:
        service.create_organization_listing(
            organization_user_id=user.id,
            project_name=project_name,
            primary_category=primary_category,
            secondary_category=secondary_category,
            short_description=short_description,
            description=description,
            location=location,
            start_date=start_date,
            end_date=end_date,
            commitment_type=commitment_type,
            estimated_hours_per_session=estimated_hours_per_session,
            availability=availability,
            application_requirements=application_requirements,
            max_volunteers=max_volunteers,
            project_cover_image=cover_image_path,
        )
    except EndDateBeforeStartError as exc:
        if cover_image_path is not None:
            delete_cover_image(cover_image_path)
        form_data["end_date"] = ""
        flash(request, str(exc), "danger")
        return templates.TemplateResponse(
            request=request,
            name="organization_listing_form.html",
            context={"user": user, "today": date.today(), "form_data": form_data},
            status_code=422,
        )
    except ValueError as exc:
        if cover_image_path is not None:
            delete_cover_image(cover_image_path)
        flash(request, str(exc), "danger")
        return templates.TemplateResponse(
            request=request,
            name="organization_listing_form.html",
            context={"user": user, "today": date.today(), "form_data": form_data},
            status_code=422,
        )

    return RedirectResponse(
        url=request.url_for("organization_listings_view").include_query_params(
            submitted="1"
        ),
        status_code=303,
    )
