import pandas as pd

# Load the original Nasdaq file
df = pd.read_csv("AAPL_historical_data.csv")

# Remove accidental whitespace from column names
df.columns = df.columns.str.strip()

# Rename columns for easier use in Python
df = df.rename(columns={
    "Date": "date",
    "Close/Last": "close",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Volume": "volume"
})

# Convert date strings to datetime objects
df["date"] = pd.to_datetime(
    df["date"],
    format="%m/%d/%Y",
    errors="coerce"
)

# Remove dollar signs and commas, then convert prices to numbers
for column in ["close", "open", "high", "low"]:
    df[column] = pd.to_numeric(
        df[column]
        .astype(str)
        .str.replace("$", "", regex=False),
        errors="coerce"
    )

# Convert volume to a numeric column
df["volume"] = pd.to_numeric(
    df["volume"]
    .astype(str)
    .str.replace(",", "", regex=False),
    errors="coerce"
)


# Sort oldest to newest
df = (
    df.sort_values("date")
      .drop_duplicates(subset="date")
      .reset_index(drop=True)
)

# Save a separate cleaned copy
df.to_csv("AAPL_cleaned.csv", index=False)

print(df.head())
