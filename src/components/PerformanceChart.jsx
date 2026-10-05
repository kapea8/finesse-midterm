import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

const data = [
  { time: "10:00", accuracy: 91 },
  { time: "10:05", accuracy: 93 },
  { time: "10:10", accuracy: 94 },
  { time: "10:15", accuracy: 92 },
  { time: "10:20", accuracy: 95 },
];

function PerformanceChart() {
  return (
    <div className="chart-container">
      <h2>Model Accuracy</h2>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip />

          <Line
            type="monotone"
            dataKey="accuracy"
            stroke="#8884d8"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default PerformanceChart;