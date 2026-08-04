from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("discounts", "0011_offer_external_link_and_details"),
    ]

    operations = [
        migrations.CreateModel(
            name="BusinessEngagementStats",
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
                ("view_count", models.PositiveIntegerField(default=0)),
                ("like_count", models.PositiveIntegerField(default=0)),
                (
                    "business",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="engagement_stats",
                        to="discounts.business",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="OfferEngagementStats",
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
                ("view_count", models.PositiveIntegerField(default=0)),
                ("like_count", models.PositiveIntegerField(default=0)),
                (
                    "offer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="engagement_stats",
                        to="discounts.offer",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BusinessLike",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "business",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="discounts.business",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="business_likes",
                        to="discounts.user",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "business"),
                        name="unique_business_like_per_user",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="OfferLike",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="discounts.offer",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offer_likes",
                        to="discounts.user",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "offer"),
                        name="unique_offer_like_per_user",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="OfferViewEvent",
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
                ("viewed_on", models.DateField(auto_now_add=True)),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="view_events",
                        to="discounts.offer",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offer_view_events",
                        to="discounts.user",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "offer", "viewed_on"),
                        condition=models.Q(user__isnull=False),
                        name="unique_offer_view_per_user_day",
                    )
                ],
            },
        ),
    ]
