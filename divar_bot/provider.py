from abc import ABC, abstractmethod
from .models import Listing

class DivarProvider(ABC):
    """
    اتصال اختصاصی دیوار باید بر اساس API/دسترسی مجاز و مستندات واقعی پیاده‌سازی شود.
    این کلاس عمداً ورود، استخراج صفحه خصوصی یا ارسال پیام ساختگی انجام نمی‌دهد.
    """
    @abstractmethod
    def fetch_listings(self) -> list[Listing]:
        """آگهی‌های حاصل از جست‌وجوی مجاز را برگرداند."""
        raise NotImplementedError

    @abstractmethod
    def can_chat(self, listing: Listing) -> bool | None:
        """True/False اگر وضعیت چت قابل تشخیص است؛ در غیر این صورت None."""
        raise NotImplementedError

    @abstractmethod
    def send_message(self, listing: Listing, message: str) -> tuple[bool, str]:
        """(موفقیت, توضیح). فقط با اتصال مجاز و واقعی پیاده‌سازی شود."""
        raise NotImplementedError


class ManualImportProvider(DivarProvider):
    """
    حالت فعلی: فایل CSV آگهی‌ها را می‌خواند. ارسال پیام را انجام نمی‌دهد.
    برای تست گردش‌کار و دیتابیس مناسب است.
    """
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def fetch_listings(self) -> list[Listing]:
        import csv
        items = []
        with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                price_raw = (row.get("price") or "").strip()
                try:
                    price = int(price_raw) if price_raw else None
                except ValueError:
                    price = None
                chat_raw = (row.get("chat_available") or "").strip().lower()
                chat = True if chat_raw in {"1","true","yes","بله"} else (
                    False if chat_raw in {"0","false","no","خیر"} else None
                )
                items.append(Listing(
                    listing_id=(row.get("listing_id") or "").strip(),
                    title=(row.get("title") or "").strip(),
                    url=(row.get("url") or "").strip(),
                    price=price,
                    city=(row.get("city") or "").strip(),
                    description=(row.get("description") or "").strip(),
                    chat_available=chat,
                    published_at=(row.get("published_at") or "").strip()
                ))
        return items

    def can_chat(self, listing: Listing) -> bool | None:
        return listing.chat_available

    def send_message(self, listing: Listing, message: str) -> tuple[bool, str]:
        return False, "اتصال ارسال پیام پیکربندی نشده است؛ پیام ارسال نشد."
