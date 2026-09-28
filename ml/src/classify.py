
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from preprocessing import build_preprocessor


ROOT = Path(__file__).resolve().parents[2]

INPUT = ROOT / "ml/data/features/telecom_features.csv"
MODEL_OUTPUT = ROOT / "ml/models/latency_classifier.joblib"

TARGET = "elevated_latency"

FEATURES = [
    "operator",
    "hour",
    "day_of_week",
    "5g_frequency_mhz",
    "5g_pci",
    "lte_earfcn",
]


def load_data():
    df = pd.read_csv(INPUT)

    df[TARGET] = (
        df["rtt_ms"] >= 75
    ).astype(int)

    return df


def create_model():

    preprocessor = build_preprocessor(
        include_radio=True,
        include_location=False,
        include_time=True,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def find_best_threshold(
    y_true,
    probabilities,
):

    thresholds = [
        i / 100
        for i in range(10, 91)
    ]

    best_threshold = 0.5
    best_f1 = -1

    for threshold in thresholds:

        predictions = (
            probabilities >= threshold
        ).astype(int)

        f1 = f1_score(
            y_true,
            predictions,
            zero_division=0,
        )

        if f1 > best_f1:

            best_f1 = f1
            best_threshold = threshold

    return best_threshold, best_f1


def main():

    df = load_data()

    # -----------------------------------------
    # Select d2 measurement campaign
    # -----------------------------------------

    d2_df = df[
        df["source_drive"] == "d2"
    ].copy()

    d2_df = d2_df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    # -----------------------------------------
    # Time-aware 80/20 split
    # -----------------------------------------

    split_index = int(
        len(d2_df) * 0.8
    )

    train_df = d2_df.iloc[
        :split_index
    ].copy()

    test_df = d2_df.iloc[
        split_index:
    ].copy()

    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]

    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]

    print(
        "Training rows:",
        len(train_df),
    )

    print(
        "Testing rows:",
        len(test_df),
    )

    # -----------------------------------------
    # Training-only threshold selection
    # -----------------------------------------

    print(
        "\nGenerating out-of-fold "
        "training probabilities..."
    )

    cv_model = create_model()

    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    oof_probabilities = cross_val_predict(
        cv_model,
        X_train,
        y_train,
        cv=cv,
        method="predict_proba",
        n_jobs=1,
    )[:, 1]

    threshold, training_f1 = (
        find_best_threshold(
            y_train,
            oof_probabilities,
        )
    )

    print(
        "\nSelected threshold:",
        threshold,
    )

    print(
        "Training OOF F1:",
        round(training_f1, 4),
    )

    # -----------------------------------------
    # Train final model
    # -----------------------------------------

    print(
        "\nTraining final Random Forest..."
    )

    final_model = create_model()

    final_model.fit(
        X_train,
        y_train,
    )

    # -----------------------------------------
    # Evaluate on untouched test set
    # -----------------------------------------

    probabilities = (
        final_model.predict_proba(
            X_test
        )[:, 1]
    )

    predictions = (
        probabilities >= threshold
    ).astype(int)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0,
    )

    roc_auc = roc_auc_score(
        y_test,
        probabilities,
    )

    matrix = confusion_matrix(
        y_test,
        predictions,
    )

    print(
        "\nFinal Model Evaluation"
    )

    print("-" * 40)

    print(
        f"Threshold: {threshold:.2f}"
    )

    print(
        f"Accuracy:  {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall:    {recall:.4f}"
    )

    print(
        f"F1 Score:  {f1:.4f}"
    )

    print(
        f"ROC-AUC:   {roc_auc:.4f}"
    )

    print(
        "\nConfusion Matrix:"
    )

    print(matrix)

    # -----------------------------------------
    # Save model + threshold + metadata
    # -----------------------------------------

    MODEL_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_package = {
        "model": final_model,
        "threshold": threshold,
        "target": TARGET,
        "features": FEATURES,
        "rtt_threshold_ms": 75,
        "training_drive": "d2",
    }

    joblib.dump(
        model_package,
        MODEL_OUTPUT,
    )

    print(
        "\nModel saved to:"
    )

    print(MODEL_OUTPUT)


if __name__ == "__main__":
    main()

