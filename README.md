# Olist DM Project — Phase 2 — Member 2 (DWH & ETL)

**Author:** Yasmin (231000650)
**Role:** M2 — Data Warehouse & ETL Engineer
**Course:** Olist E-commerce Recommendation, Phase 2
**Phase 1 baseline:** Power BI–only star schema (`Phase 1 DM FINAL.pbix`)
**Phase 2 deliverable:** real PostgreSQL warehouse + ETL + 4 consumer views + paper artifacts
**Last updated:** after applying Phase 1 fidelity migration

> This README is the **chronological story** of what I built and why each step happened — including every tweak, dead end, and refinement.
> For the **reference manual** (schema details, per-teammate handoff instructions), see [`dwh/M2_handoff.md`](dwh/M2_handoff.md).
> For the **30-check audit report** confirming the schema is correct, see [`dwh/audit_results.txt`](dwh/audit_results.txt).
> For the **18-check Phase 1 fidelity report** confirming every Power Query transformation is replicated, see [`dwh/phase1_fidelity_results.txt`](dwh/phase1_fidelity_results.txt).

---

## TL;DR — 3-sentence summary

Built a PostgreSQL snowflake-extended star schema (7 tables · 110,197 facts · 4 views) with a fully data-driven 10-group category taxonomy that validates at an **11.04× within/cross-group lift ratio**. After the first handoff I re-inspected the Phase 1 `.pbix` more carefully (the `Mashup` section was hidden inside its `DataModel` blob, not exposed as a separate file), discovered a set of Power Query cleaning steps that hadn't been migrated, and applied a **Phase 1 fidelity migration** that replicates every Power Query transformation 1-for-1. The warehouse now has **Phase 1's exact cleaning + Phase 2's new enhancements**; 30 / 30 audit checks pass and 18 / 18 Phase 1 fidelity checks pass.

---

## Why M2 existed — the Phase 1 gap analysis

Phase 1 produced a star-schema design *in Power BI only*. Five gaps were identified during plan review:

| # | Phase 1 gap | What M2 had to add in Phase 2 |
|---|---|---|
| 1 | DWH was Power-BI–only, no real DB engine | Build a real **PostgreSQL** instance |
| 2 | 88% single-item baskets → weak product-level rules | **Data-driven category roll-up** to densify baskets |
| 3 | `Dim_Date` was thin (only calendar fields) | Add `is_holiday`, `holiday_name`, `is_weekend`, `season`, `payday_window` |
| 4 | `geolocation.csv` was never used | Add **`Dim_Region`** (state + macro-region) |
| 5 | No SQL view layer for downstream members | Publish 4 task-specific views (`v_baskets_product`, `v_baskets_category`, `v_customer_features`, `v_orders_with_holiday`) |

Every M2 task in this README maps back to one or more of these gaps.

---

## The 11 implementation steps

### Step 1 — Postgres setup (~5 min)
- **What:** `brew install postgresql@16`, started the service, `createdb olist_dwh`.
- **Why:** Phase 1 gap #1.
- **Tweak:** macOS Postgres uses *peer auth* by default — no password setup needed.

### Step 2 — DDL for 7 tables (~30 min)
- **What:** Wrote [`dwh/ddl.sql`](dwh/ddl.sql) — 1 fact + 4 primary dims + 2 outrigger tables.
- **Why:** Translate Phase 1's star into a real schema, then layer Phase 2 additions (`dim_region`, `dim_category_group`, 5 new `dim_date` columns).
- **Tweaks:**
  - FK ordering: declared `Dim_Region` and `Dim_Category_Group` *before* `Dim_Customers` / `Dim_Products` so the FKs validate.
  - Postgres lowercase folding: restored Phase 1's `Date / MonthName / MonthNumber / OrderDate` as `date / monthname / monthnumber / orderdate` (their lowercase-folded forms) to keep 1-to-1 fidelity without quoting.
  - `total_item_value GENERATED ALWAYS AS (price + freight_value) STORED` — Postgres-enforced so it can never drift.
  - `DROP TABLE IF EXISTS … CASCADE` at the top → idempotent.
  - Schema is technically a **partial snowflake** (two outriggers off `Dim_Customers` and `Dim_Products`) — paper terminology updated to *"star schema extended with outrigger reference tables (Kimball pattern)"*.

