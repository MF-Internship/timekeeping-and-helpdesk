from django.core.management.base import BaseCommand, CommandError

from config.composition import reconciliation_service


class Command(BaseCommand):
    help = "Reconcile stale attendance sessions without inventing checkout time."

    def handle(self, *args: object, **options: object) -> None:
        outcome = reconciliation_service().run()
        summary = (
            f"status={outcome.status} scanned={outcome.scanned_count} "
            f"changed={outcome.changed_count} anomalies={outcome.anomaly_count}"
        )
        if outcome.status != "SUCCEEDED":
            raise CommandError(summary)
        self.stdout.write(summary)
