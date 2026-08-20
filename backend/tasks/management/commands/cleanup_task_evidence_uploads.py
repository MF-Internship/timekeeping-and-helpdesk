from django.core.management.base import BaseCommand, CommandError, CommandParser

from config.composition import task_container


class Command(BaseCommand):
    help = "Delete expired, unbound Task evidence staging objects and intents."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args: object, **options: object) -> None:
        limit = options.get("limit")
        if not isinstance(limit, int):
            raise CommandError("--limit must be an integer")
        outcome = task_container().evidence_cleanup.run(limit=limit)
        self.stdout.write(
            f"scanned={outcome.scanned_count} deleted={outcome.deleted_count} "
            f"failed={outcome.failed_count}"
        )
