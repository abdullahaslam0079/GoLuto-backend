from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0018_branchlike"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="firebase_uid",
            field=models.CharField(
                blank=True,
                help_text="Firebase Auth UID linked to this account.",
                max_length=128,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True,
                help_text="E.164 phone number from Firebase Phone Auth.",
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
    ]
