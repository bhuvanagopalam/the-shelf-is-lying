"""Create a small, traceable retail dataset for the project.

The simulation keeps two views of inventory:

* book inventory: what the inventory system believes is present;
* physical state: where units actually are in the store.

Book inventory can be positive even when units are sitting in returns, hidden in
clearance, damaged, or missing. Keeping those states separate lets the later
analysis test whether an item offered online was truly findable.
"""

from pathlib import Path

import numpy as np
import pandas as pd


SEED = 2027
START_DATE = pd.Timestamp("2027-06-01")
NUMBER_OF_DAYS = 112
NUMBER_OF_STORES = 24
NUMBER_OF_PRODUCTS = 120

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_DIR / "data" / "raw"


STORE_ARCHETYPES = [
    "College Town",
    "Urban Small Format",
    "Suburban Family",
    "High Digital Demand",
    "Warm Weather",
    "Lower Volume",
]

CATEGORY_PRODUCTS = {
    "Storage": [
        "Three-Tier Cart",
        "Under-Bed Storage Bin",
        "Fabric Cube Organizer",
        "Stackable Drawer",
        "Over-Door Organizer",
    ],
    "Bedding": [
        "Twin XL Sheet Set",
        "Reversible Comforter",
        "Mattress Topper",
        "Bed Pillow Pair",
        "Throw Blanket",
    ],
    "Bath": [
        "Quick-Dry Towel Set",
        "Shower Caddy",
        "Bath Mat",
        "Laundry Hamper",
        "Robe Hook Set",
    ],
    "Desk": [
        "LED Desk Lamp",
        "Desktop Organizer",
        "Lap Desk",
        "Cork Memo Board",
        "Cable Management Kit",
    ],
    "Kitchen": [
        "Food Storage Set",
        "Compact Dish Rack",
        "Insulated Tumbler",
        "Microwave Bowl Set",
        "Reusable Cutlery Kit",
    ],
    "Decor": [
        "Wall Photo Grid",
        "Accent Pillow",
        "String Light Set",
        "Small Area Rug",
        "Tabletop Mirror",
    ],
}

STYLES = ["Essential", "Modern", "Soft", "Compact"]


def make_stores(rng: np.random.Generator) -> pd.DataFrame:
    """Create four stores for each market archetype."""

    rows = []
    for index in range(NUMBER_OF_STORES):
        archetype = STORE_ARCHETYPES[index % len(STORE_ARCHETYPES)]

        volume_multiplier = {
            "College Town": 1.20,
            "Urban Small Format": 0.90,
            "Suburban Family": 1.10,
            "High Digital Demand": 1.05,
            "Warm Weather": 0.95,
            "Lower Volume": 0.70,
        }[archetype]

        pickup_share = {
            "College Town": 0.32,
            "Urban Small Format": 0.38,
            "Suburban Family": 0.26,
            "High Digital Demand": 0.48,
            "Warm Weather": 0.28,
            "Lower Volume": 0.22,
        }[archetype]

        rows.append(
            {
                "store_id": f"S{index + 1:02d}",
                "store_name": f"{archetype} {index // len(STORE_ARCHETYPES) + 1}",
                "archetype": archetype,
                "volume_multiplier": round(
                    volume_multiplier * rng.uniform(0.90, 1.10), 3
                ),
                "pickup_share": round(pickup_share * rng.uniform(0.90, 1.10), 3),
                "execution_score": round(rng.uniform(0.58, 0.94), 3),
                "clearance_capacity_units": int(rng.integers(180, 360)),
                "weekly_inventory_labor_hours": int(rng.integers(7, 15)),
                "markdown_day_offset": int(rng.integers(-4, 6)),
            }
        )

    return pd.DataFrame(rows)


