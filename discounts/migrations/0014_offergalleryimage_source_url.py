from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discounts", "0013_offer_gallery_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="offergalleryimage",
            name="image",
            field=models.ImageField(
                blank=True, null=True, upload_to="offer_gallery/"
            ),
        ),
        migrations.AddField(
            model_name="offergalleryimage",
            name="source_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
