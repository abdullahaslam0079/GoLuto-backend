from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("discounts", "0012_engagement_analytics"),
    ]

    operations = [
        migrations.CreateModel(
            name="OfferGalleryImage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("image", models.ImageField(upload_to="offer_gallery/")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gallery_images",
                        to="discounts.offer",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
