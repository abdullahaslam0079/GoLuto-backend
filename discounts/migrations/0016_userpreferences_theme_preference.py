from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discounts", "0015_devicetoken_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpreferences",
            name="theme_preference",
            field=models.CharField(
                choices=[
                    ("system", "System"),
                    ("light", "Light"),
                    ("dark", "Dark"),
                ],
                default="system",
                max_length=16,
            ),
        ),
    ]
