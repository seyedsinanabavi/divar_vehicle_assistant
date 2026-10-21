from dataclasses import dataclass
from typing import Optional

@dataclass
class Listing:
    listing_id: str
    title: str
    url: str
    price: Optional[int] = None
    city: str = ""
    description: str = ""
    chat_available: Optional[bool] = None
    published_at: str = ""
