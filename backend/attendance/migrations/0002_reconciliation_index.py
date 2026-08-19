from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("attendance", "0001_initial")]
    operations = [
        migrations.AddIndex(
            model_name="attendancesession",
            index=models.Index(
                fields=["work_date", "id"],
                condition=models.Q(check_out__isnull=True, closed_by_job=False),
                name="attendance_reconcile_idx",
            ),
        )
    ]
