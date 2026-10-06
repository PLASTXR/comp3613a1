from datetime import date

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.models.reward import Redemption, RewardListing
from app.models.student import Student


class RewardRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_rewards(self) -> int:
        statement = select(func.count()).select_from(RewardListing)
        return int(self.db.exec(statement).one())

    def list_rewards(
        self,
        query: str | None = None,
        category: str | None = None,
        sort_by: str = "name",
    ) -> list[RewardListing]:
        statement = select(RewardListing)
        if query:
            search_term = f"%{query}%"
            statement = statement.where(
                or_(
                    RewardListing.name.ilike(search_term),
                    RewardListing.description.ilike(search_term),
                )
            )
        if category:
            statement = statement.where(
                or_(
                    RewardListing.primary_category.ilike(category),
                    RewardListing.secondary_category.ilike(category),
                )
            )

        sort_columns = {
            "name": RewardListing.name,
            "points_low": RewardListing.points_cost,
            "points_high": RewardListing.points_cost.desc(),
            "recent": RewardListing.updated_date.desc(),
        }
        if sort_by not in sort_columns:
            raise ValueError("Unsupported reward sort order.")
        statement = statement.order_by(sort_columns[sort_by])
        return list(self.db.exec(statement).all())

    def get_reward(self, reward_id: int) -> RewardListing | None:
        return self.db.get(RewardListing, reward_id)

    def get_student(self, student_id: int | None) -> Student | None:
        if student_id is None:
            return None
        return self.db.get(Student, student_id)

    def list_redemptions(
        self,
        student_id: int,
    ) -> list[tuple[Redemption, RewardListing]]:
        statement = (
            select(Redemption, RewardListing)
            .join(
                RewardListing,
                Redemption.reward_listing_id == RewardListing.reward_id,
            )
            .where(Redemption.student_id == student_id)
            .order_by(
                Redemption.redeemed_date.desc(),
                Redemption.redemption_id.desc(),
            )
        )
        return list(self.db.exec(statement).all())

    def create_redemption(
        self,
        student: Student,
        reward: RewardListing,
        quantity: int,
        points_spent: int,
    ) -> Redemption:
        if student.student_id is None:
            raise RuntimeError("Cannot redeem a reward without a student ID.")
        if reward.reward_id is None:
            raise RuntimeError("Cannot redeem a reward without a database ID.")

        redemption = Redemption(
            student_id=student.student_id,
            reward_listing_id=reward.reward_id,
            quantity=quantity,
            points_spent=points_spent,
        )

        student.credits -= points_spent
        reward.quantity_available -= quantity
        reward.updated_date = date.today()

        try:
            self.db.add(redemption)
            self.db.add(student)
            self.db.add(reward)
            self.db.commit()
            self.db.refresh(redemption)
        except Exception:
            self.db.rollback()
            raise

        return redemption
