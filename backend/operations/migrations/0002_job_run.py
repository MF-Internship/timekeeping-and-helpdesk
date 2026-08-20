from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("operations", "0001_throttle_cache_table")]

    operations = [
        migrations.CreateModel(
            name="JobRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_name", models.CharField(max_length=32)),
                ("started_at", models.DateTimeField()),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(db_default="RUNNING", default="RUNNING", max_length=32)),
                ("scanned_count", models.PositiveIntegerField(db_default=0, default=0)),
                ("changed_count", models.PositiveIntegerField(db_default=0, default=0)),
                ("anomaly_count", models.PositiveIntegerField(db_default=0, default=0)),
                ("error_code", models.CharField(blank=True, max_length=32, null=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["job_name", "started_at", "id"], name="job_run_started_idx"),
                    models.Index(fields=["job_name", "status", "finished_at", "id"], name="job_run_status_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("job_name__in", ["MISSING_CHECK_OUT"])), name="job_run_name_valid"),
                    models.CheckConstraint(condition=models.Q(("status__in", ["RUNNING", "SUCCEEDED", "PARTIAL_FAILED", "FAILED"])), name="job_run_status_valid"),
                    models.CheckConstraint(condition=models.Q(("error_code__isnull", True), ("error_code__in", ["SESSION_PROCESSING_FAILED", "RUN_ABORTED"]), _connector="OR"), name="job_run_error_valid"),
                    models.CheckConstraint(condition=models.Q(models.Q(("error_code__isnull", True), ("finished_at__isnull", True), ("status", "RUNNING")), models.Q(("error_code__isnull", True), ("finished_at__isnull", False), ("status", "SUCCEEDED")), models.Q(("error_code__isnull", False), ("finished_at__isnull", False), ("status__in", ["PARTIAL_FAILED", "FAILED"])), _connector="OR"), name="job_run_terminal_shape"),
                    models.CheckConstraint(condition=models.Q(("finished_at__isnull", True), ("finished_at__gte", models.F("started_at")), _connector="OR"), name="job_run_finish_order"),
                    models.CheckConstraint(condition=models.Q(("changed_count", models.F("anomaly_count")), ("scanned_count__gte", models.F("changed_count"))), name="job_run_counts_valid"),
                    models.CheckConstraint(condition=models.Q(("status", "RUNNING"), ("status", "SUCCEEDED"), models.Q(("changed_count__gt", 0), ("error_code", "SESSION_PROCESSING_FAILED"), ("status", "PARTIAL_FAILED")), models.Q(("changed_count", 0), ("error_code", "SESSION_PROCESSING_FAILED"), ("status", "FAILED")), models.Q(("changed_count", 0), ("error_code", "RUN_ABORTED"), ("status", "FAILED")), _connector="OR"), name="job_run_failure_shape"),
                ],
            },
        )
    ]
