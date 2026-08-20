import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_notification"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="PushSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("endpoint_hash", models.CharField(max_length=64)),
                ("encrypted_subscription", models.BinaryField()),
                ("user_agent_family", models.CharField(max_length=32)),
                ("is_active", models.BooleanField(db_default=True, default=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="push_subscriptions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [models.Index(fields=["user", "is_active", "id"], name="push_sub_owner_active_idx"), models.Index(fields=["endpoint_hash"], name="push_sub_endpoint_hash_idx")],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("is_active", True)), fields=("endpoint_hash",), name="push_subscription_active_endpoint_uniq"),
                    models.CheckConstraint(condition=models.Q(("endpoint_hash__regex", r"^[0-9a-f]{64}$")), name="push_subscription_hash_valid"),
                    models.CheckConstraint(condition=models.Q(models.Q(("is_active", True), ("revoked_at__isnull", True)), models.Q(("is_active", False), ("revoked_at__isnull", False)), _connector="OR"), name="push_subscription_state_valid"),
                ],
            },
        ),
        migrations.CreateModel(
            name="PushDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("state", models.CharField(choices=[("PENDING", "PENDING"), ("LEASED", "LEASED"), ("DELIVERED", "DELIVERED"), ("SUPPRESSED", "SUPPRESSED"), ("EXPIRED", "EXPIRED")], db_default="PENDING", default="PENDING", max_length=16)),
                ("not_before", models.DateTimeField()), ("expires_at", models.DateTimeField()),
                ("collapse_key", models.CharField(max_length=32)),
                ("attempt_count", models.PositiveIntegerField(db_default=0, default=0)),
                ("next_attempt_at", models.DateTimeField()),
                ("lease_expires_at", models.DateTimeField(blank=True, null=True)),
                ("leased_by", models.CharField(blank=True, max_length=64, null=True)),
                ("attempted_at", models.DateTimeField(blank=True, null=True)),
                ("failure_code", models.CharField(blank=True, choices=[("TRANSIENT_PROVIDER_FAILURE", "TRANSIENT_PROVIDER_FAILURE"), ("SUBSCRIPTION_GONE", "SUBSCRIPTION_GONE"), ("ORIGIN_REJECTED", "ORIGIN_REJECTED"), ("CONFIGURATION_UNAVAILABLE", "CONFIGURATION_UNAVAILABLE"), ("TRANSPORT_TIMEOUT", "TRANSPORT_TIMEOUT")], max_length=40, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("notification", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="push_deliveries", to="notifications.notification")),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deliveries", to="notifications.pushsubscription")),
            ],
            options={
                "indexes": [models.Index(fields=["state", "next_attempt_at", "expires_at", "id"], name="push_delivery_due_idx"), models.Index(fields=["subscription", "state", "id"], name="push_delivery_sub_state_idx"), models.Index(fields=["notification", "state", "id"], name="push_delivery_notif_state_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("notification", "subscription"), name="push_delivery_notification_subscription_uniq"),
                    models.CheckConstraint(condition=models.Q(("state__in", ["PENDING", "LEASED", "DELIVERED", "SUPPRESSED", "EXPIRED"])), name="push_delivery_state_valid"),
                    models.CheckConstraint(condition=models.Q(("not_before__lt", models.F("expires_at"))), name="push_delivery_window_valid"),
                    models.CheckConstraint(condition=models.Q(("next_attempt_at__lte", models.F("expires_at"))), name="push_delivery_retry_time_valid"),
                    models.CheckConstraint(condition=models.Q(models.Q(("lease_expires_at__isnull", False), ("leased_by__isnull", False), ("state", "LEASED")), models.Q(models.Q(("state", "LEASED"), _negated=True), ("lease_expires_at__isnull", True), ("leased_by__isnull", True)), _connector="OR"), name="push_delivery_lease_shape_valid"),
                    models.CheckConstraint(condition=models.Q(models.Q(("state", "DELIVERED"), _negated=True), ("attempted_at__isnull", False), _connector="OR"), name="push_delivery_delivered_attempt_valid"),
                ],
            },
        ),
    ]

