import socket

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Deliver a bounded batch of due best-effort Web Push records."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--worker-id", default=socket.gethostname()[:48])

    def handle(self, *args: object, **options: object) -> None:
        from config import composition

        limit = max(1, min(int(str(options["limit"])), 1000))
        worker_id = str(options["worker_id"])[:64]
        processed = 0
        container = composition.notification_container
        while processed < limit and container().delivery.deliver_one(worker_id):
            processed += 1
        self.stdout.write(f"processed={processed}")
