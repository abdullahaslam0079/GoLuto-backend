from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0020_offer_deal_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="DealSource",
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
                ("name", models.CharField(blank=True, max_length=120)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("brand_listing", "Brand listing page"),
                            ("affiliate_feed", "Affiliate product feed"),
                        ],
                        default="brand_listing",
                        max_length=32,
                    ),
                ),
                ("listing_url", models.URLField(blank=True, max_length=1000)),
                ("feed_url", models.URLField(blank=True, max_length=1000)),
                ("is_enabled", models.BooleanField(default=True)),
                (
                    "is_online",
                    models.BooleanField(
                        default=True,
                        help_text="Imported offers are treated as online (view-only) when true.",
                    ),
                ),
                (
                    "max_items",
                    models.PositiveIntegerField(
                        default=80,
                        help_text="Cap product URLs/rows processed per sync run.",
                    ),
                ),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "business",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deal_sources",
                        to="discounts.business",
                    ),
                ),
            ],
            options={
                "ordering": ["name", "id"],
            },
        ),
        migrations.AddField(
            model_name="offer",
            name="disabled_by",
            field=models.CharField(
                blank=True,
                choices=[("sync", "Sync"), ("admin", "Admin")],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="last_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="offer",
            name="last_synced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="offer",
            name="origin",
            field=models.CharField(
                choices=[
                    ("manual", "Manual"),
                    ("brand_listing", "Brand listing"),
                    ("affiliate_feed", "Affiliate feed"),
                ],
                default="manual",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="approved",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="source_key",
            field=models.CharField(blank=True, db_index=True, max_length=500),
        ),
        migrations.AddField(
            model_name="offer",
            name="source_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name="offer",
            name="unavailable_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("missing_from_source", "Missing from source"),
                    ("http_404", "Product page gone"),
                    ("out_of_stock", "Out of stock"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="source",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="offers",
                to="discounts.dealsource",
            ),
        ),
        migrations.AddIndex(
            model_name="offer",
            index=models.Index(
                fields=["review_status", "origin"],
                name="discounts_o_review__idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="offer",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_key__gt", "")),
                fields=("business", "source_key"),
                name="unique_offer_source_key_per_business",
            ),
        ),
    ]
