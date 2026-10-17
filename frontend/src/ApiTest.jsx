
import { useEffect, useState } from "react";
import { fetchLatestMetrics } from "./services/api";

function ApiTest() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchLatestMetrics()
      .then(setMetrics)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p>API error: {error}</p>;
  if (!metrics) return <p>Loading metrics...</p>;

  return (
    <div>
      <h2>API Connection Test</h2>
      <p>Model: {metrics.model_name}</p>
      <p>
        Accuracy: {(metrics.metrics.accuracy * 100).toFixed(1)}%
      </p>
      <p>
        Precision: {(metrics.metrics.precision * 100).toFixed(1)}%
      </p>
      <p>
        Recall: {(metrics.metrics.recall * 100).toFixed(1)}%
      </p>
    </div>
  );
}

export default ApiTest;
