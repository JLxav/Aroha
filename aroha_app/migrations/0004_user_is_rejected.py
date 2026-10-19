from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aroha_app", "0003_helprequest_feedback_and_rejection_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_rejected",
            field=models.BooleanField(default=False),
        ),
    ]
