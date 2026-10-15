from datetime import datetime

from extensions import db


class Run(db.Model):
    __tablename__ = "runs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    model_type = db.Column(
        db.String(80), nullable=False, default="unknown"
    )
    status = db.Column(
        db.String(24), nullable=False, default="running"
    )
    config = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )

    metrics = db.relationship(
        "Metric",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Metric(db.Model):
    __tablename__ = "metrics"

    id = db.Column(db.BigInteger, primary_key=True)
    run_id = db.Column(
        db.Integer,
        db.ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(64), nullable=False)
    step = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Float, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )

    run = db.relationship("Run", back_populates="metrics")

    __table_args__ = (
        db.UniqueConstraint(
            "run_id", "name", "step",
            name="uq_metric_run_name_step",
        ),
        db.Index(
            "ix_metrics_run_name_step",
            "run_id", "name", "step",
        ),
    )
