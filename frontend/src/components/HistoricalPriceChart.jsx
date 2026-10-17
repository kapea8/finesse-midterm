
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

import "./HistoricalPriceChart.css";

function HistoricalPriceChart({ data }) {
  const chartData = data
    .filter((item) => Number.isFinite(item.price))
    .sort((a, b) => new Date(a.date) - new Date(b.date));

  if (chartData.length === 0) {
    return (
      <section className="dashboard-panel">
        <h2>Historical Stock Price</h2>
        <p>No historical price data is available yet.</p>
      </section>
    );
  }

  const formattedData = chartData.map((item) => ({
    ...item,
    normalPrice: item.isAnomaly ? null : item.price,
    anomalyPrice: item.isAnomaly ? item.price : null,
  }));

  return (
    <section className="dashboard-panel historical-chart">
      <div className="section-heading">
        <h2>Historical Stock Price</h2>
        <span>{formattedData.length} observations</span>
      </div>

      <p className="chart-description">
        AAPL closing price over time, with detected anomalies highlighted.
      </p>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart
            data={formattedData}
            margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" />

            <XAxis
              dataKey="date"
              tickFormatter={(date) =>
                new Date(date).toLocaleDateString("en-US", {
                  month: "short",
                  year: "2-digit",
                })
              }
              minTickGap={35}
            />

            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(value) => `$${value}`}
            />


            <Tooltip
            labelFormatter={(date) => {
                const parsedDate = new Date(date);

                return Number.isNaN(parsedDate.getTime())
                ? String(date)
                : parsedDate.toLocaleDateString();
            }}
            formatter={(value, name) => {
                if (value === null || value === undefined) {
                return ["--", name];
                }

                const numericValue = Number(value);

                if (!Number.isFinite(numericValue)) {
                return [String(value), name];
                }

                return [`$${numericValue.toFixed(2)}`, name];
            }}
            contentStyle={{
                backgroundColor: "#ffffff",
                border: "1px solid #f0d6e0",
                borderRadius: "10px",
                color: "#432c38",
                boxShadow: "0 8px 24px rgba(154, 83, 112, 0.12)",
                }}
                labelStyle={{ color: "#432c38" }}
                itemStyle={{ color: "#b45c7a" }}
            />


            <Legend />

            <Line
              type="monotone"
              dataKey="price"
              name="Stock Price"
              stroke="#d982a3"
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />

            <Scatter
              dataKey="anomalyPrice"
              name="Detected Anomaly"
              fill="#c94f65"
              shape="circle"
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default HistoricalPriceChart;
