from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discounts", "0010_offer_redemption_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="detailed_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="offer",
            name="external_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="offer",
            name="external_url_label",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
