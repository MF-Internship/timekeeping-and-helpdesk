class Migration:
    dependencies = []
    operations = [migrations.AddField(name="note", field=models.CharField(null=True))]
