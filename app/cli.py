#!/usr/bin/env python3
"""FastStarter project CLI — stdlib argparse (no extra CLI library).

From the project root (venv active, deps installed; ``.env`` optional — falls back to ``.env.example``):

    python manage.py init
    python manage.py run
    python manage.py users
    python manage.py report --name "Student Name" --id "816000000"
    python manage.py usecase
    python manage.py skills-verify
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def _ensure_models_loaded() -> None:
    import app.models  # noqa: F401


def cmd_init(args: argparse.Namespace) -> None:
    """Create tables and seed demo accounts, organizations, projects, and applications."""
    from app.config import get_settings
    from app.database import drop_all, ensure_db_and_tables

    _ensure_models_loaded()
    if args.drop:
        print("Dropping all tables…")
        # Drop can fail on a brand-new empty DB; create path still retries.
        try:
            drop_all()
        except Exception as exc:  # noqa: BLE001
            from app.database import is_db_not_ready_error

            if not is_db_not_ready_error(exc):
                raise
            print(f"Database not ready yet while dropping ({exc}); continuing…")
    print("Creating tables…")
    ensure_db_and_tables()
    print(f"Database ready ({get_settings().database_uri}).")
    if getattr(args, "seed", True):
        cmd_seed(args)


def cmd_seed(args: argparse.Namespace) -> None:
    """Insert demo accounts, organizations, projects, and workflow test data.

    bob / bobpass       (regular_user)
    applicant1 / applicantpass (regular_user)
    admin / adminpass   (admin)
    """
    from app.database import ensure_db_and_tables, get_cli_session
    from app.models.campus_admin import CampusVolunteerismCentreAdmin
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
    from app.models.user import UserBase
    from app.models.volunteer_project import (
        VolunteerOrganization,
        VolunteerProject,
        VolunteerProjectStatus,
    )
    from app.repositories.user import UserRepository
    from app.schemas.user import AdminCreate, RegularUserCreate
    from app.utilities.security import encrypt_password
    from sqlmodel import select

    _ensure_models_loaded()
    ensure_db_and_tables()

    demo_users = [
        ("bob", "bob@example.com", "bobpass", "regular_user"),
        ("applicant1", "casey.rivera@example.com", "applicantpass", "regular_user"),
        ("applicant2", "morgan.lee@example.com", "applicantpass", "regular_user"),
        ("applicant3", "jamie.patel@example.com", "applicantpass", "regular_user"),
        ("admin", "admin@example.com", "adminpass", "admin"),
        ("greenearth", "hello@greenearth.example", "orgpass", "volunteer_organization"),
        ("campuspantry", "volunteer@campuspantry.example", "orgpass", "volunteer_organization"),
        ("learningnetwork", "team@learningnetwork.example", "orgpass", "volunteer_organization"),
    ]
    organization_seeds = [
        {
            "organization_name": "Green Earth Collective",
            "contact_email": "hello@greenearth.example",
            "contact_phone": "555-0101",
            "address": "12 Garden Lane",
        },
        {
            "organization_name": "Campus Community Pantry",
            "contact_email": "volunteer@campuspantry.example",
            "contact_phone": "555-0102",
            "address": "44 University Avenue",
        },
        {
            "organization_name": "Neighbourhood Learning Network",
            "contact_email": "team@learningnetwork.example",
            "contact_phone": "555-0103",
            "address": "8 Library Square",
        },
    ]
    organization_accounts = {
        "Green Earth Collective": "greenearth",
        "Campus Community Pantry": "campuspantry",
        "Neighbourhood Learning Network": "learningnetwork",
    }
    demo_applicants = [
        {
            "username": "applicant1",
            "first_name": "Casey",
            "last_name": "Rivera",
            "motivation": "I enjoy working with others and would like to contribute to this community project.",
        },
        {
            "username": "applicant2",
            "first_name": "Morgan",
            "last_name": "Lee",
            "motivation": "I am interested in volunteering, learning new skills, and supporting local residents.",
        },
        {
            "username": "applicant3",
            "first_name": "Jamie",
            "last_name": "Patel",
            "motivation": "I can contribute reliable time and enthusiasm to help this project succeed.",
        },
    ]
    today = date.today()
    project_seeds = [
        {
            "organization": "Green Earth Collective",
            "project_name": "Community Garden Crew",
            "hours_demo": True,
            "primary_category": "Environment",
            "secondary_category": "Community",
            "description": "Help prepare garden beds, plant seasonal vegetables, and care for shared growing spaces.",
            "location": "Riverside Community Garden",
            "estimated_hours_per_session": 2,
            "availability": "weekends",
        },
        {
            "organization": "Green Earth Collective",
            "project_name": "Park Clean-Up Team",
            "primary_category": "Environment",
            "secondary_category": "Community",
            "description": "Join a local team to collect litter and keep neighbourhood parks welcoming.",
            "location": "Cedar Grove Park",
            "estimated_hours_per_session": 3,
            "availability": "weekends",
        },
        {
            "organization": "Green Earth Collective",
            "project_name": "Native Plant Restoration",
            "primary_category": "Environment",
            "secondary_category": "Education",
            "description": "Support habitat restoration by planting native species and removing invasive plants.",
            "location": "North Creek Nature Reserve",
            "estimated_hours_per_session": 3,
            "availability": "weekdays",
        },
        {
            "organization": "Green Earth Collective",
            "project_name": "Recycling Education Booth",
            "primary_category": "Environment",
            "secondary_category": "Education",
            "description": "Share practical recycling tips with visitors at community events.",
            "location": "Student Union Plaza",
            "estimated_hours_per_session": 2,
            "availability": "weekdays",
        },
        {
            "organization": "Campus Community Pantry",
            "project_name": "Weekly Pantry Sorting",
            "primary_category": "Social Outreach",
            "secondary_category": "Community",
            "description": "Sort donated groceries and prepare pantry shelves for student and family visitors.",
            "location": "Campus Community Pantry",
            "estimated_hours_per_session": 2,
            "availability": "weekdays",
        },
        {
            "organization": "Campus Community Pantry",
            "project_name": "Fresh Food Distribution",
            "primary_category": "Social Outreach",
            "secondary_category": "Community",
            "description": "Help welcome visitors and distribute fresh food hampers during weekly service hours.",
            "location": "Campus Community Pantry",
            "estimated_hours_per_session": 3,
            "availability": "weekends",
        },
        {
            "organization": "Campus Community Pantry",
            "project_name": "Community Meal Preparation",
            "primary_category": "Social Outreach",
            "secondary_category": "Community",
            "description": "Prepare ingredients and package ready-to-share meals with the pantry kitchen team.",
            "location": "Campus Teaching Kitchen",
            "estimated_hours_per_session": 3,
            "availability": "weekends",
        },
        {
            "organization": "Neighbourhood Learning Network",
            "project_name": "After-School Reading Buddies",
            "primary_category": "Education",
            "secondary_category": "Youth",
            "description": "Read with elementary learners and encourage confidence through weekly literacy activities.",
            "location": "Maple Street Learning Centre",
            "estimated_hours_per_session": 2,
            "availability": "weekdays",
        },
        {
            "organization": "Neighbourhood Learning Network",
            "project_name": "Homework Help Club",
            "primary_category": "Education",
            "secondary_category": "Youth",
            "description": "Support middle-school students with homework planning and subject review.",
            "location": "Westside Public Library",
            "estimated_hours_per_session": 2,
            "availability": "weekdays",
        },
        {
            "organization": "Neighbourhood Learning Network",
            "project_name": "Digital Skills for Seniors",
            "primary_category": "Education",
            "secondary_category": "Community",
            "description": "Help older adults practise everyday computer, smartphone, and online safety skills.",
            "location": "Neighbourhood Learning Hub",
            "estimated_hours_per_session": 2,
            "availability": "weekends",
            "full_for_demo": True,
        },
    ]
    reward_seeds = [
        ("StudentCare T-Shirt", "A soft cotton StudentCare shirt.", "Clothing", 80, 30),
        ("Campus Hoodie", "A warm hoodie for cool campus days.", "Clothing", 220, 12),
        ("Campus Cap", "A classic cap in campus colours.", "Clothing", 120, 20),
        ("Campus Cafe Gift Card", "A gift card for a campus cafe visit.", "Gift Cards", 150, 15),
        ("Campus Bookstore Gift Card", "Credit toward books and supplies.", "Gift Cards", 250, 10),
        ("Community Grocery Gift Card", "A grocery gift card from a local partner.", "Gift Cards", 300, 8),
        ("Library Printing Credits", "Printing credit for campus library services.", "Campus Perks", 50, 100),
        ("Study Room Booking", "Reserve a study room for a group session.", "Campus Perks", 100, 25),
        ("Campus Event Pass", "Admission to a participating campus event.", "Campus Perks", 125, 20),
    ]

    created = 0
    skipped = 0
    organizations_created = 0
    organizations_skipped = 0
    projects_created = 0
    projects_skipped = 0
    projects_updated = 0
    applications_created = 0
    applications_skipped = 0
    volunteer_records_created = 0
    volunteer_records_skipped = 0
    rewards_created = 0
    rewards_skipped = 0
    bob_credits_initialized = False
    with get_cli_session() as session:
        repo = UserRepository(session)
        for username, email, password, role in demo_users:
            if repo.get_by_username(username):
                print(f"  skip  {username} (already exists)")
                skipped += 1
                continue
            payload_cls = (
                AdminCreate
                if role == "admin"
                else RegularUserCreate
                if role == "regular_user"
                else UserBase
            )
            repo.create(
                payload_cls(
                    username=username,
                    email=email,
                    password=encrypt_password(password),
                    role=role,
                )
            )
            print(f"  create {username} ({role})")
            created += 1

        admin_user = repo.get_by_username("admin")
        if admin_user is not None and admin_user.id is not None:
            admin_profile = session.get(
                CampusVolunteerismCentreAdmin,
                admin_user.id,
            )
            if admin_profile is None:
                session.add(
                    CampusVolunteerismCentreAdmin(
                        admin_id=admin_user.id,
                        contact_email=str(admin_user.email),
                    )
                )

        bob = repo.get_by_username("bob")
        if bob is not None and bob.id is not None:
            bob_student = session.get(Student, bob.id)
            if bob_student is not None and bob_student.credits == 0:
                redemption_statement = select(Redemption).where(
                    Redemption.student_id == bob.id
                )
                if session.exec(redemption_statement).first() is None:
                    bob_student.credits = 500
                    session.add(bob_student)
                    bob_credits_initialized = True

        organization_ids: dict[str, int] = {}
        for organization_data in organization_seeds:
            statement = select(VolunteerOrganization).where(
                VolunteerOrganization.organization_name
                == organization_data["organization_name"]
            )
            organization = session.exec(statement).one_or_none()
            if organization is None:
                organization = VolunteerOrganization(**organization_data)
                session.add(organization)
                session.flush()
                organizations_created += 1
                print(f"  create organization: {organization.organization_name}")
            else:
                organizations_skipped += 1
                print(f"  skip organization: {organization.organization_name} (already exists)")
            if organization.volunteer_organization_id is None:
                raise RuntimeError(
                    f"Could not assign an ID to {organization.organization_name}."
                )
            organization_user = repo.get_by_username(
                organization_accounts[organization.organization_name]
            )
            if organization_user is None or organization_user.id is None:
                raise RuntimeError(
                    f"Missing organization account for {organization.organization_name}."
                )
            if organization_user.role != "volunteer_organization":
                raise RuntimeError(
                    f"Account {organization_user.username} is not an organization account."
                )
            if organization.user_id not in (None, organization_user.id):
                raise RuntimeError(
                    f"{organization.organization_name} is linked to a different account."
                )
            organization.user_id = organization_user.id
            session.add(organization)
            organization_ids[organization.organization_name] = organization.volunteer_organization_id

        for index, project_data in enumerate(project_seeds):
            project_name = project_data["project_name"]
            organization_name = project_data["organization"]
            statement = select(VolunteerProject).where(
                VolunteerProject.project_name == project_name,
                VolunteerProject.volunteer_organization_id
                == organization_ids[organization_name],
            )
            project = session.exec(statement).one_or_none()
            if project is not None:
                if project_data.get("hours_demo") and project.start_date >= today:
                    project.start_date = today - timedelta(days=14)
                    session.add(project)
                    projects_updated += 1
                    print(f"  update project: {project_name} (hours demo date)")
                if (
                    project_data.get("hours_demo")
                    and (project.end_date is None or project.end_date <= today)
                ):
                    project.end_date = today + timedelta(days=180)
                    session.add(project)
                    projects_updated += 1
                    print(f"  update project: {project_name} (hours demo end date)")
                if (
                    project_data.get("full_for_demo")
                    and project.current_volunteers != project.max_volunteers
                ):
                    project.current_volunteers = project.max_volunteers
                    projects_updated += 1
                    print(f"  update project: {project_name} (full capacity demo)")
                projects_skipped += 1
                print(f"  skip project: {project_name} (already exists)")
                continue

            starts_at = (
                today - timedelta(days=14)
                if project_data.get("hours_demo")
                else today + timedelta(days=7 + index * 2)
            )
            max_volunteers = 12 + (index % 4) * 3
            project = VolunteerProject(
                volunteer_organization_id=organization_ids[organization_name],
                project_name=project_name,
                primary_category=project_data["primary_category"],
                secondary_category=project_data["secondary_category"],
                current_volunteers=(
                    max_volunteers if project_data.get("full_for_demo") else 0
                ),
                max_volunteers=max_volunteers,
                application_requirements="No previous experience required.",
                commitment_type="weekly",
                estimated_hours_per_session=project_data[
                    "estimated_hours_per_session"
                ],
                availability=project_data["availability"],
                start_date=starts_at,
                end_date=starts_at + timedelta(days=180),
                description=project_data["description"],
                location=project_data["location"],
                status=VolunteerProjectStatus.APPROVED,
            )
            session.add(project)
            projects_created += 1
            print(f"  create project: {project_name} ({organization_name})")

        bob = repo.get_by_username("bob")
        if bob is None or bob.id is None:
            raise RuntimeError("Missing demo student account bob.")
        if bob.role != "regular_user":
            raise RuntimeError("The demo account bob is not a student account.")
        bob_student = session.get(Student, bob.id)
        if bob_student is None:
            bob_student = Student(
                student_id=bob.id,
                contact_email=str(bob.email),
            )
            session.add(bob_student)
            session.flush()

        hours_demo_data = next(
            project_data
            for project_data in project_seeds
            if project_data.get("hours_demo")
        )
        hours_demo_statement = select(VolunteerProject).where(
            VolunteerProject.project_name == hours_demo_data["project_name"],
            VolunteerProject.volunteer_organization_id
            == organization_ids[hours_demo_data["organization"]],
        )
        hours_demo_project = session.exec(hours_demo_statement).one_or_none()
        if (
            hours_demo_project is None
            or hours_demo_project.volunteer_project_id is None
        ):
            raise RuntimeError("Could not find the seeded hours demo project.")

        record_statement = select(StudentVolunteerRecord).where(
            StudentVolunteerRecord.student_id == bob.id,
            StudentVolunteerRecord.volunteer_project_id
            == hours_demo_project.volunteer_project_id,
        )
        if session.exec(record_statement).first() is not None:
            volunteer_records_skipped += 1
            print("  skip Bob's hours demo volunteer record (already exists)")
        else:
            session.add(
                StudentVolunteerRecord(
                    student_id=bob.id,
                    volunteer_project_id=hours_demo_project.volunteer_project_id,
                    organization_name=hours_demo_data["organization"],
                    start_date=hours_demo_project.start_date,
                    end_date=hours_demo_project.end_date,
                    participation_status=ParticipationStatus.ACTIVE,
                )
            )
            hours_demo_project.current_volunteers = min(
                hours_demo_project.current_volunteers + 1,
                hours_demo_project.max_volunteers,
            )
            session.add(hours_demo_project)
            volunteer_records_created += 1

        applicant_students: list[tuple[Student, dict[str, str]]] = []
        for applicant_data in demo_applicants:
            applicant_user = repo.get_by_username(applicant_data["username"])
            if applicant_user is None or applicant_user.id is None:
                raise RuntimeError(
                    f"Missing demo applicant account {applicant_data['username']}."
                )
            if applicant_user.role != "regular_user":
                raise RuntimeError(
                    f"Account {applicant_user.username} is not a student account."
                )
            applicant_student = session.get(Student, applicant_user.id)
            if applicant_student is None:
                applicant_student = Student(
                    student_id=applicant_user.id,
                    contact_email=str(applicant_user.email),
                )
            if not applicant_student.first_name:
                applicant_student.first_name = applicant_data["first_name"]
            if not applicant_student.last_name:
                applicant_student.last_name = applicant_data["last_name"]
            session.add(applicant_student)
            applicant_students.append((applicant_student, applicant_data))

        session.flush()
        application_projects: list[VolunteerProject] = []
        selected_projects_per_organization: dict[str, int] = {}
        for project_data in project_seeds:
            organization_name = project_data["organization"]
            selected_count = selected_projects_per_organization.get(
                organization_name, 0
            )
            if project_data.get("full_for_demo") or selected_count >= 2:
                continue
            statement = select(VolunteerProject).where(
                VolunteerProject.project_name == project_data["project_name"],
                VolunteerProject.volunteer_organization_id
                == organization_ids[organization_name],
            )
            project = session.exec(statement).one_or_none()
            if (
                project is None
                or project.status != VolunteerProjectStatus.APPROVED
                or project.current_volunteers >= project.max_volunteers
            ):
                continue
            application_projects.append(project)
            selected_projects_per_organization[organization_name] = selected_count + 1

        seed_time = datetime.now(timezone.utc)
        for project_index, project in enumerate(application_projects):
            if project.volunteer_project_id is None:
                raise RuntimeError(
                    f"Could not assign an ID to {project.project_name}."
                )
            for applicant_index, (student, applicant_data) in enumerate(
                applicant_students
            ):
                statement = select(StudentVolunteerApplication).where(
                    StudentVolunteerApplication.student_id == student.student_id,
                    StudentVolunteerApplication.volunteer_project_id
                    == project.volunteer_project_id,
                )
                if session.exec(statement).first() is not None:
                    applications_skipped += 1
                    continue
                session.add(
                    StudentVolunteerApplication(
                        student_id=student.student_id,
                        volunteer_project_id=project.volunteer_project_id,
                        application_status=StudentVolunteerApplicationStatus.PENDING,
                        creation_date=seed_time
                        - timedelta(
                            days=project_index * len(applicant_students)
                            + applicant_index
                        ),
                        student_motivation=applicant_data["motivation"],
                    )
                )
                applications_created += 1

        for name, description, category, points_cost, quantity_available in reward_seeds:
            statement = select(RewardListing).where(RewardListing.name == name)
            reward = session.exec(statement).one_or_none()
            if reward is not None:
                rewards_skipped += 1
                print(f"  skip reward: {name} (already exists)")
                continue

            session.add(
                RewardListing(
                    name=name,
                    description=description,
                    primary_category=category,
                    points_cost=points_cost,
                    quantity_available=quantity_available,
                    reward_image_url="/static/img/reward-placeholder.svg",
                )
            )
            rewards_created += 1
            print(f"  create reward: {name}")

        session.commit()

    print(
        "Seed done — "
        f"users created {created}, skipped {skipped}; "
        f"organizations created {organizations_created}, skipped {organizations_skipped}; "
        f"projects created {projects_created}, skipped {projects_skipped}, "
        f"updated {projects_updated}; applications created {applications_created}, "
        f"skipped {applications_skipped}; volunteer records created "
        f"{volunteer_records_created}, skipped {volunteer_records_skipped}; "
        f"rewards created {rewards_created}, "
        f"skipped {rewards_skipped}."
    )
    if bob_credits_initialized:
        print("Initialized bob's student profile with 500 demo credits.")
    print(
        "Login with bob/bobpass, applicant1/applicantpass, "
        "applicant2/applicantpass, applicant3/applicantpass, admin/adminpass, "
        "or an organization username with orgpass."
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Start the FastAPI app with Uvicorn."""
    import uvicorn

    from app.config import get_settings

    settings = get_settings()
    bind_host = args.host or settings.app_host
    bind_port = args.port or settings.app_port
    if args.reload is None:
        use_reload = settings.env.lower() != "production"
    else:
        use_reload = args.reload
    print(f"Starting FastStarter on http://{bind_host}:{bind_port} (reload={use_reload})")
    uvicorn.run(
        "app.main:app",
        host=bind_host,
        port=bind_port,
        reload=use_reload,
    )


