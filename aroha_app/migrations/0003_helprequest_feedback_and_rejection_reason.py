from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aroha_app", "0002_helprequest_assigned_volunteer"),
    ]

    operations = [
        migrations.AddField(
            model_name="helprequest",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="helprequest",
            name="volunteer_rating",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="helprequest",
            name="volunteer_feedback",
            field=models.TextField(blank=True),
        ),
    ]
