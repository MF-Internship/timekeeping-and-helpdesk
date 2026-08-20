from django.db import migrations, models
import django.db.models.deletion


IMMUTABLE_CODE_SQL = """
CREATE OR REPLACE FUNCTION locations_reject_code_update() RETURNS trigger AS $$
BEGIN
    IF NEW.code IS DISTINCT FROM OLD.code THEN
        RAISE EXCEPTION 'Location code is immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER locations_code_immutable
BEFORE UPDATE OF code ON locations_location
FOR EACH ROW EXECUTE FUNCTION locations_reject_code_update();
"""
IMMUTABLE_CODE_REVERSE_SQL = """
DROP TRIGGER IF EXISTS locations_code_immutable ON locations_location;
DROP FUNCTION IF EXISTS locations_reject_code_update();
"""


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Config",
            fields=[
                ("id", models.SmallIntegerField(default=1, primary_key=True, serialize=False)),
                ("timezone", models.CharField(db_default="Asia/Ho_Chi_Minh", default="Asia/Ho_Chi_Minh", max_length=64)),
                ("working_weekdays", models.JSONField(db_default=[], default=list)),
                ("default_radius_m", models.DecimalField(db_default=50, decimal_places=3, default=50, max_digits=10)),
                ("max_radius_m", models.DecimalField(db_default=70, decimal_places=3, default=70, max_digits=10)),
                ("max_attendance_accuracy_m", models.DecimalField(db_default=25, decimal_places=3, default=25, max_digits=10)),
                ("task_gps_good_accuracy_m", models.DecimalField(db_default=25, decimal_places=3, default=25, max_digits=10)),
                ("task_gps_low_accuracy_m", models.DecimalField(db_default=100, decimal_places=3, default=100, max_digits=10)),
                ("shift_start", models.TimeField()),
                ("shift_end", models.TimeField()),
                ("late_grace_minutes", models.PositiveIntegerField()),
                ("early_checkout_grace_minutes", models.PositiveIntegerField()),
                ("late_checkout_grace_minutes", models.PositiveIntegerField(db_default=60, default=60)),
            ],
        ),
        migrations.CreateModel(
            name="Holiday",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True)),
                ("name", models.CharField(max_length=255)),
            ],
            options={"ordering": ("date", "id")},
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("kind", models.CharField(choices=[("BUSINESS_CENTER", "BUSINESS_CENTER"), ("SHOP", "SHOP")], max_length=32)),
                ("address", models.CharField(max_length=500)),
                ("latitude", models.DecimalField(decimal_places=15, max_digits=18)),
                ("longitude", models.DecimalField(decimal_places=15, max_digits=18)),
                ("radius_m", models.DecimalField(decimal_places=3, max_digits=10)),
                ("is_active", models.BooleanField(db_default=True, default=True)),
                ("version", models.PositiveBigIntegerField(db_default=1, default=1)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="locations.location")),
            ],
            options={"ordering": ("kind", "code", "id")},
        ),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("id", 1)), name="location_config_singleton")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("timezone", "Asia/Ho_Chi_Minh")), name="location_config_timezone_fixed")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("default_radius_m__gt", 0), ("default_radius_m__lt", 10000000)), name="location_config_default_radius_finite")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("max_radius_m__gt", 0), ("max_radius_m__lt", 10000000)), name="location_config_max_radius_finite")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("max_attendance_accuracy_m__gt", 0), ("max_attendance_accuracy_m__lt", 10000000)), name="location_config_attendance_accuracy_finite")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("task_gps_good_accuracy_m__gt", 0), ("task_gps_good_accuracy_m__lt", 10000000)), name="location_config_task_good_finite")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("task_gps_low_accuracy_m__gt", 0), ("task_gps_low_accuracy_m__lt", 10000000)), name="location_config_task_low_finite")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("default_radius_m__lte", models.F("max_radius_m"))), name="location_config_default_lte_max")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("task_gps_good_accuracy_m__lte", models.F("task_gps_low_accuracy_m"))), name="location_config_task_good_lte_low")),
        migrations.AddConstraint(model_name="config", constraint=models.CheckConstraint(condition=models.Q(("shift_start__lt", models.F("shift_end"))), name="location_config_shift_order")),
        migrations.AddConstraint(model_name="holiday", constraint=models.CheckConstraint(condition=models.Q(("name__regex", "^\\s*$"), _negated=True), name="holiday_name_nonblank")),
        migrations.AddIndex(model_name="holiday", index=models.Index(fields=["date", "id"], name="holiday_date_id_idx")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("code__regex", "^\\s*$"), _negated=True), name="location_code_nonblank")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("name__regex", "^\\s*$"), _negated=True), name="location_name_nonblank")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("address__regex", "^\\s*$"), _negated=True), name="location_address_nonblank")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("kind__in", ["BUSINESS_CENTER", "SHOP"])), name="location_kind_valid")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("latitude__gte", -90), ("latitude__lte", 90)), name="location_latitude_range")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("longitude__gte", -180), ("longitude__lte", 180)), name="location_longitude_range")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("radius_m__gt", 0), ("radius_m__lt", 10000000)), name="location_radius_valid")),
        migrations.AddConstraint(model_name="location", constraint=models.CheckConstraint(condition=models.Q(("version__gte", 1)), name="location_version_positive")),
        migrations.AddIndex(model_name="location", index=models.Index(fields=["kind", "code"], name="location_kind_code_idx")),
        migrations.AddIndex(model_name="location", index=models.Index(fields=["parent"], name="location_parent_idx")),
        migrations.AddIndex(model_name="location", index=models.Index(fields=["is_active"], name="location_active_idx")),
        migrations.RunSQL(IMMUTABLE_CODE_SQL, IMMUTABLE_CODE_REVERSE_SQL),
    ]
