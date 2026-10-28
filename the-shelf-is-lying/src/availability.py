"""Estimate whether recorded inventory is practically available."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from metrics import precision_at_capacity


PROJECT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

NUMERIC_FEATURES = [
    "book_inventory",
    "markdown_depth",
    "days_since_sale",
    "days_since_verified_count",
    "sales_units_7d",
    "pickup_requested_7d",
    "pickup_cancelled_7d",
    "pickup_cancel_rate_7d",
    "returned_units_7d",
    "lost_demand_7d",
    "adjusted_units_30d",
    "peer_daily_sales",
    "days_remaining_in_season",
]

CATEGORICAL_FEATURES = ["archetype", "category"]


def rule_based_risk(frame: pd.DataFrame) -> pd.Series:
    """A clear baseline built from ordinary inventory warning signs."""

    cancellation_signal = frame["pickup_cancel_rate_7d"].clip(0, 1)
    no_sale_signal = (frame["days_since_sale"] / 14).clip(0, 1)
    return_signal = (frame["returned_units_7d"] / 3).clip(0, 1)
    count_age_signal = (frame["days_since_verified_count"] / 35).clip(0, 1)
    adjustment_signal = (frame["adjusted_units_30d"] / 3).clip(0, 1)
    markdown_signal = (frame["markdown_depth"] / 0.50).clip(0, 1)

    return (
        0.34 * cancellation_signal
        + 0.21 * no_sale_signal
        + 0.15 * return_signal
        + 0.12 * count_age_signal
        + 0.10 * adjustment_signal
        + 0.08 * markdown_signal
    ).clip(0, 1)


def build_model() -> Pipeline:
    preprocessing = ColumnTransformer(
        [
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            (
                "category",
                OneHotEncoder(handle_unknown="ignore", drop="first"),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    return Pipeline(
        [
            ("prepare", preprocessing),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=500,
                    random_state=2027,
                    solver="liblinear",
                ),
            ),
        ]
    )


def model_coefficients(model: Pipeline) -> pd.DataFrame:
    feature_names = model.named_steps["prepare"].get_feature_names_out()
    coefficients = model.named_steps["model"].coef_[0]
    return (
        pd.DataFrame({"feature": feature_names, "coefficient": coefficients})
        .assign(abs_coefficient=lambda frame: frame["coefficient"].abs())
        .sort_values("abs_coefficient", ascending=False)
        .drop(columns="abs_coefficient")
    )


def train_and_score() -> tuple[pd.DataFrame, pd.DataFrame]:
    model_table = pd.read_csv(
        PROCESSED_DIR / "model_table.csv", parse_dates=["date"]
    ).sort_values("date")
    snapshot = pd.read_csv(
        PROCESSED_DIR / "analysis_snapshot.csv", parse_dates=["date"]
    )

    cutoff = model_table["date"].quantile(0.75)
    train = model_table[model_table["date"] <= cutoff].copy()
    test = model_table[model_table["date"] > cutoff].copy()

    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    model = build_model()
    model.fit(train[features], train["availability_gap"])

    test_model_score = pd.Series(
        model.predict_proba(test[features])[:, 1], index=test.index
    )
    test_rule_score = rule_based_risk(test)

    metric_rows = []
    for method, scores in [
        ("Interpretable model", test_model_score),
        ("Business-rule baseline", test_rule_score),
    ]:
        metric_rows.append(
            {
                "method": method,
                "test_rows": len(test),
                "positive_rate": test["availability_gap"].mean(),
                "roc_auc": roc_auc_score(test["availability_gap"], scores),
                "average_precision": average_precision_score(
                    test["availability_gap"], scores
                ),
                "precision_top_20_percent": precision_at_capacity(
                    test["availability_gap"], scores, capacity_share=0.20
                ),
            }
        )

    snapshot["rule_risk"] = rule_based_risk(snapshot)
    snapshot["availability_risk"] = model.predict_proba(snapshot[features])[:, 1]
    snapshot["availability_confidence"] = (
        100 * (1 - snapshot["availability_risk"])
    ).round(1)

    metrics = pd.DataFrame(metric_rows)
    coefficients = model_coefficients(model)

    snapshot.to_csv(PROCESSED_DIR / "availability_scores.csv", index=False)
    metrics.to_csv(PROCESSED_DIR / "model_metrics.csv", index=False)
    coefficients.to_csv(PROCESSED_DIR / "model_coefficients.csv", index=False)

    print(metrics.round(3).to_string(index=False))
    return snapshot, metrics


if __name__ == "__main__":
    train_and_score()