### Step 3 — Populated `dim_region` (~2 min)
- **What:** [`etl/load_region.py`](etl/load_region.py) inserts 27 rows (states + 5 macro-regions).
- **Why:** Phase 1 gap #4.
- **Tweak:** Hand-coded `{state: macro_region}` dict instead of scanning the 1 M-row `geolocation.csv` — BR state codes are stable.

### Step 4 — Populated `dim_date` with enrichment (~3 min)
- **What:** [`etl/load_date.py`](etl/load_date.py) populates 1,096 rows (2016-01-01 → 2018-12-31) with day, monthnumber, monthname, quarter, weekday, year + **is_holiday**, **holiday_name**, **is_weekend**, **season**, **payday_window**.
- **Why:** Phase 1 gap #3. Enables M3's holiday-conditioned mining (★★★ bonus) and the seasonal pivot fallback.

### Step 5 — Built the 73×73 category co-purchase matrix (~30 sec)
- **What:** [`etl/build_cooccur.py`](etl/build_cooccur.py).
- **Why:** Phase 1 gap #2 (foundation for the roll-up).

### Step 6 — Clustering into 10 groups (Ward linkage)
- **What:** [`etl/cluster_categories_v2.py`](etl/cluster_categories_v2.py).
- **Why:** Densify baskets to category-level (Phase 1 gap #2).
- **Major refinement (the one allowed re-cut):**
  - **v1** used row-similarity (cosine/Jaccard on rows of `M`). It clustered categories by *similar buying neighbourhoods*, not direct co-purchase — within-group lift came out 0.10×, worse than random.
  - **v2** uses direct pairwise co-occurrence (treat each category as a set of orders; cosine / Jaccard between those sets). Validation jumped to **11.04× cosine** / **9.34× jaccard**.

### Step 6c — Paper-quality dendrogram re-render (~10 sec)
- **What:** [`etl/render_dendrograms.py`](etl/render_dendrograms.py) regenerates `dendrogram_cosine.png` and `dendrogram_jaccard.png` with Y-axis zoomed past the sparsity plateau and clear cluster colours.
- **Why:** First-pass PNGs were dominated by visual noise at distance ≈ 1.0; zooming surfaces the 10 real clusters.

### Step 7 — Validation (~30 sec)
- **What:** [`etl/validate_rollup.py`](etl/validate_rollup.py) computes within-group vs cross-group lift.
- **Result:** cosine **11.04× PASS**, jaccard **9.34× PASS**. Cosine selected.

### Step 8 — Persist `Dim_Category_Group` + manual renames (~5 sec + 10 min)
- **What:** [`etl/persist_groups.py`](etl/persist_groups.py) writes 10 group rows. Then [`dwh/rename_groups.sql`](dwh/rename_groups.sql) renamed 5 of them where the auto-derived top-1 name didn't represent all members.
- **Special case:** Group 10 has 48 of 73 leaf categories — renamed to `diversified_other` and documented as the data-sparsity catch-all.

### Step 9 — Master ETL (~10 min)
- **What:** [`etl/etl.py`](etl/etl.py) loads `dim_customers` (99,441), `dim_sellers` (3,095), `dim_products` (32,951), `fact_orderitems` (110,197). Builds 4 FK indexes. **Filters to `order_status = 'delivered'` only** (improvement over Phase 1).
- **Result:** 0 FK orphans across all 4 fact-to-dim joins.

### Step 10 — Published the 4 consumer views (~2 sec)
- **What:** [`dwh/views.sql`](dwh/views.sql) — the hard handoff. After this, M3/M4/M5 can query real data.

  | View | Consumer | Purpose |
  |---|---|---|
  | `v_baskets_product` | M3 | product-level rule mining baseline |
  | `v_baskets_category` | M3 | dense category-level rule mining |
  | `v_customer_features` | M4 | RFM-style clustering input |
  | `v_orders_with_holiday` | M3 | holiday-conditioned mining bonus |

### Step 11 — Documentation + paper artifacts (~2 hrs)
- `dwh/schema.md` — table-by-table reference.
- `dwh/category_mapping.md` — paper Methodology subsection (auto-generated from live DB).
- `dwh/category_group_examples.csv` — paper Table 2.
- `dwh/ER.png` — generated via `eralchemy2`.
- `dwh/audit.sql` — 30-section reproducible sanity check.

### Step 12 — First team handoff (~30 min)
- `pg_dump -F c -f olist_dwh.dump` (13 MB initially).
- Uploaded `/dwh/`, `/etl/`, dump, and the 9 Olist CSVs to a shared Google Drive folder.
- Granted Editor access to 4 teammates.
- Posted the `🎯 Olist DWH is LIVE` announce in team chat.

---

## Step 13 — Phase 1 fidelity discovery and refinement *(post-handoff)*

After the first handoff, I re-inspected the Phase 1 `.pbix` to verify nothing was missed. The first read had concluded *"there's no `/Mashup` section in [Content_Types].xml, so Phase 1 had no Power Query transformations"* — that conclusion was wrong. The .pbix was created via Power BI Service (`Cloud` origin), which stores `Mashup` **embedded inside the `DataModel` blob** rather than as a separate package section. Decoding the `DataModel` with [`pbixray`](https://pypi.org/project/pbixray/) revealed 5 full M-code blocks (one per table).

### What Phase 1's Power Query actually did (and Phase 2 v1 status)

| Phase 1 transformation | Phase 2 v1 status | Action needed |
|---|---|---|
| Trim + Clean `customer_city` / `customer_state` | ⚠ not explicit (Olist source was already clean) | Apply for fidelity |
| Trim + Clean `seller_city` / `seller_state` | ⚠ same | Apply for fidelity |
| **`Text.Proper(seller_city)`** ("são paulo" → "São Paulo") | ❌ not done | **Apply** |
| **`Text.Upper(seller_state)`** ("sp" → "SP") | ❌ not done | **Apply** |
| **Replace empty/null `product_category_name` with `"unknown"`** | ❌ kept as NULL | **Apply** |
| **Replace null `product_category_name_english` with `"unknown"`** | ❌ kept as NULL | **Apply** |
| **Replace null `product_photos_qty` with `0`** | ❌ kept as NULL | **Apply** |
| **Median-impute null `product_weight_g` / `_length_cm` / `_height_cm` / `_width_cm`** | ❌ kept as NULL | **Apply** |
| Filter `freight_value >= 0` | ⚠ not explicit (Olist had 0 negatives) | Apply for fidelity |
| **`order_item_key = order_id & "-" & order_item_id`** (TEXT concat) | ❌ was BIGSERIAL int | **Apply** |
| Merge fact with Dim_Orders → expand customer_id + order_status + timestamp | ✅ etl.py replicated this | — |
| Remove fact columns `order_status, shipping_limit_date, order_purchase_timestamp` | ✅ etl.py replicated this | — |
| `total_item_value = price + freight_value` | ✅ DDL GENERATED column | — |
| Promote headers + Change types (every table) | ✅ pandas does this | — |
| Remove duplicates on each PK | ✅ PK constraint enforces this | — |
| Generate `Dim_Date` from min/max OrderDate range | ✅ we generate 2016-01..2018-12 (superset) | — |

### The migration: [`dwh/match_phase1_cleaning.sql`](dwh/match_phase1_cleaning.sql)

One SQL script, wrapped in a transaction, with 6 numbered sections matching the table above. Re-runnable; the `order_item_key` rebuild errors if already TEXT, which is the safe idempotency check.

### What changed in the data after running it

```
UPDATE 99441    ← dim_customers trim/clean
UPDATE 3095     ← dim_sellers trim/clean/Proper/Upper
UPDATE 610      ← dim_products: NULL category_name → "unknown"
UPDATE 623      ← dim_products: NULL category_name_english → "unknown"
UPDATE 610      ← dim_products: NULL photos_qty → 0
UPDATE 2        ← dim_products: median-impute 4 dimensions
DELETE 0        ← fact: freight_value < 0 (none existed)
ALTER + UPDATE 110197 ← fact: order_item_key rebuilt as TEXT
4 views recreated
```

Sample post-migration data:

```
seller_id 01c97ebb…   seller_city = "Catanduva"   seller_state = "SP"
product_id a41e356c…  category = "unknown"        weight = 650g, photos_qty = 0
order_item_key = "00010242fe8c5a6d1ba2dd792cb16214-1"
```

### Verification: [`dwh/phase1_fidelity_check.sql`](dwh/phase1_fidelity_check.sql)

18 checks covering every Power Query step. Result: **every `bad` count = 0**, plus the PK type is now `text` (not `bigint`) as Phase 1 required. Full output in [`dwh/phase1_fidelity_results.txt`](dwh/phase1_fidelity_results.txt).

The original 30-section audit was re-run after the migration → still 30 / 30 PASS. The schema is bit-for-bit Phase-1-compatible while keeping every Phase 2 enhancement.

---

## Step 14 — Refreshed team handoff

- Regenerated `pg_dump` → **`olist_dwh.dump` is now 14 MB** (was 13 MB; TEXT keys are larger than BIGINT).
- Re-uploaded to Drive `M2_DB_dump/`.
- Uploaded the 4 new artifacts to `M2_DWH/`:
  - `match_phase1_cleaning.sql`
  - `phase1_fidelity_check.sql`
  - `migration_results.txt`
  - `phase1_fidelity_results.txt`
- Refreshed `audit_results.txt`.
- Posted schema-update message in team chat so teammates re-restore from the new dump.

---

## Final inventory — what each teammate finds in `M2_DWH/`

| File | Role |
|---|---|
| `ddl.sql` | the 7-table schema, idempotent |
| `views.sql` | the 4 consumer views |
| `rename_groups.sql` | the 5 group renames |
| **`match_phase1_cleaning.sql`** | **Phase 1 fidelity migration (NEW)** |
| **`phase1_fidelity_check.sql`** | **18-check Phase 1 fidelity verifier (NEW)** |
| `audit.sql` | 30-section sanity check |
| `audit_results.txt` | captured run of `audit.sql` (post-migration, 30 / 30 PASS) |
| **`migration_results.txt`** | **captured run of the migration (NEW)** |
| **`phase1_fidelity_results.txt`** | **captured fidelity-check output (18 / 18 PASS) (NEW)** |
| `schema.md` | table-by-table reference |
| `category_mapping.md` | paper Methodology subsection |
| `category_group_examples.csv` | paper Table 2 |
| `M2_handoff.md` | reference manual + per-teammate handoff |
| `ER.png` | paper Figure 1 (schema) |
| `dendrogram_cosine.png` | paper Figure 2 (data-driven taxonomy) |
| `dendrogram_jaccard.png` | paper Figure 3 (Jaccard comparison) |
| `validation_results.txt` | raw 11.04× / 9.34× numbers |

---

## What I'd do differently if I had to rebuild from scratch

- **Decode the `.pbix` `DataModel` with `pbixray` on day 1.** First-pass conclusion that "no `Mashup` section → no Power Query" was wrong because the cloud-created PBIX format embeds Mashup inside DataModel. Reading the M code earlier would have saved a round trip.
- **Cluster at k = 15 instead of k = 10**, then merge small groups manually. Might give 6 small interpretable groups + 4 tiny ones, instead of 9 small + 1 giant `diversified_other`. Trade-off: less paper-clean.
- **Filter to "active" categories before clustering** (those with ≥ 50 multi-item co-occurrences). Would remove ~30 long-tail categories from the input, producing tighter groups — but loses the "data-driven taxonomy over ALL categories" framing.

None of these are blocking — the current state is defensible.

---

## Numbers at a glance

| Metric | Value |
|---|---|
| Tables | 7 (1 fact + 4 primary dims + 2 outriggers) |
| Views | 4 |
| Customers | 99,441 |
| Sellers | 3,095 |
| Products | 32,951 |
| Delivered orders | 96,478 |
| Order-item facts | 110,197 |
| Leaf product categories | 73 |
| Data-driven category groups | 10 |
| Category-roll-up validation ratio | **11.04×** (cosine) / 9.34× (Jaccard) |
| BR federal holidays covered | 27 (2016–2018) |
| Brazilian macro-regions | 5 |
| Fact date range | 2016-09-15 → 2018-08-29 |
| Audit checks (schema + integrity + consumer queries) | **30 / 30 PASS** |
| Phase 1 fidelity checks (post-migration) | **18 / 18 PASS** |
| Products imputed from NULL during fidelity migration | 610 category-name + 623 english + 610 photos + 2 dimensions |
| DB dump size | **14 MB** (post-fidelity migration) |

---

## Pointers

- **First read for teammates** → this README (top of file).
- **Restore the warehouse** → see [`dwh/M2_handoff.md`](dwh/M2_handoff.md) "Quick start" + the `pg_restore` line in Step 14 above.
- **Per-teammate handoff notes** → [`dwh/M2_handoff.md`](dwh/M2_handoff.md) §10.
- **Paper Methodology subsection** → [`dwh/category_mapping.md`](dwh/category_mapping.md).
- **Sanity check** → `psql -d olist_dwh -f dwh/audit.sql` → 30 PASS sections.
- **Phase 1 fidelity check** → `psql -d olist_dwh -f dwh/phase1_fidelity_check.sql` → 18 PASS sections.
- **Re-apply migration on a fresh restore** → not needed; the dump already contains the post-migration state.

---------------
---------------

# Olist DM Project — Phase 2 — Member 3 Documentation

**Role:** M3 — Association Rules / Market Basket Analysis  
**Project:** Olist E-commerce Recommendation System  
**Input source:** PostgreSQL Data Warehouse built by M2  
**Main notebook:** `M3_Association_Rules_Olist_READY_FIXED.ipynb`  
**Main output for integration:** `outputs/rules/ranked_rules_for_m5.csv`  
**Readable output for paper/presentation:** `outputs/rules/ranked_rules_for_m5_readable.csv`

---

## 1. Purpose of Member 3 Work

Member 3 is responsible for mining association rules from the Olist order baskets. The goal is to discover patterns of the form:

```text
A -> B
```

Meaning:

> If a customer/order contains item A, item B is likely to appear with it.

The extracted rules are later used by the recommendation pipeline, especially by M5 for the hybrid recommender / Reciprocal Rank Fusion stage.

---

## 2. Data Sources Used

M3 does **not** start from the raw Olist CSV files. M3 starts from M2's PostgreSQL Data Warehouse.

The main views used were:

| View | Purpose in M3 |
|---|---|
| `v_baskets_product` | Product-level basket mining using `product_id` values |
| `v_baskets_category` | Category-group-level basket mining using M2's data-driven category groups |
| `v_orders_with_holiday` | Holiday/seasonal EDA and conditional mining decision |

These views were loaded into pandas inside the notebook.

---

## 3. Finalized Work Went Through 3 Main Steps

The M3 implementation was finalized in three stages. This is important because the first output looked weak, but the later fixes made the final handoff usable and documented.

---

### Step 1 — Initial Association Rule Mining Attempt

**What was done:**

- Loaded M2's basket views from PostgreSQL.
- Converted PostgreSQL arrays into Python lists.
- Converted baskets into one-hot encoded format using `TransactionEncoder`.
- Applied the three required algorithms:
  - Apriori
  - FP-Growth
  - ECLAT-style pair mining
- Ran the algorithms on:
  - Category-level baskets
  - Product-level baskets

**Initial issue discovered:**

Category-level rules returned 0 rules, and product-level rules were very few.
The basket-size EDA showed that the Olist order data is extremely sparse: most orders contain only one product/category. Since association rules require co-occurrence, single-item baskets naturally produce few or no rules.

---

### Step 2 — Fixes, Threshold Tuning, and Final Algorithm Run

**What was fixed/improved:**

- Output folders were created automatically inside the notebook.
- Empty CSV files were saved with headers, so they can still be read later.
- Product-level thresholds were tuned to avoid ending with only 3 weak outputs.
- A threshold-trial table was produced to document the support/confidence search.
- Product-level mining was finalized using lower support values suitable for sparse Olist baskets.

**Final algorithm outputs:**

| Output file | Rows | Meaning |
|---|---:|---|
| `product_apriori_rules.csv` | 10 | Final product-level Apriori rules |
| `product_fpgrowth_rules.csv` | 10 | Final product-level FP-Growth rules |
| `product_eclat_rules.csv` | 10 | Final product-level ECLAT-style rules |
| `category_apriori_rules.csv` | 0 | No category-level rules due to sparse baskets |
| `category_fpgrowth_rules.csv` | 0 | No category-level rules due to sparse baskets |
| `category_eclat_rules.csv` | 0 | No category-level rules due to sparse baskets |

**Important interpretation:**

FP-Growth produced the same rule set as Apriori but with much faster runtime, so it is the more efficient algorithm for this dataset.

---

### Step 3 — Final Handoff, Holiday/Seasonal Decision, and Readable Rules

**What was finalized:**

- Holiday EDA was performed before holiday-conditioned mining.
- The notebook counted holiday vs non-holiday baskets.
- A chi-square test was used to check whether category distribution differed between holiday and non-holiday orders.
- Because the holiday sample was too small and the signal was weak, the notebook pivoted to seasonal mining.
- Final ranked rules were exported for M5.
- A readable version of the ranked rules was created by joining product/category metadata.

**Holiday/seasonal result:**

| Metric | Value |
|---|---:|
| Holiday baskets | 1,459 |
| Non-holiday baskets | 93,687 |
| Chi-square p-value | 0.0818 |
| Final decision | Seasonal pivot |

**Final ranked output:**

| Output file | Rows | Purpose |
|---|---:|---|
| `ranked_rules_for_m5.csv` | 30 | Main handoff file for M5 / RRF hybrid recommender |
| `ranked_rules_for_m5_readable.csv` | 30 | Same rules with readable product/category information for paper and slides |

---

## 4. Algorithms Implemented

### 4.1 Apriori

Apriori was used as the classic baseline association-rule algorithm. It finds frequent itemsets by gradually expanding from single items to larger itemsets, then generates rules based on support and confidence.

### 4.2 FP-Growth

FP-Growth was used as a faster alternative to Apriori. In the final product-level run, it produced the same rules as Apriori but with much lower runtime.

### 4.3 ECLAT-style Pair Mining

ECLAT-style mining was implemented using vertical transaction ID sets. It finds product pairs by intersecting the transaction sets of products, then calculates support, confidence, and lift.

---

## 5. Evaluation Metrics Used for Rules

| Metric | Meaning |
|---|---|
| Support | How often the item pair appears in all baskets |
| Confidence | When A appears, how often B also appears |
| Lift | How much stronger the relationship is than random chance |
| Runtime | Time needed to generate the rules |

Rules were ranked mainly by:

```text
lift DESC, confidence DESC, support DESC
```

This means the strongest non-random relationships are prioritized first.

---

## 6. Main Results Summary

The final product-level rules showed a small number of strong co-purchase relationships. Some rules had very high lift values, meaning the item pairs co-occur much more often than expected by random chance.

Example strong results from the final ranked rules:

| Query item | Recommended item | Confidence | Lift |
|---|---|---:|---:|
| `f4f67ccaece962d013a4e1d7dc3a61f7` | `4fcb3d9a5f4871e8362dfedbdb02b064` | 0.3036 | 51.2968 |
| `36f60d45225e60c7da4558b070ce4b60` | `e53e557d5a159f5aa2c5e995dfdf244b` | 0.3091 | 30.1845 |
| `35afc973633aaeb6b877ff57b2793310` | `99a4788cb24856965c36a24e339b6058` | 0.1895 | 6.2512 |

---

## 7. Output Files Produced by M3

### Rule Outputs

| File | Description |
|---|---|
| `product_apriori_rules.csv` | Product-level rules from Apriori |
| `product_fpgrowth_rules.csv` | Product-level rules from FP-Growth |
| `product_eclat_rules.csv` | Product-level rules from ECLAT-style mining |
| `category_apriori_rules.csv` | Category-level Apriori rules; empty due to sparse baskets |
| `category_fpgrowth_rules.csv` | Category-level FP-Growth rules; empty due to sparse baskets |
| `category_eclat_rules.csv` | Category-level ECLAT-style rules; empty due to sparse baskets |

### EDA and Tuning Outputs

| File | Description |
|---|---|
| `basket_size_summary.csv` | Basket-size statistics proving sparsity |
| `product_threshold_trials.csv` | Product support/confidence threshold trials |
| `sensitivity_results_category.csv` | Category-level support/confidence sensitivity sweep |
| `holiday_eda_summary.csv` | Holiday EDA decision summary |
| `holiday_category_mix.csv` | Holiday vs non-holiday category proportions |
| `seasonal_category_rules.csv` | Seasonal category rules; empty due to sparse category baskets |

### Final Handoff Outputs

| File | Used by | Description |
|---|---|---|
| `ranked_rules_for_m5.csv` | M5 | Main ranked recommendation-rule file for RRF hybrid recommender |
| `ranked_rules_for_m5_readable.csv` | M1 / M5 | Same ranked rules with product category metadata for explanation |

### Figure Outputs

The following figures were generated in `outputs/figures/`:

- `category_apriori_rule_count_sweep.png`
- `category_apriori_avg_lift_sweep.png`
- `category_fp_growth_rule_count_sweep.png`
- `category_fp_growth_avg_lift_sweep.png`
- `category_eclat_style_rule_count_sweep.png`
- `category_eclat_style_avg_lift_sweep.png`

---

## 8. How M5 Should Use M3 Outputs

M5 should use:

```text
outputs/rules/ranked_rules_for_m5.csv
```

This file contains ranked recommendation rules with the following columns:

| Column | Meaning |
|---|---|
| `query_item` | Item already purchased / seed item |
| `recommended_item` | Item recommended by the rule |
| `rank` | Rank of recommendation for that query item |
| `algorithm` | Apriori, FP-Growth, or ECLAT-style |
| `basket_type` | Product or category |
| `condition` | all / holiday / seasonal / segment condition |
| `segment_id` | Customer segment if available; currently `None` until M4 handoff |
| `support` | Rule support |
| `confidence` | Rule confidence |
| `lift` | Rule lift |

For the hybrid recommender, M5 can treat every row as an ordered rule recommendation. If a customer has bought `query_item`, the system may recommend `recommended_item`. Since the file is ranked, it can be directly used in Reciprocal Rank Fusion.

---

## 9. M4 Handoff / How Member 4 Should Start

M4 does **not** need to wait for M3 to start clustering. M4 mainly starts from M2's warehouse view:

```text
v_customer_features
```

M4 should perform customer segmentation using features such as:

- Frequency
- Monetary value
- Average basket size
- Number of unique categories
- Region / state features

M4 will run clustering algorithms such as:

- K-Means
- DBSCAN
- Hierarchical clustering

After M4 finalizes customer segments, M4 should export a cluster assignment file for M3 and M5.

### Required M4 Output for M3

M4 should send M3 a file named something like:

```text
outputs/clustering/customer_cluster_assignments.csv
```

Minimum required columns:

| Column | Required? | Meaning |
|---|---|---|
| `customer_id` | Yes | Customer identifier matching the DWH/customer records |
| `cluster_id` | Yes | Final assigned customer segment |
| `cluster_label` | Optional but useful | Human-readable name, e.g., high-value customers |
| `algorithm` | Optional | Usually K-Means if that is the selected final clustering model |

Example:

```csv
customer_id,cluster_id,cluster_label,algorithm
06b8999e2fba1a1fbc88172c00ba8bc7,0,high_value_loyalists,KMeans
18955e83d337fd6b2def6b18a428ac77,1,one_time_buyers,KMeans
```

### How M3 Will Use M4 Output Later

After M4 sends `customer_cluster_assignments.csv`, M3 will do per-segment association-rule mining:

```text
Cluster 0 baskets -> association rules
Cluster 1 baskets -> association rules
Cluster 2 baskets -> association rules
...
```

The output will extend the current ranked rules file by filling `segment_id` instead of `None`.

Expected future file:

```text
outputs/rules/per_segment_ranked_rules_for_m5.csv
```

This will allow M5 to recommend different products for different customer segments.

---

## 10. Current Status

| Task | Status |
|---|---|
| Load M2 views | Done |
| Product-level Apriori | Done |
| Product-level FP-Growth | Done |
| Product-level ECLAT-style mining | Done |
| Category-level Apriori / FP-Growth / ECLAT | Done, but produced 0 valid rules due to basket sparsity |
| Sensitivity sweep | Done |
| Holiday EDA gate | Done |
| Seasonal pivot | Done |
| Ranked rules for M5 | Done |
| Readable rules for paper | Done |
| Per-segment mining | Waiting for M4 cluster assignments |

---

## 11. Notes for the Paper / Presentation

> Olist order-level baskets are highly sparse because most orders contain only one product/category. This limits the effectiveness of classical market basket analysis at the order level.

This explains why category-level rules were not generated even after threshold tuning. Product-level rules were still found, but only a limited number of high-lift rules were produced.

> Association-rule mining was applied using Apriori, FP-Growth, and ECLAT-style pair mining. Due to the high proportion of single-item baskets in the Olist dataset, category-level mining did not generate valid rules. Product-level mining produced a small set of high-lift rules, and FP-Growth achieved the same rules as Apriori with lower runtime.

---

## 12. Conclusion

The final workflow applied Apriori, FP-Growth, and ECLAT-style mining, performed threshold sensitivity analysis, executed the holiday EDA gate, pivoted to seasonal analysis when the holiday signal was weak, and exported ranked product-level rules for M5.

The main technical conclusion is that the Olist dataset is sparse at the order-basket level. This made category-level rule mining ineffective, but product-level mining still produced a small set of strong, high-lift rules. These rules are now ready for integration into the hybrid recommendation system, while per-segment rule mining remains pending until M4 provides customer cluster assignments.

---
---

# Olist DM Project — Phase 2 — Member 4 (Customer Clustering & Segmentation)

**Author:** Zakaria (ID: zakariahmedd34)
**Role:** M4 — Customer Clustering & Segmentation
**Input:** `v_customer_features` view from M2 PostgreSQL DWH + 3 enriched features from raw CSVs
**Main notebook:** `notebooks/M4_Customer_Clustering.ipynb`
**Full report:** `M4_Report.md`
**Primary output for M3 & M5:** `outputs/clustering/customer_cluster_assignments.csv`

---

## 1. Purpose

M4 segments all 96,478 Olist customers into meaningful behavioral groups using unsupervised clustering. The resulting segments are handed off to M3 (per-segment association rules) and M5 (hybrid recommender routing).

---

## 2. Data & Feature Engineering

The base feature set comes from M2's `v_customer_features` view (frequency, monetary, avg_basket_size, n_categories, region). However, ~97% of Olist customers are one-time buyers with a single item — leaving these features with near-zero variance.

Three continuous features were computed from the raw CSVs and added before clustering:

| Feature | Source | Description |
|---------|--------|-------------|
| `avg_review_score` | `olist_order_reviews_dataset.csv` | Customer satisfaction (1–5) |
| `freight_share` | `olist_order_items_dataset.csv` | Freight cost as fraction of total spend |
| `payment_installments` | `olist_order_payments_dataset.csv` | Avg payment instalments per order |

`delivery_delay_days` was computed but kept **held out** for external validation only.

**Final feature matrix:** 96,478 × 12 (7 numeric + 5 region one-hot columns), scaled with `StandardScaler`.

---

## 3. Algorithms

| Algorithm | Approach | Notes |
|-----------|----------|-------|
| **K-Means** | Full 96k dataset, k-means++, n_init=25 | Grid search k=2…10 |
| **DBSCAN** | 15k subsample in PCA-5 space + 1-NN propagation | Port 22 memory constraint workaround |
| **Hierarchical (Ward)** | 10k subsample + 1-NN propagation | Full n×n matrix = 34.7 GB — not feasible |

---

## 4. Results

**Best algorithm: K-Means (k=5)**

| Metric | Value |
|--------|-------|
| Silhouette | **0.4082** |
| Davies-Bouldin | 0.9631 |
| Stability (mean ARI, 5×80% subsamples) | **0.8109** ✅ |

### Customer Segments

| Cluster | Segment Name | Size | % | Monetary | Freight Share | Instalments |
|---------|-------------|------|---|----------|--------------|-------------|
| C0 | Urban Core Buyers | 66,200 | 68.6% | 150 BRL | 0.195 | 2.83 |
| C1 | Southern Mid-Spend Buyers | 13,814 | 14.3% | 162 BRL | 0.223 | 2.97 |
| C2 | Central High-Value Buyers | 5,624 | 5.8% | 177 BRL | 0.227 | 2.94 |
| C3 | Credit-Reliant Northeast Buyers | 9,044 | 9.4% | 201 BRL | 0.263 | 3.50 |
| C4 | Remote Northern Premium Buyers | 1,796 | 1.9% | 223 BRL | 0.283 | 3.31 |

The clustering reveals a **geographic segmentation** driven by Brazil's logistics geography. Freight share increases monotonically from Sudeste (0.195) to Norte (0.283). Northeastern customers show the highest instalment use (3.50), consistent with lower average incomes in that region.

### External Validation (Kruskal-Wallis)

| Feature | Role | H-statistic | p-value | Effect |
|---------|------|------------|---------|--------|
| delivery_delay_days | **HELD-OUT** | 926.81 | < 0.001 | small |
| avg_review_score | enriched | 241.11 | < 0.001 | small |
| freight_share | enriched | 2769.97 | < 0.001 | small |
| payment_installments | enriched | 541.60 | < 0.001 | small |

All clusters differ significantly on every feature (p < 0.001), confirming the segments capture real behavioral and logistic variation.

---

## 5. Output Files

All outputs are in `outputs/clustering/`:

| File | Description |
|------|-------------|
| `customer_cluster_assignments.csv` | **Primary handoff** — customer_id, cluster_id, cluster_label, algorithm |
| `all_algorithm_assignments.csv` | All three algorithm labels per customer |
| `cluster_profile_table.csv` | Per-cluster feature means and segment names |
| `algorithm_comparison.csv` | Silhouette + Davies-Bouldin for all 3 algorithms |
| `stability_results.txt` | ARI scores across 10 subsample pairs |
| `anova_results.txt` | Full Kruskal-Wallis results |
| `*.png` | All clustering visualizations (PCA, t-SNE, heatmap, etc.) |

---

## 6. Handoff to M3 & M5

```
File   : outputs/clustering/customer_cluster_assignments.csv
Columns: customer_id | cluster_id | cluster_label | algorithm
Rows   : 96,478
```

- **M3** uses `cluster_id` to mine per-segment association rules.
- **M5** uses `cluster_id` to route customers to the correct segment-specific recommender.

For the full technical write-up see `M4_Report.md`.

