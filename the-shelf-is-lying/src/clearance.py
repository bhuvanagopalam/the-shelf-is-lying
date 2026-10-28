"""Describe each store's clearance assortment and operational warning signs."""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"


def assortment_comparison(
    store_id: str,
    archetype: str,
    current_products: dict[str, set[str]],
    stores: pd.DataFrame,
) -> tuple[float, float]:
    """Return average peer overlap and share of locally unusual clearance SKUs."""

    store_set = current_products.get(store_id, set())
    peer_ids = stores.loc[
        stores["archetype"].eq(archetype) & stores["store_id"].ne(store_id),
        "store_id",
    ]
    peer_sets = [current_products.get(peer_id, set()) for peer_id in peer_ids]

    if not store_set or not peer_sets:
        return 0.0, 0.0

    overlaps = []
    for peer_set in peer_sets:
        union = store_set | peer_set
        overlaps.append(len(store_set & peer_set) / len(union) if union else 0.0)

    peer_product_counts = {
        product_id: sum(product_id in peer_set for peer_set in peer_sets)
        for product_id in store_set
    }
    unusual_count = sum(
        count < (len(peer_sets) / 2) for count in peer_product_counts.values()
    )
    return float(np.mean(overlaps)), unusual_count / len(store_set)


def describe_pattern(row: pd.Series, thresholds: pd.Series) -> str:
    if (
        row["return_origin_share"] > thresholds["return_origin_share"]
        and row["clearance_pickup_cancel_rate"]
        > thresholds["clearance_pickup_cancel_rate"]
    ):
        return "Return-heavy and difficult to fulfill"
    if (
        row["median_days_in_clearance"] > thresholds["median_days_in_clearance"]
        and row["clearance_sell_through_28d"]
        < thresholds["clearance_sell_through_28d"]
    ):
        return "Aging seasonal inventory"
    if (
        row["unusual_clearance_sku_share"]
        > thresholds["unusual_clearance_sku_share"]
    ):
        return "Highly localized assortment"
    return "Within peer pattern"


