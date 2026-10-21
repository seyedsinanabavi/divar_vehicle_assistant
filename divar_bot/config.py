from dataclasses import dataclass
import os

def _optional_int(name: str):
    value = os.getenv(name, "").strip()
    return int(value) if value else None

@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DIVAR_DB_PATH", "divar_bot.sqlite3")
    log_path: str = os.getenv("DIVAR_LOG_PATH", "divar_bot.log")
    search_url: str = os.getenv("DIVAR_SEARCH_URL", "")
    message_text: str = os.getenv(
        "DIVAR_MESSAGE_TEXT",
        "سلام، وقت بخیر. آگهی خودروی شما رو دیدم؛ آیا هنوز موجوده؟ امکان صحبت درباره جزئیات و شرایط معامله هست؟"
    )
    min_price: int | None = _optional_int("DIVAR_MIN_PRICE")
    max_price: int | None = _optional_int("DIVAR_MAX_PRICE")
    max_age_days: int | None = _optional_int("DIVAR_MAX_AGE_DAYS")
    dry_run: bool = os.getenv("DIVAR_DRY_RUN", "1").strip().lower() not in {"0", "false", "no"}
    poll_seconds: int = int(os.getenv("DIVAR_POLL_SECONDS", "60"))

SETTINGS = Settings()
