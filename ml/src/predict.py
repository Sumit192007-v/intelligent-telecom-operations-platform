
import os
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from ml.src.preprocessing import CLASSIFIER_FEATURES


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

configured_model_path = Path(
    os.getenv("ML_MODEL_PATH", "ml/models/latency_classifier.joblib")
)
MODEL_PATH = (
    configured_model_path
    if configured_model_path.is_absolute()
    else ROOT / configured_model_path
)


def load_model():
    """
    Load the trained ML model and its metadata.
    """

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Trained latency classifier is unavailable. "
            "Run `python -m ml.src.classify` to create it."
        )

    package = joblib.load(MODEL_PATH)

    required_keys = {
        "model",
        "threshold",
        "features",
    }

    missing_keys = required_keys - package.keys()

    if missing_keys:
        raise ValueError(
            "Saved model package is missing: "
            + ", ".join(sorted(missing_keys))
        )

    if package["features"] != CLASSIFIER_FEATURES:
        raise ValueError(
            "Saved classifier features do not match the current prediction API."
        )

    return package


def predict_latency(
    operator,
    hour,
    day_of_week,
    five_g_frequency_mhz=None,
    five_g_pci=None,
    lte_earfcn=None,
):
    """
    Predict whether network latency is elevated.

    Returns:
        dict containing prediction probability,
        threshold, and classification.
    """

    package = load_model()

    model = package["model"]
    threshold = package["threshold"]
    input_data = pd.DataFrame(
        [
            {
                "operator": operator,
                "hour": hour,
                "day_of_week": day_of_week,
                "5g_frequency_mhz": five_g_frequency_mhz,
                "5g_pci": five_g_pci,
                "lte_earfcn": lte_earfcn,
            }
        ]
    )

    input_data = input_data[CLASSIFIER_FEATURES]

    probability = model.predict_proba(
        input_data
    )[0][1]

    prediction = (
        probability >= threshold
    )

    if prediction:
        result = "Elevated Latency"
    else:
        result = "Normal Latency"

    return {
        "prediction": result,
        "probability": round(
            float(probability),
            4,
        ),
        "threshold": round(
            float(threshold),
            2,
        ),
    }


if __name__ == "__main__":

    # Test the reusable prediction function
    result = predict_latency(
        operator="AT&T",
        hour=14,
        day_of_week=5,
        five_g_frequency_mhz=None,
        five_g_pci=None,
        lte_earfcn=700,
    )

    print("Prediction result:")
    print(result)
