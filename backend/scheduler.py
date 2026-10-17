import logging
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from stock_monitor_service import run_and_save_stock_check

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

EASTERN = ZoneInfo("America/New_York")

logging.basicConfig(
    level=os.getenv("SCHEDULER_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("stock-monitor-scheduler")


def scheduled_stock_check():
    """Run one scheduled check; log failures so later runs still happen."""
    logger.info("Starting scheduled AAPL anomaly check")
    try:
        result, created = run_and_save_stock_check("AAPL")
        if created:
            logger.info(
                "Saved run_id=%s price=%.2f anomaly=%s score=%.6f",
                result["run_id"],
                result["price"],
                result["is_anomaly"],
                result["anomaly_score"],
            )
        else:
            logger.info("Skipped duplicate quote: %s", result.get("skip_reason"))
    except requests.RequestException:
        logger.exception("Could not fetch the Finnhub quote; will retry next run")
    except Exception:
        logger.exception("Scheduled stock check failed; will retry next run")


def main():
    scheduler = BlockingScheduler(timezone=EASTERN)

    # Run at :35 each hour during the regular US stock-market session.
    # A final :55 run catches a quote closer to the 4:00 PM ET close.
    scheduler.add_job(
        scheduled_stock_check,
        trigger="cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute=35,
        id="aapl-hourly-market-check",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        scheduled_stock_check,
        trigger="cron",
        day_of_week="mon-fri",
        hour=15,
        minute=55,
        id="aapl-market-close-check",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    logger.info("Scheduler started. Time zone: America/New_York")
    logger.info("Checks: weekdays at :35 from 9 AM–3 PM ET, plus 3:55 PM ET")
    scheduler.start()


if __name__ == "__main__":
    main()
