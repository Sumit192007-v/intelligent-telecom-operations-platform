from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parents[2]
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
    df = pd.read_csv(INPUT)

    features = CORE_FEATURES + RADIO_FEATURES
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