def make_products(rng: np.random.Generator) -> pd.DataFrame:
    """Create recognizable products with different economics and return patterns."""

    product_names = []
    for category, base_names in CATEGORY_PRODUCTS.items():
        for base_name in base_names:
            for style in STYLES:
                product_names.append((category, f"{style} {base_name}"))

    rows = []
    for index, (category, name) in enumerate(product_names[:NUMBER_OF_PRODUCTS]):
        price_band = {
            "Storage": (14, 48),
            "Bedding": (18, 72),
            "Bath": (9, 38),
            "Desk": (10, 52),
            "Kitchen": (8, 34),
            "Decor": (10, 45),
        }[category]
        regular_price = round(rng.uniform(*price_band), 2)

        rows.append(
            {
                "product_id": f"P{index + 1:03d}",
                "product_name": name,
                "category": category,
                "regular_price": regular_price,
                "unit_cost": round(regular_price * rng.uniform(0.43, 0.64), 2),
                "base_daily_demand": round(rng.uniform(0.08, 0.34), 3),
                "return_rate": round(rng.uniform(0.04, 0.17), 3),
                "presentation_minimum": int(rng.integers(2, 7)),
            }
        )

    return pd.DataFrame(rows)


def demand_affinity(archetype: str, category: str) -> float:
    """Express a few deliberate local assortment differences."""

    if archetype == "College Town" and category in {"Storage", "Bedding", "Desk"}:
        return 1.35
    if archetype == "Urban Small Format" and category in {"Storage", "Kitchen"}:
        return 1.18
    if archetype == "Suburban Family" and category in {"Bedding", "Bath"}:
        return 1.16
    if archetype == "High Digital Demand" and category in {"Desk", "Decor"}:
        return 1.12
    if archetype == "Warm Weather" and category == "Bedding":
        return 0.82
    if archetype == "Lower Volume":
        return 0.84
    return 1.0


def seasonal_multiplier(day_number: int) -> float:
    """Back-to-campus demand rises, peaks, and then falls sharply."""

    if day_number < 28:
        return 0.75 + 0.02 * day_number
    if day_number < 63:
        return 1.35
    if day_number < 84:
        return 1.05
    if day_number < 98:
        return 0.62
    return 0.28


def take_units(available: int, requested: int) -> tuple[int, int]:
    """Remove as many requested units as a location can supply."""

    taken = min(available, requested)
    return available - taken, requested - taken


def fulfill_pickup(
    shelf_units: int,
    backroom_units: int,
    clearance_units: int,
    requested_units: int,
    execution_score: float,
    rng: np.random.Generator,
) -> tuple[int, int, int, int]:
    """Try to locate pickup units, beginning with the expected shelf location."""

    remaining = requested_units

    shelf_units, remaining = take_units(shelf_units, remaining)

    if remaining and backroom_units:
        searched = min(backroom_units, remaining)
        located = int(rng.binomial(searched, 0.35 + 0.45 * execution_score))
        backroom_units -= located
        remaining -= located

    if remaining and clearance_units:
        searched = min(clearance_units, remaining)
        located = int(rng.binomial(searched, 0.18 + 0.55 * execution_score))
        clearance_units -= located
        remaining -= located

    fulfilled = requested_units - remaining
    return shelf_units, backroom_units, clearance_units, fulfilled


def move_units(
    source_units: int,
    destination_units: int,
    quantity: int,
) -> tuple[int, int]:
    """Move a quantity between two physical inventory states."""

    moved = min(source_units, quantity)
    return source_units - moved, destination_units + moved


