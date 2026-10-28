"""A few checks for the business logic, without a production-style test suite."""

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from recommendations import choose_action, likely_hidden_location  # noqa: E402


class BusinessRuleTests(unittest.TestCase):
    def test_recent_return_points_to_returns_or_clearance(self) -> None:
        row = pd.Series(
            {
                "returned_units_7d": 2,
                "markdown_depth": 0.30,
                "adjusted_units_30d": 0,
                "days_since_verified_count": 10,
            }
        )
        self.assertEqual(likely_hidden_location(row), "returns or clearance")

    def test_repeated_failures_trigger_verification_hold(self) -> None:
        row = pd.Series(
            {
                "likely_location": "clearance",
                "sales_units_7d": 1,
                "availability_risk": 0.80,
                "pickup_cancelled_7d": 3,
                "markdown_depth": 0.30,
                "days_remaining_in_season": 20,
                "peer_daily_sales": 0.20,
            }
        )
        action, _, _ = choose_action(row)
        self.assertEqual(action, "Suppress online and verify")

    def test_model_table_excludes_hidden_inventory_states(self) -> None:
        model_table = pd.read_csv(PROJECT_DIR / "data" / "processed" / "model_table.csv")
        hidden_columns = {
            "physical_inventory",
            "findable_units",
            "clearance_units",
            "returns_area_units",
            "missing_record_units",
        }
        self.assertTrue(hidden_columns.isdisjoint(model_table.columns))

    def test_funded_actions_fit_each_store_budget(self) -> None:
        actions = pd.read_csv(PROJECT_DIR / "data" / "processed" / "action_queue.csv")
        stores = pd.read_csv(PROJECT_DIR / "data" / "raw" / "stores.csv")
        funded_minutes = (
            actions[actions["funded_this_week"]]
            .groupby("store_id", as_index=False)["labor_minutes"]
            .sum()
        )
        check = funded_minutes.merge(stores, on="store_id")
        self.assertTrue(
            (
                check["labor_minutes"]
                <= check["weekly_inventory_labor_hours"] * 60
            ).all()
        )


if __name__ == "__main__":
    unittest.main()

