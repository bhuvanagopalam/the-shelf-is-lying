"""Small metric helpers shared by the analysis modules."""

import numpy as np
import pandas as pd


def safe_rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def precision_at_capacity(
    labels: pd.Series,
    scores: pd.Series,
    capacity_share: float = 0.20,
) -> float:
    """Precision among the highest-risk records that can be inspected."""

    number_to_check = max(1, int(np.ceil(len(labels) * capacity_share)))
    selected = labels.loc[scores.nlargest(number_to_check).index]
    return float(selected.mean())


def dollars(value: float) -> str:
    return f"${value:,.0f}"

