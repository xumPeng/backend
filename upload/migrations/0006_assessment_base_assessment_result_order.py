# Generated by Django 4.2.6 on 2024-02-03 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("upload", "0005_alter_assessment_base_assessment_result"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessment_base",
            name="assessment_result_order",
            field=models.IntegerField(default=0, editable=False),
        ),
    ]