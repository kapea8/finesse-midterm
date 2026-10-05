import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

const data = [
  { category: "Class A", predictions: 120 },
  { category: "Class B", predictions: 85 },
  { category: "Class C", predictions: 95 },
  { category: "Class D", predictions: 60 },
];

function PredictionChart() {
  return (
    <div className="chart-container">
      <h2>Prediction Distribution</h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="category" />
          <YAxis />
          <Tooltip />

          <Bar
            dataKey="predictions"
            fill="#8884d8"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default PredictionChart;