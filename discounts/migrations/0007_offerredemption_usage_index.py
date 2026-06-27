from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discounts", "0006_deduplicate_offer_qr_codes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="offerredemption",
            index=models.Index(
                fields=["user", "offer", "redeemed_at"],
                name="offer_redemption_user_offer_idx",
            ),
        ),
    ]
