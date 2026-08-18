from datetime import time
from typing import cast

from django.core.management.base import BaseCommand, CommandError, CommandParser

from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.config_admin import default_config


class Command(BaseCommand):
    help = "Initialize the complete Location configuration singleton."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--actor-id", type=int, required=True)
        parser.add_argument("--shift-start", type=time.fromisoformat, required=True)
        parser.add_argument("--shift-end", type=time.fromisoformat, required=True)
        parser.add_argument("--late-grace-minutes", type=int, required=True)
        parser.add_argument("--early-checkout-grace-minutes", type=int, required=True)

    def handle(self, *args: object, **options: object) -> None:
        try:
            value = default_config(
                shift_start=cast(time, options["shift_start"]),
                shift_end=cast(time, options["shift_end"]),
                late_grace_minutes=cast(int, options["late_grace_minutes"]),
                early_checkout_grace_minutes=cast(int, options["early_checkout_grace_minutes"]),
            )
            locations_container().config_admin.initialize(cast(int, options["actor_id"]), value)
        except (IdentityAPIError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write("Config initialized")
