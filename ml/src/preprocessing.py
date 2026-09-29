from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "dataset/telecom_real_measurements.csv"
OUTPUT = ROOT / "ml/data/processed/telecom_clean.csv"
INPUT = ROOT / "ml/data/features/telecom_features.csv"


TARGET = "rtt_ms"

CORE_FEATURES = [
    "operator",
    "latitude",
    "longitude",
    "hour",
    "day_of_week",
]

RADIO_FEATURES = [
    "5g_frequency_mhz",
    "5g_pci",
    "lte_earfcn",
]

CLASSIFIER_FEATURES = [
    "operator",
    "hour",
    "day_of_week",
    "5g_frequency_mhz",
    "5g_pci",
    "lte_earfcn",
]


def load_data(path=SOURCE):
    return pd.read_csv(path)


def clean_data(df):
    required_columns = {"operator", "timestamp", "rtt_ms"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    cleaned = df.copy()
    cleaned["operator"] = cleaned["operator"].astype("string").str.strip()
    cleaned["timestamp"] = pd.to_datetime(
        cleaned["timestamp"], errors="coerce", utc=True
    )
    numeric_columns = [
        "latitude",
        "longitude",
        "download_mbps",
        "upload_mbps",
        "rtt_ms",
        *RADIO_FEATURES,
    ]
    for column in numeric_columns:
        if column in cleaned:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    return cleaned.dropna(subset=["operator", "timestamp", "rtt_ms"])


def preprocess_data(source=SOURCE, output=OUTPUT):
    cleaned = clean_data(load_data(source))
    output.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output, index=False)
    return cleaned


def build_preprocessor(
    include_radio=True,
    include_location=True,
    include_time=True,
):
    numeric_features = []

    if include_location:
        numeric_features += [
            "latitude",
            "longitude",
        ]

    if include_time:
        numeric_features += [
            "hour",
            "day_of_week",
        ]

    if include_radio:
        numeric_features += RADIO_FEATURES

    categorical_features = ["operator"]

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                ),
            )
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )

    return preprocessor


if __name__ == "__main__":
    df = preprocess_data()

    features = [*CORE_FEATURES, *RADIO_FEATURES]
    X = df[features]
    y = df[TARGET]

    preprocessor = build_preprocessor(
        include_radio=True,
        include_location=True,
        include_time=True,
    )

    X_transformed = preprocessor.fit_transform(X)

    print("Original feature columns:", len(features))
    print("Transformed feature shape:", X_transformed.shape)
    print("Target shape:", y.shape)
    print("Target missing values:", y.isna().sum())