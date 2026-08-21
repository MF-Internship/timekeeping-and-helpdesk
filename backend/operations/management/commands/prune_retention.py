from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Prune bounded operational retention categories."

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        from config.operations_adapters import DjangoRetentionRepository
        from operations.application.retention import prune_retention

        result = prune_retention(
            DjangoRetentionRepository(),
            now=timezone.now(),
            batch_size=settings.RETENTION_PRUNE_BATCH_SIZE,
        )
        self.stdout.write(
            f"processed_event={result.processed_event} "
            f"outbox_published={result.outbox_published} "
            f"outbox_dead_letter={result.outbox_dead_letter}"
        )
