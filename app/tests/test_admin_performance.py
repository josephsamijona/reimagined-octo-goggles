from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from app import models
from app.admin.services import AssignmentAdmin


class AssignmentAdminPerformanceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        with patch("app.signals._safe_celery_delay"):
            cls.admin_user = User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="password",
                role=models.User.Roles.ADMIN,
            )
            cls.client_user = User.objects.create_user(
                username="client",
                email="client@example.com",
                password="password",
                role=models.User.Roles.CLIENT,
            )
            cls.interpreter_user = User.objects.create_user(
                username="interpreter",
                email="interpreter@example.com",
                password="password",
                first_name="Jane",
                last_name="Doe",
                role=models.User.Roles.INTERPRETER,
            )
        cls.source_language = models.Language.objects.create(name="Spanish", code="es")
        cls.target_language = models.Language.objects.create(name="English", code="en")
        cls.service_type = models.ServiceType.objects.create(
            name="Medical",
            description="Medical interpretation",
            base_rate=Decimal("100.00"),
            minimum_hours=2,
            cancellation_policy="Standard",
            requires_certification=False,
            active=True,
        )
        cls.client_profile = models.Client.objects.create(
            user=cls.client_user,
            company_name="Acme Clinic",
            address="1 Main St",
            city="Boston",
            state="MA",
            zip_code="02108",
            preferred_language=cls.target_language,
            active=True,
        )
        cls.interpreter = models.Interpreter.objects.create(
            user=cls.interpreter_user,
            address="10 Park St",
            city="Boston",
            state="MA",
            zip_code="02108",
            active=True,
        )

    def setUp(self):
        self.client.force_login(self.admin_user)
        session = self.client.session
        session["admin_mfa_verified"] = True
        session.save()

    def _create_assignments(self, count, offset=0):
        start = timezone.now() + timedelta(days=1)
        assignments = []
        for index in range(offset, offset + count):
            assignments.append(
                models.Assignment(
                    client=self.client_profile,
                    interpreter=self.interpreter,
                    service_type=self.service_type,
                    source_language=self.source_language,
                    target_language=self.target_language,
                    start_time=start + timedelta(hours=index),
                    end_time=start + timedelta(hours=index + 2),
                    location="1 Main St",
                    city="Boston",
                    state="MA",
                    zip_code="02108",
                    status=models.Assignment.Status.PENDING,
                    interpreter_rate=Decimal("50.00"),
                    minimum_hours=2,
                )
            )
        models.Assignment.objects.bulk_create(assignments)

    def _get_changelist_query_count(self):
        url = reverse("admin:app_assignment_changelist")
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(captured)

    def test_assignment_changelist_query_count_is_bounded(self):
        self._create_assignments(1)
        baseline_queries = self._get_changelist_query_count()

        self._create_assignments(60, offset=1)
        larger_page_queries = self._get_changelist_query_count()

        self.assertLessEqual(larger_page_queries, baseline_queries + 5)

    def test_assignment_display_methods_are_null_safe(self):
        admin = AssignmentAdmin(models.Assignment, AdminSite())
        assignment = models.Assignment(
            service_type=self.service_type,
            source_language=self.source_language,
            target_language=self.target_language,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
            location="1 Main St",
            city="Boston",
            state="MA",
            zip_code="02108",
            status=models.Assignment.Status.PENDING,
            interpreter_rate=Decimal("50.00"),
            minimum_hours=2,
        )

        self.assertEqual(admin.get_interpreter(assignment), "-")
        self.assertEqual(admin.get_client_display(assignment), "Unspecified Client")
        self.assertEqual(admin.get_languages(assignment), "Spanish -> English")
