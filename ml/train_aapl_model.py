
import json
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Input, Dense
import joblib
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler


# 1. Load historical AAPL price data
df = pd.read_csv("AAPL_cleaned.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

# Calculate previous trading day's closing price
df["previous_close"] = df["close"].shift(1)

# Calculate features
df["daily_return"] = (
    (df["close"] - df["previous_close"]) / df["previous_close"]
)
df["intraday_range"] = (
    (df["high"] - df["low"]) / df["open"]
)
df["opening_gap"] = (
    (df["open"] - df["previous_close"]) / df["previous_close"]
)

# Remove the first row because it has no previous close
df = df.dropna(
    subset=[
        "previous_close",
        "daily_return",
        "intraday_range",
        "opening_gap",
    ]
).reset_index(drop=True)


# 2. Select features and split data chronologically
feature_columns = [
    "daily_return",
    "intraday_range",
    "opening_gap",
]

X = df[feature_columns].astype("float32")

# Split: 70% training, 15% validation, 15% testing
n = len(df)
train_end = int(n * 0.70)
val_end = int(n * 0.85)

X_train = X.iloc[:train_end]
X_val = X.iloc[train_end:val_end]
X_test = X.iloc[val_end:]

test_rows = df.iloc[val_end:].reset_index(drop=True)

print("Training observations:", len(X_train))
print("Validation observations:", len(X_val))
print("Test observations:", len(X_test))


# 3. Scale the features
scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)


# 4. Build and train the autoencoder
tf.keras.utils.set_random_seed(42)

model = Sequential([
    Input(shape=(len(feature_columns),)),
    Dense(2, activation="relu"),
    Dense(1, activation="relu"),
    Dense(2, activation="relu"),
    Dense(len(feature_columns), activation="linear"),
])

model.compile(
    optimizer="adam",
    loss="mae",
)

model.summary()

early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor="val_loss",
    patience=10,
    restore_best_weights=True,
)

history = model.fit(
    X_train_scaled,
    X_train_scaled,
    validation_data=(X_val_scaled, X_val_scaled),
    epochs=100,
    batch_size=32,
    shuffle=False,
    callbacks=[early_stopping],
    verbose=1,
)


# 5. Calculate reconstruction errors and threshold
def reconstruction_errors(data):
    reconstructed = model.predict(data, verbose=0)
    return np.mean(np.abs(data - reconstructed), axis=1)


train_errors = reconstruction_errors(X_train_scaled)
val_errors = reconstruction_errors(X_val_scaled)
test_errors = reconstruction_errors(X_test_scaled)

# 95th percentile of validation errors
threshold = float(np.percentile(val_errors, 95))

print("\nAnomaly threshold:", threshold)


# 6. Gather historical results
historical_results = []

for i, row in test_rows.iterrows():
    price = float(row["close"])
    previous_close = float(row["previous_close"])
    change = price - previous_close
    percent_change = (change / previous_close) * 100

    anomaly_score = float(test_errors[i])
    is_anomaly = bool(anomaly_score > threshold)

    result = {
        "symbol": "AAPL",
        "price": price,
        "change": float(change),
        "percent_change": float(percent_change),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "previous_close": previous_close,
        "features": {
            name: float(row[name])
            for name in feature_columns
        },
        "anomaly_score": anomaly_score,
        "anomaly_threshold": threshold,
        "is_anomaly": is_anomaly,
        "status": (
            "Anomaly Detected" if is_anomaly else "Normal"
        ),
        # Historical date rather than a live timestamp
        "quote_timestamp": row["date"].strftime("%Y-%m-%d"),
    }

    historical_results.append(result)


# Save results as JSON
with open("AAPL_historical_results.json", "w", encoding="utf-8") as f:
    json.dump(historical_results, f, indent=2)


print("\nSaved historical results:")

print(
    "\nTest observations flagged:",
    sum(r["is_anomaly"] for r in historical_results),
    "out of",
    len(historical_results),
)


# 7. Plot training history
plt.figure(figsize=(10, 5))
plt.plot(history.history["loss"], label="Training loss")
plt.plot(history.history["val_loss"], label="Validation loss")
plt.xlabel("Epoch")
plt.ylabel("Mean absolute error")
plt.title("Autoencoder Training History")
plt.legend()
plt.tight_layout()
plt.savefig("AAPL_training_history.png")
plt.show()


# 8. Save model and preprocessing artifacts
model.save("aapl.keras")
joblib.dump(scaler, "aapl_scaler.joblib")
joblib.dump(feature_columns, "aapl_feature_columns.joblib")
joblib.dump(threshold, "aapl_threshold.joblib")

print("\nSaved model, scaler, feature list, and threshold.")
