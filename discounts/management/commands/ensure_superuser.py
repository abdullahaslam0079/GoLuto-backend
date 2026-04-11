import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "If ADMIN_EMAIL and ADMIN_PASSWORD env vars are set, ensure a staff/superuser "
        "exists (create or promote). Use on hosts without a shell (e.g. Render free tier)."
    )

    def handle(self, *args, **options):
        raw_email = (os.environ.get("ADMIN_EMAIL") or "").strip()
        password = os.environ.get("ADMIN_PASSWORD")
        if not raw_email or not password:
            return

        User = get_user_model()
        email = User.objects.normalize_email(raw_email)

        user = User.objects.filter(email=email).first()
        if user is None:
            User.objects.create_superuser(email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Created superuser: {email}"))
            return

        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Promoted existing user to superuser (was normal account): {email}"
                )
            )
            return

        self.stdout.write(f"Superuser already exists: {email}")
