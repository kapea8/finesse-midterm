
import os
import sys
import math
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
from database import get_db_connection

api = Blueprint("api", __name__, url_prefix="/api")

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
ML_DIR = PROJECT_DIR / "model"

if not ML_DIR.is_dir():
    raise RuntimeError(f"ML_DIR does not exist: {ML_DIR}")

sys.path.insert(0, str(ML_DIR))

from live_stock_check import get_stock_result


@api.route("/health", methods=["GET"])
def health():
    connection = None

    try:
        connection = get_db_connection()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except mysql_error():
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected"
        }), 500
    finally:
        if connection and connection.is_connected():
            connection.close()


@api.route("/runs", methods=["GET"])
def get_runs():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM runs ORDER BY started_at DESC, id DESC"
        )
        runs = cursor.fetchall()
        return jsonify(runs), 200
    finally:
        cursor.close()
        connection.close()


@api.route("/runs", methods=["POST"])
def create_run():
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    model_type = data.get("model_type")

    if not name or not model_type:
        return jsonify({
            "error": "name and model_type are required"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO runs (name, model_type, status)
            VALUES (%s, %s, %s)
            """,
            (name, model_type, "completed")
        )
        connection.commit()

        run_id = cursor.lastrowid

        return jsonify({
            "id": run_id,
            "name": name,
            "model_type": model_type,
            "status": "completed"
        }), 201
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


@api.route("/runs/<int:run_id>/metrics", methods=["GET"])
def get_run_metrics(run_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id FROM runs WHERE id = %s",
            (run_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Run not found"}), 404

        cursor.execute(
            """
            SELECT name, value, recorded_at
            FROM metrics
            WHERE run_id = %s
            ORDER BY recorded_at ASC
            """,
            (run_id,)
        )

        metrics = cursor.fetchall()
        return jsonify(metrics), 200
    finally:
        cursor.close()
        connection.close()


@api.route("/metrics", methods=["POST"])
def add_metrics():
    data = request.get_json(silent=True) or {}

    run_id = data.get("run_id")
    metrics = data.get("metrics", [])

    if not run_id or not metrics:
        return jsonify({
            "error": "run_id and metrics are required"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Make sure the run exists
        cursor.execute(
            "SELECT id FROM runs WHERE id = %s",
            (run_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Run not found"}), 404

        # Insert each metric
        for metric in metrics:
            name = metric.get("name")
            value = metric.get("value")

            if name is None or value is None:
                return jsonify({
                    "error": "Each metric needs a name and value"
                }), 400

            cursor.execute(
                """
                INSERT INTO metrics (run_id, name, value)
                VALUES (%s, %s, %s)
                """,
                (run_id, name, value)
            )

        connection.commit()

        return jsonify({
            "message": "Metrics saved successfully",
            "run_id": run_id,
            "count": len(metrics)
        }), 201

    except Exception as error:
        connection.rollback()
        return jsonify({"error": str(error)}), 500

    finally:
        cursor.close()
        connection.close()


@api.route("/stock/<symbol>/run", methods=["POST"])
def run_stock_inference(symbol):
    connection = None
    cursor = None

    try:
        # Fetch quote and run the autoencoder
        result = get_stock_result(symbol.upper())

        # Create a run record
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO runs (name, model_type, status)
            VALUES (%s, %s, %s)
            """,
            (
                f"{result['symbol']} Stock Anomaly Check",
                "autoencoder",
                "completed",
            ),
        )
        run_id = cursor.lastrowid

        # Save numeric results as metrics
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

        for name, value in metrics.items():
            if not math.isfinite(float(value)):
                raise ValueError(f"Invalid metric value: {name}")

            cursor.execute(
                """
                INSERT INTO metrics (run_id, name, value)
                VALUES (%s, %s, %s)
                """,
                (run_id, name, float(value)),
            )

        connection.commit()

        # Return the inference result, including its database run ID
        result["run_id"] = run_id
        return jsonify(result), 201

    except requests.RequestException:
        if connection:
            connection.rollback()
        return jsonify({"error": "Unable to fetch stock quote."}), 502

    except Exception as error:
        if connection:
            connection.rollback()
        return jsonify({
            "error": "Failed to run and save stock inference.",
            "details": str(error),
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@api.route("/stock/latest", methods=["GET"])
def get_latest_stock_result():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, model_type, status, started_at
            FROM runs
            WHERE model_type = %s
              AND name LIKE %s
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """,
            ("autoencoder", "%AAPL Stock Anomaly Check"),
        )
        run = cursor.fetchone()

        if run is None:
            return jsonify({
                "error": "No saved AAPL inference found. Run POST first."
            }), 404

        cursor.execute(
            """
            SELECT name, value, recorded_at
            FROM metrics
            WHERE run_id = %s
            ORDER BY recorded_at ASC
            """,
            (run["id"],),
        )
        rows = cursor.fetchall()

        metrics = {
            row["name"]: float(row["value"])
            for row in rows
        }

        feature_names = [
            "daily_return",
            "intraday_range",
            "opening_gap",
        ]

        return jsonify({
            "run_id": run["id"],
            "name": run["name"],
            "model_type": run["model_type"],
            "status": run["status"],
            "created_at": run["started_at"].isoformat()
                if run["started_at"] else None,
            "symbol": "AAPL",
            "price": metrics.get("price"),
            "change": metrics.get("change"),
            "percent_change": metrics.get("percent_change"),
            "anomaly_score": metrics.get("anomaly_score"),
            "anomaly_threshold": metrics.get("anomaly_threshold"),
            "is_anomaly": bool(metrics["is_anomaly"])
                if "is_anomaly" in metrics else None,
            "features": {
                name: metrics[name]
                for name in feature_names
                if name in metrics
            },
            "metrics": metrics,
        }), 200

    except Exception as error:
        return jsonify({
            "error": "Unable to retrieve saved stock result.",
            "details": str(error),
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@api.route("/stock/history", methods=["GET"])
def get_stock_history():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                r.id AS run_id,
                r.started_at,
                m.value AS anomaly_score
            FROM runs r
            JOIN metrics m ON m.run_id = r.id
            WHERE r.model_type = %s
              AND r.name LIKE %s
              AND m.name = %s
            ORDER BY r.started_at ASC, r.id ASC
            LIMIT 500
            """,
            (
                "autoencoder",
                "%AAPL Stock Anomaly Check",
                "anomaly_score",
            ),
        )

        rows = cursor.fetchall()

        history = [
            {
                "run_id": row["run_id"],
                "timestamp": row["started_at"].isoformat()
                    if row["started_at"] else None,
                "anomaly_score": float(row["anomaly_score"]),
            }
            for row in rows
        ]

        return jsonify(history), 200

    except Exception as error:
        return jsonify({
            "error": "Unable to retrieve stock history.",
            "details": str(error),
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def mysql_error():
    from mysql.connector import Error
    return Error
