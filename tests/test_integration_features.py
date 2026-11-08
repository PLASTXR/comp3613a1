from datetime import date, datetime, timedelta

import jwt
import pytest
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.config import get_settings
from app.models.campus_admin import CampusVolunteerismCentreAdmin
from app.models.hours_log import HoursLog, HoursLogStatus
from app.models.reward import Redemption, RewardListing
from app.models.student import (
    ParticipationStatus,
    Student,
    StudentVolunteerRecord,
)
from app.models.student_application import (
    StudentVolunteerApplication,
    StudentVolunteerApplicationStatus,
)
from app.models.user import User
from app.models.volunteer_project import (
    VolunteerOrganization,
    VolunteerProject,
    VolunteerProjectStatus,
)
from app.repositories.admin_review import AdminReviewRepository
from app.repositories.hours_log import HoursLogRepository
from app.repositories.reward import RewardRepository
from app.repositories.student_application import StudentApplicationRepository
from app.repositories.user import UserRepository
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.admin_review import AdminReviewService
from app.services.auth_service import AuthService
from app.services.hours_log import HoursLogService
from app.services.reward import RewardService
from app.services.student_application import StudentApplicationService
from app.services.volunteer_project import (
    ListingHasAssociatedRecordsError,
    VolunteerProjectService,
)
from app.utilities.security import encrypt_password


def current_date() -> date:
    return datetime.now().astimezone().date()


@pytest.fixture(scope="class")
def engine(tmp_path_factory):
    database_path = tmp_path_factory.mktemp("integration-tests") / "tests.sqlite"
    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(test_engine)
    try:
        yield test_engine
    finally:
        SQLModel.metadata.drop_all(test_engine)
        test_engine.dispose()


@pytest.fixture(scope="class")
def session(engine):
    with Session(engine) as db_session:
        yield db_session


def create_student(
    session: Session,
    *,
    username: str = "student",
    credits: int = 0,
) -> Student:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password=encrypt_password("test-password"),
        role="regular_user",
    )
    session.add(user)
    session.flush()
    student = Student(
        student_id=user.id,
        contact_email=str(user.email),
        first_name="Test",
        last_name="Student",
        credits=credits,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def create_organization(
    session: Session,
    *,
    username: str = "organization",
) -> VolunteerOrganization:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password=encrypt_password("test-password"),
        role="volunteer_organization",
    )
    session.add(user)
    session.flush()
    organization = VolunteerOrganization(
        user_id=user.id,
        organization_name="Community Helpers",
        contact_email=str(user.email),
    )
    session.add(organization)
    session.commit()
    session.refresh(organization)
    return organization


