import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_business_locations(apps, schema_editor):
    User = apps.get_model("discounts", "User")
    Business = apps.get_model("discounts", "Business")
    Branch = apps.get_model("discounts", "Branch")
    Offer = apps.get_model("discounts", "Offer")

    for business in Business.objects.all():
        owner = getattr(business, "owner", None)
        if owner is None:
            email = f"legacy-business-{business.pk}@goluto.local"
            owner, _ = User.objects.get_or_create(
                email=email,
                defaults={"account_type": "business", "password": "!"},
            )
            owner.account_type = "business"
            owner.save(update_fields=["account_type"])
            business.owner = owner
            business.save(update_fields=["owner"])

        latitude = getattr(business, "latitude", None)
        longitude = getattr(business, "longitude", None)
        if latitude is None or longitude is None:
            continue

        branch, _ = Branch.objects.get_or_create(
            business=business,
            name=f"{business.name} Main Branch",
            defaults={
                "street": "Main Street",
                "house_number": "1",
                "postal_code": "00000",
                "city": "Unknown",
                "latitude": latitude,
                "longitude": longitude,
            },
        )

        for offer in Offer.objects.filter(business=business):
            offer.branches.add(branch)


def assign_unique_offer_qr_codes(apps, schema_editor):
    Offer = apps.get_model("discounts", "Offer")
    for offer in Offer.objects.all().only("pk"):
        Offer.objects.filter(pk=offer.pk).update(qr_code=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0003_passwordresettoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="account_type",
            field=models.CharField(
                choices=[("consumer", "Consumer"), ("business", "Business")],
                default="consumer",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="business",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to="business_logos/"),
        ),
        migrations.AddField(
            model_name="business",
            name="owner",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="business_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="Branch",
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
                ("name", models.CharField(max_length=120)),
                ("street", models.CharField(max_length=120)),
                ("house_number", models.CharField(max_length=20)),
                ("postal_code", models.CharField(max_length=20)),
                ("city", models.CharField(max_length=80)),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                (
                    "business",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branches",
                        to="discounts.business",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "branches",
                "ordering": ["name", "id"],
            },
        ),
        migrations.AddField(
            model_name="offer",
            name="discounted_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="item_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="offer",
            name="offer_type",
            field=models.CharField(
                choices=[
                    ("percentage_bill", "Percentage off entire bill"),
                    ("item", "Item or service discount"),
                ],
                default="percentage_bill",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="original_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="qr_code",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="offer",
            name="usage_limit_count",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="offer",
            name="usage_limit_type",
            field=models.CharField(
                choices=[
                    ("one_time", "One time only"),
                    ("once_per_week", "Once per week"),
                    ("once_per_month", "Once per month"),
                    ("n_times_per_week", "N times per week"),
                    ("n_times_per_month", "N times per month"),
                    ("n_times_total", "N times total"),
                ],
                default="one_time",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="branches",
            field=models.ManyToManyField(related_name="offers", to="discounts.branch"),
        ),
        migrations.RunPython(migrate_business_locations, migrations.RunPython.noop),
        migrations.RunPython(assign_unique_offer_qr_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="offer",
            name="qr_code",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="business",
            name="owner",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="business_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveField(
            model_name="business",
            name="latitude",
        ),
        migrations.RemoveField(
            model_name="business",
            name="longitude",
        ),
        migrations.CreateModel(
            name="OfferBranchStats",
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
                ("scan_count", models.PositiveIntegerField(default=0)),
                ("avail_count", models.PositiveIntegerField(default=0)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offer_stats",
                        to="discounts.branch",
                    ),
                ),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branch_stats",
                        to="discounts.offer",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "offer branch stats",
            },
        ),
        migrations.AddConstraint(
            model_name="offerbranchstats",
            constraint=models.UniqueConstraint(
                fields=("offer", "branch"), name="unique_offer_branch_stats"
            ),
        ),
        migrations.CreateModel(
            name="OfferRedemption",
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
                ("redeemed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="redemptions",
                        to="discounts.branch",
                    ),
                ),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="redemptions",
                        to="discounts.offer",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offer_redemptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-redeemed_at"],
            },
        ),
        migrations.CreateModel(
            name="OfferScan",
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
                ("scanned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scans",
                        to="discounts.branch",
                    ),
                ),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scans",
                        to="discounts.offer",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="offer_scans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-scanned_at"],
            },
        ),
    ]
