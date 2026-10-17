
import { useCallback, useEffect, useState } from "react";
import "./App.css";

import MetricCard from "./components/MetricCard";
import HistoricalPriceChart from "./components/HistoricalPriceChart";
import { fetchRuns, fetchRunMetrics } from "./lib/api";

const API_BASE = "http://127.0.0.1:5000/api";
const BATCH_SIZE = 20;

function formatNumber(value, digits = 2) {
  if (value == null || !Number.isFinite(Number(value))) return "--";
  return Number(value).toFixed(digits);
}

function formatDate(value) {
  if (!value) return "--";

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "--"
    : date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
}

function getDetectionResult(value) {
  if (value == null) return "--";
  return Number(value) === 1 || value === true ? "Anomaly" : "Normal";
}

async function loadRunMetrics(run) {
  try {
    const response = await fetchRunMetrics(run.id);
    const metrics = Array.isArray(response)
      ? response
      : response.metrics ?? [];

    const values = Object.fromEntries(
      metrics.map(({ name, value }) => [name, Number(value)])
    );

    if (!Number.isFinite(values.price)) return null;

    return {
      id: run.id,
      date: run.started_at,
      price: values.price,
      isAnomaly: values.is_anomaly === 1,
      anomalyScore: values.anomaly_score,
      anomalyThreshold: values.anomaly_threshold,
      status: run.status,
    };
  } catch (err) {
    console.warn(`Could not load metrics for run ${run.id}:`, err);
    return null;
  }
}

function DetectionBadge({ isAnomaly }) {
  const type = isAnomaly ? "yes" : "no";

  return (
    <span className={`anomaly-badge anomaly-badge--${type}`}>
      {isAnomaly ? "Anomaly" : "Normal"}
    </span>
  );
}

