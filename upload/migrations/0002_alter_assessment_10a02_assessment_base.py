# Generated by Django 4.2.6 on 2024-02-02 11:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("upload", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assessment_10a02",
            name="assessment_base",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assessment_10A02",
                to="upload.assessment_base",
            ),
        ),
    ]
