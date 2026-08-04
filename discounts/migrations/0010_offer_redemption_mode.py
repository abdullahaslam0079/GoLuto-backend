from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discounts", "0009_offer_payment_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="redemption_mode",
            field=models.CharField(
                choices=[
                    ("scannable", "Scannable"),
                    ("view_only", "View only"),
                ],
                default="scannable",
                max_length=20,
            ),
        ),
    ]
