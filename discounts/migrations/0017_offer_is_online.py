from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0016_userpreferences_theme_preference"),
    ]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="is_online",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Offer is available online (no in-store branch required when true)."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="offer",
            name="branches",
            field=models.ManyToManyField(
                blank=True, related_name="offers", to="discounts.branch"
            ),
        ),
    ]
