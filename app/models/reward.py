from datetime import date
from typing import ClassVar

from sqlmodel import Field, SQLModel


class RewardListing(SQLModel, table=True):
    __tablename__: ClassVar[str] = "reward_listing"

    reward_id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    primary_category: str = ""
    secondary_category: str = ""
    points_cost: int = Field(ge=0)
    quantity_available: int = Field(default=0, ge=0)
    reward_image_url: str | None = None
    updated_date: date = Field(default_factory=date.today)


class Redemption(SQLModel, table=True):
    __tablename__: ClassVar[str] = "redemption"

    redemption_id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.student_id")
    reward_listing_id: int = Field(foreign_key="reward_listing.reward_id")
    points_spent: int = Field(ge=0)
    quantity: int = Field(ge=1)
    status: str = Field(default="redeemed")
    redeemed_date: date = Field(default_factory=date.today)
