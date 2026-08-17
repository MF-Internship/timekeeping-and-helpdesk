def create_cache(apps, schema_editor):
    call_command("createcachetable", "duplicated_cache_table")


class Migration:
    dependencies = []
    operations = [migrations.RunPython(create_cache)]
