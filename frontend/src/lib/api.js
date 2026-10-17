
const API_BASE_URL = "http://127.0.0.1:5000/api";

// Fetch all model runs
export async function fetchRuns() {
  const response = await fetch(`${API_BASE_URL}/runs`);

  if (!response.ok) {
    throw new Error("Failed to fetch model runs");
  }

  return response.json();
}

// Fetch metrics for one model run
export async function fetchRunMetrics(runId) {
  const response = await fetch(
    `${API_BASE_URL}/runs/${runId}/metrics`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch model metrics");
  }

  return response.json();
}