function App() {
  const [result, setResult] = useState(null);
  const [runs, setRuns] = useState([]);
  const [historicalData, setHistoricalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [historyStartDate, setHistoryStartDate] = useState("");
  const [historyEndDate, setHistoryEndDate] = useState("");

  const loadDashboard = useCallback(async () => {
    try {
      setError("");

      const [latestResponse, runsData] = await Promise.all([
        fetch(`${API_BASE}/stock/latest`),
        fetchRuns(),
      ]);

      let latestResult = null;

      if (latestResponse.ok) {
        latestResult = await latestResponse.json();
      } else if (latestResponse.status !== 404) {
        throw new Error("Could not load the latest stock result.");
      }

      const allRuns = Array.isArray(runsData)
        ? runsData
        : runsData.runs ?? [];

      const sortedRuns = [...allRuns].sort(
        (a, b) =>
          new Date(b.started_at) - new Date(a.started_at) || b.id - a.id
      );

      setRuns(sortedRuns);

      const history = [];

      // Limit concurrent metric requests to batches of 20.
      for (let i = 0; i < sortedRuns.length; i += BATCH_SIZE) {
        const batch = sortedRuns.slice(i, i + BATCH_SIZE);
        const results = await Promise.all(batch.map(loadRunMetrics));
        history.push(...results.filter(Boolean));
      }

      setHistoricalData(history);

      if (latestResult) {
        const matchingRun = sortedRuns.find(
          (run) => Number(run.id) === Number(latestResult.run_id)
        );

        setResult({
          ...latestResult,
          observation_date:
            latestResult.observation_date ||
            matchingRun?.started_at ||
            latestResult.started_at,
        });
      } else {
        setResult(null);
      }
    } catch (err) {
      console.error("Dashboard loading error:", err);
      setError(err.message || "Could not load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  async function runAnalysis() {
    try {
      setRunning(true);
      setError("");

      const response = await fetch(`${API_BASE}/stock/AAPL/run`, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Stock analysis failed.");
      }

      await loadDashboard();
    } catch (err) {
      console.error("Stock analysis error:", err);
      setError(err.message || "Could not run stock analysis.");
    } finally {
      setRunning(false);
    }
  }

  // Date filters affect only the historical chart, not the dashboard's other sections.
  const filteredHistoricalData = historicalData.filter((item) => {
    if (!item.date) return false;

    const date = new Date(item.date);
    if (Number.isNaN(date.getTime())) return false;

    const dateKey = [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");

    if (historyStartDate && dateKey < historyStartDate) return false;
    if (historyEndDate && dateKey > historyEndDate) return false;
    return true;
  });

  const recentRuns = runs.slice(0, 5);

  const recentAnomalies = [...historicalData]
    .filter((item) => item.isAnomaly)
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .slice(0, 5);

  const historyById = new Map(
    historicalData.map((item) => [Number(item.id), item])
  );

  const latestDate =
    result?.observation_date ||
    result?.started_at ||
    historyById.get(Number(result?.run_id))?.date;

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">MODEL MONITORING</p>
          <h1>TensorFlow Web Monitor</h1>
          <p className="dashboard-subtitle">AAPL stock anomaly detection</p>
        </div>
      </header>

      <section className="analysis-panel">
        <div>
          <h2>Stock Analysis</h2>
          <p>Run the model against the latest available AAPL quote.</p>
          {result?.created_at && (
            <p className="last-run">
              Last saved: {new Date(result.created_at).toLocaleString()}
            </p>
          )}
        </div>

        <button
          className="run-button"
          onClick={runAnalysis}
          disabled={running}
        >
          {running ? "Analyzing..." : "Run Analysis"}
        </button>
      </section>

      {error && <p className="error-message">{error}</p>}
      {loading && <p>Loading dashboard data...</p>}

      {!loading && !error && (
        <>
          <section>
            <div className="section-heading">
              <div>
                <h2>Latest Result</h2>
                {result && (
                  <p className="result-date">
                    Observation date: {formatDate(latestDate)}
                  </p>
                )}
              </div>
              <span>
                {result ? `Run #${result.run_id}` : "No saved result"}
              </span>
            </div>

            <div className="metric-grid">
              <MetricCard
                title="Stock Price"
                value={result ? `$${formatNumber(result.price)}` : "--"}
              />
              <MetricCard
                title="Detection Result"
                value={getDetectionResult(result?.is_anomaly)}
              />
              <MetricCard
                title="Anomaly Score"
                value={formatNumber(result?.anomaly_score, 4)}
              />
              <MetricCard
                title="Anomaly Threshold"
                value={formatNumber(result?.anomaly_threshold, 4)}
              />
            </div>
          </section>

          <section className="dashboard-panel history-filter-panel">
            <div className="section-heading">
              <h2>Historical Chart Date Range</h2>
              <span>{filteredHistoricalData.length} observations</span>
            </div>
            <div className="history-date-filters">
              <label>
                Start date
                <input
                  type="date"
                  value={historyStartDate}
                  max={historyEndDate || undefined}
                  onChange={(event) => setHistoryStartDate(event.target.value)}
                />
              </label>
              <label>
                End date
                <input
                  type="date"
                  value={historyEndDate}
                  min={historyStartDate || undefined}
                  onChange={(event) => setHistoryEndDate(event.target.value)}
                />
              </label>
              <button
                type="button"
                className="run-button history-reset-button"
                onClick={() => {
                  setHistoryStartDate("");
                  setHistoryEndDate("");
                }}
                disabled={!historyStartDate && !historyEndDate}
              >
                Reset dates
              </button>
            </div>
          </section>

          <HistoricalPriceChart data={filteredHistoricalData} />

          <section className="dashboard-panel">
            <div className="section-heading">
              <h2>Recent Anomalies</h2>
              <span>Latest {recentAnomalies.length}</span>
            </div>

            {recentAnomalies.length === 0 ? (
              <p>No anomalous observations found in the saved runs.</p>
            ) : (
              <div className="table-wrapper">
                <table className="run-history-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Stock Price</th>
                      <th>Anomaly Score</th>
                      <th>Threshold</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentAnomalies.map((item) => (
                      <tr key={item.id}>
                        <td>{formatDate(item.date)}</td>
                        <td>${formatNumber(item.price)}</td>
                        <td>{formatNumber(item.anomalyScore, 4)}</td>
                        <td>{formatNumber(item.anomalyThreshold, 4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="dashboard-panel">
            <div className="section-heading">
              <h2>Recent Runs</h2>
              <span>Latest {recentRuns.length} runs</span>
            </div>

            {recentRuns.length === 0 ? (
              <p>No saved runs found yet.</p>
            ) : (
              <div className="table-wrapper">
                <table className="run-history-table">
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Observation Date</th>
                      <th>Stock Price</th>
                      <th>Detection</th>
                      <th>Anomaly Score</th>
                      <th>Threshold</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRuns.map((run) => {
                      const item = historyById.get(Number(run.id));

                      return (
                        <tr key={run.id}>
                          <td>#{run.id}</td>
                          <td>{formatDate(run.started_at)}</td>
                          <td>
                            {item ? `$${formatNumber(item.price)}` : "--"}
                          </td>
                          <td>
                            {item ? (
                              <DetectionBadge isAnomaly={item.isAnomaly} />
                            ) : (
                              <span className="anomaly-badge anomaly-badge--unknown">
                                No data
                              </span>
                            )}
                          </td>
                          <td>{formatNumber(item?.anomalyScore, 4)}</td>
                          <td>{formatNumber(item?.anomalyThreshold, 4)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}

export default App;
