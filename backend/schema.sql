
CREATE DATABASE IF NOT EXISTS tensorflow_monitor;

USE tensorflow_monitor;

CREATE TABLE IF NOT EXISTS runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    value DECIMAL(10,4) NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_metrics_run
        FOREIGN KEY (run_id) REFERENCES runs(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_runs_started_at
    ON runs(started_at);

CREATE INDEX idx_metrics_run_id
    ON metrics(run_id);
