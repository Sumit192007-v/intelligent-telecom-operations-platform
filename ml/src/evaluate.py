from pathlib import Path
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "ml/data/features/telecom_features.csv"
MODEL_PATH = ROOT / "ml/models/rtt_regressor.joblib"

def main():
    bundle = joblib.load(MODEL_PATH)
    features = bundle["features"]
    model = bundle["model"]
    df = pd.read_csv(INPUT).dropna(subset=features + ["rtt_ms"])
    _, X_test, _, y_test = train_test_split(
        df[features], df["rtt_ms"], test_size=0.2, random_state=42
    )
    pred = model.predict(X_test)
    rmse = mean_squared_error(y_test, pred) ** 0.5
    print({"MAE": mean_absolute_error(y_test,pred), "RMSE": rmse,
           "R2": r2_score(y_test,pred), "test_rows": len(y_test)})

if __name__ == "__main__":
    main()
