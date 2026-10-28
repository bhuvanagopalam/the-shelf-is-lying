"""Turn availability risk into a weekly store action plan."""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
LABOR_COST_PER_HOUR = 18.0
STANDARD_CHECK_MINUTES = 15


def likely_hidden_location(row: pd.Series) -> str:
    if row["returned_units_7d"] >= 1 and row["markdown_depth"] > 0:
        return "returns or clearance"
    if row["returned_units_7d"] >= 1:
        return "returns or reshop"
    if row["markdown_depth"] > 0:
        return "clearance"
    if row["adjusted_units_30d"] > 0 or row["days_since_verified_count"] > 35:
        return "inventory record discrepancy"
    return "backroom or misplaced shelf stock"


def choose_action(row: pd.Series) -> tuple[str, str, int]:
    location = row["likely_location"]
    local_daily_sales = row["sales_units_7d"] / 7

    if row["availability_risk"] < 0.35 and row["pickup_cancelled_7d"] == 0:
        return (
            "No action",
            "Availability risk is low and no recent pickup failure requires review.",
            0,
        )

    if row["pickup_cancelled_7d"] >= 2 and row["availability_risk"] >= 0.65:
        return (
            "Suppress online and verify",
            "Repeated pickup failures make another guest promise riskier than a short verification hold.",
            18,
        )

    if location in {"returns or clearance", "returns or reshop"}:
        return (
            "Search returns and clearance",
            "Recent returns make a processed-but-not-replaced unit a credible explanation.",
            14,
        )

    if (
        row["markdown_depth"] > 0
        and row["days_remaining_in_season"] <= 24
        and row["sales_units_7d"] == 0
        and row["peer_daily_sales"] < 0.10
    ):
        return (
            "Deepen markdown",
            "The selling window is short and both local and peer demand are weak.",
            8,
        )

    if (
        row["markdown_depth"] > 0
        and row["peer_daily_sales"] > local_daily_sales + 0.12
        and row["days_remaining_in_season"] > 14
    ):
        return (
            "Review for transfer",
            "Peer stores are selling faster while enough season remains to move the units.",
            20,
        )

    return (
        "Verify shelf and cycle count",
        "The recorded quantity is not supported by recent selling and fulfillment behavior.",
        12,
    )


def recovery_probability(location: str) -> float:
    return {
        "returns or clearance": 0.78,
        "returns or reshop": 0.82,
        "clearance": 0.70,
        "backroom or misplaced shelf stock": 0.66,
        "inventory record discrepancy": 0.18,
    }[location]


