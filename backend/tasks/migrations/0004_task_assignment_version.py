from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0003_task_correction")]

    operations = [
        migrations.AddField(
            model_name="task",
            name="assignment_version",
            field=models.PositiveBigIntegerField(db_default=1, default=1),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=models.Q(assignment_version__gt=0),
                name="task_assignment_version_positive",
            ),
        ),
    ]
