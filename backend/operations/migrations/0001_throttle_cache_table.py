from django.core.management import call_command
from django.db import migrations

from core.cache import THROTTLE_CACHE_TABLE


def create_throttle_cache_table(_apps, schema_editor):
    call_command(
        "createcachetable",
        THROTTLE_CACHE_TABLE,
        database=schema_editor.connection.alias,
        verbosity=0,
    )


def drop_throttle_cache_table(_apps, schema_editor):
    quoted_table = schema_editor.connection.ops.quote_name(THROTTLE_CACHE_TABLE)
    schema_editor.execute(f"DROP TABLE IF EXISTS {quoted_table}")


class Migration(migrations.Migration):
    initial = True
    dependencies = ()
    operations = (
        migrations.RunPython(
            create_throttle_cache_table,
            reverse_code=drop_throttle_cache_table,
        ),
    )
