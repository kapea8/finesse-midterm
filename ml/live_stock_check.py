import os
from dotenv import load_dotenv
from pathlib import Path
import requests
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from tensorflow.keras.models import load_model
import json



# 1. Load your trained model and matching artifacts
ML_DIR = Path(__file__).resolve().parent
model = load_model(ML_DIR / "aapl.keras")
scaler = joblib.load(ML_DIR / "aapl_scaler.joblib")
feature_columns = joblib.load(ML_DIR / "aapl_feature_columns.joblib")
threshold = joblib.load(ML_DIR / "aapl_threshold.joblib")

# 2. Get your Finnhub API key from an environment variable
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")
API_KEY = os.getenv("FINNHUB_API_KEY")
if not API_KEY:
    raise ValueError(
        "Set the FINNHUB_API_KEY environment variable first."
    )

# 3. Fetch the latest AAPL quote
def get_stock_result(symbol="AAPL"):

    url = "https://finnhub.io/api/v1/quote"

    response = requests.get(
        url,
        params={"symbol": "AAPL", "token": API_KEY},
        timeout=15,
    )
    response.raise_for_status()
    quote = response.json()

    # Check that Finnhub returned usable price data
    required = ["c", "h", "l", "o", "pc"]

    if any(quote.get(key) is None for key in required):
        raise ValueError(f"Incomplete quote returned: {quote}")

    if any(not np.isfinite(quote[key]) for key in required):
        raise ValueError(f"Invalid price data returned: {quote}")

    if quote["o"] <= 0 or quote["pc"] <= 0:
        raise ValueError(f"Invalid opening or previous closing price: {quote}")

    # 4. Convert quote data into the training features
    features = {
        "daily_return": (quote["c"] - quote["pc"]) / quote["pc"],
        "intraday_range": (quote["h"] - quote["l"]) / quote["o"],
        "opening_gap": (quote["o"] - quote["pc"]) / quote["pc"],
    }

    # Keep features in exactly the training order
    X = pd.DataFrame([features])[feature_columns]

    # 5. Scale, reconstruct, and calculate anomaly score
    X_scaled = scaler.transform(X)
    reconstructed = model.predict(X_scaled, verbose=0)

    anomaly_score = float(
        np.mean(np.abs(X_scaled - reconstructed))
    )

    is_anomaly = anomaly_score > float(threshold)

    # 6. Display results
    timestamp = quote.get("t")
    quote_time = (
        datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        if timestamp
        else "Unavailable"
    )

    result = {
        "symbol": symbol,
        "price": float(quote["c"]),
        "change": float(quote["d"]),
        "percent_change": float(quote["dp"]),
        "open": float(quote["o"]),
        "high": float(quote["h"]),
        "low": float(quote["l"]),
        "previous_close": float(quote["pc"]),
        "features": {
            name: float(value)
            for name, value in features.items()
        },
        "anomaly_score": float(anomaly_score),
        "anomaly_threshold": float(threshold),
        "is_anomaly": bool(is_anomaly),
        "status": (
            "Anomaly Detected" if is_anomaly else "Normal"
        ),
        "quote_timestamp": quote.get("t"),
    }

    return result

if __name__ == "__main__":
    print(json.dumps(get_stock_result(), indent=2))