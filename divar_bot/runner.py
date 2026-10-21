import logging
from .config import SETTINGS
from .database import Database
from .filters import matches_filters
from .provider import DivarProvider

logger = logging.getLogger(__name__)

class Runner:
    def __init__(self, provider: DivarProvider):
        self.provider = provider
        self.db = Database(SETTINGS.database_path)

    def run_once(self):
        listings = self.provider.fetch_listings()
        logger.info("Fetched %d listings", len(listings))
        for item in listings:
            try:
                if self.db.seen(item.listing_id):
                    logger.info("Skipping already processed listing %s", item.listing_id)
                    continue

                ok, reason = matches_filters(item, SETTINGS)
                if not ok:
                    self.db.upsert_listing(item, status="filtered_out", error=reason)
                    continue

                chat = self.provider.can_chat(item)
                item.chat_available = chat
                if chat is False:
                    self.db.upsert_listing(item, status="chat_unavailable",
                                           error="امکان چت غیرفعال است")
                    continue
                if chat is None:
                    self.db.upsert_listing(item, status="needs_chat_check",
                                           error="وضعیت چت مشخص نیست؛ ارسال انجام نشد")
                    continue

                if SETTINGS.dry_run:
                    self.db.upsert_listing(item, status="dry_run",
                                           message=SETTINGS.message_text)
                    logger.info("[DRY RUN] Would message %s (%s)", item.title, item.url)
                    continue

                success, detail = self.provider.send_message(item, SETTINGS.message_text)
                self.db.upsert_listing(
                    item,
                    status="sent" if success else "send_failed",
                    message=SETTINGS.message_text if success else None,
                    error=None if success else detail
                )
            except Exception as exc:
                logger.exception("Error processing listing %s", getattr(item, "listing_id", "?"))
                self.db.upsert_listing(item, status="error", error=str(exc))
        logger.info("Stats: %s", self.db.stats())
