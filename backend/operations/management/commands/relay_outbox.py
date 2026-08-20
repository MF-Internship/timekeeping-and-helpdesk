from __future__ import annotations

import socket

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Publish a bounded batch of leased transactional outbox events."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--worker-id", default=socket.gethostname()[:48])

    def handle(self, *args: object, **options: object) -> None:
        del args
        from config.composition import operations_container

        worker_id = str(options["worker_id"])[:64]
        result = operations_container().outbox_relay.run_once(worker_id)
        self.stdout.write(
            f"claimed={result.claimed} published={result.published} "
            f"failed={result.failed} lost_claims={result.lost_claims}"
        )
