import math
import sys
from pathlib import Path

import requests
from database import get_db_connection

PROJECT_DIR = Path(__file__).resolve().parent.parent
ML_DIR = PROJECT_DIR / "ml"

if not ML_DIR.is_dir():
    raise RuntimeError(
        f"ML_DIR does not exist: {ML_DIR}. "
        "Place the trained model files in the project's ml directory."
    )

if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from live_stock_check import get_stock_result


def run_and_save_stock_check(symbol="AAPL"):
    """Fetch a quote, run anomaly detection, and save a new run to MySQL.

    Returns (result, created). If Finnhub reports the same quote timestamp as
    the most recently saved check, no duplicate run is inserted.
    """
    result = get_stock_result(symbol.upper())
    quote_timestamp = result.get("quote_timestamp")

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Finnhub may return the same latest quote on repeated requests.
        # Save it only once when a usable quote timestamp is provided.
        if quote_timestamp is not None:
            cursor.execute(
                """
                SELECT m.value
                FROM runs r
                JOIN metrics m ON m.run_id = r.id
                WHERE r.model_type = %s
                  AND r.name LIKE %s
                  AND m.name = %s
                ORDER BY r.started_at DESC, r.id DESC
                LIMIT 1
                """,
                ("autoencoder", f"{result['symbol']} Stock Anomaly Check", "quote_timestamp"),
            )
            previous = cursor.fetchone()
            if previous and int(float(previous["value"])) == int(quote_timestamp):
                result["skipped"] = True
                result["skip_reason"] = "This quote timestamp has already been saved."
                return result, False

        cursor.execute(
            """
            INSERT INTO runs (name, model_type, status)
            VALUES (%s, %s, %s)
            """,
            (f"{result['symbol']} Stock Anomaly Check", "autoencoder", "completed"),
        )
        run_id = cursor.lastrowid

        metrics = {
            "price": result["price"],
            "change": result["change"],
            "percent_change": result["percent_change"],
            "open": result["open"],
            "high": result["high"],
            "low": result["low"],
            "previous_close": result["previous_close"],
            "anomaly_score": result["anomaly_score"],
            "anomaly_threshold": result["anomaly_threshold"],
            "is_anomaly": int(result["is_anomaly"]),
        }
        metrics.update(result["features"])
        if quote_timestamp is not None:
            metrics["quote_timestamp"] = quote_timestamp

        # The route's existing metrics table stores metric values as numbers.
        for name, value in metrics.items():
            if not math.isfinite(float(value)):
                raise ValueError(f"Invalid metric value: {name}")
            cursor.execute(
                "INSERT INTO metrics (run_id, name, value) VALUES (%s, %s, %s)",
                (run_id, name, float(value)),
            )

        connection.commit()
        result["run_id"] = run_id
        result["skipped"] = False
        return result, True

    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
