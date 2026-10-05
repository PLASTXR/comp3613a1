from app.models.reward import Redemption, RewardListing
from app.repositories.reward import RewardRepository


class RewardService:
    def __init__(self, repository: RewardRepository):
        self.repository = repository

    def list_rewards(
        self,
        query: str | None = None,
        category: str | None = None,
        sort_by: str = "name",
    ) -> list[RewardListing]:
        clean_query = query.strip() if query else None
        clean_category = category.strip() if category else None
        return self.repository.list_rewards(
            query=clean_query or None,
            category=clean_category or None,
            sort_by=sort_by,
        )

    def get_student_balance(self, student_id: int | None) -> int:
        student = self.repository.get_student(student_id)
        if student is None:
            raise ValueError("Student profile not found.")
        return student.credits

    def get_student_redemptions(
        self,
        student_id: int | None,
    ) -> list[tuple[Redemption, RewardListing]]:
        if student_id is None or self.repository.get_student(student_id) is None:
            raise ValueError("Student profile not found.")
        return self.repository.list_redemptions(student_id)

    def redeem_reward(
        self,
        student_id: int | None,
        reward_id: int,
        quantity: int,
    ) -> tuple[Redemption, RewardListing, int]:
        if student_id is None:
            raise ValueError("Student ID is required.")

        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

        student = self.repository.get_student(student_id)
        if student is None:
            raise ValueError("Student not found.")

        reward = self.repository.get_reward(reward_id)
        if reward is None:
            raise ValueError("Reward not found.")

        if reward.quantity_available < quantity:
            raise ValueError("Not enough quantity available for this reward.")

        total_points_required = reward.points_cost * quantity
        if student.credits < total_points_required:
            raise ValueError("Student does not have enough credits to redeem this reward.")

        remaining_credits = student.credits - total_points_required
        redemption = self.repository.create_redemption(
            student=student,
            reward=reward,
            quantity=quantity,
            points_spent=total_points_required,
        )

        return redemption, reward, remaining_credits
        
