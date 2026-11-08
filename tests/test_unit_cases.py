import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import create_autospec

from pydantic import ValidationError

from app.models.hours_log import HoursLog
from app.models.reward import Redemption
from app.models.student import ParticipationStatus, Student
from app.models.student_application import StudentVolunteerApplication
from app.models.volunteer_project import (
    VolunteerOrganization,
    VolunteerProject,
    VolunteerProjectStatus,
)
from app.repositories.admin_review import AdminReviewRepository
from app.repositories.hours_log import HoursLogRepository
from app.repositories.reward import RewardRepository
from app.repositories.student_application import StudentApplicationRepository
from app.repositories.volunteer_project import VolunteerProjectRepository
from app.services.admin_review import AdminReviewService
from app.services.hours_log import HoursLogService
from app.services.reward import RewardService
from app.services.student_application import StudentApplicationService
from app.services.volunteer_project import (
    EndDateBeforeStartError,
    ListingHasAssociatedRecordsError,
    OrganizationListingNotFoundError,
    VolunteerProjectService,
)


class ModelValidationTests(unittest.TestCase):
    def test_negative_redemption_quantity(self):
        with self.assertRaises(ValidationError) as raised:
            Redemption.model_validate(
                {
                    "student_id": 1,
                    "reward_listing_id": 1,
                    "points_spent": 0,
                    "quantity": 0,
                }
            )

        self.assertEqual(raised.exception.errors()[0]["loc"], ("quantity",))
        self.assertEqual(
            raised.exception.errors()[0]["type"],
            "greater_than_equal",
        )

    def test_negative_verified_hours(self):
        with self.assertRaises(ValidationError) as raised:
            Student.model_validate(
                {"student_id": 1, "total_verified_hours": -5}
            )

        self.assertEqual(
            raised.exception.errors()[0]["loc"],
            ("total_verified_hours",),
        )
        self.assertEqual(
            raised.exception.errors()[0]["type"],
            "greater_than_equal",
        )

    def test_default_project_status(self):
        project = VolunteerProject(
            volunteer_organization_id=1,
            project_name="Beach Cleanup",
            start_date=date.today(),
        )

        self.assertEqual(project.status, VolunteerProjectStatus.PENDING)


class StudentApplicationServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = create_autospec(
            StudentApplicationRepository,
            instance=True,
        )
        self.service = StudentApplicationService(self.repository)

    def _approved_project(self, **overrides):
        values = {
            "status": VolunteerProjectStatus.APPROVED,
            "end_date": date.today() + timedelta(days=1),
            "current_volunteers": 1,
            "max_volunteers": 5,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_submit_application_success(self):
        student = SimpleNamespace(student_id=7)
        project = self._approved_project()
        application = StudentVolunteerApplication(
            student_id=7,
            volunteer_project_id=3,
            student_motivation="I want to help.",
        )
        self.repository.get_student_by_id.return_value = student
        self.repository.get_project_by_id.return_value = project
        self.repository.has_active_or_approved_participation.return_value = False
        self.repository.find_for_student_and_project.return_value = None
        self.repository.create.return_value = application

        result = self.service.submit_application(
            student_id=7,
            volunteer_project_id=3,
            student_motivation="I want to help.",
        )

        self.assertIsInstance(result, StudentVolunteerApplication)
        self.assertIs(result, application)
        self.repository.create.assert_called_once()

    def test_submit_application_no_student(self):
        with self.assertRaises(ValueError) as raised:
            self.service.submit_application(
                student_id=None,
                volunteer_project_id=3,
                student_motivation="I want to help.",
            )

        self.assertEqual(str(raised.exception), "Student ID is required.")

    def test_submit_duplicate_application(self):
        self.repository.get_student_by_id.return_value = SimpleNamespace(
            student_id=7
        )
        self.repository.get_project_by_id.return_value = self._approved_project()
        self.repository.has_active_or_approved_participation.return_value = False
        self.repository.find_for_student_and_project.return_value = (
            StudentVolunteerApplication(
                student_id=7,
                volunteer_project_id=3,
                student_motivation="Already applied.",
            )
        )

        with self.assertRaises(ValueError) as raised:
            self.service.submit_application(
                student_id=7,
                volunteer_project_id=3,
                student_motivation="Please consider me.",
            )

        self.assertEqual(
            str(raised.exception),
            "Student has already applied to this project.",
        )

    def test_submit_application_empty_motivation(self):
        self.repository.get_student_by_id.return_value = SimpleNamespace(
            student_id=7
        )

        with self.assertRaises(ValueError) as raised:
            self.service.submit_application(
                student_id=7,
                volunteer_project_id=3,
                student_motivation=" ",
            )

        self.assertEqual(
            str(raised.exception),
            "Student motivation is required.",
        )

    def test_submit_application_project_full(self):
        self.repository.get_student_by_id.return_value = SimpleNamespace(
            student_id=7
        )
        self.repository.get_project_by_id.return_value = self._approved_project(
            current_volunteers=5,
            max_volunteers=5,
        )

        with self.assertRaises(ValueError) as raised:
            self.service.submit_application(
                student_id=7,
                volunteer_project_id=3,
                student_motivation="Please consider me.",
            )

        self.assertEqual(
            str(raised.exception),
            "This project has reached its volunteer limit.",
        )

    def test_submit_application_project_unapproved(self):
        self.repository.get_student_by_id.return_value = SimpleNamespace(
            student_id=7
        )
        self.repository.get_project_by_id.return_value = self._approved_project(
            status=VolunteerProjectStatus.PENDING,
        )

        with self.assertRaises(ValueError) as raised:
            self.service.submit_application(
                student_id=7,
                volunteer_project_id=3,
                student_motivation="Please consider me.",
            )

        self.assertEqual(
            str(raised.exception),
            "Cannot apply to a project that is not approved.",
        )


class RewardServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = create_autospec(RewardRepository, instance=True)
        self.service = RewardService(self.repository)

    def _student(self, credits):
        return SimpleNamespace(student_id=7, credits=credits)

    def _reward(self, quantity_available=10, points_cost=100):
        return SimpleNamespace(
            reward_id=3,
            quantity_available=quantity_available,
            points_cost=points_cost,
        )

    def test_redeem_reward_success(self):
        student = self._student(credits=500)
        reward = self._reward()
        redemption = Redemption(
            student_id=7,
            reward_listing_id=3,
            points_spent=100,
            quantity=1,
        )
        self.repository.get_student.return_value = student
        self.repository.get_reward.return_value = reward
        self.repository.create_redemption.return_value = redemption

        result = self.service.redeem_reward(
            student_id=7,
            reward_id=3,
            quantity=1,
        )

        self.assertEqual(result, (redemption, reward, 400))
        self.repository.create_redemption.assert_called_once_with(
            student=student,
            reward=reward,
            quantity=1,
            points_spent=100,
        )

    def test_redeem_reward_negative_quantity(self):
        with self.assertRaises(ValueError) as raised:
            self.service.redeem_reward(
                student_id=7,
                reward_id=3,
                quantity=0,
            )

        self.assertEqual(
            str(raised.exception),
            "Quantity must be a positive integer.",
        )

    def test_redeem_reward_out_of_stock(self):
        self.repository.get_student.return_value = self._student(credits=500)
        self.repository.get_reward.return_value = self._reward(
            quantity_available=2,
        )

        with self.assertRaises(ValueError) as raised:
            self.service.redeem_reward(
                student_id=7,
                reward_id=3,
                quantity=5,
            )

        self.assertEqual(
            str(raised.exception),
            "Not enough quantity available for this reward.",
        )

    def test_redeem_reward_insufficient_credits(self):
        self.repository.get_student.return_value = self._student(credits=50)
        self.repository.get_reward.return_value = self._reward(points_cost=100)

        with self.assertRaises(ValueError) as raised:
            self.service.redeem_reward(
                student_id=7,
                reward_id=3,
                quantity=1,
            )

        self.assertEqual(
            str(raised.exception),
            "Student does not have enough credits to redeem this reward.",
        )


class HoursLogServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = create_autospec(HoursLogRepository, instance=True)
        self.service = HoursLogService(self.repository)

    def _active_record(self, **overrides):
        values = {
            "student_id": 7,
            "participation_status": ParticipationStatus.ACTIVE,
            "start_date": date.today() - timedelta(days=30),
            "end_date": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_log_hours_success(self):
        self.repository.get_volunteer_record.return_value = self._active_record()
        saved_log = HoursLog(
            volunteer_record_id=9,
            student_id=7,
            volunteer_date=date.today(),
            hours=2,
            description="Garden cleanup",
        )
        self.repository.create_hours_log.return_value = saved_log

        result = self.service.log_hours(
            student_id=7,
            volunteer_record_id=9,
            volunteer_date=date.today(),
            hours=2,
            description="Garden cleanup",
            evidence_attachment=None,
        )

        self.assertIs(result, saved_log)
        self.repository.create_hours_log.assert_called_once()
        logged_hours = self.repository.create_hours_log.call_args.args[0]
        self.assertEqual(logged_hours.hours, 2)
        self.assertEqual(logged_hours.status, "pending")

    def test_log_hours_zero_hours(self):
        with self.assertRaises(ValueError) as raised:
            self.service.log_hours(
                student_id=7,
                volunteer_record_id=9,
                volunteer_date=date.today(),
                hours=0,
                description="Garden cleanup",
                evidence_attachment=None,
            )

        self.assertEqual(str(raised.exception), "Hours must be greater than zero.")

    def test_log_hours_future_date(self):
        with self.assertRaises(ValueError) as raised:
            self.service.log_hours(
                student_id=7,
                volunteer_record_id=9,
                volunteer_date=date.today() + timedelta(days=1),
                hours=2,
                description="Garden cleanup",
                evidence_attachment=None,
            )

        self.assertEqual(
            str(raised.exception),
            "Volunteer date cannot be in the future.",
        )

    def test_log_hours_outside_date_window(self):
        self.repository.get_volunteer_record.return_value = self._active_record(
            start_date=date.today(),
        )

        with self.assertRaises(ValueError) as raised:
            self.service.log_hours(
                student_id=7,
                volunteer_record_id=9,
                volunteer_date=date.today() - timedelta(days=365),
                hours=2,
                description="Garden cleanup",
                evidence_attachment=None,
            )

        self.assertEqual(
            str(raised.exception),
            "Volunteer date must be within the volunteer record's start and end dates.",
        )


class AdminReviewServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = create_autospec(AdminReviewRepository, instance=True)
        self.service = AdminReviewService(self.repository)

    def test_approve_hours_missing_admin(self):
        with self.assertRaises(ValueError) as raised:
            self.service.approve_hours_log(log_id=1, admin_user_id=None)

        self.assertEqual(
            str(raised.exception),
            "Authenticated admin ID is missing.",
        )

    def test_approve_hours_success(self):
        self.service.approve_hours_log(log_id=1, admin_user_id=1)

        self.repository.review_hours_log.assert_called_once_with(
            log_id=1,
            admin_user_id=1,
            approve=True,
            denial_reason=None,
        )

    def test_deny_hours_reason(self):
        self.service.deny_hours_log(
            log_id=1,
            admin_user_id=1,
            denial_reason="Not enough evidence",
        )

        self.repository.review_hours_log.assert_called_once_with(
            log_id=1,
            admin_user_id=1,
            approve=False,
            denial_reason="Not enough evidence",
        )

    def test_review_project_approve(self):
        self.service.review_project(project_id=1, approve=True)

        self.repository.review_project.assert_called_once_with(
            1,
            VolunteerProjectStatus.APPROVED,
        )

    def test_get_queue_invalid_name(self):
        with self.assertRaises(ValueError) as raised:
            self.service.get_queue("invalid_queue_name")

        self.assertEqual(
            str(raised.exception),
            "Unknown admin review queue.",
        )


class VolunteerProjectServiceTests(unittest.TestCase):
    def setUp(self):
        self.repository = create_autospec(
            VolunteerProjectRepository,
            instance=True,
        )
        self.service = VolunteerProjectService(self.repository)

    def _organization(self):
        return VolunteerOrganization(
            volunteer_organization_id=4,
            user_id=8,
        )

    def _listing_fields(self, **overrides):
        values = {
            "organization_user_id": 8,
            "project_name": "Community Garden",
            "primary_category": "Environment",
            "secondary_category": "",
            "short_description": "Help in the garden",
            "description": "Work with local gardeners.",
            "location": "Campus",
            "start_date": date.today() + timedelta(days=2),
            "end_date": date.today() + timedelta(days=10),
            "commitment_type": "one_time",
            "estimated_hours_per_session": 2,
            "availability": "weekends",
            "application_requirements": "",
            "max_volunteers": 10,
            "project_cover_image": None,
        }
        values.update(overrides)
        return values

    def test_resign_student_success(self):
        self.repository.get_student_volunteer_record.return_value = (
            SimpleNamespace(
                student_id=7,
                volunteer_project_id=3,
                participation_status=ParticipationStatus.ACTIVE,
            )
        )
        self.repository.resign_student_volunteer_record.return_value = True

        result = self.service.resign_student_from_project(
            student_id=7,
            volunteer_record_id=9,
            reason="Schedule change",
        )

        self.assertIsNone(result)
        self.repository.resign_student_volunteer_record.assert_called_once_with(
            volunteer_record_id=9,
            student_id=7,
            volunteer_project_id=3,
            reason="Schedule change",
            resignation_date=date.today(),
        )

    def test_resign_student_wrong_owner(self):
        self.repository.get_student_volunteer_record.return_value = (
            SimpleNamespace(
                student_id=2,
                volunteer_project_id=3,
                participation_status=ParticipationStatus.ACTIVE,
            )
        )

        with self.assertRaises(ValueError) as raised:
            self.service.resign_student_from_project(
                student_id=1,
                volunteer_record_id=9,
                reason=None,
            )

        self.assertEqual(
            str(raised.exception),
            "You can only resign from your own projects.",
        )

    def test_create_listing_end_before_start(self):
        self.repository.get_organization_by_user_id.return_value = (
            self._organization()
        )

        with self.assertRaises(EndDateBeforeStartError) as raised:
            self.service.create_organization_listing(
                **self._listing_fields(
                    start_date=date.today() + timedelta(days=2),
                    end_date=date.today() + timedelta(days=1),
                )
            )

        self.assertEqual(
            str(raised.exception),
            "End date cannot be earlier than start date.",
        )

    def test_create_listing_past_start_date(self):
        self.repository.get_organization_by_user_id.return_value = (
            self._organization()
        )

        with self.assertRaises(ValueError) as raised:
            self.service.create_organization_listing(
                **self._listing_fields(
                    start_date=date.today() - timedelta(days=1),
                )
            )

        self.assertEqual(
            str(raised.exception),
            "Start date cannot be in the past.",
        )

    def test_delete_listing_with_records(self):
        project = SimpleNamespace(project_cover_image=None)
        self.repository.get_organization_by_user_id.return_value = (
            self._organization()
        )
        self.repository.get_organization_listing.return_value = project
        self.repository.listing_has_applications_or_volunteer_records.return_value = (
            True
        )

        with self.assertRaises(ListingHasAssociatedRecordsError) as raised:
            self.service.delete_organization_listing(
                organization_user_id=8,
                volunteer_project_id=3,
            )

        self.assertEqual(
            str(raised.exception),
            "This listing cannot be deleted because it has applications or volunteer records.",
        )

    def test_delete_listing_not_found(self):
        self.repository.get_organization_by_user_id.return_value = (
            self._organization()
        )
        self.repository.get_organization_listing.return_value = None

        with self.assertRaises(OrganizationListingNotFoundError) as raised:
            self.service.delete_organization_listing(
                organization_user_id=8,
                volunteer_project_id=3,
            )

        self.assertEqual(str(raised.exception), "Listing not found.")


if __name__ == "__main__":
    unittest.main()
