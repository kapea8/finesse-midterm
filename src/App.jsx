import "./App.css";
import ModelStatus from "./components/ModelStatus";
import MetricCard from "./components/MetricCard";
import PerformanceChart from "./components/PerformanceChart";
import PredictionChart from "./components/PredictionChart";
import AnomalyAlert from "./components/AnomalyAlert";


function App() {
  return (
    <div className="dashboard">

      <h1>TensorFlow Web Monitor</h1>

      <ModelStatus />

      <div className="metric-grid">
        <MetricCard
          title="Accuracy"
          value="94.2"
          unit="%"
        />

        <MetricCard
          title="Precision"
          value="91.8"
          unit="%"
        />

        <MetricCard
          title="Recall"
          value="93.5"
          unit="%"
        />

      </div>

      <PerformanceChart />
      
      <PredictionChart />

      <AnomalyAlert />

    </div>
  );
}

export default App;