import re
import time
from collections import Counter

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse


class Command(BaseCommand):
    help = "Profile SQL query count and response time for a Django admin changelist."

    def add_arguments(self, parser):
        parser.add_argument("model", help="Model label in app_label.model_name format.")
        parser.add_argument("--username", help="Superuser/staff username to authenticate as.")
        parser.add_argument("--repeat", type=int, default=1, help="Number of requests to run.")

    def handle(self, *args, **options):
        model_label = options["model"]
        repeat = max(options["repeat"], 1)
        model = self._get_model(model_label)
        user = self._get_admin_user(options.get("username"))
        url = reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
        )

        client = Client()
        client.force_login(user)
        session = client.session
        session["admin_mfa_verified"] = True
        session.save()

        for run_number in range(1, repeat + 1):
            with override_settings(DEBUG=True):
                with CaptureQueriesContext(connection) as captured:
                    started = time.perf_counter()
                    response = client.get(url)
                    elapsed_ms = (time.perf_counter() - started) * 1000

            self.stdout.write(
                f"run={run_number} status={response.status_code} "
                f"elapsed_ms={elapsed_ms:.1f} queries={len(captured)}"
            )
            self._print_duplicate_queries(captured)

    def _get_model(self, model_label):
        try:
            app_label, model_name = model_label.split(".", 1)
        except ValueError as exc:
            raise CommandError("Model must be in app_label.model_name format.") from exc

        model = apps.get_model(app_label, model_name)
        if model is None:
            raise CommandError(f"Unknown model: {model_label}")
        return model

    def _get_admin_user(self, username):
        User = get_user_model()
        queryset = User.objects.filter(is_active=True, is_staff=True)
        if username:
            queryset = queryset.filter(username=username)
        else:
            queryset = queryset.filter(is_superuser=True)

        user = queryset.order_by("id").first()
        if not user:
            raise CommandError("No active staff/superuser account found for profiling.")
        return user

    def _print_duplicate_queries(self, captured):
        fingerprints = Counter(self._fingerprint(query["sql"]) for query in captured)
        duplicates = [(sql, count) for sql, count in fingerprints.most_common() if count > 1]
        if not duplicates:
            self.stdout.write("duplicates=0")
            return

        self.stdout.write(f"duplicates={len(duplicates)}")
        for sql, count in duplicates[:10]:
            self.stdout.write(f"  x{count} {sql[:240]}")

    @staticmethod
    def _fingerprint(sql):
        sql = re.sub(r"'(?:''|[^'])*'", "'?'", sql)
        sql = re.sub(r"\b\d+\b", "?", sql)
        return re.sub(r"\s+", " ", sql).strip()