def simulate_retail(
    stores: pd.DataFrame,
    products: pd.DataFrame,
    rng: np.random.Generator,
) -> dict[str, pd.DataFrame]:
    """Simulate daily inventory, sales, returns, markdowns, pickup, and audits."""

    inventory_rows = []
    return_rows = []
    pickup_rows = []
    markdown_rows = []
    audit_rows = []

    return_id = 1
    audit_id = 1

    for store in stores.itertuples(index=False):
        for product in products.itertuples(index=False):
            affinity = demand_affinity(store.archetype, product.category)
            expected_season_units = (
                product.base_daily_demand
                * store.volume_multiplier
                * affinity
                * NUMBER_OF_DAYS
            )
            initial_units = max(5, int(rng.poisson(expected_season_units * 0.72)))

            shelf_units = min(
                initial_units,
                product.presentation_minimum + int(rng.integers(1, 5)),
            )
            backroom_units = initial_units - shelf_units
            returns_units = 0
            clearance_units = 0
            damaged_units = 0
            missing_record_units = 0

            pending_returns = []
            last_sale_day = -int(rng.integers(0, 10))
            last_count_day = -int(rng.integers(4, 35))
            first_markdown_day = 70 + store.markdown_day_offset
            deep_markdown_day = 91 + store.markdown_day_offset

            for day_number in range(NUMBER_OF_DAYS):
                date = START_DATE + pd.Timedelta(days=day_number)
                inventory_adjustment = 0
                receipt_units = 0
                returned_today = 0

                due_returns = [
                    item for item in pending_returns if item["resolve_day"] == day_number
                ]
                pending_returns = [
                    item for item in pending_returns if item["resolve_day"] != day_number
                ]

                for item in due_returns:
                    returns_units -= item["quantity"]
                    if item["destination"] == "shelf":
                        shelf_units += item["quantity"]
                    elif item["destination"] == "clearance":
                        clearance_units += item["quantity"]
                    elif item["destination"] == "backroom":
                        backroom_units += item["quantity"]
                    else:
                        damaged_units += item["quantity"]

                if day_number in {21, 42} and rng.random() < 0.72:
                    receipt_units = max(2, int(rng.poisson(expected_season_units * 0.16)))
                    backroom_units += receipt_units

                markdown_depth = 0.0
                if day_number >= deep_markdown_day:
                    markdown_depth = 0.50
                elif day_number >= first_markdown_day:
                    markdown_depth = 0.30

                if day_number in {first_markdown_day, deep_markdown_day}:
                    move_share = 0.42 if day_number == first_markdown_day else 0.70
                    candidate_units = shelf_units + backroom_units
                    units_to_clearance = int(rng.binomial(candidate_units, move_share))

                    from_backroom = min(backroom_units, units_to_clearance)
                    backroom_units, clearance_units = move_units(
                        backroom_units, clearance_units, from_backroom
                    )
                    remaining_move = units_to_clearance - from_backroom
                    if remaining_move:
                        shelf_units, clearance_units = move_units(
                            shelf_units, clearance_units, remaining_move
                        )

                    markdown_rows.append(
                        {
                            "date": date,
                            "store_id": store.store_id,
                            "product_id": product.product_id,
                            "markdown_depth": markdown_depth,
                            "units_moved_to_clearance": units_to_clearance,
                            "reason": "Planned seasonal markdown",
                        }
                    )

                target_shelf = product.presentation_minimum + 2
                if shelf_units < target_shelf and backroom_units > 0:
                    replenish_capacity = max(1, int(round(3 * store.execution_score)))
                    backroom_units, shelf_units = move_units(
                        backroom_units,
                        shelf_units,
                        min(target_shelf - shelf_units, replenish_capacity),
                    )

                if shelf_units > 0 and rng.random() < 0.0015:
                    shelf_units -= 1
                    missing_record_units += 1

                price_demand = 1.0 + markdown_depth * 1.25
                expected_demand = (
                    product.base_daily_demand
                    * store.volume_multiplier
                    * affinity
                    * seasonal_multiplier(day_number)
                    * price_demand
                )
                total_demand = int(rng.poisson(expected_demand))
                pickup_requested = int(rng.binomial(total_demand, store.pickup_share))
                in_store_demand = total_demand - pickup_requested

                book_before_sales = (
                    shelf_units
                    + backroom_units
                    + returns_units
                    + clearance_units
                    + damaged_units
                    + missing_record_units
                )

                (
                    shelf_units,
                    backroom_units,
                    clearance_units,
                    pickup_fulfilled,
                ) = fulfill_pickup(
                    shelf_units,
                    backroom_units,
                    clearance_units,
                    pickup_requested,
                    store.execution_score,
                    rng,
                )
                pickup_cancelled = pickup_requested - pickup_fulfilled

                shelf_before_store_sales = shelf_units
                shelf_units, remaining_store_demand = take_units(
                    shelf_units, in_store_demand
                )
                regular_store_sales = shelf_before_store_sales - shelf_units

                clearance_before_store_sales = clearance_units
                if remaining_store_demand and markdown_depth > 0:
                    clearance_units, remaining_store_demand = take_units(
                        clearance_units, remaining_store_demand
                    )
                clearance_store_sales = clearance_before_store_sales - clearance_units

                total_sales = (
                    pickup_fulfilled + regular_store_sales + clearance_store_sales
                )
                lost_demand = pickup_cancelled + remaining_store_demand
                if total_sales > 0:
                    last_sale_day = day_number

                returned_today = int(rng.binomial(total_sales, product.return_rate))
                for _ in range(returned_today):
                    if markdown_depth > 0:
                        destinations = ["shelf", "clearance", "backroom", "damaged"]
                        probabilities = [0.10, 0.58, 0.14, 0.18]
                    else:
                        destinations = ["shelf", "clearance", "backroom", "damaged"]
                        probabilities = [0.48, 0.18, 0.22, 0.12]

                    destination = str(rng.choice(destinations, p=probabilities))
                    delay_days = int(
                        max(
                            1,
                            rng.poisson(1.0 + 3.2 * (1 - store.execution_score)),
                        )
                    )
                    resolve_day = min(NUMBER_OF_DAYS - 1, day_number + delay_days)
                    returns_units += 1
                    pending_returns.append(
                        {
                            "resolve_day": resolve_day,
                            "destination": destination,
                            "quantity": 1,
                        }
                    )
                    return_rows.append(
                        {
                            "return_id": f"R{return_id:06d}",
                            "return_date": date,
                            "store_id": store.store_id,
                            "product_id": product.product_id,
                            "quantity": 1,
                            "destination": destination,
                            "processing_days": delay_days,
                            "resolved_date": START_DATE
                            + pd.Timedelta(days=resolve_day),
                            "record_available_before_reshelved": True,
                        }
                    )
                    return_id += 1

                findable_backroom = int(
                    rng.binomial(backroom_units, 0.20 + 0.42 * store.execution_score)
                )
                findable_clearance = int(
                    rng.binomial(clearance_units, 0.15 + 0.55 * store.execution_score)
                )
                findable_units = shelf_units + findable_backroom + findable_clearance

                physical_inventory = (
                    shelf_units
                    + backroom_units
                    + returns_units
                    + clearance_units
                    + damaged_units
                )
                book_inventory = physical_inventory + missing_record_units
                sellable_units = (
                    shelf_units + backroom_units + returns_units + clearance_units
                )
                availability_gap = int(
                    book_inventory > 0
                    and findable_units / book_inventory < 0.50
                )
                count_age_before_audit = day_number - last_count_day

                audit_probability = 0.004
                audit_probability += 0.025 if pickup_cancelled > 0 else 0
                audit_probability += 0.009 if returned_today > 0 else 0
                audit_probability += 0.007 if day_number - last_sale_day >= 10 else 0

                if book_inventory > 0 and rng.random() < audit_probability:
                    locations = {
                        "regular shelf": shelf_units,
                        "backroom": backroom_units,
                        "returns or reshop": returns_units,
                        "clearance": clearance_units,
                        "damaged": damaged_units,
                        "missing": missing_record_units,
                    }
                    primary_location = max(locations, key=locations.get)
                    minutes_spent = int(
                        5
                        + 2 * len([value for value in locations.values() if value > 0])
                        + rng.integers(1, 8)
                    )
                    audit_rows.append(
                        {
                            "audit_id": f"A{audit_id:05d}",
                            "date": date,
                            "store_id": store.store_id,
                            "product_id": product.product_id,
                            "book_inventory_before": book_inventory,
                            "physical_inventory_found": physical_inventory,
                            "findable_units": findable_units,
                            "availability_gap": availability_gap,
                            "primary_location": primary_location,
                            "minutes_spent": minutes_spent,
                            "count_adjustment": -missing_record_units,
                        }
                    )
                    audit_id += 1
                    last_count_day = day_number
                    inventory_adjustment = -missing_record_units
                    missing_record_units = 0

                if pickup_requested > 0:
                    if pickup_cancelled == 0:
                        cancellation_reason = ""
                    elif book_before_sales <= 0:
                        cancellation_reason = "No recorded inventory"
                    elif returns_units > 0:
                        cancellation_reason = "Inventory awaiting return processing"
                    elif clearance_units > 0:
                        cancellation_reason = "Item not located in clearance"
                    else:
                        cancellation_reason = "Recorded inventory not found"

                    pickup_rows.append(
                        {
                            "date": date,
                            "store_id": store.store_id,
                            "product_id": product.product_id,
                            "requested_units": pickup_requested,
                            "fulfilled_units": pickup_fulfilled,
                            "cancelled_units": pickup_cancelled,
                            "book_inventory_at_order": book_before_sales,
                            "cancellation_reason": cancellation_reason,
                        }
                    )

                inventory_rows.append(
                    {
                        "date": date,
                        "store_id": store.store_id,
                        "product_id": product.product_id,
                        "markdown_depth": markdown_depth,
                        "book_inventory": book_inventory,
                        "physical_inventory": physical_inventory,
                        "sellable_units": sellable_units,
                        "findable_units": findable_units,
                        "shelf_units": shelf_units,
                        "backroom_units": backroom_units,
                        "returns_area_units": returns_units,
                        "clearance_units": clearance_units,
                        "damaged_units": damaged_units,
                        "missing_record_units": (
                            missing_record_units - inventory_adjustment
                            if inventory_adjustment < 0
                            else missing_record_units
                        ),
                        "in_store_sales": regular_store_sales
                        + clearance_store_sales,
                        "clearance_sales": clearance_store_sales,
                        "pickup_fulfilled": pickup_fulfilled,
                        "pickup_cancelled": pickup_cancelled,
                        "lost_demand": lost_demand,
                        "returned_units": returned_today,
                        "receipt_units": receipt_units,
                        "inventory_adjustment": inventory_adjustment,
                        "days_since_sale": day_number - last_sale_day,
                        "days_since_verified_count": count_age_before_audit,
                        "availability_gap": availability_gap,
                    }
                )

    tables = {
        "stores": stores,
        "products": products,
        "daily_inventory": pd.DataFrame(inventory_rows),
        "returns": pd.DataFrame(return_rows),
        "pickup_orders": pd.DataFrame(pickup_rows),
        "markdown_events": pd.DataFrame(markdown_rows),
        "audits": pd.DataFrame(audit_rows),
    }
    return tables


