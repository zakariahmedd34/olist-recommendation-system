-- ============================================================
-- Phase 1 fidelity migration
-- Applies every Power Query M-code transformation from the Phase 1 .pbix
-- that was not already mirrored by the Phase 2 ETL.
-- Run: psql -d olist_dwh -f dwh/match_phase1_cleaning.sql
-- Idempotent: re-running is a no-op except for the order_item_key rebuild
-- (which fails if already TEXT — that's the indicator it was already done).
-- ============================================================

BEGIN;

-- ============================================================
-- 1. DIM_CUSTOMERS — Phase 1 did Text.Trim + Text.Clean on city + state
--    (no-op on Olist's clean source data, but applied for full fidelity)
-- ============================================================
\echo '--- 1. DIM_CUSTOMERS: trim + clean city/state ---'
UPDATE dim_customers
SET customer_city  = REGEXP_REPLACE(TRIM(customer_city),  '[^[:print:]]', '', 'g'),
    customer_state = REGEXP_REPLACE(TRIM(customer_state), '[^[:print:]]', '', 'g');

-- ============================================================
-- 2. DIM_SELLERS — Phase 1 did Text.Trim + Text.Clean + Text.Proper(city) + Text.Upper(state)
-- ============================================================
\echo '--- 2. DIM_SELLERS: trim + clean + Proper city + Upper state ---'
UPDATE dim_sellers
SET seller_city  = INITCAP(REGEXP_REPLACE(TRIM(seller_city),  '[^[:print:]]', '', 'g')),
    seller_state = UPPER(  REGEXP_REPLACE(TRIM(seller_state), '[^[:print:]]', '', 'g'));

-- ============================================================
-- 3. DIM_PRODUCTS — replace empty/null with imputed values
--    Phase 1 did this in 4 separate steps + median imputation for 4 dimensions
-- ============================================================
\echo '--- 3a. DIM_PRODUCTS: empty/NULL product_category_name → "unknown" ---'
UPDATE dim_products SET product_category_name = 'unknown'
WHERE product_category_name IS NULL OR product_category_name = '';

\echo '--- 3b. DIM_PRODUCTS: NULL product_category_name_english → "unknown" ---'
UPDATE dim_products SET product_category_name_english = 'unknown'
WHERE product_category_name_english IS NULL OR product_category_name_english = '';

\echo '--- 3c. DIM_PRODUCTS: NULL product_photos_qty → 0 ---'
UPDATE dim_products SET product_photos_qty = 0 WHERE product_photos_qty IS NULL;

\echo '--- 3d. DIM_PRODUCTS: median-impute NULL weight/length/height/width ---'
WITH medians AS (
    SELECT
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY product_weight_g))::int  AS med_w,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY product_length_cm))::int AS med_l,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY product_height_cm))::int AS med_h,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY product_width_cm))::int  AS med_wd
    FROM dim_products
)
UPDATE dim_products SET
    product_weight_g  = COALESCE(product_weight_g,  (SELECT med_w  FROM medians)),
    product_length_cm = COALESCE(product_length_cm, (SELECT med_l  FROM medians)),
    product_height_cm = COALESCE(product_height_cm, (SELECT med_h  FROM medians)),
    product_width_cm  = COALESCE(product_width_cm,  (SELECT med_wd FROM medians))
WHERE product_weight_g IS NULL
   OR product_length_cm IS NULL
   OR product_height_cm IS NULL
   OR product_width_cm  IS NULL;

-- ============================================================
-- 4. FACT_ORDERITEMS — Phase 1 "Filtered Rows: freight_value >= 0"
--    (audit showed 0 rows in Olist source, but applied for full fidelity)
-- ============================================================
\echo '--- 4. FACT_ORDERITEMS: delete rows with freight_value < 0 ---'
DELETE FROM fact_orderitems WHERE freight_value < 0;

-- ============================================================
-- 5. FACT_ORDERITEMS — rebuild order_item_key as TEXT concat
--    Phase 1: order_item_key = order_id & "-" & Text.From(order_item_id)
--    Phase 2 had it as BIGSERIAL; we replace with the Phase 1 format.
--    Views must be dropped first because they depend on fact_orderitems.
-- ============================================================
\echo '--- 5. FACT_ORDERITEMS: rebuild order_item_key as TEXT concat ---'

DROP VIEW IF EXISTS v_baskets_product   CASCADE;
DROP VIEW IF EXISTS v_baskets_category  CASCADE;
DROP VIEW IF EXISTS v_customer_features CASCADE;
DROP VIEW IF EXISTS v_orders_with_holiday CASCADE;

ALTER TABLE fact_orderitems DROP CONSTRAINT fact_orderitems_pkey;
ALTER TABLE fact_orderitems DROP COLUMN order_item_key;
ALTER TABLE fact_orderitems ADD COLUMN order_item_key TEXT;

UPDATE fact_orderitems
SET    order_item_key = order_id || '-' || order_item_id;

ALTER TABLE fact_orderitems ALTER COLUMN order_item_key SET NOT NULL;
ALTER TABLE fact_orderitems ADD PRIMARY KEY (order_item_key);

COMMIT;

-- ============================================================
-- 6. RECREATE THE 4 VIEWS
--    (must be after the COMMIT above so they see the new PK)
-- ============================================================
\echo '--- 6. RECREATE VIEWS ---'
\i dwh/views.sql

\echo
\echo '============================================================'
\echo '  Phase 1 fidelity migration complete.'
\echo '  Run dwh/phase1_fidelity_check.sql to verify.'
\echo '============================================================'
