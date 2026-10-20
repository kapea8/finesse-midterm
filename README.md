# TensorFlow Web Monitor

TensorFlow Web Monitor is a web application designed to identify unusual patterns in Apple (AAPL) stock data using a TensorFlow autoencoder. It combines a React dashboard, a Python backend, and MySQL storage to display stock analysis results, anomaly scores, thresholds, and historical analysis records.

## 👥 Team Members & Contributions

- **Leah Brown (leahbrown19)** - Documentation & Technical Communication (README Development, Model and Results Explanation, Presentation Design)
- **Kendall Harris (kehar48)** - Backend Development (API Integration, Deployment)
- **Kaitlyn Pearson (kapea8)** - Full-Stack Development (Dashboard UI, Backend Integration)

---

## 🚀 Live Demo

- **Application URL:** [Insert Link to Live App, e.g., Hugging Face Spaces / Streamlit Sharing / Vercel]
- *Note: This live demo must be fully functional and accessible during the live project presentation.*

### 🎥 Project Walkthrough

![Project Demo Walkthrough](path/to/your/demo.gif)

*Ensure your `demo.gif` is added to the repository and correctly linked above before the final submission deadline.*

---

## 🛠️ Installation & Setup

Follow these steps to set up the environment and run the project locally.

### Prerequisites

- Python 3.8+
- `pip`
- Git
- Node.js and npm
- MySQL

### Local Installation

```bash
# Clone the repository
git clone https://github.com/kapea8/finesse-midterm.git
cd finesse-midterm

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

---

## 📊 Dataset

- **Source:** [Finnhub Stock API](https://finnhub.io/), [Nasdaq Historical Stock Data](https://www.nasdaq.com/market-activity/stocks/aapl/historical)
- **Description:** Apple Inc. (AAPL) stock market data used to identify unusual trading patterns. The model analyzes three features: daily return, intraday price range, and opening price gap.
- **Data Pipeline:** Stock data is retrieved through Finnhub, processed into the three input features, and scaled before being analyzed by the TensorFlow autoencoder. The application displays the resulting anomaly scores and classifications.

---

## 🧠 Model Architecture & Training

- **Algorithm:** TensorFlow autoencoder for anomaly detection, using three features: daily return, intraday price range, and opening price gap.
- **Frameworks Used:** TensorFlow/Keras, scikit-learn, NumPy, and pandas.
- **Training Process:** Historical AAPL data is split chronologically into 70% training, 15% validation, and 15% testing. Features are scaled using `StandardScaler`. The model uses the Adam optimizer, mean absolute error (MAE) loss, a batch size of 32, and up to 100 epochs with early stopping. Anomalies are flagged when reconstruction error exceeds the 95th percentile of validation errors.
---

## 📈 Evaluation & Results

| Metric | Training Set | Test Set |
| :--- | :--- | :--- |
| MAE | 0.43 | 0.34 |

---
