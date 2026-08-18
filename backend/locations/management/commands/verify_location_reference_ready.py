from django.core.management.base import BaseCommand, CommandError

from config.composition import locations_container


class Command(BaseCommand):
    help = "Read-only readiness check for Location reference data."

    def handle(self, *args: object, **options: object) -> None:
        ready, errors = locations_container().readiness.check()
        if not ready:
            raise CommandError("reference data not ready: " + ",".join(errors))
        self.stdout.write("Location reference data ready")
