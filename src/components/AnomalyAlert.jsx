function AnomalyAlert() {
  const anomalyDetected = false;

  return (
    <div className={`anomaly-card ${anomalyDetected ? "anomaly" : "normal"}`}>
      <div>
        <h2>Anomaly Detection</h2>

        {anomalyDetected ? (
          <>
            <p className="anomaly-message">
              ⚠️ Anomaly detected
            </p>

            <p className="anomaly-details">
              Accuracy dropped below the expected range.
            </p>
          </>
        ) : (
          <>
            <p className="anomaly-message">
              🟢 No anomalies detected
            </p>

            <p className="anomaly-details">
              The model is currently operating within the expected range.
            </p>
          </>
        )}
      </div>

      <div className="anomaly-status">
        {anomalyDetected ? "ALERT" : "NORMAL"}
      </div>
    </div>
  );
}

export default AnomalyAlert;