RELEASE_PHASE = "contract"


class Migration:
    dependencies = []
    operations = [migrations.RemoveField(name="old")]
