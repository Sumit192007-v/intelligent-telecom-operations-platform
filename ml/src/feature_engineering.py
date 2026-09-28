from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "ml/data/processed/telecom_clean.csv"
OUTPUT = ROOT / "ml/data/features/telecom_features.csv"

def build_features(df):
    out = df.copy()
    out["timestamp"] = pd.to_datetime(
    out["timestamp"],
    format="ISO8601",
    errors="coerce",
    utc=True
)
    out["hour"] = out["timestamp"].dt.hour
    out["day_of_week"] = out["timestamp"].dt.dayofweek
    out["throughput_total_mbps"] = out["download_mbps"].fillna(0) + out["upload_mbps"].fillna(0)
    return out

if __name__ == "__main__":
    df = pd.read_csv(INPUT)
    features = build_features(df)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUTPUT, index=False)
    print(f"Saved {len(features)} rows to {OUTPUT}")
