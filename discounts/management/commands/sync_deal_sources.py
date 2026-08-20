from django.core.management.base import BaseCommand

from discounts.models import DealSource
from discounts.offer_sync import sync_all_deal_sources, sync_deal_source


class Command(BaseCommand):
    help = (
        "Sync deal sources: import new brand/affiliate offers into the review queue, "
        "refresh approved offers, and disable deals that disappeared from the source. "
        "Run from cron later (Render Cron or GitHub Action). No Celery required."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-id",
            type=int,
            help="Sync a single DealSource id instead of all enabled sources.",
        )
        parser.add_argument(
            "--include-disabled",
            action="store_true",
            help="Also sync sources that are currently disabled.",
        )

    def handle(self, *args, **options):
        source_id = options.get("source_id")
        if source_id:
            source = DealSource.objects.select_related("business").filter(pk=source_id).first()
            if source is None:
                self.stderr.write(f"Deal source {source_id} not found.\n")
                return
            result = sync_deal_source(source)
            self._log_result(source, result)
            return

        rows = sync_all_deal_sources(only_enabled=not options.get("include_disabled"))
        if not rows:
            self.stderr.write("No deal sources to sync.\n")
            return
        for source, result in rows:
            self._log_result(source, result)

    def _log_result(self, source, result) -> None:
        payload = result.as_dict()
        label = source.name or source.listing_url or source.feed_url or source.pk
        self.stderr.write(
            f"{source.business.name} / {label}: discovered={payload['discovered']} "
            f"created={payload['created']} updated={payload['updated']} "
            f"disabled={payload['disabled_missing'] + payload['disabled_unavailable']} "
            f"errors={payload['errors']}\n"
        )
        if source.last_error:
            self.stderr.write(f"  last_error: {source.last_error}\n")
