import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0004_business_branches_offers"),
    ]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="offer_images/"),
        ),
    ]
