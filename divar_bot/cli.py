import argparse
import logging
from .config import SETTINGS
from .database import Database
from .provider import ManualImportProvider
from .runner import Runner

def main():
    parser = argparse.ArgumentParser(description="دستیار بررسی آگهی خودرو دیوار")
    parser.add_argument("--csv", default="sample_listings.csv", help="فایل CSV آگهی‌ها")
    parser.add_argument("--stats", action="store_true", help="نمایش آمار دیتابیس")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(SETTINGS.log_path, encoding="utf-8"), logging.StreamHandler()]
    )
    db = Database(SETTINGS.database_path)
    if args.stats:
        print(db.stats())
        for e in db.recent_events():
            print(dict(e))
        return

    runner = Runner(ManualImportProvider(args.csv))
    runner.run_once()
    print("پایان بررسی. آمار:", db.stats())
    if SETTINGS.dry_run:
        print("حالت آزمایشی فعال است؛ هیچ پیامی ارسال نشده است.")

if __name__ == "__main__":
    main()
