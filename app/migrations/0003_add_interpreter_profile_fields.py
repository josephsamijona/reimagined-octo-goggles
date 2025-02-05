from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0002_languagee'),
    ]

    operations = [
        migrations.AddField(
            model_name='interpreter',
            name='bio',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='interpreter',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to='interpreter_profiles/'),
        ),
    ]