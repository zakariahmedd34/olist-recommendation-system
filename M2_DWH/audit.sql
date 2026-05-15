-- ============================================================
-- Olist DWH — FULL pre-handoff audit (25 sections)
-- Run:   psql -d olist_dwh -f dwh/audit.sql 2>&1 | tee dwh/audit_results.txt
-- Every section prints its own pass criterion at the bottom.
-- ============================================================

\echo
\echo '############################################################'
\echo '## SECTION A — SCHEMA SHAPE'
\echo '############################################################'

\echo
\echo '--- 1. TABLES PRESENT (expect exactly 7) ---'
SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;

\echo '--- 2. NO UNEXPECTED EXTRA TABLES ---'
SELECT COUNT(*) AS extra_tables
FROM pg_tables WHERE schemaname='public'
AND tablename NOT IN ('dim_region','dim_category_group','dim_customers','dim_sellers',
                      'dim_products','dim_date','fact_orderitems');

\echo '--- 3. VIEWS PRESENT (expect 4) ---'
SELECT table_name FROM information_schema.views
WHERE table_schema='public' ORDER BY table_name;

\echo '--- 4. NO UNEXPECTED EXTRA VIEWS ---'
SELECT COUNT(*) AS extra_views
FROM information_schema.views WHERE table_schema='public'
AND table_name NOT IN ('v_baskets_product','v_baskets_category',
                       'v_customer_features','v_orders_with_holiday');

\echo '--- 5. FK CONSTRAINTS DECLARED (expect 6) ---'
SELECT conrelid::regclass AS table_name, conname AS fk_name
FROM pg_constraint WHERE contype='f' ORDER BY 1, 2;

\echo
\echo '############################################################'
\echo '## SECTION B — DATA INTEGRITY'
\echo '############################################################'

\echo
\echo '--- 6. ROW COUNTS (actual vs expected) ---'
SELECT 'dim_region'         AS t, COUNT(*) AS actual, 27     AS expected FROM dim_region
UNION ALL SELECT 'dim_category_group', COUNT(*),     10     FROM dim_category_group
UNION ALL SELECT 'dim_customers',      COUNT(*),     99441  FROM dim_customers
UNION ALL SELECT 'dim_sellers',        COUNT(*),     3095   FROM dim_sellers
UNION ALL SELECT 'dim_products',       COUNT(*),     32951  FROM dim_products
UNION ALL SELECT 'dim_date',           COUNT(*),     1096   FROM dim_date
UNION ALL SELECT 'fact_orderitems',    COUNT(*),     110197 FROM fact_orderitems;