def validate_tables(tables: dict[str, pd.DataFrame]) -> None:
    """Stop generation when the basic inventory relationships do not hold."""

    inventory = tables["daily_inventory"]
    expected_rows = NUMBER_OF_STORES * NUMBER_OF_PRODUCTS * NUMBER_OF_DAYS
    assert len(inventory) == expected_rows

    recorded_components = inventory[
        [
            "shelf_units",
            "backroom_units",
            "returns_area_units",
            "clearance_units",
            "damaged_units",
            "missing_record_units",
        ]
    ].sum(axis=1)
    assert (recorded_components == inventory["book_inventory"]).all()
    assert (inventory["physical_inventory"] <= inventory["book_inventory"]).all()

    nonnegative_columns = [
        column
        for column in inventory.select_dtypes(include="number").columns
        if column != "inventory_adjustment"
    ]
    assert (inventory[nonnegative_columns] >= 0).all().all()
    assert (inventory["findable_units"] <= inventory["sellable_units"]).all()
    assert len(tables["audits"]) > 500


def save_tables(tables: dict[str, pd.DataFrame]) -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(RAW_DATA_DIR / f"{name}.csv", index=False)
        print(f"Saved {name:18s} {len(table):>9,} rows")


def main() -> None:
    rng = np.random.default_rng(SEED)
    stores = make_stores(rng)
    products = make_products(rng)
    tables = simulate_retail(stores, products, rng)
    validate_tables(tables)
    save_tables(tables)


if __name__ == "__main__":
    main()