def add_action_economics(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["likely_location"] = frame.apply(likely_hidden_location, axis=1)

    choices = frame.apply(choose_action, axis=1)
    frame[["recommended_action", "action_reason", "labor_minutes"]] = pd.DataFrame(
        choices.tolist(), index=frame.index
    )

    frame["estimated_recoverable_units"] = np.ceil(
        frame["book_inventory"] * frame["availability_risk"]
    ).clip(lower=0)
    frame["remaining_demand_units"] = np.ceil(
        np.maximum(frame["sales_units_7d"] / 7, frame["peer_daily_sales"])
        * frame["days_remaining_in_season"]
    )
    frame["expected_units_recovered"] = np.minimum(
        frame["estimated_recoverable_units"], frame["remaining_demand_units"]
    ) * frame["likely_location"].map(recovery_probability)

    frame["expected_margin_recovered"] = (
        frame["expected_units_recovered"] * frame["unit_margin"]
    )
    frame["labor_cost"] = frame["labor_minutes"] / 60 * LABOR_COST_PER_HOUR
    frame["expected_net_value"] = (
        frame["expected_margin_recovered"] - frame["labor_cost"]
    )
    frame["expected_cancellations_avoided"] = np.minimum(
        frame["pickup_cancelled_7d"], frame["expected_units_recovered"]
    )
    frame["value_per_labor_hour"] = np.where(
        frame["labor_minutes"] > 0,
        frame["expected_net_value"] / (frame["labor_minutes"] / 60),
        0.0,
    )

    uneconomic = frame["expected_net_value"] <= 0
    frame.loc[uneconomic, "recommended_action"] = "No action"
    frame.loc[uneconomic, "action_reason"] = (
        "The expected recovery does not justify the labor required."
    )
    frame.loc[uneconomic, "labor_minutes"] = 0
    frame.loc[uneconomic, "value_per_labor_hour"] = 0.0
    return frame


def fund_weekly_actions(frame: pd.DataFrame) -> pd.DataFrame:
    """Fund the highest-value actions within each store's weekly capacity."""

    funded_groups = []
    for _, group in frame.groupby("store_id", sort=False):
        group = group.sort_values("value_per_labor_hour", ascending=False).copy()
        budget_minutes = int(group["weekly_inventory_labor_hours"].iloc[0] * 60)
        eligible_minutes = group["labor_minutes"].where(
            group["recommended_action"].ne("No action"), 0
        )
        group["cumulative_labor_minutes"] = eligible_minutes.cumsum()
        group["funded_this_week"] = (
            group["recommended_action"].ne("No action")
            & group["cumulative_labor_minutes"].le(budget_minutes)
        )
        funded_groups.append(group)
    return pd.concat(funded_groups, ignore_index=True)


def actual_recoverable_units(row: pd.Series) -> int:
    """Hidden simulation truth used only to compare decision policies."""

    return int(
        row["backroom_units"]
        + row["returns_area_units"]
        + row["clearance_units"]
    )


def select_with_store_capacity(
    frame: pd.DataFrame,
    ranking_column: str,
    ascending: bool = False,
) -> pd.DataFrame:
    selections = []
    for _, group in frame.groupby("store_id"):
        checks_available = int(
            group["weekly_inventory_labor_hours"].iloc[0]
            * 60
            / STANDARD_CHECK_MINUTES
        )
        selections.append(
            group.sort_values(ranking_column, ascending=ascending).head(checks_available)
        )
    return pd.concat(selections, ignore_index=True)


def compare_policies(frame: pd.DataFrame) -> pd.DataFrame:
    evaluation = frame[frame["book_inventory"] > 0].copy()
    evaluation["random_order"] = np.random.default_rng(2027).random(len(evaluation))
    evaluation["actual_recoverable_units"] = evaluation.apply(
        actual_recoverable_units, axis=1
    )
    evaluation["evaluation_demand_cap"] = np.maximum(
        1, evaluation["remaining_demand_units"]
    )
    evaluation["actual_units_recovered"] = np.minimum(
        evaluation["actual_recoverable_units"], evaluation["evaluation_demand_cap"]
    )

    policies = [
        ("Proposed value ranking", "value_per_labor_hour", False),
        ("Cancellation-first", "pickup_cancelled_7d", False),
        ("Largest book quantity", "book_inventory", False),
        ("Random inspection", "random_order", False),
    ]
    rows = []
    for name, ranking, ascending in policies:
        selected = select_with_store_capacity(evaluation, ranking, ascending)
        margin_recovered = (
            selected["actual_units_recovered"] * selected["unit_margin"]
        ).sum()
        rows.append(
            {
                "policy": name,
                "checks": len(selected),
                "labor_hours": len(selected) * STANDARD_CHECK_MINUTES / 60,
                "availability_problems_found": int(
                    selected["availability_gap"].sum()
                ),
                "precision": selected["availability_gap"].mean(),
                "recoverable_units_found": int(
                    selected["actual_units_recovered"].sum()
                ),
                "gross_margin_recovered": margin_recovered,
            }
        )
    return pd.DataFrame(rows)


def build_recommendations() -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = pd.read_csv(
        PROCESSED_DIR / "availability_scores.csv", parse_dates=["date"]
    )
    stores = pd.read_csv(RAW_DIR / "stores.csv")

    candidates = scores[scores["book_inventory"] > 0].copy()
    candidates = candidates.merge(
        stores[["store_id", "weekly_inventory_labor_hours"]],
        on="store_id",
        how="left",
        suffixes=("", "_store"),
    )
    if "weekly_inventory_labor_hours_store" in candidates:
        candidates["weekly_inventory_labor_hours"] = candidates[
            "weekly_inventory_labor_hours"
        ].fillna(candidates["weekly_inventory_labor_hours_store"])
        candidates = candidates.drop(columns="weekly_inventory_labor_hours_store")

    candidates = add_action_economics(candidates)
    queue = fund_weekly_actions(candidates)
    comparison = compare_policies(queue)

    output_columns = [
        "date",
        "store_id",
        "store_name",
        "archetype",
        "product_id",
        "product_name",
        "category",
        "book_inventory",
        "markdown_depth",
        "availability_confidence",
        "availability_risk",
        "pickup_cancelled_7d",
        "returned_units_7d",
        "days_since_sale",
        "likely_location",
        "recommended_action",
        "action_reason",
        "labor_minutes",
        "expected_units_recovered",
        "expected_margin_recovered",
        "expected_net_value",
        "expected_cancellations_avoided",
        "value_per_labor_hour",
        "funded_this_week",
    ]
    queue[output_columns].to_csv(PROCESSED_DIR / "action_queue.csv", index=False)
    comparison.to_csv(PROCESSED_DIR / "policy_comparison.csv", index=False)

    print(comparison.round(2).to_string(index=False))
    return queue[output_columns], comparison


if __name__ == "__main__":
    build_recommendations()

