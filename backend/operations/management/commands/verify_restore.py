from __future__ import annotations

import os

import psycopg
from django.core.management.base import BaseCommand, CommandError

from core.recovery import recovery_inputs_from_environment, verify_restore


class Command(BaseCommand):
    help = "Verify an isolated restored database using read-only probes."

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        try:
            inputs = recovery_inputs_from_environment(os.environ)
            result = verify_restore(inputs, psycopg.connect)
        except Exception as error:
            raise CommandError("incomplete/unverifiable: recovery configuration") from error
        if not result.passed:
            summary = ",".join(result.failures)
            raise CommandError(f"incomplete/unverifiable: {summary}")
        self.stdout.write("passed")