def cmd_report(args: argparse.Namespace) -> None:
    """Build the submission package: merge judge, package transcripts, write PDF.

    Guide must (1) write ``docs/judge.md`` and (2) pull every Guide chat into
    ``docs/transcripts/*.md`` before this command. Report only packages those files.
    """
    from app.report_pdf import export_report
    from app.skill_integrity import format_report, verify

    result = export_report(
        name=args.name,
        student_id=args.student_id,
        source=None if args.src is None else Path(args.src),
        output=None if args.output is None else Path(args.output),
    )
    print()
    print("Report package:")
    print(
        f"  Judge:       {'merged docs/judge.md' if result.judge_merged else 'MISSING - Guide must run student-judge first'}"
    )
    print(
        f"  Transcripts: {result.transcript_count} chat(s) in docs/transcripts/"
        + (
            ""
            if result.transcript_count
            else " (EMPTY - Guide must pull Copilot/Cursor/OpenCode chats first)"
        )
    )
    if result.transcript_zip:
        print(f"  Zip:         {result.transcript_zip.as_posix()}")
    print(f"  PDF:         {result.pdf_path.as_posix()}")
    print(format_report(verify()))


def cmd_transcripts(args: argparse.Namespace) -> None:
    """Package agent-written markdown under docs/transcripts/ (+ zip)."""
    from app.transcript_export import package_transcripts

    result = package_transcripts(make_zip=not args.no_zip)
    if result.found == 0:
        print(
            "Warning: no chat markdown in docs/transcripts/. "
            "The Guide agent must pull every Guide chat for this project "
            "(Copilot Agent, Cursor, or OpenCode) into docs/transcripts/<slug>.md first."
        )
        raise SystemExit(2)
    print(f"Submission package ready: {result.out_dir}")
    if result.zip_path:
        print(f"Zip for submission: {result.zip_path}")


