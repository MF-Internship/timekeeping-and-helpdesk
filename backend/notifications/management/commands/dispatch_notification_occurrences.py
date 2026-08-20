from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Record due authoritative notification occurrences idempotently."

    def handle(self, *args: object, **options: object) -> None:
        from config import composition

        count = composition.notification_container().dispatch.dispatch()
        self.stdout.write(f"recorded={count}")
