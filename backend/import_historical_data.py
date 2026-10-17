import json
import os
from datetime import datetime
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


# Paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "ml" / "AAPL_historical_results.json"

# Load the backend's environment configuration
load_dotenv(PROJECT_DIR / ".env")


def get_connection():
    """Connect to the existing MySQL database."""
    database = os.getenv("MYSQL_DATABASE")
    if not database:
        raise RuntimeError("MYSQL_DATABASE is missing from backend/.env")

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=database,
    )


def parse_date(value):
    """Convert the historical quote date into a MySQL datetime."""
    if not value:
        raise ValueError("A historical record is missing quote_timestamp.")

    # Supports date strings such as 2026-06-23 or ISO timestamps.
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    # MySQL DATETIME stores a naive datetime here.
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)

    return parsed


def build_metrics(record):
    """Convert one JSON result into numeric database metrics."""
    metrics = {
        "price": record.get("price"),
        "change": record.get("change"),
        "percent_change": record.get("percent_change"),
        "open": record.get("open"),
        "high": record.get("high"),
        "low": record.get("low"),
        "previous_close": record.get("previous_close"),
        "anomaly_score": record.get("anomaly_score"),
        "anomaly_threshold": record.get("anomaly_threshold"),
        "is_anomaly": int(bool(record.get("is_anomaly", False))),
    }

    features = record.get("features") or {}
    metrics.update({
        "daily_return": features.get("daily_return"),
        "intraday_range": features.get("intraday_range"),
        "opening_gap": features.get("opening_gap"),
    })

    # Avoid inserting missing or non-numeric values.
    for name, value in metrics.items():
        if value is None:
            raise ValueError(f"Missing metric '{name}' in historical record.")

        try:
            metrics[name] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid value for metric '{name}': {value!r}"
            ) from exc

    return metrics


def import_historical_data():
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"JSON file not found: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Expected the JSON file to contain a list of records.")

    connection = get_connection()
    cursor = connection.cursor()

    imported = 0
    skipped = 0

    try:
        for record in records:
            if record.get("symbol", "AAPL").upper() != "AAPL":
                skipped += 1
                continue

            observed_at = parse_date(record.get("quote_timestamp"))

            # Use a stable name/date pair to make reruns idempotent.
            run_name = (
                f"AAPL Historical Test - {observed_at.date().isoformat()}"
            )

            cursor.execute(
                """
                SELECT id
                FROM runs
                WHERE name = %s
                  AND model_type = %s
                  AND started_at = %s
                LIMIT 1
                """,
                (run_name, "autoencoder", observed_at),
            )

            if cursor.fetchone():
                skipped += 1
                continue

            metrics = build_metrics(record)

            cursor.execute(
                """
                INSERT INTO runs (name, model_type, status, started_at)
                VALUES (%s, %s, %s, %s)
                """,
                (run_name, "autoencoder", "completed", observed_at),
            )
            run_id = cursor.lastrowid

            for name, value in metrics.items():
                cursor.execute(
                    """
                    INSERT INTO metrics (run_id, name, value, recorded_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (run_id, name, value, observed_at),
                )

            imported += 1

        # Commit the imported records together.
        connection.commit()

        print(f"Historical records imported: {imported}")
        print(f"Records skipped: {skipped}")

    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    import_historical_data()
