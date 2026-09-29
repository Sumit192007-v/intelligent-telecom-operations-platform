import importlib

import pandas as pd

from ml.src.feature_engineering import build_features
from ml.src.preprocessing import CLASSIFIER_FEATURES, clean_data, load_data


def test_source_data_produces_classifier_features():
    source = pd.DataFrame(
        [
            {
                "operator": " AT&T ",
                "timestamp": "2023-05-13T14:29:00+00:00",
                "rtt_ms": "80.5",
                "download_mbps": "10",
                "upload_mbps": "2",
                "5g_frequency_mhz": None,
                "5g_pci": None,
                "lte_earfcn": "700",
                "source_drive": "d2",
            },
            {
                "operator": "Verizon",
                "timestamp": "not-a-timestamp",
                "rtt_ms": "20",
                "download_mbps": "5",
                "upload_mbps": "1",
                "source_drive": "d2",
            },
        ]
    )

    cleaned = clean_data(source)
    features = build_features(cleaned)

    assert len(features) == 1
    assert features.loc[0, "operator"] == "AT&T"
    assert features.loc[0, "hour"] == 14
    assert features.loc[0, "day_of_week"] == 5
    assert set(CLASSIFIER_FEATURES).issubset(features.columns)
    assert features.loc[0, "source_drive"] == "d2"


def test_tracked_dataset_produces_classifier_labels_and_features():
    cleaned = clean_data(load_data())
    features = build_features(cleaned)
    labels = (features["rtt_ms"] >= 75).astype(int)

    assert len(features) > 0
    assert set(CLASSIFIER_FEATURES).issubset(features.columns)
    assert set(labels.unique()) == {0, 1}
    assert "d2" in set(features["source_drive"].dropna())


def test_classifier_training_saves_model_usable_by_prediction(
    monkeypatch, tmp_path
):
    classifier_module = importlib.import_module("ml.src.classify")
    predict_module = importlib.import_module("ml.src.predict")
    feature_path = tmp_path / "features.csv"
    model_path = tmp_path / "latency_classifier.joblib"
    rows = []
    for index in range(50):
        rows.append(
            {
                "operator": "AT&T" if index % 2 else "Verizon",
                "timestamp": f"2023-05-{index + 1:02d}T12:00:00Z",
                "hour": index % 24,
                "day_of_week": index % 7,
                "5g_frequency_mhz": 3500 if index % 2 else None,
                "5g_pci": index % 1000,
                "lte_earfcn": 700 + index,
                "rtt_ms": 100 if index % 2 else 20,
                "source_drive": "d2",
            }
        )
    pd.DataFrame(rows).to_csv(feature_path, index=False)
    monkeypatch.setattr(classifier_module, "INPUT", feature_path)
    monkeypatch.setattr(classifier_module, "MODEL_OUTPUT", model_path)
    monkeypatch.setattr(predict_module, "MODEL_PATH", model_path)

    classifier_module.main()
    result = predict_module.predict_latency("AT&T", 12, 2, 3500, 101, 700)

    assert model_path.exists()
    assert result["prediction"] in {"Elevated Latency", "Normal Latency"}
    assert 0 <= result["probability"] <= 1