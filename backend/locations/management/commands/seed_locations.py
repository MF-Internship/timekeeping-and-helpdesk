from pathlib import Path
from typing import cast

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from config.composition import locations_container
from core.errors import IdentityAPIError


class Command(BaseCommand):
    help = "Seed and reconcile canonical Location reference data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--actor-id", type=int, required=True)
        parser.add_argument(
            "--center-path",
            type=Path,
            default=settings.BASE_DIR.parent / "docs" / "dia_chi_ttkd.csv",
        )
        parser.add_argument(
            "--shop-path",
            type=Path,
            default=settings.BASE_DIR.parent / "docs" / "dia_chi_cua_hang.csv",
        )

    def handle(self, *args: object, **options: object) -> None:
        try:
            changed, total, warnings = locations_container().seed.seed(
                cast(int, options["actor_id"]),
                cast(Path, options["center_path"]),
                cast(Path, options["shop_path"]),
            )
        except (IdentityAPIError, ValueError) as error:
            raise CommandError(str(error)) from error
        warning_codes = ",".join(warning.code.value for warning in warnings) or "none"
        self.stdout.write(
            f"Locations reconciled changed={changed} total={total} warnings={warning_codes}"
        )
