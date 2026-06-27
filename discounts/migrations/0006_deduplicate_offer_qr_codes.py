import uuid

from django.db import migrations
from django.db.models import Count


def deduplicate_offer_qr_codes(apps, schema_editor):
    Offer = apps.get_model("discounts", "Offer")

    duplicates = (
        Offer.objects.values("qr_code")
        .annotate(total=Count("id"))
        .filter(total__gt=1, qr_code__isnull=False)
    )
    duplicate_codes = [row["qr_code"] for row in duplicates]

    for qr_code in duplicate_codes:
        offers = Offer.objects.filter(qr_code=qr_code).order_by("id")
        for offer in offers[1:]:
            Offer.objects.filter(pk=offer.pk).update(qr_code=uuid.uuid4())

    for offer in Offer.objects.filter(qr_code__isnull=True).only("pk"):
        Offer.objects.filter(pk=offer.pk).update(qr_code=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0005_offer_image"),
    ]

    operations = [
        migrations.RunPython(deduplicate_offer_qr_codes, migrations.RunPython.noop),
    ]
