from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0007_alter_assignment_interpreter'),  # Remplacez par votre dernière migration
    ]

    operations = [
        # D'abord, on supprime toute contrainte existante
        migrations.RunSQL(
            sql="ALTER TABLE app_assignment MODIFY interpreter_id BIGINT NULL;",
            reverse_sql="ALTER TABLE app_assignment MODIFY interpreter_id BIGINT NOT NULL;"
        ),
        
        # Ensuite, on met à jour le champ dans Django
        migrations.AlterField(
            model_name='assignment',
            name='interpreter',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                to='app.interpreter'
            ),
        ),
    ]