\echo '--- 7. PK / UNIQUE DUPLICATES (every dup = 0) ---'
SELECT 'dim_region.region_id' AS pk, COUNT(*) AS dup FROM (SELECT region_id FROM dim_region GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'dim_region.state UNIQUE', COUNT(*) FROM (SELECT state FROM dim_region GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'dim_category_group.group_id', COUNT(*) FROM (SELECT group_id FROM dim_category_group GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'dim_category_group.group_name UNIQUE', COUNT(*) FROM (SELECT group_name FROM dim_category_group GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'dim_customers.customer_id', COUNT(*) FROM (SELECT customer_id FROM dim_customers GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'dim_sellers.seller_id', COUNT(*) FROM (SELECT seller_id FROM dim_sellers GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'dim_products.product_id', COUNT(*) FROM (SELECT product_id FROM dim_products GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'dim_date.date', COUNT(*) FROM (SELECT date FROM dim_date GROUP BY 1 HAVING COUNT(*)>1) x
UNION ALL SELECT 'fact.(order_id, order_item_id)', COUNT(*) FROM (SELECT order_id, order_item_id FROM fact_orderitems GROUP BY 1,2 HAVING COUNT(*)>1) x;

\echo '--- 8. FACT → DIM FK ORPHANS (every orphans = 0) ---'
SELECT 'fact → customers' AS fk, COUNT(*) AS orphans FROM fact_orderitems WHERE customer_id NOT IN (SELECT customer_id FROM dim_customers)
UNION ALL SELECT 'fact → sellers',   COUNT(*) FROM fact_orderitems WHERE seller_id   NOT IN (SELECT seller_id FROM dim_sellers)
UNION ALL SELECT 'fact → products',  COUNT(*) FROM fact_orderitems WHERE product_id  NOT IN (SELECT product_id FROM dim_products)
UNION ALL SELECT 'fact → date',      COUNT(*) FROM fact_orderitems WHERE orderdate   NOT IN (SELECT date FROM dim_date);

\echo '--- 9. OUTRIGGER FK ORPHANS (orphans = 0; nulls expected) ---'
SELECT 'customers → region' AS fk,
       COUNT(*) FILTER (WHERE region_id IS NOT NULL AND region_id NOT IN (SELECT region_id FROM dim_region)) AS orphans,
       COUNT(*) FILTER (WHERE region_id IS NULL) AS null_fk
FROM dim_customers;

SELECT 'products → category_group' AS fk,
       COUNT(*) FILTER (WHERE category_group_id IS NOT NULL AND category_group_id NOT IN (SELECT group_id FROM dim_category_group)) AS orphans,
       COUNT(*) FILTER (WHERE category_group_id IS NULL) AS null_fk
FROM dim_products;

\echo '--- 10. NULL DISCIPLINE on PK-bearing IDs (bad = 0) ---'
SELECT 'dim_customers.customer_id NULL' AS check, COUNT(*) AS bad FROM dim_customers WHERE customer_id IS NULL
UNION ALL SELECT 'dim_sellers.seller_id NULL',   COUNT(*) FROM dim_sellers   WHERE seller_id  IS NULL
UNION ALL SELECT 'dim_products.product_id NULL', COUNT(*) FROM dim_products  WHERE product_id IS NULL
UNION ALL SELECT 'dim_date.date NULL',           COUNT(*) FROM dim_date      WHERE date       IS NULL
UNION ALL SELECT 'fact.order_id NULL',     COUNT(*) FROM fact_orderitems WHERE order_id  IS NULL
UNION ALL SELECT 'fact.product_id NULL',   COUNT(*) FROM fact_orderitems WHERE product_id IS NULL
UNION ALL SELECT 'fact.orderdate NULL',    COUNT(*) FROM fact_orderitems WHERE orderdate  IS NULL;

\echo '--- 11. GENERATED COLUMN total_item_value = price+freight (mismatches = 0) ---'
SELECT COUNT(*) AS mismatches FROM fact_orderitems
WHERE ROUND(total_item_value,2) <> ROUND(price + freight_value, 2);

\echo
\echo '############################################################'
\echo '## SECTION C — PHASE 1 FIDELITY'
\echo '############################################################'

\echo
\echo '--- 12. PHASE 1 COLUMNS PRESERVED (counts must match expected) ---'
SELECT 'dim_customers' AS t, COUNT(*) AS present, 5 AS expected FROM information_schema.columns
  WHERE table_name='dim_customers' AND column_name IN
  ('customer_id','customer_unique_id','customer_zip_code_prefix','customer_city','customer_state')
UNION ALL SELECT 'dim_sellers', COUNT(*), 4 FROM information_schema.columns
  WHERE table_name='dim_sellers' AND column_name IN
  ('seller_id','seller_zip_code_prefix','seller_city','seller_state')
UNION ALL SELECT 'dim_products', COUNT(*), 8 FROM information_schema.columns
  WHERE table_name='dim_products' AND column_name IN
  ('product_id','product_category_name','product_category_name_english',
   'product_weight_g','product_length_cm','product_height_cm','product_width_cm','product_photos_qty')
UNION ALL SELECT 'dim_date', COUNT(*), 7 FROM information_schema.columns
  WHERE table_name='dim_date' AND column_name IN
  ('date','day','monthname','monthnumber','quarter','weekday','year')
UNION ALL SELECT 'fact_orderitems', COUNT(*), 10 FROM information_schema.columns
  WHERE table_name='fact_orderitems' AND column_name IN
  ('order_item_key','order_id','order_item_id','customer_id','seller_id',
   'product_id','orderdate','price','freight_value','total_item_value');

\echo
\echo '############################################################'
\echo '## SECTION D — PHASE 2 ADDITIONS'
\echo '############################################################'

\echo
\echo '--- 13. PHASE 2 NEW COLUMNS PRESENT (every count = 1) ---'
SELECT 'dim_customers.region_id' AS col, COUNT(*) FROM information_schema.columns WHERE table_name='dim_customers' AND column_name='region_id'
UNION ALL SELECT 'dim_products.category_group_id', COUNT(*) FROM information_schema.columns WHERE table_name='dim_products'  AND column_name='category_group_id'
UNION ALL SELECT 'dim_date.is_holiday',             COUNT(*) FROM information_schema.columns WHERE table_name='dim_date' AND column_name='is_holiday'
UNION ALL SELECT 'dim_date.holiday_name',           COUNT(*) FROM information_schema.columns WHERE table_name='dim_date' AND column_name='holiday_name'
UNION ALL SELECT 'dim_date.is_weekend',             COUNT(*) FROM information_schema.columns WHERE table_name='dim_date' AND column_name='is_weekend'
UNION ALL SELECT 'dim_date.season',                 COUNT(*) FROM information_schema.columns WHERE table_name='dim_date' AND column_name='season'
UNION ALL SELECT 'dim_date.payday_window',          COUNT(*) FROM information_schema.columns WHERE table_name='dim_date' AND column_name='payday_window';

\echo '--- 14. BR HOLIDAYS FLAGGED (5 known holidays, all is_holiday=t) ---'
SELECT date, is_holiday, holiday_name FROM dim_date
WHERE date IN ('2017-09-07','2017-12-25','2018-04-21','2017-11-15','2018-05-01')
ORDER BY date;

\echo '--- 15. HOLIDAY COUNT (expect 25-30 federal BR holidays in window) ---'
SELECT COUNT(*) AS total_holiday_days FROM dim_date WHERE is_holiday;

\echo '--- 16. SEASON DISTRIBUTION (should be ~270 days each) ---'
SELECT season, COUNT(*) FROM dim_date GROUP BY season ORDER BY 1;

\echo '--- 17. PAYDAY-WINDOW DAYS (expect ~270-310) ---'
SELECT COUNT(*) AS payday_days FROM dim_date WHERE payday_window;

\echo '--- 18. REGION DISTRIBUTION (5 macro-regions, all populated) ---'
SELECT macro_region, COUNT(*) AS n_states FROM dim_region GROUP BY 1 ORDER BY 2 DESC;

\echo '--- 19. CATEGORY GROUPS POPULATED (10 rows, each n_products > 0) ---'
SELECT g.group_id, g.group_name, COUNT(p.product_id) AS n_products,
       COUNT(DISTINCT p.product_category_name) AS n_leaf_categories
FROM dim_category_group g LEFT JOIN dim_products p ON p.category_group_id = g.group_id
GROUP BY g.group_id, g.group_name ORDER BY g.group_id;

\echo
\echo '############################################################'
\echo '## SECTION E — FACT DATE COVERAGE'
\echo '############################################################'

\echo
\echo '--- 20. FACT DATE RANGE (must be inside dim_date 2016-2018) ---'
SELECT MIN(orderdate) AS first_order, MAX(orderdate) AS last_order,
       COUNT(DISTINCT orderdate) AS distinct_dates FROM fact_orderitems;

\echo '--- 21. FACT DATES ALL IN dim_date (orphans = 0) ---'
SELECT COUNT(*) AS fact_dates_not_in_dim_date
FROM fact_orderitems WHERE orderdate NOT IN (SELECT date FROM dim_date);

\echo
\echo '############################################################'
\echo '## SECTION F — PERFORMANCE PRIMITIVES (indexes, view counts)'
\echo '############################################################'

\echo
\echo '--- 22. INDEXES ON FACT (expect 5: PK + 4 FK indexes) ---'
SELECT indexname FROM pg_indexes WHERE tablename='fact_orderitems' ORDER BY 1;

\echo '--- 23. VIEW ROW COUNTS (none should be 0) ---'
SELECT 'v_baskets_product'      AS view, COUNT(*) FROM v_baskets_product
UNION ALL SELECT 'v_baskets_category',     COUNT(*) FROM v_baskets_category
UNION ALL SELECT 'v_customer_features',    COUNT(*) FROM v_customer_features
UNION ALL SELECT 'v_orders_with_holiday',  COUNT(*) FROM v_orders_with_holiday;

\echo
\echo '############################################################'
\echo '## SECTION G — CONSUMER QUERY SMOKE TESTS'
\echo '## (the kinds of queries M3, M4, M5 will actually run)'
\echo '############################################################'

\echo
\echo '--- 24. M3 sample — top 5 product-pair co-occurrences (rule-mining input) ---'
WITH pairs AS (
    SELECT LEAST(a.product_id, b.product_id) AS p1,
           GREATEST(a.product_id, b.product_id) AS p2
    FROM fact_orderitems a JOIN fact_orderitems b
      ON a.order_id = b.order_id AND a.product_id < b.product_id
)
SELECT p1, p2, COUNT(*) AS cooccurs FROM pairs GROUP BY 1, 2
ORDER BY 3 DESC LIMIT 5;

\echo '--- 25. M3 sample — top 5 category-group-pair co-occurrences ---'
WITH cat_pairs AS (
    SELECT LEAST(g1.group_name, g2.group_name) AS c1,
           GREATEST(g1.group_name, g2.group_name) AS c2
    FROM fact_orderitems a JOIN fact_orderitems b ON a.order_id = b.order_id AND a.product_id < b.product_id
    JOIN dim_products p1 ON p1.product_id = a.product_id
    JOIN dim_products p2 ON p2.product_id = b.product_id
    JOIN dim_category_group g1 ON g1.group_id = p1.category_group_id
    JOIN dim_category_group g2 ON g2.group_id = p2.category_group_id
)
SELECT c1, c2, COUNT(*) AS cooccurs FROM cat_pairs GROUP BY 1, 2
ORDER BY 3 DESC LIMIT 5;

\echo '--- 26. M4 sample — customer feature distribution (5-number summary) ---'
SELECT
  COUNT(*) AS n_customers,
  AVG(frequency)::NUMERIC(6,2) AS avg_freq, MAX(frequency) AS max_freq,
  AVG(monetary)::NUMERIC(8,2) AS avg_monetary, MAX(monetary)::NUMERIC(8,2) AS max_monetary,
  AVG(avg_basket_size)::NUMERIC(6,2) AS avg_basket, MAX(avg_basket_size)::NUMERIC(6,2) AS max_basket,
  AVG(n_categories)::NUMERIC(6,2) AS avg_n_cats
FROM v_customer_features;

\echo '--- 27. M5 sample — customer × product matrix dimensions ---'
SELECT COUNT(DISTINCT customer_id) AS n_customers,
       COUNT(DISTINCT product_id)  AS n_products,
       COUNT(*) AS n_interactions
FROM fact_orderitems;

\echo '--- 28. M3 holiday-conditioned baskets ready (counts on holiday vs not) ---'
SELECT is_holiday, COUNT(DISTINCT order_id) AS n_orders
FROM v_orders_with_holiday GROUP BY is_holiday;

\echo
\echo '############################################################'
\echo '## SECTION H — DOC/CODE CONSISTENCY'
\echo '############################################################'

\echo
\echo '--- 29. category_group n_categories sums to 73 leaf categories ---'
SELECT SUM(n_cat) AS total_leaf_categories FROM (
    SELECT g.group_id, COUNT(DISTINCT p.product_category_name) AS n_cat
    FROM dim_category_group g LEFT JOIN dim_products p ON p.category_group_id = g.group_id
    GROUP BY g.group_id
) x;

\echo '--- 30. SAMPLE rows from each view (must look real) ---'
\echo '--- v_baskets_product ---'
SELECT * FROM v_baskets_product LIMIT 1;
\echo '--- v_baskets_category ---'
SELECT * FROM v_baskets_category LIMIT 1;
\echo '--- v_customer_features ---'
SELECT * FROM v_customer_features LIMIT 1;
\echo '--- v_orders_with_holiday (holiday row) ---'
SELECT * FROM v_orders_with_holiday WHERE is_holiday LIMIT 1;

\echo
\echo '############################################################'
\echo '##  AUDIT COMPLETE — pass conditions:'
\echo '##  1: exactly 7 tables.    2: extra_tables = 0.'
\echo '##  3: exactly 4 views.     4: extra_views = 0.'
\echo '##  5: 6 FK constraints listed (1 on customers, 1 on products, 4 on fact).'
\echo '##  6: every actual = expected.   7: every dup = 0.   8: every orphans = 0.'
\echo '##  9: orphans = 0 (nulls are OK).   10: every bad = 0.   11: mismatches = 0.'
\echo '## 12: every present = expected (Phase 1 columns intact).'
\echo '## 13: every count = 1 (Phase 2 columns exist).'
\echo '## 14: 5 holiday rows, all is_holiday=t.   15: 25-30 total holidays.'
\echo '## 16: 4 seasons, each ~270 days.   17: ~300 payday days.'
\echo '## 18: 5 macro-regions, all populated.'
\echo '## 19: 10 groups, every n_products > 0.'
\echo '## 20: dates 2016-09..2018-08.   21: 0 fact dates outside dim_date.'
\echo '## 22: 5 indexes.   23: every view rows > 0.'
\echo '## 24-28: M3/M4/M5 sample queries all return real-looking data.'
\echo '## 29: SUM(n_cat) = 73 (every leaf category lives in exactly one group).'
\echo '## 30: each sample row is a real UUID + sensible values.'
\echo '############################################################'
