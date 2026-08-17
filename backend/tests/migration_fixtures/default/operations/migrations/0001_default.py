class Migration:
    dependencies = []
    operations = [
        migrations.AddField(name="status", field=models.CharField(null=False, db_default="NEW"))
    ]