def create_project(
    session: Session,
    organization: VolunteerOrganization,
    *,
    project_name: str = "Community Garden",
    status: VolunteerProjectStatus = VolunteerProjectStatus.APPROVED,
    current_volunteers: int = 0,
    max_volunteers: int = 10,
) -> VolunteerProject:
    project = VolunteerProject(
        volunteer_organization_id=organization.volunteer_organization_id,
        project_name=project_name,
        primary_category="Environment",
        short_listing_summary="Help in the community garden.",
        description="Plant and maintain the community garden.",
        location="Campus",
        start_date=current_date() - timedelta(days=1),
        end_date=current_date() + timedelta(days=30),
        commitment_type="weekly",
        estimated_hours_per_session=2,
        availability="weekends",
        max_volunteers=max_volunteers,
        current_volunteers=current_volunteers,
        status=status,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def create_participation_record(
    session: Session,
    student: Student,
    project: VolunteerProject,
) -> StudentVolunteerRecord:
    record = StudentVolunteerRecord(
        student_id=student.student_id,
        volunteer_project_id=project.volunteer_project_id,
        organization_name="Community Helpers",
        start_date=project.start_date,
        end_date=project.end_date,
        participation_status=ParticipationStatus.ACTIVE,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def create_admin(session: Session) -> CampusVolunteerismCentreAdmin:
    admin = CampusVolunteerismCentreAdmin(
        password="unused-test-password",
        contact_email="admin@example.test",
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def scenario_register_user(session):
    repository = UserRepository(session)
    service = AuthService(repository)

    created = service.register_user(
        username="new-student",
        email="new-student@example.com",
        password="a-strong-test-password",
    )

    saved_user = repository.get_by_username("new-student")
    assert saved_user is not None
    assert created.id == saved_user.id
    assert saved_user.email == "new-student@example.com"
    assert saved_user.role == "regular_user"
    assert session.get(Student, saved_user.id) is not None
    assert saved_user.password != "a-strong-test-password"


def scenario_authenticate_success(session):
    repository = UserRepository(session)
    service = AuthService(repository)
    service.register_user(
        username="valid-login",
        email="valid-login@example.com",
        password="a-strong-test-password",
    )

    token = service.authenticate_user(
        username="valid-login",
        password="a-strong-test-password",
    )

    assert isinstance(token, str)
    payload = jwt.decode(
        token,
        get_settings().secret_key,
        algorithms=[get_settings().jwt_algorithm],
    )
    user = repository.get_by_username("valid-login")
    assert user is not None
    assert payload["sub"] == str(user.id)
    assert payload["role"] == user.role


def scenario_authenticate_wrong_password(session):
    service = AuthService(UserRepository(session))
    service.register_user(
        username="wrong-password",
        email="wrong-password@example.com",
        password="correct-test-password",
    )

    assert (
        service.authenticate_user(
            username="wrong-password",
            password="incorrect-test-password",
        )
        is None
    )


def scenario_authenticate_invalid_username(session):
    service = AuthService(UserRepository(session))

    assert (
        service.authenticate_user(
            username="unknown-user",
            password="any-test-password",
        )
        is None
    )


def scenario_student_apply_to_project(session):
    student = create_student(session)
    organization = create_organization(session)
    project = create_project(session, organization)
    service = StudentApplicationService(StudentApplicationRepository(session))

    application = service.submit_application(
        student_id=student.student_id,
        volunteer_project_id=project.volunteer_project_id,
        student_motivation="I would like to help.",
    )

    saved_application = session.get(
        StudentVolunteerApplication,
        application.application_id,
    )
    assert saved_application is not None
    assert saved_application.student_id == student.student_id
    assert saved_application.volunteer_project_id == project.volunteer_project_id
    assert saved_application.application_status == (
        StudentVolunteerApplicationStatus.PENDING
    )


def scenario_org_post_listing_requires_admin_approval(session):
    organization = create_organization(session)
    service = VolunteerProjectService(VolunteerProjectRepository(session))
    project = service.create_organization_listing(
        organization_user_id=organization.user_id,
        project_name="Park Cleanup",
        primary_category="Environment",
        secondary_category="",
        short_description="Clean up the local park.",
        description="Collect litter and improve the park.",
        location="City Park",
        start_date=current_date() + timedelta(days=5),
        end_date=current_date() + timedelta(days=20),
        commitment_type="one_time",
        estimated_hours_per_session=3,
        availability="weekends",
        application_requirements="",
        max_volunteers=12,
        project_cover_image=None,
    )
    project_id = project.volunteer_project_id
    assert project.status == VolunteerProjectStatus.PENDING
    assert service.search_public_projects(query=None, category=None) == []

    AdminReviewService(AdminReviewRepository(session)).review_project(
        project_id=project_id,
        approve=True,
    )

    session.expire_all()
    saved_project = session.get(VolunteerProject, project_id)
    assert saved_project is not None
    assert saved_project.status == VolunteerProjectStatus.APPROVED
    public_results = service.search_public_projects(query="Park", category=None)
    assert any(item[0].volunteer_project_id == project_id for item in public_results)


def scenario_student_log_hours_increments_totals(session):
    student = create_student(session)
    organization = create_organization(session)
    project = create_project(
        session,
        organization,
        current_volunteers=1,
    )
    record = create_participation_record(session, student, project)
    admin = create_admin(session)

    log = HoursLogService(HoursLogRepository(session)).log_hours(
        student_id=student.student_id,
        volunteer_record_id=record.volunteer_record_id,
        volunteer_date=current_date(),
        hours=4,
        description="Prepared garden beds.",
        evidence_attachment=None,
    )
    session.refresh(log)
    session.refresh(student)
    assert log.status == HoursLogStatus.PENDING
    assert student.total_verified_hours == 0
    assert student.total_unverified_hours == 4

    AdminReviewService(AdminReviewRepository(session)).approve_hours_log(
        log_id=log.log_id,
        admin_user_id=admin.admin_id,
    )

    session.expire_all()
    saved_log = session.get(HoursLog, log.log_id)
    saved_student = session.get(Student, student.student_id)
    saved_record = session.get(StudentVolunteerRecord, record.volunteer_record_id)
    assert saved_log is not None
    assert saved_student is not None
    assert saved_record is not None
    assert saved_log.status == HoursLogStatus.APPROVED
    assert saved_student.total_verified_hours == 4
    assert saved_student.total_unverified_hours == 0
    assert saved_student.credits == 100
    assert saved_record.verified_hours == 4
    assert saved_record.unverified_hours == 0


def scenario_student_redeem_reward_deducts_credits(session):
    student = create_student(session, credits=500)
    reward = RewardListing(
        name="Reusable Water Bottle",
        points_cost=200,
        quantity_available=3,
    )
    session.add(reward)
    session.commit()
    session.refresh(reward)

    redemption, _, remaining_credits = RewardService(
        RewardRepository(session)
    ).redeem_reward(
        student_id=student.student_id,
        reward_id=reward.reward_id,
        quantity=1,
    )

    session.expire_all()
    saved_redemption = session.get(Redemption, redemption.redemption_id)
    saved_student = session.get(Student, student.student_id)
    saved_reward = session.get(RewardListing, reward.reward_id)
    assert saved_redemption is not None
    assert saved_student is not None
    assert saved_reward is not None
    assert saved_redemption.points_spent == 200
    assert remaining_credits == 300
    assert saved_student.credits == 300
    assert saved_reward.quantity_available == 2


def scenario_student_resignation_updates_record(session):
    student = create_student(session)
    organization = create_organization(session)
    project = create_project(
        session,
        organization,
        current_volunteers=1,
    )
    record = create_participation_record(session, student, project)
    service = VolunteerProjectService(VolunteerProjectRepository(session))

    service.resign_student_from_project(
        student_id=student.student_id,
        volunteer_record_id=record.volunteer_record_id,
        reason="Schedule changed",
    )

    session.expire_all()
    saved_record = session.get(StudentVolunteerRecord, record.volunteer_record_id)
    saved_project = session.get(VolunteerProject, project.volunteer_project_id)
    active_records = HoursLogService(HoursLogRepository(session)).get_active_records(
        student_id=student.student_id,
    )
    assert saved_record is not None
    assert saved_project is not None
    assert saved_record.participation_status == ParticipationStatus.RESIGNED
    assert saved_record.resignation_reason == "Schedule changed"
    assert saved_project.current_volunteers == 0
    assert all(
        active_record.volunteer_record_id != record.volunteer_record_id
        for active_record, _, _ in active_records
    )


def scenario_delete_listing_with_applications_fails(session):
    student = create_student(session)
    organization = create_organization(session)
    project = create_project(
        session,
        organization,
        status=VolunteerProjectStatus.PENDING,
    )
    application = StudentVolunteerApplication(
        student_id=student.student_id,
        volunteer_project_id=project.volunteer_project_id,
        student_motivation="Please consider me.",
    )
    session.add(application)
    session.commit()
    project_id = project.volunteer_project_id
    service = VolunteerProjectService(VolunteerProjectRepository(session))

    with pytest.raises(ListingHasAssociatedRecordsError):
        service.delete_organization_listing(
            organization_user_id=organization.user_id,
            volunteer_project_id=project_id,
        )

    assert session.get(VolunteerProject, project_id) is not None
    assert session.exec(
        select(StudentVolunteerApplication).where(
            StudentVolunteerApplication.volunteer_project_id == project_id
        )
    ).first() is not None


class TestIntegrationFeatures:
    @pytest.fixture(autouse=True)
    def clean_database(self, session):
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.execute(delete(table))
        session.commit()
        session.expire_all()

    def test_register_user(self, session):
        scenario_register_user(session)

    def test_authenticate_success(self, session):
        scenario_authenticate_success(session)

    def test_authenticate_wrong_password(self, session):
        scenario_authenticate_wrong_password(session)

    def test_authenticate_invalid_username(self, session):
        scenario_authenticate_invalid_username(session)

    def test_student_apply_to_project(self, session):
        scenario_student_apply_to_project(session)

    def test_org_post_listing_requires_admin_approval(self, session):
        scenario_org_post_listing_requires_admin_approval(session)

    def test_student_log_hours_increments_totals(self, session):
        scenario_student_log_hours_increments_totals(session)

    def test_student_redeem_reward_deducts_credits(self, session):
        scenario_student_redeem_reward_deducts_credits(session)

    def test_student_resignation_updates_record(self, session):
        scenario_student_resignation_updates_record(session)

    def test_delete_listing_with_applications_fails(self, session):
        scenario_delete_listing_with_applications_fails(session)
