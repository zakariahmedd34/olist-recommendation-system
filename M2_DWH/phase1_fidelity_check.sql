-- ============================================================
-- Phase 1 fidelity check
-- After running dwh/match_phase1_cleaning.sql, this verifies that every
-- Phase 1 Power Query transformation now holds in the DB.
-- Run: psql -d olist_dwh -f dwh/phase1_fidelity_check.sql 2>&1 | tee dwh/phase1_fidelity_results.txt
-- Pass criterion: every "bad" count = 0.
-- ============================================================

\echo
\echo '============================================================'
\echo '  PHASE 1 FIDELITY CHECK'
\echo '============================================================'

\echo
\echo '--- A. DIM_CUSTOMERS — trim/clean ---'
SELECT 'customer_city has leading/trailing space'  AS check, COUNT(*) AS bad FROM dim_customers WHERE customer_city  <> TRIM(customer_city)
UNION ALL SELECT 'customer_state has leading/trailing space', COUNT(*) FROM dim_customers WHERE customer_state <> TRIM(customer_state)
UNION ALL SELECT 'customer_city has non-printable char',      COUNT(*) FROM dim_customers WHERE customer_city  ~ '[^[:print:]]'
UNION ALL SELECT 'customer_state has non-printable char',     COUNT(*) FROM dim_customers WHERE customer_state ~ '[^[:print:]]';

\echo
\echo '--- B. DIM_SELLERS — Proper case city + UPPER state ---'
SELECT 'seller_city not INITCAP'  AS check, COUNT(*) AS bad FROM dim_sellers WHERE seller_city  <> INITCAP(seller_city)
UNION ALL SELECT 'seller_state not UPPER', COUNT(*) FROM dim_sellers WHERE seller_state <> UPPER(seller_state)
UNION ALL SELECT 'seller_city has leading/trailing space',  COUNT(*) FROM dim_sellers WHERE seller_city  <> TRIM(seller_city)
UNION ALL SELECT 'seller_state has leading/trailing space', COUNT(*) FROM dim_sellers WHERE seller_state <> TRIM(seller_state);

\echo '--- B sample — verify capitalization with 5 random rows ---'
SELECT seller_id, seller_city, seller_state FROM dim_sellers ORDER BY random() LIMIT 5;

\echo
\echo '--- C. DIM_PRODUCTS — null/empty imputed ---'
SELECT 'product_weight_g NULL'  AS check, COUNT(*) AS bad FROM dim_products WHERE product_weight_g IS NULL
UNION ALL SELECT 'product_length_cm NULL',          COUNT(*) FROM dim_products WHERE product_length_cm IS NULL
UNION ALL SELECT 'product_height_cm NULL',          COUNT(*) FROM dim_products WHERE product_height_cm IS NULL
UNION ALL SELECT 'product_width_cm NULL',           COUNT(*) FROM dim_products WHERE product_width_cm  IS NULL
UNION ALL SELECT 'product_photos_qty NULL',         COUNT(*) FROM dim_products WHERE product_photos_qty IS NULL
UNION ALL SELECT 'product_category_name NULL/empty', COUNT(*) FROM dim_products WHERE product_category_name IS NULL OR product_category_name = ''
UNION ALL SELECT 'product_category_name_english NULL/empty', COUNT(*) FROM dim_products WHERE product_category_name_english IS NULL OR product_category_name_english = '';

\echo '--- C sample — products that were imputed (formerly NULL) ---'
SELECT product_id, product_category_name, product_category_name_english,
       product_weight_g, product_length_cm, product_height_cm, product_width_cm,
       product_photos_qty
FROM dim_products
WHERE product_category_name = 'unknown'
LIMIT 5;

\echo
\echo '--- D. FACT_ORDERITEMS — freight ≥ 0 ---'
SELECT 'freight_value < 0' AS check, COUNT(*) AS bad FROM fact_orderitems WHERE freight_value < 0;

\echo
\echo '--- E. FACT_ORDERITEMS — order_item_key as Phase 1 text concat ---'
SELECT 'order_item_key NULL'                AS check, COUNT(*) AS bad FROM fact_orderitems WHERE order_item_key IS NULL
UNION ALL SELECT 'order_item_key not "orderid-N" format',  COUNT(*) FROM fact_orderitems
   WHERE order_item_key !~ '^[a-f0-9]{32}-[0-9]+$'                                  -- Olist order_ids are 32-char hex
UNION ALL SELECT 'order_item_key mismatch vs (order_id, order_item_id)', COUNT(*) FROM fact_orderitems
   WHERE order_item_key <> (order_id || '-' || order_item_id);

\echo '--- E PK type check (expect: text) ---'
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'fact_orderitems' AND column_name = 'order_item_key';

\echo '--- E sample — 3 order_item_key values to eyeball ---'
SELECT order_item_key, order_id, order_item_id FROM fact_orderitems LIMIT 3;

\echo
\echo '--- F. PK + FK still valid after migration ---'
SELECT 'order_item_key duplicates' AS check, COUNT(*) AS bad
FROM (SELECT order_item_key FROM fact_orderitems GROUP BY 1 HAVING COUNT(*)>1) x;

SELECT 'fact → customers orphans' AS check, COUNT(*) AS bad
FROM fact_orderitems WHERE customer_id NOT IN (SELECT customer_id FROM dim_customers)
UNION ALL SELECT 'fact → sellers orphans',   COUNT(*) FROM fact_orderitems WHERE seller_id   NOT IN (SELECT seller_id   FROM dim_sellers)
UNION ALL SELECT 'fact → products orphans',  COUNT(*) FROM fact_orderitems WHERE product_id  NOT IN (SELECT product_id  FROM dim_products)
UNION ALL SELECT 'fact → date orphans',      COUNT(*) FROM fact_orderitems WHERE orderdate   NOT IN (SELECT date        FROM dim_date);

\echo
\echo '--- G. VIEWS still working ---'
SELECT 'v_baskets_product rows'    AS view, COUNT(*) FROM v_baskets_product
UNION ALL SELECT 'v_baskets_category rows',    COUNT(*) FROM v_baskets_category
UNION ALL SELECT 'v_customer_features rows',   COUNT(*) FROM v_customer_features
UNION ALL SELECT 'v_orders_with_holiday rows', COUNT(*) FROM v_orders_with_holiday;

\echo
\echo '============================================================'
\echo '  PHASE 1 FIDELITY VERIFICATION COMPLETE'
\echo '  Pass criteria: every "bad" = 0 · view rows > 0 · PK type = text'
\echo '  Sample rows: eyeball that seller_city looks Like This,'
\echo '                seller_state looks LIKE THIS, order_item_key'
\echo '                looks like "abc...123-1"'
\echo '============================================================'
