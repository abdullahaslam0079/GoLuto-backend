import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "If ADMIN_EMAIL and ADMIN_PASSWORD env vars are set, create a superuser "
        "when missing (for hosts without a shell, e.g. Render free tier)."
    )

    def handle(self, *args, **options):
        email = (os.environ.get("ADMIN_EMAIL") or "").strip()
        password = os.environ.get("ADMIN_PASSWORD")
        if not email or not password:
            return

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser: {email}"))
