from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0019_user_phone_firebase_uid"),
    ]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="included_items",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Included item names for deal/bundle offers.",
            ),
        ),
        migrations.AlterField(
            model_name="offer",
            name="offer_type",
            field=models.CharField(
                choices=[
                    ("percentage_bill", "Percentage off entire bill"),
                    ("item", "Item or service discount"),
                    ("deal", "Deal or bundle"),
                ],
                max_length=20,
            ),
        ),
    ]