def cmd_skills_verify(args: argparse.Namespace) -> None:
    """Check course skill files against .agents/skills.lock.json."""
    from app.skill_integrity import format_report, verify

    result = verify()
    print(format_report(result))
    if not result.ok:
        raise SystemExit(1)


def cmd_usecase(args: argparse.Namespace) -> None:
    """Render docs/diagrams/use-case.json to a UML use-case PNG."""
    from app.usecase_diagram import render_usecase_png

    dest = render_usecase_png(
        spec_path=None if args.spec is None else Path(args.spec),
        output=None if args.output is None else Path(args.output),
    )
    print(f"Wrote {dest}")


def cmd_skills_lock(args: argparse.Namespace) -> None:
    """Rewrite the skill lockfile (course authors only)."""
    from app.skill_integrity import write_lock

    dest = write_lock()
    print(f"Wrote {dest}")


def cmd_users(args: argparse.Namespace) -> None:
    """List users currently in the database."""
    from sqlmodel import select

    from app.database import get_cli_session
    from app.models.user import User

    _ensure_models_loaded()
    with get_cli_session() as session:
        users = session.exec(select(User)).all()
        if not users:
            print("No users found. Run: python manage.py init")
            return
        for user in users:
            print(
                f"  id={user.id}  username={user.username}  "
                f"role={user.role}  email={user.email}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python manage.py",
        description="FastStarter Python CLI — init database, seed demo data, run the app.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init",
        help=(
            "Create DB tables and seed demo users, volunteer organizations, "
            "approved projects, and sample applications (drops existing tables by default)"
        ),
    )
    p_init.add_argument(
        "--no-drop",
        dest="drop",
        action="store_false",
        help="Create tables without dropping existing ones",
    )
    p_init.add_argument(
        "--no-seed",
        dest="seed",
        action="store_false",
        help="Skip demo user seed after creating tables",
    )
    p_init.set_defaults(drop=True, seed=True, func=cmd_init)

    p_seed = sub.add_parser(
        "seed",
        help=(
            "Idempotently add demo users, volunteer organizations, "
            "approved projects, and sample applications"
        ),
    )
    p_seed.set_defaults(func=cmd_seed)

    p_run = sub.add_parser("run", help="Start the web app (uvicorn)")
    p_run.add_argument("--host", default=None, help="Bind host")
    p_run.add_argument("--port", type=int, default=None, help="Bind port")
    reload_group = p_run.add_mutually_exclusive_group()
    reload_group.add_argument(
        "--reload", dest="reload", action="store_true", default=None, help="Enable auto-reload"
    )
    reload_group.add_argument(
        "--no-reload", dest="reload", action="store_false", help="Disable auto-reload"
    )
    p_run.set_defaults(func=cmd_run, reload=None)

    p_users = sub.add_parser("users", help="List users in the database")
    p_users.set_defaults(func=cmd_users)

    p_report = sub.add_parser(
        "report",
        help=(
            "Build submission package: merge docs/judge.md, package docs/transcripts/, "
            "write docs/report.pdf (Guide pulls chats + runs student-judge first)"
        ),
    )
    p_report.add_argument("--name", required=True, help="Student name (printed on the PDF cover)")
    p_report.add_argument("--id", dest="student_id", required=True, help="Student ID (PDF only)")
    p_report.add_argument("--src", default=None, help="Markdown path (default: docs/report.md)")
    p_report.add_argument("--output", default=None, help="PDF path (default: docs/report.pdf)")
    p_report.set_defaults(func=cmd_report)

    p_transcripts = sub.add_parser(
        "transcripts",
        help="Package agent-written docs/transcripts/*.md into INDEX + zip (no IDE scrape)",
    )
    p_transcripts.add_argument(
        "--no-zip",
        action="store_true",
        help="Skip writing docs/transcripts.zip",
    )
    p_transcripts.set_defaults(func=cmd_transcripts)

    p_usecase = sub.add_parser(
        "usecase",
        help="Render docs/diagrams/use-case.json to a UML use-case PNG",
    )
    p_usecase.add_argument("--spec", default=None, help="JSON spec (default: docs/diagrams/use-case.json)")
    p_usecase.add_argument("--output", default=None, help="PNG path (default: docs/diagrams/use-case.png)")
    p_usecase.set_defaults(func=cmd_usecase)

    p_skills_verify = sub.add_parser(
        "skills-verify",
        help="Check course skills against .agents/skills.lock.json",
    )
    p_skills_verify.set_defaults(func=cmd_skills_verify)

    p_skills_lock = sub.add_parser(
        "skills-lock",
        help="Rewrite .agents/skills.lock.json (course authors; needs FASTSTARTER_SKILLS_LOCK=1)",
    )
    p_skills_lock.set_defaults(func=cmd_skills_lock)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
