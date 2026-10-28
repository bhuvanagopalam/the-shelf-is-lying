"""Streamlit presentation for The Shelf Is Lying."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"


st.set_page_config(page_title="The Shelf Is Lying", page_icon="📦", layout="wide")


@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    return {
        "actions": pd.read_csv(PROCESSED_DIR / "action_queue.csv", parse_dates=["date"]),
        "clearance": pd.read_csv(PROCESSED_DIR / "clearance_fingerprints.csv"),
        "clearance_detail": pd.read_csv(
            PROCESSED_DIR / "clearance_detail.csv", parse_dates=["date"]
        ),
        "policy": pd.read_csv(PROCESSED_DIR / "policy_comparison.csv"),
        "metrics": pd.read_csv(PROCESSED_DIR / "model_metrics.csv"),
        "inventory": pd.read_csv(RAW_DIR / "daily_inventory.csv", parse_dates=["date"]),
        "returns": pd.read_csv(
            RAW_DIR / "returns.csv", parse_dates=["return_date", "resolved_date"]
        ),
        "stores": pd.read_csv(RAW_DIR / "stores.csv"),
        "products": pd.read_csv(RAW_DIR / "products.csv"),
    }


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{100 * value:.1f}%"


def executive_view(data: dict[str, pd.DataFrame]) -> None:
    actions = data["actions"]
    funded = actions[actions["funded_this_week"]]
    clearance = data["clearance"]
    model_result = data["metrics"].iloc[0]

    st.subheader("The inventory system can be right about quantity and wrong about availability")
    st.write(
        "This case follows a back-to-campus collection. It looks for products that "
        "remain in book inventory but may be trapped in returns, clearance, the "
        "backroom, or an inaccurate record."
    )

    columns = st.columns(4)
    columns[0].metric("Funded actions", f"{len(funded):,}")
    columns[1].metric(
        "Expected margin recovered", money(funded["expected_margin_recovered"].sum())
    )
    columns[2].metric(
        "Clearance units at decision date", f"{clearance['clearance_units'].sum():,.0f}"
    )
    columns[3].metric(
        "Precision in highest-risk 20%",
        percent(model_result["precision_top_20_percent"]),
    )

    left, right = st.columns(2)
    with left:
        action_mix = (
            funded.groupby("recommended_action", as_index=False)
            .agg(actions=("product_id", "size"))
            .sort_values("actions")
        )
        figure = px.bar(
            action_mix,
            x="actions",
            y="recommended_action",
            orientation="h",
            title="What stores should do this week",
            labels={"recommended_action": "", "actions": "Funded actions"},
        )
        figure.update_layout(showlegend=False)
        st.plotly_chart(figure)

    with right:
        policy = data["policy"].sort_values("gross_margin_recovered")
        figure = px.bar(
            policy,
            x="gross_margin_recovered",
            y="policy",
            orientation="h",
            title="Same labor budget, different inspection policy",
            labels={"policy": "", "gross_margin_recovered": "Gross margin recovered"},
        )
        figure.update_xaxes(tickprefix="$", tickformat=",")
        figure.update_layout(showlegend=False)
        st.plotly_chart(figure)

    st.info(
        "The proposed policy is not trying to find the most anomalies. It prioritizes "
        "the availability problems with the greatest recoverable margin per labor hour."
    )


def investigation_view(data: dict[str, pd.DataFrame]) -> None:
    actions = data["actions"]
    inventory = data["inventory"]
    returns = data["returns"]

    store_names = actions[["store_id", "store_name"]].drop_duplicates()
    store_label = st.selectbox("Store", store_names["store_name"], key="invest_store")
    store_id = store_names.loc[
        store_names["store_name"].eq(store_label), "store_id"
    ].iloc[0]

    store_actions = actions[actions["store_id"].eq(store_id)].sort_values(
        ["funded_this_week", "value_per_labor_hour", "availability_risk"],
        ascending=False,
    )
    product_label = st.selectbox(
        "Product",
        store_actions["product_name"],
        key="invest_product",
    )
    selected = store_actions[store_actions["product_name"].eq(product_label)].iloc[0]
    product_id = selected["product_id"]

    st.subheader(selected["recommended_action"])
    st.write(selected["action_reason"])

    columns = st.columns(4)
    columns[0].metric("Book inventory", f"{selected['book_inventory']:.0f}")
    columns[1].metric(
        "Availability confidence", f"{selected['availability_confidence']:.1f}%"
    )
    columns[2].metric("Likely location", selected["likely_location"])
    columns[3].metric(
        "Expected margin recovered", money(selected["expected_margin_recovered"])
    )

    history = inventory[
        inventory["store_id"].eq(store_id)
        & inventory["product_id"].eq(product_id)
    ].copy()
    figure = go.Figure()
    for column, label in [
        ("book_inventory", "Recorded inventory"),
        ("shelf_units", "Regular shelf"),
        ("clearance_units", "Clearance"),
        ("returns_area_units", "Returns / reshop"),
    ]:
        figure.add_trace(
            go.Scatter(x=history["date"], y=history[column], name=label, mode="lines")
        )
    figure.update_layout(
        title="Where the recorded units moved during the season",
        xaxis_title="",
        yaxis_title="Units",
        hovermode="x unified",
    )
    st.plotly_chart(figure)

    item_returns = returns[
        returns["store_id"].eq(store_id) & returns["product_id"].eq(product_id)
    ]
    if len(item_returns):
        st.caption(
            f"{len(item_returns)} return(s); average processing time "
            f"{item_returns['processing_days'].mean():.1f} days."
        )

    with st.expander("Show the simulation's hidden evaluation truth"):
        st.write(
            "These fields are used to evaluate the decision method. A real analyst "
            "would only observe them after a physical check."
        )
        st.dataframe(
            history[
                [
                    "date",
                    "physical_inventory",
                    "findable_units",
                    "damaged_units",
                    "missing_record_units",
                    "availability_gap",
                ]
            ].tail(20),
            hide_index=True,
            width="stretch",
        )


def clearance_view(data: dict[str, pd.DataFrame]) -> None:
    clearance = data["clearance"]
    detail = data["clearance_detail"]

    store_label = st.selectbox(
        "Store", clearance["store_name"], key="clearance_store"
    )
    store = clearance[clearance["store_name"].eq(store_label)].iloc[0]
    store_detail = detail[detail["store_id"].eq(store["store_id"])]

    st.subheader(store["clearance_pattern"])
    st.write(
        "A different clearance assortment is not automatically a problem. This "
        "comparison asks whether the difference reflects local demand or inventory "
        "that may be stranded after returns and markdown moves."
    )

    columns = st.columns(4)
    columns[0].metric("Clearance units", f"{store['clearance_units']:.0f}")
    columns[1].metric(
        "Assortment unlike peers", percent(store["unusual_clearance_sku_share"])
    )
    columns[2].metric(
        "28-day clearance sell-through", percent(store["clearance_sell_through_28d"])
    )
    columns[3].metric(
        "Returns sent to clearance", f"{store['returns_sent_to_clearance']:.0f}"
    )

    left, right = st.columns(2)
    with left:
        category_mix = (
            store_detail.groupby("category", as_index=False)["clearance_units"]
            .sum()
            .sort_values("clearance_units", ascending=False)
        )
        figure = px.bar(
            category_mix,
            x="category",
            y="clearance_units",
            title=f"{store_label} clearance mix",
            labels={"category": "", "clearance_units": "Units"},
        )
        st.plotly_chart(figure)

    with right:
        figure = px.scatter(
            clearance,
            x="unusual_clearance_sku_share",
            y="clearance_sell_through_28d",
            color="clearance_pattern",
            hover_name="store_name",
            title="Clearance differs by store for different reasons",
            labels={
                "unusual_clearance_sku_share": "Assortment unlike peers",
                "clearance_sell_through_28d": "28-day sell-through",
                "clearance_pattern": "Pattern",
            },
        )
        figure.update_xaxes(tickformat=".0%")
        figure.update_yaxes(tickformat=".0%")
        st.plotly_chart(figure)

    st.dataframe(
        store_detail[
            [
                "product_name",
                "category",
                "clearance_units",
                "days_in_clearance",
                "pickup_cancelled_7d",
                "availability_confidence",
            ]
        ]
        .sort_values(["pickup_cancelled_7d", "clearance_units"], ascending=False)
        .head(20),
        hide_index=True,
        width="stretch",
    )


def action_plan_view(data: dict[str, pd.DataFrame]) -> None:
    actions = data["actions"]
    store_names = actions[["store_id", "store_name"]].drop_duplicates()
    store_label = st.selectbox("Store", store_names["store_name"], key="action_store")
    store_id = store_names.loc[
        store_names["store_name"].eq(store_label), "store_id"
    ].iloc[0]
    labor_hours = st.slider("Inventory labor available this week", 1, 16, 8)

    store_actions = actions[
        actions["store_id"].eq(store_id)
        & actions["recommended_action"].ne("No action")
    ].sort_values("value_per_labor_hour", ascending=False)
    store_actions = store_actions.copy()
    store_actions["running_minutes"] = store_actions["labor_minutes"].cumsum()
    selected = store_actions[store_actions["running_minutes"] <= labor_hours * 60]

    columns = st.columns(3)
    columns[0].metric("Actions funded", f"{len(selected):,}")
    columns[1].metric(
        "Expected margin recovered", money(selected["expected_margin_recovered"].sum())
    )
    columns[2].metric(
        "Expected cancellations avoided",
        f"{selected['expected_cancellations_avoided'].sum():.1f}",
    )

    st.dataframe(
        selected[
            [
                "product_name",
                "book_inventory",
                "availability_confidence",
                "likely_location",
                "recommended_action",
                "labor_minutes",
                "expected_margin_recovered",
                "value_per_labor_hour",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "expected_margin_recovered": st.column_config.NumberColumn(
                "Expected margin", format="$%.2f"
            ),
            "value_per_labor_hour": st.column_config.NumberColumn(
                "Value / labor hour", format="$%.2f"
            ),
            "availability_confidence": st.column_config.NumberColumn(
                "Availability confidence", format="%.1f%%"
            ),
        },
    )


st.title("The Shelf Is Lying")
st.caption("Inventory truth, returns, and store-specific clearance recovery")

try:
    project_data = load_data()
except FileNotFoundError:
    st.error("Project data is missing. Run `python src/run_pipeline.py` first.")
    st.stop()

tab_overview, tab_investigation, tab_clearance, tab_actions = st.tabs(
    ["Executive overview", "Item investigation", "Clearance by store", "Weekly action plan"]
)

with tab_overview:
    executive_view(project_data)
with tab_investigation:
    investigation_view(project_data)
with tab_clearance:
    clearance_view(project_data)
with tab_actions:
    action_plan_view(project_data)

st.caption(
    "Fictional retailer and synthetic operational data. The project demonstrates a "
    "decision method; it does not describe any retailer's internal systems."
)

