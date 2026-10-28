"""Prepare observable features for the inventory analysis.

The raw simulation contains hidden physical states so the project can be
evaluated. This module deliberately keeps those states out of the model table.
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
ANALYSIS_DAY_NUMBER = 87


def load_raw_tables() -> dict[str, pd.DataFrame]:
    date_columns = {
        "daily_inventory": ["date"],
        "returns": ["return_date", "resolved_date"],
        "pickup_orders": ["date"],
        "markdown_events": ["date"],
        "audits": ["date"],
    }

    tables = {}
    for name in [
        "stores",
        "products",
        "daily_inventory",
        "returns",
        "pickup_orders",
        "markdown_events",
        "audits",
    ]:
        tables[name] = pd.read_csv(
            RAW_DIR / f"{name}.csv",
            parse_dates=date_columns.get(name),
        )
    return tables


def add_rolling_sum(
    frame: pd.DataFrame,
    source_column: str,
    output_column: str,
    window: int,
) -> None:
    frame[output_column] = (
        frame.groupby(["store_id", "product_id"], sort=False)[source_column]
        .transform(lambda values: values.rolling(window, min_periods=1).sum())
        .astype(float)
    )


def build_daily_features(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    inventory = tables["daily_inventory"].sort_values(
        ["store_id", "product_id", "date"]
    )
    inventory = inventory.copy()

    inventory["total_sales"] = (
        inventory["in_store_sales"] + inventory["pickup_fulfilled"]
    )
    inventory["pickup_requested"] = (
        inventory["pickup_fulfilled"] + inventory["pickup_cancelled"]
    )
    inventory["absolute_adjustment"] = inventory["inventory_adjustment"].abs()

    for source, output, window in [
        ("total_sales", "sales_units_7d", 7),
        ("pickup_requested", "pickup_requested_7d", 7),
        ("pickup_cancelled", "pickup_cancelled_7d", 7),
        ("returned_units", "returned_units_7d", 7),
        ("lost_demand", "lost_demand_7d", 7),
        ("absolute_adjustment", "adjusted_units_30d", 30),
    ]:
        add_rolling_sum(inventory, source, output, window)

    inventory["pickup_cancel_rate_7d"] = np.where(
        inventory["pickup_requested_7d"] > 0,
        inventory["pickup_cancelled_7d"]
        / inventory["pickup_requested_7d"],
        0.0,
    )

    peer_sales = (
        inventory.groupby(["product_id", "date"], as_index=False)["total_sales"]
        .mean()
        .rename(columns={"total_sales": "peer_daily_sales"})
    )
    inventory = inventory.merge(peer_sales, on=["product_id", "date"], how="left")
    inventory = inventory.merge(tables["stores"], on="store_id", how="left")
    inventory = inventory.merge(tables["products"], on="product_id", how="left")

    season_end = inventory["date"].max()
    inventory["days_remaining_in_season"] = (
        season_end - inventory["date"]
    ).dt.days
    inventory["current_price"] = inventory["regular_price"] * (
        1 - inventory["markdown_depth"]
    )
    inventory["unit_margin"] = (
        inventory["current_price"] - inventory["unit_cost"]
    ).clip(lower=0)

    return inventory


def build_model_table(
    daily_features: pd.DataFrame,
    audits: pd.DataFrame,
) -> pd.DataFrame:
    observable_columns = [
        "date",
        "store_id",
        "product_id",
        "archetype",
        "category",
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
        "regular_price",
        "unit_cost",
        "unit_margin",
    ]

    model_table = audits[
        [
            "audit_id",
            "date",
            "store_id",
            "product_id",
            "availability_gap",
            "primary_location",
        ]
    ].merge(
        daily_features[observable_columns],
        on=["date", "store_id", "product_id"],
        how="left",
        validate="one_to_one",
    )
    return model_table


def prepare_and_save() -> tuple[pd.DataFrame, pd.DataFrame]:
    tables = load_raw_tables()
    daily_features = build_daily_features(tables)
    model_table = build_model_table(daily_features, tables["audits"])

    first_date = daily_features["date"].min()
    decision_date = first_date + pd.Timedelta(days=ANALYSIS_DAY_NUMBER)
    analysis_snapshot = daily_features[
        daily_features["date"].eq(decision_date)
    ].copy()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    model_table.to_csv(PROCESSED_DIR / "model_table.csv", index=False)
    analysis_snapshot.to_csv(PROCESSED_DIR / "analysis_snapshot.csv", index=False)

    print(f"Prepared {len(model_table):,} audited model rows")
    print(
        f"Prepared {len(analysis_snapshot):,} store-product rows "
        f"for {decision_date.date()}"
    )
    return model_table, analysis_snapshot


if __name__ == "__main__":
    prepare_and_save()

