# Olist DM Project — Member 2 Handoff Notes

**Owner:** Yasmin (231000650) — M2, Data Warehouse & ETL Engineer
**Project:** Olist E-commerce Recommendation, Phase 2
**Status as of writing:** All M2 deliverables shipped, audited, handoff-ready.

This document records *exactly what was built, why, and how* — so that any teammate can pick up the M2 work cold, and so that I (or anyone) can reconstruct the decisions months later.

---

## 1. Scope of M2

Build a real PostgreSQL data warehouse that supersedes Phase 1's Power-BI-only model. Three deliverables:

1. **PostgreSQL star/snowflake schema** with 7 tables: 1 fact + 4 primary dims + 2 outrigger reference tables.
2. **ETL pipeline** in Python that loads all 9 Olist CSVs into the schema, applies the data-driven category roll-up, and verifies referential integrity.
3. **4 SQL views** that hand basket / customer / holiday data to M3, M4, M5 in the exact shape they need.

Plus the paper-grade artifacts: dendrograms, methodology subsection, ER diagram, validation results, group-examples table.

---

## 2. Connection info

```
Host:      localhost
Port:      5432
Database:  olist_dwh
URL:       postgresql://localhost/olist_dwh
```

No password — default macOS Postgres uses peer auth. Override via env var `DATABASE_URL` if needed.

---

## 3. Schema design

**Snowflake-extended star.** One fact, 4 primary dims, 2 outrigger reference tables.

```
                              dim_region
                                  ↑ FK
                                  |
              dim_customers ──────┘
                    ↑ FK
                    |
dim_date  ←──  fact_orderitems  ──→  dim_sellers
                    ↑ FK
                    |
              dim_products ───────┐
                                  | FK
                                  ↓
                          dim_category_group
```

**Grain:** `fact_orderitems` = one row per item per delivered order (same as Phase 1).

The full DDL is in `dwh/ddl.sql`. Table-by-table column reference is in `dwh/schema.md`.

---

## 4. What was added vs Phase 1

