from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_business_likes_to_branch_likes(apps, schema_editor):
    """Best-effort: map each business like to that business's first branch."""
    BusinessLike = apps.get_model("discounts", "BusinessLike")
    Branch = apps.get_model("discounts", "Branch")
    BranchLike = apps.get_model("discounts", "BranchLike")

    existing = {
        (row.user_id, row.branch_id)
        for row in BranchLike.objects.all().only("user_id", "branch_id")
    }

    to_create = []
    for like in BusinessLike.objects.all().iterator():
        branch = (
            Branch.objects.filter(business_id=like.business_id)
            .order_by("id")
            .first()
        )
        if branch is None:
            continue
        key = (like.user_id, branch.id)
        if key in existing:
            continue
        existing.add(key)
        to_create.append(
            BranchLike(
                user_id=like.user_id,
                branch_id=branch.id,
                created_at=like.created_at,
            )
        )

    if to_create:
        BranchLike.objects.bulk_create(to_create, batch_size=500)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("discounts", "0017_offer_is_online"),
    ]

    operations = [
        migrations.CreateModel(
            name="BranchLike",
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
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="discounts.branch",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branch_likes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="branchlike",
            constraint=models.UniqueConstraint(
                fields=("user", "branch"),
                name="unique_branch_like_per_user",
            ),
        ),
        migrations.RunPython(
            migrate_business_likes_to_branch_likes,
            noop_reverse,
        ),
    ]
