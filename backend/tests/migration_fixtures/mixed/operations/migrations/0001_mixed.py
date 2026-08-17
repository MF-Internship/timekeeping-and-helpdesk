RELEASE_PHASE = "contract"


class Migration:
    dependencies = []
    operations = [
        migrations.RemoveField(name="old"),
        migrations.AddField(name="new", field=models.CharField(null=True)),
    ]
