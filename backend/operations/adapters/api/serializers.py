from rest_framework import serializers

from operations.application.job_health import ScopedJobHealth


class JobRunSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    job_name = serializers.ChoiceField(choices=["MISSING_CHECK_OUT"])
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    status = serializers.ChoiceField(choices=["RUNNING", "SUCCEEDED", "PARTIAL_FAILED", "FAILED"])
    scanned_count = serializers.IntegerField(min_value=0)
    changed_count = serializers.IntegerField(min_value=0)
    anomaly_count = serializers.IntegerField(min_value=0)
    error_code = serializers.ChoiceField(
        choices=["SESSION_PROCESSING_FAILED", "RUN_ABORTED"], allow_null=True
    )


class EvidenceSerializer(serializers.Serializer):
    job_closed_session_count = serializers.IntegerField(min_value=0)
    missing_checkout_anomaly_count = serializers.IntegerField(min_value=0)
    job_closed_without_anomaly_count = serializers.IntegerField(min_value=0)
    anomaly_without_job_closed_count = serializers.IntegerField(min_value=0)


class ReasonsSerializer(serializers.Serializer):
    no_run_history = serializers.BooleanField()
    missing_timely_success = serializers.BooleanField()
    unfinished_run = serializers.BooleanField()
    stale_running = serializers.BooleanField()
    latest_terminal_failed = serializers.BooleanField()
    run_count_mismatch = serializers.BooleanField()
    persisted_evidence_mismatch = serializers.BooleanField()
    overdue_open_sessions = serializers.BooleanField()


class LinksSerializer(serializers.Serializer):
    accounts = serializers.ChoiceField(choices=["/api/v1/users/"])


class JobHealthSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=["ok", "alert", "unknown"])
    timezone = serializers.ChoiceField(choices=["Asia/Ho_Chi_Minh"])
    cutoff_at = serializers.DateTimeField()
    refreshed_at = serializers.DateTimeField()
    latest_run = JobRunSerializer(allow_null=True)
    latest_successful_run = JobRunSerializer(allow_null=True)
    overdue_open_session_count = serializers.IntegerField(min_value=0)
    evidence_counts = EvidenceSerializer()
    invariant_valid = serializers.BooleanField()
    reason_flags = ReasonsSerializer()
    investigation_links = LinksSerializer(allow_null=True)
    escalation_guidance = serializers.CharField(allow_null=True)


def job_health_payload(scoped: ScopedJobHealth) -> dict[str, object]:
    health = scoped.health
    return {
        "state": health.state.value,
        "timezone": health.timezone,
        "cutoff_at": health.cutoff_at,
        "refreshed_at": health.refreshed_at,
        "latest_run": _run_payload(health.latest_run),
        "latest_successful_run": _run_payload(health.latest_successful_run),
        "overdue_open_session_count": health.overdue_open_session_count,
        "evidence_counts": {
            "job_closed_session_count": health.evidence.job_closed_session_count,
            "missing_checkout_anomaly_count": health.evidence.missing_checkout_anomaly_count,
            "job_closed_without_anomaly_count": health.evidence.job_closed_without_anomaly_count,
            "anomaly_without_job_closed_count": health.evidence.anomaly_without_job_closed_count,
        },
        "invariant_valid": health.invariant_valid,
        "reason_flags": {
            name: getattr(health.reasons, name) for name in health.reasons.__dataclass_fields__
        },
        "investigation_links": scoped.investigation_links,
        "escalation_guidance": scoped.escalation_guidance,
    }


def _run_payload(run):  # type: ignore[no-untyped-def]
    if run is None:
        return None
    return {
        "id": run.id,
        "job_name": run.job_name.value,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status.value,
        "scanned_count": run.scanned_count,
        "changed_count": run.changed_count,
        "anomaly_count": run.anomaly_count,
        "error_code": run.error_code.value if run.error_code else None,
    }
