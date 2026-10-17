
function RunHistory({ runs = [] }) {
  const recentRuns = [...runs]
    .sort((a, b) => b.id - a.id)
    .slice(0, 5);

  function formatPercent(value) {
    if (value === undefined || value === null ||
        !Number.isFinite(Number(value))) {
      return "--";
    }

    const number = Number(value);
    return `${(number <= 1 ? number * 100 : number).toFixed(1)}%`;
  }

  function formatTime(value) {
    if (value === undefined || value === null ||
        !Number.isFinite(Number(value))) {
      return "--";
    }

    return `${Number(value).toFixed(2)} s`;
  }

  return (
    <div className="chart-container run-history">
      <h2>Recent Run History</h2>
      <p className="run-history-subtitle">
        Showing the {recentRuns.length} most recent model runs
      </p>

      <div className="run-history-table-wrapper">
        <table className="run-history-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Accuracy</th>
              <th>Precision</th>
              <th>Recall</th>
              <th>F1 Score</th>
              <th>Training Time</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {recentRuns.map((run) => (
              <tr key={run.id}>
                <td>{run.runName || `Run #${run.id}`}</td>
                <td>{formatPercent(run.accuracy)}</td>
                <td>{formatPercent(run.precision)}</td>
                <td>{formatPercent(run.recall)}</td>
                <td>{formatPercent(run.f1_score)}</td>
                <td>{formatTime(run.training_time_seconds)}</td>
                <td>{run.status || "--"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {recentRuns.length === 0 && (
        <p>No model runs available yet.</p>
      )}
    </div>
  );
}

export default RunHistory;
