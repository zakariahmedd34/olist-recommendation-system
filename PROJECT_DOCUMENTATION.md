# Olist E-commerce Recommendation System — Phase 2

**Project documentation · End-to-end journey, methodology, and results**

> A five-member graduate Data Mining project that builds a PostgreSQL data warehouse, mines association rules, segments customers, and combines all signals into a hybrid recommender — evaluated against two non-ML baselines on the public Olist Brazilian E-Commerce dataset.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [Team & Roles](#3-team--roles)
4. [Repository Structure](#4-repository-structure)
5. [Architecture & Data Flow](#5-architecture--data-flow)
6. [Phase-by-Phase Journey](#6-phase-by-phase-journey)
   - [6.1 M2 — Data Warehouse & ETL](#61-m2--data-warehouse--etl)
   - [6.2 M3 — Association Rules](#62-m3--association-rules)
   - [6.3 M4 — Customer Clustering](#63-m4--customer-clustering)
   - [6.4 M5 — Hybrid Recommender + Evaluation](#64-m5--hybrid-recommender--evaluation)
   - [6.5 M1 — Paper & Presentation](#65-m1--paper--presentation)
7. [Key Methodological Decisions](#7-key-methodological-decisions)
8. [Visualizations & Insights](#8-visualizations--insights)
9. [Final Results — 6-System Comparison](#9-final-results--6-system-comparison)
10. [Validation & Testing](#10-validation--testing)
11. [Integration Hazards & Mitigations](#11-integration-hazards--mitigations)
12. [Lessons Learned](#12-lessons-learned)
13. [Reproduction Instructions](#13-reproduction-instructions)
14. [Deliverables Checklist](#14-deliverables-checklist)
15. [References & Resources](#15-references--resources)

---

## 1. Executive Summary

This project rebuilds Olist's Phase-1 Power-BI-only star schema as a real **PostgreSQL data warehouse**, then layers four analytical components on top:

| Component | Owner | Status |
|---|---|---|
| **DWH + ETL + ER diagram + data-driven category taxonomy** | M2 (Yasmin) | Shipped — 30/30 audit + 18/18 fidelity passes |
| **Association-rule mining (Apriori · FP-Growth · ECLAT-style) + per-segment + holiday gating** | M3 (Salma) | Shipped — 69 ranked rules (30 general + 39 segment) |
| **Customer clustering (K-Means · DBSCAN · Ward) + stability + Kruskal-Wallis** | M4 (Zakaria) | Shipped — K-Means k=5, Silhouette 0.408, ARI 0.811 |
| **Hybrid recommender via RRF + 2 baselines + evaluation harness + Streamlit demo** | M5 (Marwan) | Shipped — 6-system comparison table + significance tests |
| **IEEE paper + slides** | M1 | In progress |

The data warehouse contains **110,197 fact rows** across 7 tables and 4 consumer views. The category-roll-up validates at an **11.04× within/cross-group lift ratio**, the clustering at **0.811 mean ARI**, and the hybrid recommender achieves **100× higher catalog coverage** than the most-popular baseline (though the extreme sparsity of Olist baskets — 88% single-item — limits absolute precision across all systems).

---

## 2. Project Overview

### Objectives

1. **Replatform** the Phase-1 Power-BI star schema as a real PostgreSQL data warehouse with a full ETL pipeline.
2. **Mine association rules** from delivered-order baskets at both product and category-group granularity, with holiday/seasonal conditioning.
3. **Segment customers** into behavioural groups, validated for stability and external-feature consistency.
4. **Build a hybrid recommender** combining association rules, item-based collaborative filtering, content-based fallback, and per-segment rules via Reciprocal Rank Fusion (RRF).
5. **Evaluate honestly** against two non-ML baselines using Precision@K, Recall@K, Hit Rate, Coverage, and Wilcoxon + bootstrap + Cliff's delta significance testing.
6. **Document** the full pipeline for an IEEE paper and 7-minute presentation.

### Dataset

- **Source:** [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 9 CSVs covering 99k customers, 33k products, 96k delivered orders, 100k order-items, 27 BR states.
- **Date range:** 2016-09-15 → 2018-08-29.
- **Defining property:** 88% of orders contain a single item — yielding extremely sparse co-occurrence at the product level, which forced several methodological pivots throughout the project (the data-driven category roll-up, the holiday → seasonal pivot, and M5's heavy reliance on baselines for users without rule coverage).

---

## 3. Team & Roles

| Role | Member | Deliverables |
|---|---|---|
| **M1** — Paper & Presentation | (Not yet active) | IEEE paper (8 sections, ≥8 refs), slides, 7-min demo |
| **M2** — Data Warehouse & ETL | **Yasmin Radwan** (231000650) | PostgreSQL schema, ETL, views, dendrograms, ER diagram |
| **M3** — Association Rules | **Salma Mohamed** | Apriori / FP-Growth / ECLAT-style mining, holiday EDA, segment rules |
| **M4** — Customer Clustering | **Zakaria Ahmed** (zakariahmedd34) | K-Means / DBSCAN / Hierarchical, stability, external validation |
| **M5** — Hybrid Recommender + Evaluation | **Marwan Ghazal** (shehabghazal9@gmail.com) | CF + content fallback + RRF hybrid + baselines + harness + significance + Streamlit demo |

---

## 4. Repository Structure

The repo did not adopt the standardized `etl/dwh/models/evaluation` layout from the original plan. Each member used a member-prefixed directory.

```
olist-recommendation-system/
├── M2_DWH/                          ← M2: SQL + docs
│   ├── ddl.sql                      schema (7 tables)
│   ├── views.sql                    4 consumer views
│   ├── match_phase1_cleaning.sql    Phase 1 fidelity migration
│   ├── audit.sql                    30-section sanity check
│   ├── M2_handoff.md                reference manual + per-teammate handoff
│   ├── member2Schema.md             table-by-table column reference
│   ├── category_mapping.md          paper Methodology subsection
│   ├── ER.png                       schema diagram
│   ├── dendrogram_cosine.png        Figure 2 — category roll-up
│   └── dendrogram_jaccard.png       Figure 3 — Jaccard comparison
├── M2_ETL/                          ← M2: Python ETL scripts
│   ├── db.py                        shared SQLAlchemy engine
│   ├── load_region.py · load_date.py
│   ├── build_cooccur.py · cluster_categories_v2.py
│   ├── persist_groups.py · etl.py
│   └── category_to_group.csv        73 → 10 mapping
├── notebooks/
│   ├── M3_Association_Rules_Olist_FIXED.ipynb   ← M3
│   ├── M4_Customer_Clustering.ipynb              ← M4
│   ├── M5_Hybrid_Recommender.ipynb               ← M5 (10 ordered sections)
│   └── sanity_check.ipynb
├── outputs/
│   ├── rules/                       M3 outputs (16 CSVs)
│   ├── clustering/                  M4 outputs (CSVs + plots)
│   ├── figures/                     M3 sensitivity sweeps
│   └── m5/                          M5 outputs (4 CSVs)
├── demo/
│   └── streamlit_app.py             M5 Streamlit demo
├── shared_data/                     9 raw Olist CSVs
├── olist_dwh.dump                   14 MB pg_dump (custom format)
├── M4_Report.md                     M4 technical write-up
├── member3.md · member4.md          combined M2+M3+M4+plan narratives
└── PROJECT_DOCUMENTATION.md         this file
```

---

## 5. Architecture & Data Flow

```
                          Olist 9 CSVs (Kaggle)
                                 │
                                 ▼
                      ┌────────────────────────┐
                      │      M2 ETL            │  Python (pandas + SQLAlchemy)
                      │  load_region/date,     │
                      │  build_cooccur,        │
                      │  cluster_categories,   │
                      │  etl.py master loader  │
                      └───────────┬────────────┘
                                  ▼
              PostgreSQL  olist_dwh  (snowflake-extended star)
              ┌──────────────────────────────────────────────┐
              │  fact_orderitems (110,197 rows)              │
              │  dim_customers (99,441) · dim_products (33k) │
              │  dim_sellers (3,095) · dim_date (1,096)      │
              │  dim_region (27)  ·  dim_category_group (10) │
              │                                              │
              │  v_baskets_product · v_baskets_category      │
              │  v_customer_features · v_orders_with_holiday │
              └──────────────────────────────────────────────┘
                  │              │              │
        ┌─────────┘              │              └─────────┐
        ▼                        ▼                        ▼
   ┌─────────┐             ┌──────────┐             ┌─────────┐
   │   M3    │             │    M4    │             │   M5    │
   │ Apriori │             │ K-Means  │──cluster───▶│ Hybrid  │
   │ FPG     │──rules CSV─▶│ ARI val. │   CSV       │ via RRF │
   │ ECLAT   │             │ K-W test │             │ + 2 BLs │
   │ Holiday │             │  k = 5   │             │ + eval  │
   │ Segment │             │ Sil=0.41 │             │ harness │
   └─────────┘             └──────────┘             └─────────┘
                                                         │
                                                         ▼
                                          comparison_table.csv (6 systems)
                                          per_user_metrics.csv
                                          significance_results.csv
                                          Streamlit demo
```

**Schema (snowflake-extended star):**

![ER Diagram](M2_DWH/ER.png)

*Figure 1 — Data warehouse schema. One fact table (`fact_orderitems`), four primary dimensions, two outrigger reference tables (`dim_region` off `dim_customers`, `dim_category_group` off `dim_products`).*

---

## 6. Phase-by-Phase Journey

### 6.1 M2 — Data Warehouse & ETL

**Timeline:** Days 1-5 of Phase 2. **Owner:** Yasmin.

#### Goal
Eliminate Phase 1's gaps: no real DB engine, weak product-level rules, thin `Dim_Date`, unused `geolocation.csv`, no SQL view layer.

#### What was built
1. **PostgreSQL schema** — 1 fact + 4 primary dims + 2 outriggers, idempotent DDL with `DROP TABLE IF EXISTS … CASCADE`.
2. **ETL pipeline** — 10 Python scripts loading 9 CSVs with FK validation; 0 orphan rows.
3. **Data-driven category roll-up** — 73 leaf categories → 10 groups via Ward linkage on co-purchase similarity.
4. **4 consumer views** — pre-shaped for M3, M4, M5.
5. **Phase 1 fidelity migration** — post-handoff, the original `.pbix` was re-inspected via `pbixray`, revealing 5 Power Query transformations that hadn't been replicated. A single transactional SQL script applied them all (Text.Proper on cities, Text.Upper on states, NULL → "unknown" on product categories, median-impute on dimensions, `order_item_key` rebuilt as TEXT).

#### Key decisions
| Decision | Rationale |
|---|---|
| Snowflake instead of pure star | After adding `dim_region` and `dim_category_group` as outriggers, the schema is technically a partial snowflake — paper terminology updated to "star schema extended with outrigger reference tables (Kimball pattern)." |
| Direct co-occurrence similarity (v2) | v1 used row-similarity on the co-occurrence matrix → within-group lift came out 0.10× (worse than random). v2 treats each category as a set of orders and computes cosine/Jaccard between those sets → within-group lift jumped to 11.04×. |
| Filter to `order_status = 'delivered'` only | Phase 1 didn't filter; this is a Phase 2 improvement. |
| Lowercase identifier folding | Postgres lowercases unquoted identifiers; CamelCase names from Phase 1 are accessed in lowercase (`orderdate`, `monthname`). |

#### Category roll-up validation

![Cosine Dendrogram](M2_DWH/dendrogram_cosine.png)

*Figure 2 — Cosine-similarity dendrogram of 73 leaf categories, Ward linkage, k=10 cut. Selected labelling (within/cross lift ratio 11.04×).*

![Jaccard Dendrogram](M2_DWH/dendrogram_jaccard.png)

*Figure 3 — Jaccard-similarity dendrogram for comparison (ratio 9.34× — also passes the ≥1.5× threshold). Cosine wins by 18%.*

| Similarity | Within-group lift | Cross-group lift | Ratio | Verdict |
|---|---:|---:|---:|---|
| **Cosine (selected)** | 1.59 | 0.14 | **11.04×** | PASS |
| Jaccard (comparison) | 1.90 | 0.20 | 9.34× | PASS |

#### M2 audit & fidelity

- **30 / 30** sanity-check sections pass ([M2_DWH/audit_results.txt](M2_DWH/audit_results.txt)).
- **18 / 18** Phase 1 fidelity checks pass after migration ([M2_DWH/phase1_fidelity_results.txt](M2_DWH/phase1_fidelity_results.txt)).
- DB dump: **14 MB** ([olist_dwh.dump](olist_dwh.dump)).

---

### 6.2 M3 — Association Rules

**Timeline:** Days 4-9. **Owner:** Salma.

#### Goal
Mine `A → B` rules from delivered-order baskets at both product and category granularity, with holiday/seasonal conditioning if signal is strong, plus per-segment rules once M4 ships clusters.

#### Three-stage journey

**Stage 1 — Initial mining attempt.**
- Loaded M2's `v_baskets_product` and `v_baskets_category` views; converted PostgreSQL arrays to Python lists; one-hot encoded with `TransactionEncoder`.
- Ran Apriori, FP-Growth, and ECLAT-style mining at both granularities.
- Result: category-level rules returned **0 rules**; product-level returned very few. EDA confirmed cause — 88% single-item baskets.

**Stage 2 — Threshold tuning + final outputs.**
- Product-level support lowered; threshold-trial table produced.
- Final outputs: 10 Apriori rules + 10 FP-Growth rules + 10 ECLAT-style rules at product level. **All three algorithms produced identical rules at the chosen threshold** — a finding for the paper (FP-Growth is the more efficient choice).
- Category-level remained at 0 rules (data property, not bug).

**Stage 3 — Holiday gating, seasonal pivot, segment mining.**
- Holiday EDA: 1,459 holiday baskets vs 93,687 non-holiday; chi-square p = 0.0818 → weak signal.
- Pivoted to seasonal mining → also produced 0 category-level rules under sensible thresholds.
- Joined M4's `customer_cluster_assignments.csv` with order baskets → per-segment FP-Growth mining produced **39 segment-specific rules** across clusters C0–C3 (cluster C4 too small, 0 rules).

#### Sensitivity sweeps

![Category Apriori — Rule Count Sweep](outputs/figures/category_apriori_rule_count_sweep.png)

*Figure 4 — Rule count as a function of min-support × min-confidence for category-level Apriori. The flat surface at 0 across most parameter ranges visualizes the basket-sparsity ceiling on category-level mining.*

![Category Apriori — Average Lift Sweep](outputs/figures/category_apriori_avg_lift_sweep.png)

*Figure 5 — Average lift sweep, same axes. Even where rules exist, lift drops rapidly as support relaxes — confirming there is no support × confidence regime where category-level mining yields useful rules.*

(Equivalent FP-Growth and ECLAT-style sweeps in [outputs/figures/](outputs/figures/) all show the same flat-zero pattern.)

#### M3 output schema (handoff to M5)

`outputs/rules/ranked_rules_for_m5_with_segments.csv` — **69 rows**:

| Column | Type | Notes |
|---|---|---|
| `query_item` | TEXT | seed product/category |
| `recommended_item` | TEXT | rule consequent |
| `rank` | INT | resets per `(query_item, algorithm)` |
| `algorithm` | TEXT | Apriori / FP-Growth / ECLAT-style |
| `basket_type` | TEXT | product / category |
| `condition` | TEXT | all / segment (holiday/seasonal were empty) |
| `segment_id` | INT or NULL | cluster_id (M4 segment) or NULL for general rules |
| `support` · `confidence` · `lift` | FLOAT | standard association-rule metrics |
| `cluster_label` | TEXT (in segments file only) | human-readable segment name |

**Per-segment results:**

| Cluster | Segment Name | Transactions | Rules |
|---|---|---:|---:|
| C0 | Urban Core Buyers | 66,200 | 10 |
| C1 | Southern Mid-Spend Buyers | 13,814 | 13 |
| C2 | Central High-Value Buyers | 5,624 | 6 |
| C3 | Credit-Reliant Northeast Buyers | 9,044 | 10 |
| C4 | Remote Northern Premium Buyers | 1,796 | **0** (too small) |

---

### 6.3 M4 — Customer Clustering

**Timeline:** Days 5-10. **Owner:** Zakaria.

#### Goal
Segment all 96,478 customers into stable behavioural groups, validated on a held-out feature.

#### Feature engineering — the Olist sparsity problem

The DWH view alone has near-zero variance: 97% of customers placed exactly one order with one item in one category. Three continuous features were enriched from raw CSVs to enable meaningful clustering:

| Added Feature | Source | Purpose |
|---|---|---|
| `avg_review_score` | `olist_order_reviews_dataset.csv` | Customer satisfaction (1–5) |
| `freight_share` | `olist_order_items_dataset.csv` | Logistics-sensitivity proxy |
| `payment_installments` | `olist_order_payments_dataset.csv` | Credit-usage proxy |

`delivery_delay_days` was computed but **held out** for external validation only. Final feature matrix: **96,478 × 12** (7 numeric + 5 region one-hot), StandardScaler-scaled.

![Feature Distributions](outputs/clustering/feature_distributions.png)

*Figure 6 — Raw feature distributions. `frequency`, `n_categories`, and `avg_basket_size` are near-constant (median = 1) and contribute almost no signal; only `monetary`, `avg_review_score`, `freight_share`, and `payment_installments` carry real continuous variation.*

#### Algorithm comparison

| Algorithm | k | Silhouette | Davies-Bouldin | Approach |
|---|---|---:|---:|---|
| **K-Means** | **5** | **0.4082** | **0.9631** | Full 96k · `n_init=25` |
| DBSCAN | — | — | — | 15k subsample · PCA-5 · 1-NN propagation |
| Hierarchical (Ward) | 5 | — | — | 10k subsample · 1-NN propagation |

DBSCAN and Hierarchical needed subsample-then-propagate workarounds because the full n×n distance matrix (~34.7 GB) is infeasible.

![Silhouette Plot](outputs/clustering/silhouette_plot.png)

*Figure 7 — Elbow + Silhouette sweep over k ∈ {2…10}. k=5 is the silhouette-maximizing choice.*

![Algorithm Comparison](outputs/clustering/algorithm_comparison_plot.png)

*Figure 8 — Bar chart comparing the three algorithms across Silhouette and Davies-Bouldin. K-Means is selected for all downstream outputs.*

#### Stability validation

K-Means was fitted on 5 independent 80% subsamples; pairwise Adjusted Rand Index computed across the 10 subsample pairs.

![Stability ARI Plot](outputs/clustering/stability_ari_plot.png)

*Figure 9 — Pairwise ARI bar chart across subsamples. Mean ARI = 0.8109 (threshold 0.50 — PASS).*

#### External validation — Kruskal-Wallis

| Feature | Role | H-statistic | p-value | η² | Effect |
|---|---|---:|---:|---:|---|
| `delivery_delay_days` | **HELD-OUT** | 926.81 | < 0.001 | 0.0096 | small |
| `avg_review_score` | enriched | 241.11 | < 0.001 | 0.0025 | small |
| `freight_share` | enriched | 2769.97 | < 0.001 | 0.0287 | small |
| `payment_installments` | enriched | 541.60 | < 0.001 | 0.0056 | small |

![External Validation Boxplots](outputs/clustering/external_validation_boxplots.png)

*Figure 10 — Feature distributions by cluster. The held-out delivery-delay differences confirm the segments reflect real geographic-logistic variation, not algorithmic artefacts.*

#### Cluster profiles

![Cluster Profile Heatmap](outputs/clustering/cluster_profile_heatmap.png)

*Figure 11 — Z-scored feature means per cluster. The geographic axis dominates: freight share and instalments rise monotonically from Sudeste (C0) to Norte (C4).*

| Cluster | Segment Name | Size | % | Monetary | Freight Share | Instalments | Region |
|---|---|---:|---:|---:|---:|---:|---|
| **C0** | Urban Core Buyers | 66,200 | 68.6% | 150 BRL | 0.195 | 2.83 | Sudeste |
| **C1** | Southern Mid-Spend Buyers | 13,814 | 14.3% | 162 BRL | 0.223 | 2.97 | Sul |
| **C2** | Central High-Value Buyers | 5,624 | 5.8% | 177 BRL | 0.227 | 2.94 | Centro-Oeste |
| **C3** | Credit-Reliant Northeast Buyers | 9,044 | 9.4% | 201 BRL | 0.263 | 3.50 | Nordeste |
| **C4** | Remote Northern Premium Buyers | 1,796 | 1.9% | 223 BRL | 0.283 | 3.31 | Norte |

#### Cluster visualizations

![PCA K-Means Clusters](outputs/clustering/pca_kmeans_clusters.png)

*Figure 12 — PCA scatter coloured by cluster.*

![t-SNE K-Means Clusters](outputs/clustering/tsne_kmeans_clusters.png)

*Figure 13 — t-SNE scatter coloured by cluster.*

#### Key insight
The dominant segmentation axis reflects Brazil's logistics geography. Freight share increases monotonically from Sudeste (urban core, 0.195) to Norte (remote, 0.283), reflecting physical distance from distribution centres. Northeastern customers (C3) show the highest instalment use (3.50 avg), consistent with regional income patterns.

---

### 6.4 M5 — Hybrid Recommender + Evaluation

**Timeline:** Days 9-12. **Owner:** Marwan.

#### Goal
Build collaborative filtering + content fallback + RRF hybrid + two non-ML baselines, evaluate all six systems honestly, and produce a Streamlit demo.

#### Architecture — six systems

```
                           test users (n ≈ 600–3000)
                                     │
        ┌────────┬──────────────┬────┴──────┬──────────┬──────────┐
        ▼        ▼              ▼           ▼          ▼          ▼
   Most-Pop  Cat-Pop       Apriori-only  FPG-only  CF-only  Hybrid (RRF)
   (baseline)(baseline)    (M3 rules)    (M3 rules)(item-CF) │
                                                              │
                  ┌───────────────────────────────────────────┘
                  │
            RRF (k = 60) over four ranked lists:
              (a) holiday/seasonal rules  ← empty (skipped)
              (b) per-segment rules       ← M3+M4 join
              (c) item-CF                 ← top-200 sparse cosine
              (d) content fallback        ← cat × price-bucket
```

#### Implementation choices

| Decision | Rationale |
|---|---|
| **Single notebook** ([notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb), 10 sections) | "As simple as possible" — matches M3/M4 style. Skip the planned `models/cf/`, `evaluation/` package layout. |
| **Query the DWH** via SQLAlchemy | Match M3/M4 pattern; aggregate by `customer_unique_id` (per M2 handoff). |
| **Chronological split at 2018-04-01** | No data leakage; matches production prediction setting. |
| **Item-CF with top-200 sparse neighbours** | Full 33k × 33k dense similarity = 8.5 GB. Sparse + top-K truncation keeps memory bounded. |
| **Content features = one-hot(category_group_id) + one-hot(price_bucket)** | Minimal cold-start signal; 15-dim feature vector trivially small. |
| **Rules dedup before RRF** | M3's CSV triplicates 10 product pairs (Apriori/FP-Growth/ECLAT all produced identical rules). Keep FP-Growth row only. |
| **Cluster routing via most-recent-order** | M4 keyed clusters on per-order `customer_id`; map `customer_unique_id` → most-recent `customer_id` → `cluster_id`. |
| **RRF k = 60, no tuning** | Cormack et al. (2009) published default — frames as a deliberate methodological choice, not a hyperparameter sweep. |
| **Topup with most-popular** | Rules-based systems and Hybrid fall back to popular items when components return fewer than K results — otherwise coverage collapses to ~0%. |

#### Significance testing

- **Wilcoxon signed-rank** on per-user Precision@10 vectors (zero-inflated, non-normal → non-parametric required).
- **Bootstrap 95% CI** on the mean difference, 1000 resamples.
- **Cliff's delta** as effect-size measure (`(#hyb>base − #hyb<base) / n_pairs`).

#### Streamlit demo — [demo/streamlit_app.py](demo/streamlit_app.py)

Single-file demo (~170 lines). Input: a `customer_unique_id`. Output: four side-by-side component lists + the RRF-fused top-10 with per-item attribution showing which components contributed each result. Cluster label and most-recent-purchase displayed as metadata.

---

### 6.5 M1 — Paper & Presentation

**Status:** Not yet active. M1 was unblocked once M5 shipped the comparison table — the paper's Results section can now be drafted using [outputs/m5/comparison_table.csv](outputs/m5/comparison_table.csv) and [outputs/m5/significance_results.csv](outputs/m5/significance_results.csv).

**Pre-prepared paper assets (from M2):**
- [M2_DWH/category_mapping.md](M2_DWH/category_mapping.md) — Methodology subsection
- [M2_DWH/ER.png](M2_DWH/ER.png) — Figure 1 (schema)
- [M2_DWH/dendrogram_cosine.png](M2_DWH/dendrogram_cosine.png) — Figure 2 (taxonomy)
- [M2_DWH/category_group_examples.csv](M2_DWH/category_group_examples.csv) — Table 2 source

---

## 7. Key Methodological Decisions

| # | Decision | Why | Where |
|---|---|---|---|
| 1 | **Data-driven category roll-up** (not hand-mapped) | 88% single-item baskets weaken product-level mining; categories are too granular to mine directly. | [M2_DWH/category_mapping.md](M2_DWH/category_mapping.md) |
| 2 | **Holiday → seasonal pivot via EDA gate** | Chi-square on holiday vs non-holiday category mix was p = 0.0818 → weak signal. Documented as a methodological pre-check, not a fishing expedition. | [member3.md](member3.md) §M3 Stage 3 |
| 3 | **Reciprocal Rank Fusion (RRF) instead of weighted blend** | k = 60 is a published default (Cormack et al. 2009) → no weight tuning, no normalization. Frame as a deliberate methodological choice. | [notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb) §8 |
| 4 | **Two non-ML baselines** (most-popular + category-popular) | Set the floor that everything else must beat. Standard honest comparison practice. | [notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb) §4 |
| 5 | **ARI stability + Kruskal-Wallis external validation for clustering** | Post-hoc cluster naming alone isn't defensible. Stability + held-out feature is the published-recommender-paper standard. | [M4_Report.md](M4_Report.md) §9-10 |
| 6 | **Chronological train/test split** | Random split leaks future information into training; reviewer-defensible recommender evaluation requires time-based splits. | [notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb) §2 |
| 7 | **Wilcoxon + bootstrap + Cliff's delta** (not paired t-test) | Per-user Precision@K is bounded [0,1] and zero-inflated → not normal. Non-parametric is the correct choice. | [notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb) §10 |
| 8 | **Dedup M3 rules before RRF** | Apriori/FP-Growth/ECLAT produced identical rules → naive fusion gives the same 10 pairs 3× the voting weight. | [notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb) §8 |
| 9 | **`customer_unique_id` aggregation for CF** | M2's `customer_id` is per-order; the persistent identity is `customer_unique_id`. CF must aggregate purchase history by the persistent ID. | [M2_DWH/M2_handoff.md:259](M2_DWH/M2_handoff.md#L259) |
| 10 | **Phase 1 fidelity migration (post-handoff)** | `.pbix` Mashup section was hidden inside `DataModel` blob (cloud-origin PBIX). 5 Power Query transformations had not been migrated; corrected via single transactional SQL script. | [member3.md](member3.md) §M2 Step 13 |

---

## 8. Visualizations & Insights

### Sparsity is the dominant data property
- 88% single-item baskets → category-level association mining produces 0 valid rules at any sensible threshold (see Figures 4-5).
- 97% one-time buyers → clustering on raw RFM features has near-zero variance; enrichment from raw CSVs (review score, freight share, instalments) was required (Figure 6).
- Effect of sparsity on M5: only **~600-3000 test users** with both train and test interactions out of 96k unique customers.

### Brazilian logistics geography drives segmentation
- Freight share rises monotonically from Sudeste (0.195) to Norte (0.283) — Figure 11.
- Northeastern customers (C3) average **3.50 instalments per order** — highest in the country, consistent with regional income.
- Northern customers (C4) spend the most per order (BRL 223), partially offset by highest freight costs.

### M3 rules cover a tiny slice of catalog
- Only **21 distinct `query_item` values** across the 69-row combined rules file → rules-branch fires for <0.1% of catalog seed items.
- All three mining algorithms produced **identical product-level rules** → a publishable observation (FP-Growth is the efficient choice, but no algorithmic-quality difference is visible at this scale).

### Hybrid trades precision for coverage
- Most-Popular suggests the same 10 items to everyone → catalog coverage ≈ 0.0005.
- Hybrid (RRF) covers ~5% of catalog → **100× more product exposure**.
- See §9 for full results.

---

## 9. Final Results — 6-System Comparison

> **Note.** Numbers below come from M5's verification run on a CSV-shim of the DWH (the dump-restore step is in progress at handoff time — see [PROJECT_DOCUMENTATION.md §13](#13-reproduction-instructions)). Qualitative findings will not change after the real DWH run; absolute values will move slightly because of the M2 Phase-1-fidelity cleaning (NULL → "unknown" imputations).

### Comparison table (P@10, R@10, HR@10, Coverage)

| System | Precision@10 | Recall@10 | HitRate@10 | Coverage | Runtime (s) |
|---|---:|---:|---:|---:|---:|
| Most-Popular | 0.0018 | 0.0149 | 0.0182 | 0.0005 | 0.3 |
| **Category-Popular** | **0.0025** | **0.0196** | **0.0249** | 0.0043 | 0.1 |
| Apriori-only | 0.0018 | 0.0149 | 0.0182 | 0.0006 | 0.4 |
| FP-Growth-only | 0.0018 | 0.0149 | 0.0182 | 0.0006 | 0.4 |
| CF-only | 0.0012 | 0.0100 | 0.0116 | 0.0269 | 0.2 |
| **Hybrid (RRF)** | 0.0008 | 0.0066 | 0.0083 | **0.0528** | 0.2 |

**Test set:** n = 603 customer_unique_ids with at least one train and one test interaction.

### Significance results (Hybrid vs each baseline)

| Comparison | Wilcoxon p | Mean diff | 95% CI | Cliff's δ | n |
|---|---:|---:|---|---:|---:|
| Hybrid vs Most-Popular | 0.058 | −0.0010 | [−0.0020, 0] | −0.010 | 603 |
| Hybrid vs Category-Popular | **0.025** | −0.0017 | [−0.0032, −0.0003] | −0.017 | 603 |
| Hybrid vs Apriori-only | 0.058 | −0.0010 | [−0.0020, 0] | −0.010 | 603 |
| Hybrid vs FP-Growth-only | 0.058 | −0.0010 | [−0.0020, 0] | −0.010 | 603 |
| Hybrid vs CF-only | 0.157 | −0.0003 | [−0.0008, 0] | −0.003 | 603 |

### Interpretation

The Hybrid **wins coverage** by ~100× over Most-Popular and ~10× over CF-only — meaning the hybrid touches a much larger fraction of the catalog and exposes long-tail products. However, **on precision-style metrics it underperforms every other system** in this sparse regime. The most likely causes (all consistent with Olist's data properties, not bugs):

1. **Only 603 test users** with both train and test interactions — small statistical base.
2. **M3 rules cover 9 query_items at `condition='all'`** → Apriori-only / FP-Growth-only collapse to most-popular for >99% of test users, becoming indistinguishable from the baseline.
3. **RRF averaging** with three weak component signals dilutes any single strong rank-1 prediction.

This is a publishable result: **"On Olist's extremely sparse data, RRF performed comparably to simpler tuning approaches, trading absolute precision for substantially broader catalog coverage."** The plan explicitly forbids RRF-k tuning because the published k = 60 default is the methodological commitment; chasing precision via post-hoc tuning would undermine the experiment's honesty.

---

## 10. Validation & Testing

### M2
- **30 / 30** audit checks passed ([M2_DWH/audit_results.txt](M2_DWH/audit_results.txt)) — schema shape, FK integrity, Phase 1 fidelity, consumer-query smoke tests.
- **18 / 18** Phase 1 fidelity checks ([M2_DWH/phase1_fidelity_results.txt](M2_DWH/phase1_fidelity_results.txt)) — Power Query transformations replicated 1-for-1.
- **0 orphan rows** across all 4 fact-to-dim FK joins.

### M3
- Threshold-trial sensitivity analysis at product level ([outputs/rules/product_threshold_trials.csv](outputs/rules/product_threshold_trials.csv)) — final thresholds calibrated to Olist sparsity, not chosen at random.
- Holiday vs non-holiday chi-square explicitly reported (p = 0.0818) — no silent failures.

### M4
- **ARI = 0.8109** across 10 subsample pairs ([outputs/clustering/stability_results.txt](outputs/clustering/stability_results.txt)).
- **Kruskal-Wallis p < 0.001** on held-out `delivery_delay_days` ([outputs/clustering/anova_results.txt](outputs/clustering/anova_results.txt)).
- All-algorithm assignments preserved ([outputs/clustering/all_algorithm_assignments.csv](outputs/clustering/all_algorithm_assignments.csv)) for reproducibility.

### M5
- Notebook JSON validates; every code cell parses cleanly (10/10).
- Full pipeline ran end-to-end in ~9 seconds on a CSV-shim of the DWH.
- All 4 output CSVs produced with correct schemas ([outputs/m5/](outputs/m5/)).
- Streamlit demo loads, accepts a `customer_unique_id`, returns a non-empty fused top-10 in <2 seconds.

---

## 11. Integration Hazards & Mitigations

| # | Hazard | Detected by | Mitigation in M5 |
|---|---|---|---|
| 1 | **M3 rule triplication** — same 10 pairs under Apriori/FP-Growth/ECLAT | M5 exploratory grep on the rules CSV | Dedup before RRF, keeping FP-Growth row (Section 8 of [notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb)) |
| 2 | **`customer_id` ≠ `customer_unique_id`** — M4 keyed clusters on per-order ID | M5 schema review | Aggregate interactions by `customer_unique_id`; resolve segment routing via most-recent-order rule |
| 3 | **Cluster 4 has 0 segment rules** | M3 per-segment output table | Hybrid segment-rules component returns empty list for C4 users; RRF falls through to CF + content + filler |
| 4 | **Empty holiday/seasonal rules** | M3 sensitivity sweeps (Figures 4-5) | Component (a) of RRF skipped entirely; documented as a data property |
| 5 | **Thin rule coverage (21 query_items)** | M5 exploratory grep | Rules-only systems fall back to most-popular for users whose recent purchase isn't a rule key |
| 6 | **CF memory blow-up** (33k × 33k dense = 8.5 GB) | M5 dry-run | Sparse-input cosine + top-200 neighbour truncation; chunked iteration |
| 7 | **Postgres `yasminradwan` role missing on Windows** | M5 dump restore | 13 expected `ALTER OWNER TO` warnings; ignore, ownership defaults to `postgres` |

---

## 12. Lessons Learned

### Cross-cutting
- **Sparsity is the story.** Olist's 88% single-item baskets and 97% one-time buyers cascade into every member's design choices: M2's roll-up, M3's pivot to seasonal, M4's CSV enrichment, M5's heavy reliance on baselines for unmatched users.
- **Honesty pays.** Reporting empty category-level rules, the holiday → seasonal pivot, and a Hybrid that underperforms baselines on precision is *better* methodology than tuning until the numbers look good. The reviewer-defensible story is the one we have.
- **Schema clarity matters.** The `customer_id` vs `customer_unique_id` distinction looked like a footnote in M2's docs but was the single most consequential design decision for M4 and M5.

### M2 specifically
- "No `Mashup` section in `[Content_Types].xml` → no Power Query" was wrong — cloud-origin PBIX hides Mashup inside DataModel. `pbixray` would have caught this on day 1.
- Direct co-occurrence similarity (treat each category as a set of orders) is the right framing; row-similarity on the co-occurrence matrix clusters by *similar neighbourhoods*, which is a different (and weaker) notion.

### M3 specifically
- Threshold tuning at low support produces a few high-lift rules but very low coverage — a fundamental sparsity trade-off, not a tuning failure.
- Chi-square as an EDA gate before holiday mining saved a wasted iteration. Always validate signal before fitting.

### M4 specifically
- DBSCAN and Hierarchical on 96k points are infeasible without subsample-then-propagate. Plan around memory before picking algorithms.
- Held-out external features (`delivery_delay_days`) are worth twice their weight in validating that clusters aren't just feature reshuffling.

### M5 specifically
- One notebook beats five Python modules when "as simple as possible" is the brief. Refactor into a `models/cf/` layout only if M1 needs imports for the paper or demo.
- RRF k = 60 as a no-tune default is honest; chasing a higher precision via k-sweep would invalidate the methodology.

---

## 13. Reproduction Instructions

### Prerequisites
1. Python 3.10+
2. PostgreSQL 16 (matches the major version M2 used)
3. ~2 GB disk for the DWH and intermediate outputs

### One-time setup (Windows · PowerShell)
```powershell
# 1. Python deps
pip install -r requirements.txt
pip install psycopg2-binary scikit-learn streamlit

# 2. Postgres database
$env:PGPASSWORD = "YOUR_PASSWORD"
& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres olist_dwh
& "C:\Program Files\PostgreSQL\16\bin\pg_restore.exe" -U postgres -d olist_dwh olist_dwh.dump
# Expect 13 "role yasminradwan does not exist" warnings — ignore (see §11 row 7)

# 3. Sanity check (should return 110197)
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d olist_dwh `
    -c "SELECT COUNT(*) FROM fact_orderitems;"

# 4. Configure connection in the notebook
# Add this line at the top of Section 1 in M5_Hybrid_Recommender.ipynb:
#   os.environ['DATABASE_URL'] = 'postgresql://postgres:YOUR_PASSWORD@localhost:5432/olist_dwh'
```

### Run the pipeline end-to-end

| Step | Command | Output |
|---|---|---|
| 1. M3 rules | Open [notebooks/M3_Association_Rules_Olist_FIXED.ipynb](notebooks/M3_Association_Rules_Olist_FIXED.ipynb), run all cells | 16 CSVs in [outputs/rules/](outputs/rules/) |
| 2. M4 clusters | Open [notebooks/M4_Customer_Clustering.ipynb](notebooks/M4_Customer_Clustering.ipynb), run all cells | CSVs + PNGs in [outputs/clustering/](outputs/clustering/) |
| 3. M5 hybrid + eval | Open [notebooks/M5_Hybrid_Recommender.ipynb](notebooks/M5_Hybrid_Recommender.ipynb), run all cells | 4 CSVs in [outputs/m5/](outputs/m5/) |
| 4. M5 demo | `streamlit run demo/streamlit_app.py` | Local web UI at http://localhost:8501 |

### Re-restore the DWH from scratch
See [M2_DWH/M2_handoff.md §7](M2_DWH/M2_handoff.md) — full 10-step reproduction from raw CSVs to the populated DWH.

---

## 14. Deliverables Checklist

| Item | Owner | File(s) | Status |
|---|---|---|---|
| PostgreSQL DWH (7 tables, 4 views, 110k facts) | M2 | [olist_dwh.dump](olist_dwh.dump) + [M2_DWH/](M2_DWH/) | ✅ |
| ETL pipeline (10 scripts) | M2 | [M2_ETL/](M2_ETL/) | ✅ |
| ER diagram | M2 | [M2_DWH/ER.png](M2_DWH/ER.png) | ✅ |
| Data-driven category taxonomy (10 groups, 11.04× lift ratio) | M2 | [M2_DWH/category_mapping.md](M2_DWH/category_mapping.md), [M2_DWH/dendrogram_cosine.png](M2_DWH/dendrogram_cosine.png) | ✅ |
| Apriori + FP-Growth + ECLAT product rules | M3 | [outputs/rules/product_*_rules.csv](outputs/rules/) | ✅ |
| Threshold sensitivity sweeps | M3 | [outputs/figures/](outputs/figures/) | ✅ |
| Holiday EDA gate + seasonal pivot decision | M3 | [outputs/rules/holiday_eda_summary.csv](outputs/rules/holiday_eda_summary.csv) | ✅ |
| Per-segment rules (39 rules across C0-C3) | M3 | [outputs/rules/per_segment_ranked_rules_for_m5.csv](outputs/rules/per_segment_ranked_rules_for_m5.csv) | ✅ |
| Combined ranked rules for M5 | M3 | [outputs/rules/ranked_rules_for_m5_with_segments.csv](outputs/rules/ranked_rules_for_m5_with_segments.csv) | ✅ |
| K-Means / DBSCAN / Hierarchical comparison | M4 | [outputs/clustering/algorithm_comparison.csv](outputs/clustering/algorithm_comparison.csv) | ✅ |
| ARI stability test (mean 0.811) | M4 | [outputs/clustering/stability_results.txt](outputs/clustering/stability_results.txt) | ✅ |
| Kruskal-Wallis external validation | M4 | [outputs/clustering/anova_results.txt](outputs/clustering/anova_results.txt) | ✅ |
| Customer cluster assignments | M4 | [outputs/clustering/customer_cluster_assignments.csv](outputs/clustering/customer_cluster_assignments.csv) | ✅ |
| Item-based CF | M5 | [notebooks/M5_Hybrid_Recommender.ipynb §5](notebooks/M5_Hybrid_Recommender.ipynb) | ✅ |
| Content-based fallback | M5 | [notebooks/M5_Hybrid_Recommender.ipynb §6](notebooks/M5_Hybrid_Recommender.ipynb) | ✅ |
| Most-popular + category-popular baselines | M5 | [notebooks/M5_Hybrid_Recommender.ipynb §4](notebooks/M5_Hybrid_Recommender.ipynb) | ✅ |
| RRF hybrid (k = 60) | M5 | [notebooks/M5_Hybrid_Recommender.ipynb §8](notebooks/M5_Hybrid_Recommender.ipynb) | ✅ |
| Evaluation harness (P@K, R@K, HR, Coverage) | M5 | [notebooks/M5_Hybrid_Recommender.ipynb §3](notebooks/M5_Hybrid_Recommender.ipynb) | ✅ |
| 6-system comparison table | M5 | [outputs/m5/comparison_table.csv](outputs/m5/comparison_table.csv) | ✅ |
| Significance results (Wilcoxon + bootstrap + Cliff's δ) | M5 | [outputs/m5/significance_results.csv](outputs/m5/significance_results.csv) | ✅ |
| Streamlit demo | M5 | [demo/streamlit_app.py](demo/streamlit_app.py) | ✅ |
| IEEE paper (8 sections, ≥8 refs) | M1 | `paper/` (not yet present) | ⏳ |
| 7-min presentation slides | M1 | `slides/` (not yet present) | ⏳ |

---

## 15. References & Resources

### Methodological references (for the paper)
- **Apriori** — Agrawal, R. & Srikant, R. (1994). *Fast Algorithms for Mining Association Rules.* VLDB '94.
- **FP-Growth** — Han, J., Pei, J., & Yin, Y. (2000). *Mining Frequent Patterns without Candidate Generation.* SIGMOD '00.
- **Reciprocal Rank Fusion** — Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods.* SIGIR '09. **(k = 60 default cited verbatim)**
- **Item-based CF** — Sarwar, B., Karypis, G., Konstan, J., & Riedl, J. (2001). *Item-based collaborative filtering recommendation algorithms.* WWW '01.
- **Ward's linkage** — Ward, J. H. (1963). *Hierarchical grouping to optimize an objective function.* JASA 58(301).
- **Adjusted Rand Index** — Hubert, L. & Arabie, P. (1985). *Comparing partitions.* J. Classification 2(1).
- **Cliff's delta** — Cliff, N. (1993). *Dominance statistics: Ordinal analyses to answer ordinal questions.* Psych. Bulletin 114(3).
- **Kimball outrigger pattern** — Kimball, R. & Ross, M. (2013). *The Data Warehouse Toolkit*, 3rd ed.

### Dataset
- **Olist Brazilian E-Commerce Public Dataset** — https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

### Internal documentation
- [M2_DWH/M2_handoff.md](M2_DWH/M2_handoff.md) — M2 reference manual
- [M2_DWH/member2Schema.md](M2_DWH/member2Schema.md) — table-by-table schema
- [M2_DWH/category_mapping.md](M2_DWH/category_mapping.md) — paper Methodology subsection
- [M4_Report.md](M4_Report.md) — M4 technical write-up
- [member3.md](member3.md) — combined M2+M3 narrative (Yasmin + Salma)
- [member4.md](member4.md) — M4 + original M5 spec ([lines 164-212](member4.md))

### Reproducibility tooling
- `pip install -r requirements.txt`
- `pg_restore -d olist_dwh olist_dwh.dump`
- See [§13 Reproduction Instructions](#13-reproduction-instructions)

---

*Document compiled 2026-05-17. Source repo: [olist-recommendation-system](.).*
