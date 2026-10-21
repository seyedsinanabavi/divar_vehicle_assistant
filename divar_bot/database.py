import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True) if Path(path).parent != Path(".") else None
        self.init_db()

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def init_db(self):
        with self.connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    listing_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    price INTEGER,
                    city TEXT,
                    chat_available INTEGER,
                    status TEXT NOT NULL,
                    message TEXT,
                    first_seen TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error TEXT
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id TEXT,
                    event TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL
                )
            """)

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def seen(self, listing_id: str) -> bool:
        with self.connect() as con:
            return con.execute(
                "SELECT 1 FROM listings WHERE listing_id=?", (listing_id,)
            ).fetchone() is not None

    def status(self, listing_id: str):
        with self.connect() as con:
            row = con.execute("SELECT status FROM listings WHERE listing_id=?", (listing_id,)).fetchone()
            return row["status"] if row else None

    def upsert_listing(self, listing, status="discovered", message=None, error=None):
        now = self.now()
        chat = None if listing.chat_available is None else int(listing.chat_available)
        with self.connect() as con:
            con.execute("""
                INSERT INTO listings
                (listing_id,title,url,price,city,chat_available,status,message,first_seen,updated_at,error)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(listing_id) DO UPDATE SET
                    title=excluded.title, url=excluded.url, price=excluded.price,
                    city=excluded.city, chat_available=excluded.chat_available,
                    status=excluded.status, message=COALESCE(excluded.message,listings.message),
                    updated_at=excluded.updated_at, error=excluded.error
            """, (listing.listing_id, listing.title, listing.url, listing.price, listing.city,
                  chat, status, message, now, now, error))
            con.execute("INSERT INTO events(listing_id,event,detail,created_at) VALUES (?,?,?,?)",
                        (listing.listing_id, status, error or message or "", now))

    def stats(self):
        with self.connect() as con:
            rows = con.execute("SELECT status, COUNT(*) AS n FROM listings GROUP BY status").fetchall()
            return {r["status"]: r["n"] for r in rows}

    def recent_events(self, limit=20):
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
