from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0002_task_evidence")]

    operations = [
        migrations.AddField(
            model_name="task",
            name="expected_location_text",
            field=models.TextField(blank=True, db_default="", default=""),
        ),
        migrations.AddField(
            model_name="task",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
