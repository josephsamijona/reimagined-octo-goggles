# app/migrations/0004_create_assignment_notification.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_add_interpreter_profile_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='app.assignment')),
                ('interpreter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignment_notifications', to='app.interpreter')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='assignmentnotification',
            index=models.Index(fields=['interpreter', 'is_read'], name='app_assignm_interpr_idx'),
        ),
        migrations.AddIndex(
            model_name='assignmentnotification',
            index=models.Index(fields=['created_at'], name='app_assignm_created_idx'),
        ),
    ]