import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(choices=[("TASK_ASSIGNED", "TASK_ASSIGNED"), ("TASK_UPCOMING", "TASK_UPCOMING"), ("TASK_OVERDUE", "TASK_OVERDUE"), ("ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END", "ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END"), ("MULTI_ASSIGNEE_TASK_COMPLETED", "MULTI_ASSIGNEE_TASK_COMPLETED")], max_length=64)),
                ("target_type", models.CharField(choices=[("TASK", "TASK"), ("ATTENDANCE_SESSION", "ATTENDANCE_SESSION")], max_length=32)),
                ("target_id", models.PositiveBigIntegerField()),
                ("dedupe_key", models.CharField(max_length=255, unique=True)),
                ("title", models.CharField(max_length=160)),
                ("occurred_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["recipient", "-created_at", "-id"], name="notif_owner_created_idx"),
                    models.Index(condition=models.Q(("read_at__isnull", True)), fields=["recipient", "-created_at", "-id"], name="notif_owner_unread_idx"),
                    models.Index(fields=["target_type", "target_id", "recipient"], name="notif_target_owner_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("event_type__in", ["TASK_ASSIGNED", "TASK_UPCOMING", "TASK_OVERDUE", "ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END", "MULTI_ASSIGNEE_TASK_COMPLETED"])), name="notification_event_type_valid"),
                    models.CheckConstraint(condition=models.Q(("target_type__in", ["TASK", "ATTENDANCE_SESSION"])), name="notification_target_type_valid"),
                    models.CheckConstraint(condition=models.Q(("target_id__gt", 0)), name="notification_target_id_positive"),
                    models.CheckConstraint(condition=models.Q(("dedupe_key__regex", r"^\s*$"), _negated=True), name="notification_dedupe_nonblank"),
                    models.CheckConstraint(condition=models.Q(("title__regex", r"^\s*$"), _negated=True), name="notification_title_nonblank"),
                    models.CheckConstraint(condition=models.Q(("read_at__isnull", True), ("read_at__gte", models.F("created_at")), _connector="OR"), name="notification_read_time_valid"),
                ],
            },
        )
    ]

