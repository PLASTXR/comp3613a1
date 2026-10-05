from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.reward import RewardRepository
from app.services.reward import RewardService
from app.utilities.flash import flash, get_flashed_messages
from . import router, templates


@router.get("/rewards", response_class=HTMLResponse, name="rewards_view")
async def rewards_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    query: str | None = None,
    category: str | None = None,
    sort_by: str = "name",
    redeemed: str | None = None,
):
    if user.role != "regular_user":
        raise HTTPException(status_code=403, detail="Student access is required.")

    repository = RewardRepository(db)
    service = RewardService(repository)
    try:
        rewards = service.list_rewards(
            query=query,
            category=category,
            sort_by=sort_by,
        )
        credits = service.get_student_balance(user.id)
        redemptions = service.get_student_redemptions(user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="rewards.html",
        context={
            "user": user,
            "user_logged_in": True,
            "rewards": rewards,
            "credits": credits,
            "redemptions": redemptions,
            "query": query or "",
            "category": category or "",
            "sort_by": sort_by,
            "redeemed": redeemed == "1",
            "flash_messages": get_flashed_messages(request),
        },
    )


@router.post("/rewards/{reward_id}/redeem", name="redeem_reward")
async def redeem_reward_action(
    request: Request,
    reward_id: int,
    user: AuthDep,
    db: SessionDep,
    quantity: int = Form(),
):
    repository = RewardRepository(db)
    service = RewardService(repository)
    try:
        redemption, reward, remaining_credits = service.redeem_reward(
            student_id=user.id,
            reward_id=reward_id,
            quantity=quantity,
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("rewards_view"),
            status_code=303,
        )

    flash(
        request,
        (
            f"You redeemed {quantity} × {reward.name} for "
            f"{redemption.points_spent} credits. Your new balance is "
            f"{remaining_credits} credits."
        ),
        "success",
    )
    return RedirectResponse(
        url=request.url_for("rewards_view").include_query_params(redeemed="1"),
        status_code=303,
    )
