"""
Create a filtered Olist raw dataset that keeps only orders with more than one distinct product.

This script does NOT replace the original shared_data folder.
It writes filtered CSVs to shared_data_multi_item/ and a summary CSV for documentation.

Run from the project root:
    python scripts/create_multi_item_dataset.py
"""
from __future__ import annotations

from pathlib import Path
import shutil
import sys
import pandas as pd

RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "translation": "product_category_name_translation.csv",
}


def find_project_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in [cwd] + list(cwd.parents):
        if (candidate / "M2_DWH").exists() or (candidate / "olist_dwh.dump").exists():
            return candidate
    return cwd


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def main() -> int:
    project_root = find_project_root()
    raw_dir = project_root / "shared_data"
    out_dir = project_root / "shared_data_multi_item"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print("ERROR: shared_data/ was not found.")
        print("Put the original Olist CSV files in shared_data/ first, then run this again.")
        print(f"Expected folder: {raw_dir}")
        return 1

    print(f"Project root: {project_root}")
    print(f"Input data : {raw_dir}")
    print(f"Output data: {out_dir}")

    order_items = read_csv(raw_dir / RAW_FILES["order_items"])

    # Use distinct products because association rules need at least two unique items in a basket.
    order_product_counts = (
        order_items.groupby("order_id")["product_id"]
        .nunique()
        .reset_index(name="distinct_product_count")
    )
    multi_item_order_ids = set(
        order_product_counts.loc[order_product_counts["distinct_product_count"] > 1, "order_id"]
    )

    total_orders_with_items = int(order_product_counts["order_id"].nunique())
    multi_item_orders = int(len(multi_item_order_ids))
    single_or_repeated_same_product_orders = int(total_orders_with_items - multi_item_orders)

    print("\n=== Multi-item filter summary ===")
    print(f"Orders with items              : {total_orders_with_items:,}")
    print(f"Orders with >1 distinct product: {multi_item_orders:,}")
    print(f"Orders removed                 : {single_or_repeated_same_product_orders:,}")
    print(f"Kept percentage                : {multi_item_orders / total_orders_with_items * 100:.2f}%")

    order_items_multi = order_items[order_items["order_id"].isin(multi_item_order_ids)].copy()
    order_items_multi.to_csv(out_dir / RAW_FILES["order_items"], index=False)

    # Order-level tables.
    orders = read_csv(raw_dir / RAW_FILES["orders"])
    orders_multi = orders[orders["order_id"].isin(multi_item_order_ids)].copy()
    orders_multi.to_csv(out_dir / RAW_FILES["orders"], index=False)

    for key in ["payments", "reviews"]:
        path = raw_dir / RAW_FILES[key]
        if path.exists():
            df = pd.read_csv(path)
            df_multi = df[df["order_id"].isin(multi_item_order_ids)].copy()
            df_multi.to_csv(out_dir / RAW_FILES[key], index=False)
            print(f"Saved {RAW_FILES[key]}: {len(df_multi):,} rows")

    # Dimension/support tables.
    customers = read_csv(raw_dir / RAW_FILES["customers"])
    customer_ids = set(orders_multi["customer_id"])
    customers_multi = customers[customers["customer_id"].isin(customer_ids)].copy()
    customers_multi.to_csv(out_dir / RAW_FILES["customers"], index=False)

    products = read_csv(raw_dir / RAW_FILES["products"])
    product_ids = set(order_items_multi["product_id"])
    products_multi = products[products["product_id"].isin(product_ids)].copy()
    products_multi.to_csv(out_dir / RAW_FILES["products"], index=False)

    sellers = read_csv(raw_dir / RAW_FILES["sellers"])
    seller_ids = set(order_items_multi["seller_id"])
    sellers_multi = sellers[sellers["seller_id"].isin(seller_ids)].copy()
    sellers_multi.to_csv(out_dir / RAW_FILES["sellers"], index=False)

    # These are support tables. Keep full copies to avoid losing lookup coverage.
    for key in ["geolocation", "translation"]:
        src = raw_dir / RAW_FILES[key]
        if src.exists():
            shutil.copy2(src, out_dir / RAW_FILES[key])
            print(f"Copied {RAW_FILES[key]} unchanged")

    check_counts = order_items_multi.groupby("order_id")["product_id"].nunique()
    min_distinct_products = int(check_counts.min()) if len(check_counts) else 0

    summary = pd.DataFrame({
        "metric": [
            "original_order_items_rows",
            "filtered_order_items_rows",
            "original_orders_with_items",
            "multi_item_orders_distinct_product_gt_1",
            "removed_orders",
            "multi_item_order_percentage",
            "min_distinct_products_per_kept_order",
            "filtered_customers_rows",
            "filtered_products_rows",
            "filtered_sellers_rows",
        ],
        "value": [
            len(order_items),
            len(order_items_multi),
            total_orders_with_items,
            multi_item_orders,
            single_or_repeated_same_product_orders,
            multi_item_orders / total_orders_with_items * 100,
            min_distinct_products,
            len(customers_multi),
            len(products_multi),
            len(sellers_multi),
        ]
    })
    summary.to_csv(out_dir / "multi_item_filter_summary.csv", index=False)

    print("\nSaved filtered raw dataset successfully.")
    print(f"Validation min distinct products per kept order: {min_distinct_products}")
    print(f"Summary file: {out_dir / 'multi_item_filter_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
