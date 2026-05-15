"""Step 9 — Day 2 master ETL: loads dim_customers, dim_sellers, dim_products, fact_orderitems."""
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from db import engine

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
ETL  = ROOT / "etl"


def truncate(table: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {table} RESTART IDENTITY CASCADE"))


def extract():
    customers  = pd.read_csv(DATA / "olist_customers_dataset.csv")
    sellers    = pd.read_csv(DATA / "olist_sellers_dataset.csv")
    products   = pd.read_csv(DATA / "olist_products_dataset.csv")
    orders     = pd.read_csv(DATA / "olist_orders_dataset.csv")
    items      = pd.read_csv(DATA / "olist_order_items_dataset.csv")
    trans      = pd.read_csv(DATA / "product_category_name_translation.csv")
    cat_to_grp = pd.read_csv(ETL / "category_to_group.csv")
    return customers, sellers, products, orders, items, trans, cat_to_grp


def transform(customers, sellers, products, orders, items, trans, cat_to_grp):
    with engine.begin() as conn:
        region_df = pd.read_sql("SELECT region_id, state FROM dim_region", conn)
    state_map = dict(zip(region_df["state"], region_df["region_id"]))

    customers["region_id"] = customers["customer_state"].map(state_map).astype("Int64")

    products = products.merge(trans, on="product_category_name", how="left")
    products = products.merge(cat_to_grp, on="product_category_name", how="left")
    products["category_group_id"] = products["category_group_id"].astype("Int64")
    for col in ["product_weight_g", "product_length_cm", "product_height_cm",
                "product_width_cm", "product_photos_qty"]:
        products[col] = pd.to_numeric(products[col], errors="coerce").astype("Int64")

    orders["order_date"] = pd.to_datetime(orders["order_purchase_timestamp"]).dt.date
    delivered = orders.loc[orders["order_status"] == "delivered",
                           ["order_id", "customer_id", "order_date"]]

    fact = (items.merge(delivered, on="order_id", how="inner")
                 [["order_id", "order_item_id", "customer_id", "seller_id",
                   "product_id", "order_date", "price", "freight_value"]]
                 .rename(columns={"order_date": "orderdate"}))

    customers_db = customers[["customer_id", "customer_unique_id",
                              "customer_zip_code_prefix", "customer_city",
                              "customer_state", "region_id"]]
    sellers_db   = sellers[["seller_id", "seller_zip_code_prefix",
                            "seller_city", "seller_state"]]
    products_db  = products[["product_id", "product_category_name",
                             "product_category_name_english",
                             "product_weight_g", "product_length_cm",
                             "product_height_cm", "product_width_cm",
                             "product_photos_qty", "category_group_id"]]
    return customers_db, sellers_db, products_db, fact


def load(customers_db, sellers_db, products_db, fact):
    print("loading dim_customers …")
    truncate("dim_customers")
    customers_db.to_sql("dim_customers", engine, if_exists="append",
                        index=False, chunksize=5000, method="multi")

    print("loading dim_sellers …")
    truncate("dim_sellers")
    sellers_db.to_sql("dim_sellers", engine, if_exists="append",
                      index=False, chunksize=5000, method="multi")

    print("loading dim_products …")
    truncate("dim_products")
    products_db.to_sql("dim_products", engine, if_exists="append",
                       index=False, chunksize=5000, method="multi")

    print(f"loading fact_orderitems ({len(fact):,} rows) …")
    truncate("fact_orderitems")
    fact.to_sql("fact_orderitems", engine, if_exists="append",
                index=False, chunksize=5000, method="multi")


def index_and_verify():
    print("building indexes …")
    with engine.begin() as conn:
        for col in ("customer_id", "seller_id", "product_id", "orderdate"):
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS idx_fact_{col} ON fact_orderitems({col})"
            ))

    tables = ["dim_region", "dim_category_group", "dim_customers", "dim_sellers",
              "dim_products", "dim_date", "fact_orderitems"]
    print("\n=== row counts ===")
    with engine.begin() as conn:
        for t in tables:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:22s} {n:>10,}")

        print("\n=== referential integrity ===")
        for fk_name, sql in [
            ("fact → customers", "SELECT COUNT(*) FROM fact_orderitems WHERE customer_id NOT IN (SELECT customer_id FROM dim_customers)"),
            ("fact → sellers",   "SELECT COUNT(*) FROM fact_orderitems WHERE seller_id   NOT IN (SELECT seller_id   FROM dim_sellers)"),
            ("fact → products",  "SELECT COUNT(*) FROM fact_orderitems WHERE product_id  NOT IN (SELECT product_id  FROM dim_products)"),
            ("fact → date",      "SELECT COUNT(*) FROM fact_orderitems WHERE orderdate   NOT IN (SELECT date        FROM dim_date)"),
        ]:
            n = conn.execute(text(sql)).scalar()
            flag = "✓" if n == 0 else "⚠"
            print(f"  {flag} {fk_name:18s} orphans: {n}")


def main() -> None:
    customers, sellers, products, orders, items, trans, cat_to_grp = extract()
    customers_db, sellers_db, products_db, fact = transform(
        customers, sellers, products, orders, items, trans, cat_to_grp)
    load(customers_db, sellers_db, products_db, fact)
    index_and_verify()
    print("\n✓ ETL complete.")


if __name__ == "__main__":
    main()
