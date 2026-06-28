from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Deprecated no-op. Test seeding was removed; kept so older Render start "
        "commands that still call this do not fail deploys."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("seed_test_data is deprecated and was skipped.")
        )