def build_clearance_fingerprints() -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = pd.read_csv(
        PROCESSED_DIR / "availability_scores.csv", parse_dates=["date"]
    )
    stores = pd.read_csv(RAW_DIR / "stores.csv")
    products = pd.read_csv(RAW_DIR / "products.csv")
    inventory = pd.read_csv(RAW_DIR / "daily_inventory.csv", parse_dates=["date"])
    returns = pd.read_csv(
        RAW_DIR / "returns.csv", parse_dates=["return_date", "resolved_date"]
    )
    markdowns = pd.read_csv(RAW_DIR / "markdown_events.csv", parse_dates=["date"])

    decision_date = scores["date"].max()
    window_start = decision_date - pd.Timedelta(days=27)

    current_clearance = scores[scores["clearance_units"] > 0].copy()
    current_products = {
        store_id: set(group["product_id"])
        for store_id, group in current_clearance.groupby("store_id")
    }

    first_clearance_date = (
        inventory[
            inventory["date"].le(decision_date)
            & inventory["clearance_units"].gt(0)
        ]
        .groupby(["store_id", "product_id"], as_index=False)["date"]
        .min()
        .rename(columns={"date": "first_clearance_date"})
    )
    current_clearance = current_clearance.merge(
        first_clearance_date, on=["store_id", "product_id"], how="left"
    )
    current_clearance["days_in_clearance"] = (
        decision_date - current_clearance["first_clearance_date"]
    ).dt.days
    current_clearance["stranded_clearance_units"] = np.where(
        (current_clearance["availability_risk"] >= 0.60)
        & (current_clearance["pickup_cancelled_7d"] > 0),
        current_clearance["clearance_units"],
        0,
    )

    recent_inventory = inventory[
        inventory["date"].between(window_start, decision_date)
    ]
    recent_clearance = recent_inventory[recent_inventory["clearance_units"] > 0]
    recent_activity = recent_clearance.groupby("store_id", as_index=False).agg(
        clearance_sales_28d=("clearance_sales", "sum"),
        clearance_pickup_requests=("pickup_fulfilled", "sum"),
        clearance_pickup_cancellations=("pickup_cancelled", "sum"),
    )

    current_summary = current_clearance.groupby("store_id", as_index=False).agg(
        clearance_units=("clearance_units", "sum"),
        clearance_sku_count=("product_id", "nunique"),
        median_days_in_clearance=("days_in_clearance", "median"),
        average_markdown_depth=("markdown_depth", "mean"),
        stranded_clearance_units=("stranded_clearance_units", "sum"),
    )

    return_activity = (
        returns[
            returns["return_date"].le(decision_date)
            & returns["return_date"].ge(window_start)
        ]
        .groupby("store_id", as_index=False)
        .agg(
            returned_units_28d=("quantity", "sum"),
            average_return_processing_days=("processing_days", "mean"),
            returns_over_three_days=(
                "processing_days",
                lambda values: float((values > 3).mean()),
            ),
            returns_sent_to_clearance=(
                "destination",
                lambda values: int((values == "clearance").sum()),
            ),
        )
    )

    markdown_activity = (
        markdowns[
            markdowns["date"].le(decision_date)
            & markdowns["date"].ge(window_start)
        ]
        .groupby("store_id", as_index=False)["units_moved_to_clearance"]
        .sum()
    )

    summary = stores[["store_id", "store_name", "archetype"]].merge(
        current_summary, on="store_id", how="left"
    )
    summary = summary.merge(recent_activity, on="store_id", how="left")
    summary = summary.merge(return_activity, on="store_id", how="left")
    summary = summary.merge(markdown_activity, on="store_id", how="left")
    summary = summary.fillna(0)

    summary["clearance_sell_through_28d"] = np.where(
        summary["clearance_sales_28d"] + summary["clearance_units"] > 0,
        summary["clearance_sales_28d"]
        / (summary["clearance_sales_28d"] + summary["clearance_units"]),
        0.0,
    )
    summary["clearance_pickup_cancel_rate"] = np.where(
        summary["clearance_pickup_requests"]
        + summary["clearance_pickup_cancellations"]
        > 0,
        summary["clearance_pickup_cancellations"]
        / (
            summary["clearance_pickup_requests"]
            + summary["clearance_pickup_cancellations"]
        ),
        0.0,
    )
    summary["return_origin_share"] = np.where(
        summary["returns_sent_to_clearance"]
        + summary["units_moved_to_clearance"]
        > 0,
        summary["returns_sent_to_clearance"]
        / (
            summary["returns_sent_to_clearance"]
            + summary["units_moved_to_clearance"]
        ),
        0.0,
    )

    overlap_values = summary.apply(
        lambda row: assortment_comparison(
            row["store_id"], row["archetype"], current_products, stores
        ),
        axis=1,
    )
    summary[["peer_assortment_overlap", "unusual_clearance_sku_share"]] = pd.DataFrame(
        overlap_values.tolist(), index=summary.index
    )

    thresholds = pd.Series(
        {
            "return_origin_share": summary["return_origin_share"].quantile(0.75),
            "clearance_pickup_cancel_rate": summary[
                "clearance_pickup_cancel_rate"
            ].median(),
            "median_days_in_clearance": summary[
                "median_days_in_clearance"
            ].quantile(0.75),
            "clearance_sell_through_28d": summary[
                "clearance_sell_through_28d"
            ].median(),
            "unusual_clearance_sku_share": summary[
                "unusual_clearance_sku_share"
            ].quantile(0.75),
        }
    )
    summary["clearance_pattern"] = summary.apply(
        describe_pattern, axis=1, thresholds=thresholds
    )

    current_clearance = current_clearance.merge(
        products[["product_id", "product_name"]],
        on="product_id",
        how="left",
        suffixes=("", "_lookup"),
    )
    if "product_name_lookup" in current_clearance:
        current_clearance["product_name"] = current_clearance[
            "product_name"
        ].fillna(current_clearance["product_name_lookup"])
        current_clearance = current_clearance.drop(columns="product_name_lookup")

    summary.to_csv(PROCESSED_DIR / "clearance_fingerprints.csv", index=False)
    current_clearance.to_csv(PROCESSED_DIR / "clearance_detail.csv", index=False)

    print(
        summary[
            [
                "store_name",
                "clearance_units",
                "unusual_clearance_sku_share",
                "clearance_pattern",
            ]
        ]
        .head(8)
        .round(2)
        .to_string(index=False)
    )
    return summary, current_clearance


if __name__ == "__main__":
    build_clearance_fingerprints()
