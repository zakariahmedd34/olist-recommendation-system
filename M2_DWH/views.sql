-- ============================================================
-- Step 10 — Phase 2 SQL views (hand-off to M3, M4, M5)
-- Apply with: psql -d olist_dwh -f dwh/views.sql
-- ============================================================

DROP VIEW IF EXISTS v_baskets_product   CASCADE;
DROP VIEW IF EXISTS v_baskets_category  CASCADE;
DROP VIEW IF EXISTS v_customer_features CASCADE;
DROP VIEW IF EXISTS v_orders_with_holiday CASCADE;

-- v_baskets_product : one row per delivered order, array of product_ids  (for M3)
CREATE VIEW v_baskets_product AS
SELECT
    order_id,
    ARRAY_AGG(DISTINCT product_id) AS products
FROM fact_orderitems
WHERE product_id IS NOT NULL
GROUP BY order_id;

-- v_baskets_category : one row per delivered order, array of category-group names  (for M3)
CREATE VIEW v_baskets_category AS
SELECT
    f.order_id,
    ARRAY_AGG(DISTINCT g.group_name) AS category_groups
FROM fact_orderitems f
JOIN dim_products       p ON p.product_id       = f.product_id
JOIN dim_category_group g ON g.group_id         = p.category_group_id
GROUP BY f.order_id;

-- v_customer_features : clustering input for M4
CREATE VIEW v_customer_features AS
SELECT
    c.customer_id,
    COUNT(DISTINCT f.order_id)                                       AS frequency,
    SUM(f.total_item_value)                                          AS monetary,
    COUNT(*)::FLOAT / NULLIF(COUNT(DISTINCT f.order_id), 0)          AS avg_basket_size,
    COUNT(DISTINCT p.category_group_id)                              AS n_categories,
    r.macro_region                                                   AS region
FROM dim_customers c
JOIN fact_orderitems f ON f.customer_id = c.customer_id
JOIN dim_products    p ON p.product_id  = f.product_id
LEFT JOIN dim_region r ON r.region_id   = c.region_id
GROUP BY c.customer_id, r.macro_region;

-- v_orders_with_holiday : enables M3's holiday-conditioned mining
CREATE VIEW v_orders_with_holiday AS
SELECT DISTINCT
    f.order_id,
    f.orderdate,
    d.is_holiday,
    d.holiday_name,
    d.season,
    d.is_weekend,
    d.payday_window
FROM fact_orderitems f
JOIN dim_date d ON d.date = f.orderdate;
