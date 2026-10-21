from .models import Listing
from .config import Settings

CAR_TERMS = (
    "خودرو", "سواری", "ماشین", "پژو", "پراید", "سمند", "دنا", "تارا",
    "شاهین", "تیبا", "کوییک", "ساینا", "رانا", "تویوتا", "هیوندای",
    "کیا", "ام‌وی‌ام", "ام وی ام", "جک", "فیدلیتی", "دیگنیتی", "نیسان"
)

def is_vehicle_listing(item: Listing) -> bool:
    text = f"{item.title} {item.description}".lower()
    return any(term.lower() in text for term in CAR_TERMS)

def matches_filters(item: Listing, settings: Settings) -> tuple[bool, str]:
    if not item.listing_id or not item.url:
        return False, "شناسه یا لینک آگهی موجود نیست"
    if not is_vehicle_listing(item):
        return False, "آگهی به نظر خودرویی نمی‌رسد"
    if settings.min_price is not None and item.price is not None and item.price < settings.min_price:
        return False, "قیمت کمتر از حداقل تعیین‌شده است"
    if settings.max_price is not None and item.price is not None and item.price > settings.max_price:
        return False, "قیمت بیشتر از حداکثر تعیین‌شده است"
    return True, "مطابق فیلترها"