| Addition | Type | Justification |
|---|---|---|
| Real PostgreSQL DB (was Power-BI only) | Replatform | Phase 1 gap #1 — "DWH only in Power BI, not implemented" |
| `dim_region` table (27 BR states + 5 macro-regions) | New outrigger | Phase 1 gap #4 — `geolocation.csv` was unused |
| `dim_category_group` table (10 data-driven groups) | New outrigger | Phase 1 gap #2 — 88% single-item baskets gave weak product-level rules. **★★★ bonus.** |
| `dim_customers.region_id` FK | New column | Links region outrigger; enables `v_customer_features.region` |
| `dim_products.category_group_id` FK | New column | Links category outrigger; enables `v_baskets_category` |
| `dim_date.is_holiday` BOOLEAN | New column | Phase 1 gap #3 — enables M3's holiday-conditioned mining |
| `dim_date.holiday_name` TEXT | New column | Lets M3 condition on specific holidays (Black Friday vs Carnival, etc.) |
| `dim_date.is_weekend` BOOLEAN | New column | Free behavioural feature for M3/M4 |
| `dim_date.season` TEXT | New column | Fallback if holiday signal is too thin (M3's "seasonal pivot") |
| `dim_date.payday_window` BOOLEAN | New column | BR retail spikes on the 1st and 28-31; cheap bonus feature |
| `fact_orderitems.total_item_value` made `GENERATED ALWAYS AS (price + freight_value) STORED` | Type change | Phase 1 computed in Power BI; now DB-enforced — values identical, cannot drift |

**No Phase 1 columns were removed or renamed in spirit.** Three names look different on disk because Postgres lowercase-folds unquoted identifiers (so Phase 1's `Date` / `MonthName` / `MonthNumber` / `OrderDate` are now `date` / `monthname` / `monthnumber` / `orderdate`). Data is unchanged.

---

## 5. Tweaks, gotchas, and decisions worth remembering

These are the non-obvious choices and refinements made during build:

### 5.1 — Lowercase identifier folding
Postgres lowercases unquoted identifiers. Phase 1's CamelCase column names (`Date`, `MonthName`, etc.) became lowercase. Avoided quoting throughout to keep queries readable. **Mention this once in the paper.**

### 5.2 — Snowflake instead of pure star
Phase 1's deck said "star schema, 1 fact + 4 dims". After adding `dim_region` and `dim_category_group` as outriggers (each referenced by a primary dim), the schema is technically a **partial snowflake**. M1's paper says: *"star schema extended with two outrigger reference tables (Kimball pattern) to capture geographic hierarchy and the data-driven category roll-up."* This is honest, accurate, and academically defensible.

### 5.3 — Data-driven category roll-up: one methodology refinement
First attempt used **cosine/Jaccard on rows** of the co-occurrence matrix → clustered categories with similar *neighborhoods* (i.e., categories that co-occur with the same OTHER categories, but not necessarily with each other). Within-group lift came out 0.10× — clusters were full of categories that *avoid* each other. Replaced with **direct pairwise co-occurrence** similarity (treat each category as a set of orders containing it; compute cosine/Jaccard between those sets). Validation jumped to **11.04× cosine** / **9.34× jaccard** — both pass the ≥1.5× threshold.

**This single refinement is documented in `category_mapping.md` under "Methodological note: similarity choice" — it counts as the one allowed re-cut from the .md plan. No further iterations were made.**

### 5.4 — The 10 groups
Auto-named after each group's most-populous member category. 5 groups had clean semantics; 5 had mixed members and were manually renamed (`rename_groups.sql`) to better-fitting names:

| group_id | original name (top-1)           | renamed to               | reason |
|---:|---|---|---|
| 1  | fashion_roupa_feminina          | `fashion_apparel`        | both members are clothing |
| 7  | cool_stuff                      | `electronics_misc`       | mostly tablets / pc_gamer |
| 8  | ferramentas_jardim              | `gifts_household`        | tools + toys + babies → gift baskets |
| 9  | instrumentos_musicais           | `music_homecomfort`      | second member is casa_conforto_2 |
| 10 | beleza_saude → personal_care_acc | `diversified_other`     | renamed twice — it's the 48-category catch-all, not really personal care |

### 5.5 — Group 10 is the catch-all
48 of 73 leaf categories and 20,736 of 32,341 products land in `diversified_other`. This is a real artefact of Olist's 88%-single-item-basket sparsity, not a bug. The dendrograms show it clearly as a high-distance plateau. Documented as a limitation in `category_mapping.md` and as a publishable methodological observation.

### 5.6 — Olist source-data quirks worth knowing
- **88% single-item baskets** → category-level mining is more useful than product-level.
- **`product_category_name` is NULL for ~610 products** → those products have `category_group_id = NULL`, so they're excluded from `v_baskets_category` (correct behaviour).
- **Customer IDs are per-purchase**, not persistent. `customer_unique_id` is the persistent identity. The DWH preserves both.
- **`order_status` ≠ 'delivered'` orders are filtered out** before the fact table is built (Phase 1 didn't filter; this is a Phase 2 improvement).
- **`geolocation.csv` is ~1M rows** — we only used it as a reference, aggregating to 27 states with hand-coded macro-region mappings (Olist's state codes are stable BR UF codes).

### 5.7 — DDL ordering matters
The first DDL pass had `Dim_Customers REFERENCES Dim_Region` before `Dim_Region` was created — Postgres throws "relation does not exist". The fixed ordering in `dwh/ddl.sql` creates referenced tables first: Region → Category_Group → Customers → Sellers → Products → Date → Fact.

### 5.8 — Idempotent DDL
`dwh/ddl.sql` starts with `DROP TABLE IF EXISTS … CASCADE` so it can be re-run safely during development without DB recreate. Same pattern in `views.sql`.

### 5.9 — Postgres install on macOS
`brew install postgresql@16` + `brew services start postgresql@16` works out of the box on Apple Silicon. Connection uses peer auth (no password) for the local user.

### 5.10 — ER export
`eralchemy2` choked on `python3 -m eralchemy2` because the package has no `__main__`. The console script works. Graphviz must be installed first via `brew install graphviz`. Fallback: DBeaver's diagram export.

---

## 6. File map

```
/Users/yasminradwan/olist_project/
├── data/                          ← 9 Olist CSVs (Kaggle public dataset)
├── dwh/
│   ├── ddl.sql                    ← creates the 7 tables, idempotent
│   ├── views.sql                  ← creates the 4 consumer views
│   ├── rename_groups.sql          ← the 5 group renames (re-runnable)
│   ├── audit.sql                  ← 30-section pre-handoff sanity check
│   ├── audit_results.txt          ← captured run of audit.sql (all PASS)
│   ├── schema.md                  ← table-by-table column reference
│   ├── category_mapping.md        ← paper-quality Methodology subsection
│   ├── category_group_examples.csv ← paper Table 2 source
│   ├── validation_results.txt     ← raw 11.04× / 9.34× numbers
│   ├── dendrogram_cosine.png      ← Figure 1 in the paper
│   ├── dendrogram_jaccard.png     ← Figure 2 (comparison)
│   ├── ER.png                     ← snowflake-extended ER diagram
│   └── M2_handoff.md              ← this file
└── etl/
    ├── db.py                      ← shared SQLAlchemy engine factory
    ├── load_region.py             ← Step 3: 27 BR states + macro-regions
    ├── load_date.py               ← Step 4: holiday/season/payday cols
    ├── build_cooccur.py           ← Step 5: 73×73 co-purchase matrix
    ├── cluster_categories.py      ← Step 6 v1 (row-similarity, failed)
    ├── cluster_categories_v2.py   ← Step 6 v2 (direct co-occurrence, PASSED)
    ├── render_dendrograms.py      ← Step 6c: paper-quality re-render
    ├── validate_rollup.py         ← Step 7: within/cross-group lift check
    ├── persist_groups.py          ← Step 8: write Dim_Category_Group
    ├── etl.py                     ← Step 9: master ETL (customers/sellers/products/fact)
    └── export_paper_artifacts.py  ← Step 11: writes category_mapping.md + CSV
```

---

## 7. How to reproduce the M2 work from scratch

On a clean machine with Postgres 12+ and Python 3.10+:

```bash
# 1. Project + dependencies
git clone <repo>            # or copy /Users/yasminradwan/olist_project/
cd olist_project
pip install -r requirements.txt
createdb olist_dwh

# 2. Place the 9 Olist CSVs in data/  (download from Kaggle "Brazilian E-Commerce Public Dataset by Olist")

# 3. Schema
psql -d olist_dwh -f dwh/ddl.sql

# 4. Day-1 loads
cd etl
python3 load_region.py            # 27 BR states
python3 load_date.py              # 1,096 days with holiday/season cols
python3 build_cooccur.py          # 73×73 co-purchase matrix
python3 cluster_categories_v2.py  # cosine + jaccard, Ward, k=10
python3 validate_rollup.py        # picks cosine (11.04× ratio)
python3 persist_groups.py         # writes Dim_Category_Group
python3 render_dendrograms.py     # paper-quality PNGs

# 5. Optional: rename mixed-content groups
cd ..
psql -d olist_dwh -f dwh/rename_groups.sql

# 6. Day-2 master ETL
cd etl
python3 etl.py                    # loads customers/sellers/products/fact

# 7. Views
cd ..
psql -d olist_dwh -f dwh/views.sql

# 8. Paper artifacts
cd etl
python3 export_paper_artifacts.py # writes category_mapping.md + CSV

# 9. ER diagram
brew install graphviz
pip install eralchemy2
eralchemy2 -i postgresql://localhost/olist_dwh -o dwh/ER.png

# 10. Audit
cd ..
psql -d olist_dwh -f dwh/audit.sql 2>&1 | tee dwh/audit_results.txt
```

End-state: 7 tables × full row counts, 4 views, 11 artifacts in `/dwh/`.

---

## 8. Validation results (final, committed)

- **Selected similarity:** cosine on basket-indicator vectors (direct co-occurrence)
- **Within-group lift:** 1.59
- **Cross-group lift:** 0.14
- **Ratio:** **11.04×** (target: ≥ 1.5×)
- **Comparison:** Jaccard achieved 9.34× — also passing; cosine wins by 18%

Raw numbers in `dwh/validation_results.txt`.

---

## 9. Known limitations to mention in the paper

1. **88% single-item baskets** → thin co-occurrence signal at the long tail.
2. **`diversified_other` group has 48 of 73 leaf categories** — honest reflection of the sparsity; not artificially split.
3. **One methodology refinement** (row-similarity → direct co-occurrence) is reported as such; only one re-cut budget was used.
4. **Category-group names** reflect each group's most-populous member only; less-frequent members may be semantically distant.
5. **Date range** of fact data is 2016-09 to 2018-08; `dim_date` spans 2016-01 to 2018-12 to allow forward-looking analysis.

---

## 10. Handoff notes for each consumer

### → M3 (Association Rules)
- **Mine on `v_baskets_category`** (one row per delivered order, array of category-group names) for the dense category-level rules.
- **Also mine on `v_baskets_product`** for the sparse product-level baseline (1.5-pt rubric requires both).
- **Holiday-conditioned mining**: join your baskets to `v_orders_with_holiday` on `order_id`, filter by `is_holiday = TRUE` or by `season`. If holiday baskets are <5,000, fall back to `season` (the `.md` plan calls this the seasonal pivot).
- The 10 category groups + their member sets are in `category_group_examples.csv`.

### → M4 (Clustering)
- **Cluster on `v_customer_features`** — already aggregated to one row per customer with frequency, monetary, avg basket size, n_categories, region.
- **`region` is the macro-region** (5 categories: Norte / Nordeste / Centro-Oeste / Sudeste / Sul) — one-hot encode it for K-Means.
- For external-feature validation (the ANOVA bonus), pull raw `order_reviews` / `order_payments` directly from the Olist CSVs (those tables aren't loaded in the DWH because nothing else needs them — keep that lean).

### → M5 (Collaborative Filter + Hybrid)
- **Customer × product matrix:** `SELECT customer_id, product_id, COUNT(*) FROM fact_orderitems GROUP BY 1,2;` — that's your sparse-matrix source.
- **Chronological train/test split:** use `orderdate`. Cutoff suggestion: 2018-04-01 (~80/20 split by row count).
- **Content-based fallback:** the `product_category_name_english` column on `dim_products` is your text feature; the `category_group_id` is your discrete fallback feature.

### → M1 (Paper)
- **Methodology subsection:** copy-paste `dwh/category_mapping.md` into the paper.
- **Figures:** ER.png (Figure 1: schema), dendrogram_cosine.png (Figure 2: data-driven taxonomy).
- **Table 2:** import `dwh/category_group_examples.csv` into Overleaf.
- **DWH section talking points:** snowflake-extended star, 7 tables, 110k facts, 32k products, 99k customers, 96k delivered orders.
- **Validation paragraph:** cite the 11.04× ratio from `validation_results.txt`.

---

## 11. Pre-handoff audit

`dwh/audit.sql` runs 30 sanity checks covering schema shape, data integrity, Phase 1 fidelity, Phase 2 additions, fact date coverage, performance primitives, consumer-query smoke tests, and doc/code consistency. Output captured in `dwh/audit_results.txt`. **All checks passed at handoff time.**

To re-run after any change:

```bash
psql -d olist_dwh -f dwh/audit.sql 2>&1 | tee dwh/audit_results.txt
```

---

## 12. Contact

If anything breaks during the rest of Phase 2, ping me first — I can fix schema/view/ETL issues fastest. For methodology questions about the category roll-up, the answers are in `category_mapping.md`.
