import importlib

import joblib

from ml.src.preprocessing import CLASSIFIER_FEATURES


class TestClassifier:
    def predict_proba(self, values):
        assert list(values.columns) == CLASSIFIER_FEATURES
        return [[0.2, 0.8]]


def test_staff_prediction_uses_classifier_features(
    api_client, monkeypatch, tmp_path
):
    client, _ = api_client
    predict_module = importlib.import_module("ml.src.predict")
    model_path = tmp_path / "classifier.joblib"
    joblib.dump(
        {
            "model": TestClassifier(),
            "threshold": 0.5,
            "features": CLASSIFIER_FEATURES,
        },
        model_path,
    )
    monkeypatch.setattr(predict_module, "MODEL_PATH", model_path)

    response = client.post(
        "/api/predict/",
        json={
            "operator": "AT&T",
            "hour": 14,
            "day_of_week": 5,
            "five_g_frequency_mhz": 3500,
            "five_g_pci": 101,
            "lte_earfcn": 700,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "prediction": "Elevated Latency",
        "probability": 0.8,
        "threshold": 0.5,
    }


def test_missing_classifier_returns_clear_service_error(
    api_client, monkeypatch, tmp_path
):
    client, _ = api_client
    predict_module = importlib.import_module("ml.src.predict")
    monkeypatch.setattr(predict_module, "MODEL_PATH", tmp_path / "missing.joblib")

    response = client.post(
        "/api/predict/",
        json={"operator": "AT&T", "hour": 14, "day_of_week": 5},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Latency classifier model is unavailable"
