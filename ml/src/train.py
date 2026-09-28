from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

from preprocessing import build_preprocessor


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "ml/data/features/telecom_features.csv"


TARGET = "rtt_ms"

FEATURES = [
    "operator",
    "latitude",
    "longitude",
    "hour",
    "day_of_week",
]


def load_data():
    df = pd.read_csv(INPUT)
    return df


def create_model():
    preprocessor = build_preprocessor(include_radio=False)

    model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def evaluate(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    r2 = r2_score(y_true, y_pred)

    return mae, rmse, r2


if __name__ == "__main__":
    df = load_data()

    d2_df = df[df["source_drive"] == "d2"].copy()

    d2_df = d2_df.sort_values("timestamp").reset_index(drop=True)

    split_index = int(len(d2_df) * 0.8)

    train_df = d2_df.iloc[:split_index].copy()
    test_df = d2_df.iloc[split_index:].copy()

    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]

    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]

    print("Training rows:", len(X_train))
    print("Testing rows:", len(X_test))

    print("\nFeatures:")
    for feature in FEATURES:
        print("-", feature)

    print("\nTarget:", TARGET)

    model = create_model()

    print("\nTraining model...")
model.fit(X_train, y_train)

print("Training completed.")

predictions = model.predict(X_test)

mae, rmse, r2 = evaluate(y_test, predictions)

print("\nEvaluation on later portion of drive d2:")
print(f"MAE : {mae:.2f} ms")
print(f"RMSE: {rmse:.2f} ms")
print(f"R²  : {r2:.4f}")
print("\nActual RTT:")
print(y_test.describe().round(2).to_string())

print("\nPredicted RTT:")
print(pd.Series(predictions).describe().round(2).to_string())

print("\nFirst 20 actual vs predicted:")
comparison = pd.DataFrame({
    "actual": y_test.values[:20],
    "predicted": predictions[:20]
})
print(comparison.round(2).to_string(index=False))

print(
    "\nPrediction range:",
    round(predictions.min(), 2),
    "to",
    round(predictions.max(), 2),
    "ms"
)
import numpy as np

errors = np.abs(y_test.values - predictions)

baseline_prediction = y_train.mean()
baseline_errors = np.abs(y_test.values - baseline_prediction)

print("\nRobust error analysis:")

print("\nRandom Forest:")
print(f"Median AE: {np.median(errors):.2f} ms")
print(f"90th percentile AE: {np.percentile(errors, 90):.2f} ms")
print(f"95th percentile AE: {np.percentile(errors, 95):.2f} ms")
print(f"Within ±20 ms: {(errors <= 20).mean() * 100:.2f}%")
print(f"Within ±50 ms: {(errors <= 50).mean() * 100:.2f}%")

print("\nMean baseline:")
print(f"Median AE: {np.median(baseline_errors):.2f} ms")
print(f"90th percentile AE: {np.percentile(baseline_errors, 90):.2f} ms")
print(f"95th percentile AE: {np.percentile(baseline_errors, 95):.2f} ms")
print(f"Within ±20 ms: {(baseline_errors <= 20).mean() * 100:.2f}%")
print(f"Within ±50 ms: {(baseline_errors <= 50).mean() * 100:.2f}%")