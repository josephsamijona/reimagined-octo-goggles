# Generated by Django 5.1.5 on 2025-02-13 20:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0009_financialtransaction_expense_clientpayment_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayrollDocument",
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
                ("company_logo", models.ImageField(upload_to="company_logos/")),
                ("company_address", models.CharField(max_length=255)),
                ("company_phone", models.CharField(max_length=20)),
                ("company_email", models.EmailField(max_length=254)),
                ("interpreter_name", models.CharField(max_length=100)),
                ("interpreter_address", models.CharField(max_length=255)),
                ("interpreter_phone", models.CharField(max_length=20)),
                ("interpreter_email", models.EmailField(max_length=254)),
                ("document_number", models.CharField(max_length=50, unique=True)),
                ("document_date", models.DateField()),
                ("bank_name", models.CharField(max_length=100)),
                ("account_number", models.CharField(max_length=50)),
                ("routing_number", models.CharField(max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Service",
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
                ("date", models.DateField()),
                ("client", models.CharField(max_length=100)),
                ("source_language", models.CharField(max_length=50)),
                ("target_language", models.CharField(max_length=50)),
                ("duration", models.DecimalField(decimal_places=2, max_digits=5)),
                ("rate", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "payroll",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="services",
                        to="app.payrolldocument",
                    ),
                ),
            ],
        ),
    ]
