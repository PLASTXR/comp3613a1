from sqlmodel import Field, SQLModel


class CampusVolunteerismCentreAdmin(SQLModel, table=True):
    __tablename__ = "campus_volunteerism_centre_admin"

    admin_id: int | None = Field(default=None, primary_key=True)
    password: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    role: str = "admin"
    first_name: str = ""
    last_name: str = ""
