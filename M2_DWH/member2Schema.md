# Olist DWH — schema reference

Snowflake schema centered on `fact_orderitems`. 4 primary dimensions are joined directly to the fact; 2 outrigger reference tables (`dim_region`, `dim_category_group`) are joined to `dim_customers` and `dim_products` respectively.

```
dim_region ◀──┐
              │
              dim_customers ──┐
                              │
                  dim_date ◀──┼──▶ FACT_ORDERITEMS ◀──── dim_sellers
                              │
                              dim_products ──┐
                                             │
                                             dim_category_group ◀──┘
```

> **PostgreSQL naming:** unquoted identifiers are folded to lowercase, so Phase 1's `MonthName` / `OrderDate` are accessed as `monthname` / `orderdate`. The columns themselves are unchanged.

---

## Fact table

### `fact_orderitems`  (110,197 rows)

Grain: **one row per item per delivered order** (matches Phase 1).

| Column | Type | Notes |
|---|---|---|
| `order_item_key` | BIGSERIAL | surrogate PK |
| `order_id` | TEXT | Olist order UUID |
| `order_item_id` | INT | line-item index within order |
| `customer_id` | TEXT | FK → `dim_customers` |
| `seller_id` | TEXT | FK → `dim_sellers` |
| `product_id` | TEXT | FK → `dim_products` |
| `orderdate` | DATE | FK → `dim_date.date` (truncated from `order_purchase_timestamp`) |
| `price` | NUMERIC(10,2) | item price (BRL) |
| `freight_value` | NUMERIC(10,2) | freight portion |
| `total_item_value` | NUMERIC(10,2) | **GENERATED ALWAYS AS (`price + freight_value`) STORED** |

**Indexes:** `customer_id`, `seller_id`, `product_id`, `orderdate`. **Source:** join of `olist_order_items_dataset.csv` × `olist_orders_dataset.csv` filtered to `order_status = 'delivered'`.

---

## Primary dimensions

### `dim_customers`  (99,441 rows)

| Column | Type | Notes |
|---|---|---|
| `customer_id` | TEXT | PK (one per order-time customer record) |
| `customer_unique_id` | TEXT | persistent identity across multiple orders |
| `customer_zip_code_prefix` | TEXT | 5-digit BR ZIP prefix |
| `customer_city` | TEXT | |
| `customer_state` | TEXT | 2-letter UF code |
| `region_id` | INT | **NEW** — FK → `dim_region` |

**Source:** `olist_customers_dataset.csv`; `region_id` derived by mapping `customer_state` → `dim_region.region_id`.

### `dim_sellers`  (3,095 rows)

| Column | Type | Notes |
|---|---|---|
| `seller_id` | TEXT | PK |
| `seller_zip_code_prefix` | TEXT | |
| `seller_city` | TEXT | |
| `seller_state` | TEXT | |

**Source:** `olist_sellers_dataset.csv`. Unchanged from Phase 1.

### `dim_products`  (32,951 rows)

| Column | Type | Notes |
|---|---|---|
| `product_id` | TEXT | PK |
| `product_category_name` | TEXT | original Portuguese name |
| `product_category_name_english` | TEXT | from `product_category_name_translation.csv` |
| `product_weight_g` | INT | |
| `product_length_cm` | INT | |
| `product_height_cm` | INT | |
| `product_width_cm` | INT | |
| `product_photos_qty` | INT | |
| `category_group_id` | INT | **NEW** — FK → `dim_category_group`; derived from `etl/category_to_group.csv` |

**Source:** `olist_products_dataset.csv` + translation CSV + category-group mapping.

### `dim_date`  (1,096 rows · 2016-01-01 → 2018-12-31)

| Column | Type | Notes |
|---|---|---|
| `date` | DATE | PK |
| `day` | INT | |
| `monthnumber` | INT | |
| `monthname` | TEXT | |
| `quarter` | INT | |
| `weekday` | TEXT | |
| `year` | INT | |
| `is_holiday` | BOOLEAN | **NEW** — 27 Brazilian federal holidays |
| `holiday_name` | TEXT | **NEW** |
| `is_weekend` | BOOLEAN | **NEW** |
| `season` | TEXT | **NEW** — Verão / Outono / Inverno / Primavera (southern-hemisphere) |
| `payday_window` | BOOLEAN | **NEW** — `day ≥ 28 OR day ≤ 5` (BR payroll cadence) |

**Source:** Python `holidays.Brazil()` over a date range covering the order data.

---

## Outrigger reference tables

### `dim_region`  (27 rows)

| Column | Type | Notes |
|---|---|---|
| `region_id` | SERIAL | PK |
| `state` | TEXT UNIQUE | 2-letter UF code |
| `macro_region` | TEXT | one of Norte · Nordeste · Centro-Oeste · Sudeste · Sul |

**Source:** hand-coded mapping (the 27 BR states are stable).

### `dim_category_group`  (10 rows)

| Column | Type | Notes |
|---|---|---|
| `group_id` | SERIAL | PK |
| `group_name` | TEXT UNIQUE | data-driven group label (see `category_mapping.md`) |
| `description` | TEXT | top-3 member categories |

**Source:** Ward hierarchical clustering on direct co-occurrence similarity (cosine), cut at k=10. Detailed methodology + validation in `category_mapping.md`.

---

## Views (for M3, M4, M5)

| View | Grain | Used by |
|---|---|---|
| `v_baskets_product` | one row per order, array of product_ids | M3 (product-level rule mining) |
| `v_baskets_category` | one row per order, array of category-group names | M3 (category-level rule mining) |
| `v_customer_features` | one row per customer (frequency, monetary, avg_basket, n_categories, region) | M4 (clustering) |
| `v_orders_with_holiday` | one row per order with date enrichment | M3 (holiday-conditioned mining) |

---

## Differences from Phase 1 (Power BI .pbix)

| Change | Type | Why |
|---|---|---|
| Real PostgreSQL DB (was Power BI–only) | Replatform | Phase 1 gap #1 |
| `dim_region` added | New outrigger | Phase 1 gap #4 (`geolocation.csv` was unused) |
| `dim_category_group` added | New outrigger | Phase 1 gap #2 (88% single-item baskets) — **bonus ★★★** |
| `customers.region_id` FK | New column | links region outrigger |
| `products.category_group_id` FK | New column | links category outrigger |
| `date.{is_holiday, holiday_name, is_weekend, season, payday_window}` | 5 new columns | Phase 1 gap #3 + enables M3 bonuses |
| `total_item_value` made `GENERATED ALWAYS AS` | Type change | values identical; cannot drift from `price + freight_value` |
| `OrderDate` → `orderdate` (Phase 1 case folded) | Naming | Postgres lowercase folding |
| `MonthName`, `MonthNumber` → `monthname`, `monthnumber` | Naming | Postgres lowercase folding |
