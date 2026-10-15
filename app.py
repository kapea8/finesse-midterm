import math
import os

from dotenv import load_dotenv
from tensorflow import python

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH, override=True)


from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from extensions import db, limiter, socketio
from models import Run, Metric


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ[
        "DATABASE_URL"
    ]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True
    }
    app.config["API_KEY"] = os.environ.get("INGEST_API_KEY", "")
    origins = [
        item.strip()
        for item in os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
        if item.strip()
    ]

    CORS(app, origins=origins)
    db.init_app(app)
    limiter.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins=origins,
        async_mode="threading",
    )

    def authorized():
        configured = app.config["API_KEY"]
        supplied = request.headers.get("X-API-Key", "")
        return bool(configured) and supplied == configured

    @app.get("/")
    def home():
        return jsonify(
            message="ML Metrics API",
            status="running",
        )

    @app.get("/api/health")
    def health():
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify(status="ok", database="connected")
        except Exception:
            db.session.rollback()
            app.logger.exception("Database health check failed")
            return jsonify(
                status="error",
                database="unavailable",
            ), 503

    @app.get("/api/runs")
    def list_runs():
        runs = Run.query.order_by(
            Run.created_at.desc()
        ).limit(100).all()

        return jsonify([
            {
                "id": run.id,
                "name": run.name,
                "model_type": run.model_type,
                "status": run.status,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ])

    @app.post("/api/runs")
    @limiter.limit("30/minute")
    def create_run():
        if not authorized():
            return jsonify(error="Unauthorized"), 401

        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()

        if not name or len(name) > 120:
            return jsonify(
                error="Provide a name of 1–120 characters"
            ), 400

        run = Run(
            name=name,
            model_type=str(
                data.get("model_type", "unknown")
            )[:80],
            config=data.get("config"),
        )
        db.session.add(run)
        db.session.commit()

        result = serialize_run(run)
        socketio.emit("run_created", result)
        return jsonify(result), 201

    @app.post("/api/metrics")
    @limiter.limit("600/minute")
    def ingest_metrics():
        if not authorized():
            return jsonify(error="Unauthorized"), 401

        data = request.get_json(silent=True) or {}
        points = data.get("points")

        if not isinstance(points, list) or len(points) > 5000:
            return jsonify(
                error="points must be a list of at most 5000 items"
            ), 400

        clean = []
        try:
            for point in points:
                value = float(point["value"])
                step = int(point["step"])
                run_id = int(point["run_id"])
                name = str(point["name"]).strip()[:64]

                if (
                    not name
                    or step < 0
                    or not math.isfinite(value)
                ):
                    raise ValueError("Invalid metric values")

                clean.append({
                    "run_id": run_id,
                    "name": name,
                    "step": step,
                    "value": value,
                })
        except (KeyError, TypeError, ValueError, OverflowError):
            return jsonify(
                error="Each point needs valid run_id, name, step, and finite value"
            ), 400

        if not clean:
            return jsonify(stored=0)

        run_ids = {point["run_id"] for point in clean}
        existing_ids = {
            row[0]
            for row in db.session.execute(
                select(Run.id).where(Run.id.in_(run_ids))
            ).all()
        }

        if run_ids - existing_ids:
            return jsonify(error="Unknown run_id"), 400

        statement = mysql_insert(Metric).values(clean)
        statement = statement.on_duplicate_key_update(
            value=statement.inserted.value
        )
        db.session.execute(statement)
        db.session.commit()

        for run_id in run_ids:
            socketio.emit(
                "metrics",
                [
                    point for point in clean
                    if point["run_id"] == run_id
                ],
                room=f"run:{run_id}",
            )

        return jsonify(stored=len(clean)), 201

    @app.get("/api/runs/<int:run_id>/metrics")
    def get_metrics(run_id):
        since = request.args.get("since_step", -1, type=int)
        limit = min(
            max(request.args.get("limit", 500, type=int), 1),
            5000,
        )

        metrics = (
            Metric.query
            .filter(
                Metric.run_id == run_id,
                Metric.step > since,
            )
            .order_by(Metric.step.asc())
            .limit(limit)
            .all()
        )

        return jsonify([
            {
                "run_id": metric.run_id,
                "name": metric.name,
                "step": metric.step,
                "value": metric.value,
                "created_at": metric.created_at.isoformat(),
            }
            for metric in metrics
        ])

    @app.get("/api/runs/<int:run_id>/summary/<metric_name>")
    def metric_summary(run_id, metric_name):
        # TensorFlow performs the numeric summary calculations.
        import tensorflow as tf

        values = [
            row[0] for row in db.session.query(Metric.value)
            .filter(
                Metric.run_id == run_id,
                Metric.name == metric_name,
            )
            .order_by(Metric.step.asc())
            .limit(5000)
            .all()
        ]

        if not values:
            return jsonify(error="No matching metrics found"), 404

        tensor = tf.convert_to_tensor(values, dtype=tf.float32)
        result = {
            "run_id": run_id,
            "metric": metric_name,
            "count": len(values),
            "mean": float(tf.reduce_mean(tensor).numpy()),
            "min": float(tf.reduce_min(tensor).numpy()),
            "max": float(tf.reduce_max(tensor).numpy()),
            "stddev": float(tf.math.reduce_std(tensor).numpy()),
        }
        return jsonify(result)

    @socketio.on("subscribe_run")
    def subscribe_run(data):
        from flask_socketio import join_room

        try:
            run_id = int((data or {}).get("run_id"))
        except (TypeError, ValueError):
            return

        if db.session.get(Run, run_id) is not None:
            join_room(f"run:{run_id}")

    return app


def serialize_run(run):
    return {
        "id": run.id,
        "name": run.name,
        "model_type": run.model_type,
        "status": run.status,
        "created_at": run.created_at.isoformat(),
    }


app = create_app()

if __name__ == "__main__":
    socketio.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true",
        use_reloader=False,
    )



@app.post("/api/runs")
def create_demo_run():
    from flask import jsonify
    from models import Run
    from extensions import db

    try:
        run = Run(
            name="Demo Training Run",
            model_type="demo",
            status="completed",
            config={"source": "dashboard"}
        )

        db.session.add(run)
        db.session.commit()

        return jsonify({
            "message": "Demo run created successfully",
            "id": run.id,
            "run_id": run.id,
            "name": run.name,
            "model_type": run.model_type,
            "status": run.status
        }), 201

    except Exception:
        db.session.rollback()
        app.logger.exception("Could not create demo run")
        return jsonify({
            "error": "Could not create demo run"
        }), 500