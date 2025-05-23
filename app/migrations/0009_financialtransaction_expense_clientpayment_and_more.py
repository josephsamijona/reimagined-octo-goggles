# Generated by Django 5.1.5 on 2025-02-11 00:59

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0008_alter_assignment_interpreter"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinancialTransaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("transaction_id", models.UUIDField(default=uuid.uuid4, unique=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("INCOME", "Income"),
                            ("EXPENSE", "Expense"),
                            ("INTERNAL", "Internal Transfer"),
                        ],
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("description", models.TextField()),
                ("date", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "expense_type",
                    models.CharField(
                        choices=[
                            ("OPERATIONAL", "Operational"),
                            ("ADMINISTRATIVE", "Administrative"),
                            ("MARKETING", "Marketing"),
                            ("SALARY", "Salary"),
                            ("TAX", "Tax"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("description", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("APPROVED", "Approved"),
                            ("PAID", "Paid"),
                            ("REJECTED", "Rejected"),
                        ],
                        max_length=20,
                    ),
                ),
                ("date_incurred", models.DateTimeField()),
                ("date_paid", models.DateTimeField(blank=True, null=True)),
                (
                    "receipt",
                    models.FileField(
                        blank=True, null=True, upload_to="expense_receipts/"
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "transaction",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="app.financialtransaction",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ClientPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "tax_amount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("CREDIT_CARD", "Credit Card"),
                            ("DEBIT_CARD", "Debit Card"),
                            ("BANK_TRANSFER", "Bank Transfer"),
                            ("ACH", "ACH"),
                            ("CHECK", "Check"),
                            ("CASH", "Cash"),
                            ("ZELLE", "Zelle"),
                            ("VENMO", "Venmo"),
                            ("CASH_APP", "Cash App"),
                            ("PAYPAL", "PayPal"),
                            ("APPLE_PAY", "Apple Pay"),
                            ("GOOGLE_PAY", "Google Pay"),
                            ("SAMSUNG_PAY", "Samsung Pay"),
                            ("WESTERN_UNION", "Western Union"),
                            ("MONEY_GRAM", "MoneyGram"),
                            ("TAPTP_SEND", "Tap Tap Send"),
                            ("REMITLY", "Remitly"),
                            ("WORLDREMIT", "WorldRemit"),
                            ("XOOM", "Xoom"),
                            ("WISE", "Wise (TransferWise)"),
                            ("STRIPE", "Stripe"),
                            ("SQUARE", "Square"),
                            ("CRYPTO_BTC", "Bitcoin"),
                            ("CRYPTO_ETH", "Ethereum"),
                            ("CRYPTO_USDT", "USDT"),
                            ("OTHER", "Other"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                            ("REFUNDED", "Refunded"),
                            ("CANCELLED", "Cancelled"),
                            ("DISPUTED", "Disputed"),
                        ],
                        max_length=20,
                    ),
                ),
                ("payment_date", models.DateTimeField(auto_now_add=True)),
                ("due_date", models.DateTimeField(blank=True, null=True)),
                ("completed_date", models.DateTimeField(blank=True, null=True)),
                ("invoice_number", models.CharField(max_length=50, unique=True)),
                (
                    "payment_proof",
                    models.FileField(
                        blank=True, null=True, upload_to="payment_proofs/"
                    ),
                ),
                (
                    "external_reference",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="app.assignment",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="app.client"
                    ),
                ),
                (
                    "quote",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="app.quote",
                    ),
                ),
                (
                    "transaction",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="app.financialtransaction",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InterpreterPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("CREDIT_CARD", "Credit Card"),
                            ("DEBIT_CARD", "Debit Card"),
                            ("BANK_TRANSFER", "Bank Transfer"),
                            ("ACH", "ACH"),
                            ("CHECK", "Check"),
                            ("CASH", "Cash"),
                            ("ZELLE", "Zelle"),
                            ("VENMO", "Venmo"),
                            ("CASH_APP", "Cash App"),
                            ("PAYPAL", "PayPal"),
                            ("APPLE_PAY", "Apple Pay"),
                            ("GOOGLE_PAY", "Google Pay"),
                            ("SAMSUNG_PAY", "Samsung Pay"),
                            ("WESTERN_UNION", "Western Union"),
                            ("MONEY_GRAM", "MoneyGram"),
                            ("TAPTP_SEND", "Tap Tap Send"),
                            ("REMITLY", "Remitly"),
                            ("WORLDREMIT", "WorldRemit"),
                            ("XOOM", "Xoom"),
                            ("WISE", "Wise (TransferWise)"),
                            ("STRIPE", "Stripe"),
                            ("SQUARE", "Square"),
                            ("CRYPTO_BTC", "Bitcoin"),
                            ("CRYPTO_ETH", "Ethereum"),
                            ("CRYPTO_USDT", "USDT"),
                            ("OTHER", "Other"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        max_length=20,
                    ),
                ),
                ("scheduled_date", models.DateTimeField()),
                ("processed_date", models.DateTimeField(blank=True, null=True)),
                ("reference_number", models.CharField(max_length=50, unique=True)),
                (
                    "payment_proof",
                    models.FileField(
                        blank=True, null=True, upload_to="interpreter_payment_proofs/"
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="app.assignment",
                    ),
                ),
                (
                    "interpreter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="app.interpreter",
                    ),
                ),
                (
                    "transaction",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="app.financialtransaction",
                    ),
                ),
            ],
        ),
    ]
