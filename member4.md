# Phase 2 Plan — Olist E-commerce Recommendation (Revised)

**Today:** 2026-05-05 · **Deadline:** 17–21 May 2026
**Target:** 25/25 + 3–5 bonus = **28–30**

> **Revision notes:** This version integrates fixes for five methodological weak spots identified during plan review:
> 1. Category roll-up is now data-driven (co-purchase clustering), not manual.
> 2. Holiday-conditioned mining is gated on an EDA pre-check.
> 3. Hybrid recommender uses Reciprocal Rank Fusion instead of weighted blending.
> 4. Two non-ML baselines (most-popular, category-popular) added to the comparison.
> 5. Cluster profiling is validated via stability and external-feature checks.

---

## Phase 1 fixes (must do before modeling)

| # | Gap | Fix | Owner |
|---|---|---|---|
| 1 | DWH only in Power BI, not implemented | Build real **PostgreSQL** star schema (rubric: 3 pts) | M2 |
| 2 | 88% single-item baskets → weak rules | **Data-driven category roll-up** + mine at category-level (see below) | M2 → M3 |
| 3 | `Dim_Date` too thin | Add `is_holiday`, `holiday_name`, `is_weekend`, `season`, `payday_window` | M2 |
| 4 | `geolocation.csv` unused | Add `Dim_Region` (state/region) | M2 |
| 5 | No related work in deck | Survey ≥8 papers, comparison table | M1 |

## Dataset enrichments

| Source | Use | Bonus |
|---|---|---|
| **Brazilian holidays** (`holidays` lib) | Holiday-conditioned rule mining (gated on EDA — see Track A) | ★★★ novelty |
| **Olist `geolocation.csv`** | Region feature for clustering | ★★ |
| **Data-driven category roll-up** (71 PT cats → ~10 groups via co-purchase clustering) | Dense category-level baskets | ★★★ solves sparsity |

## Bonus-grade hooks (every one is +1 to +5)

- [ ] Holiday-conditioned association rules *(gated on EDA pre-check)*
- [ ] Category-level mining with **data-driven taxonomy**
- [ ] **6 algorithms compared** (Apriori + FP-Growth + ECLAT + K-Means + DBSCAN + Hierarchical), not the rubric minimum of 3
- [ ] **Two non-ML baselines** (most-popular, category-popular) for honest comparison
- [ ] **Hybrid recommender via Reciprocal Rank Fusion** (rules + segments + CF + content fallback)
- [ ] Cold-start content-based fallback
- [ ] Chronological train/test split
- [ ] Full **support × confidence sensitivity sweep** with surface plots
- [ ] **Cluster validation:** stability test (ARI on subsamples) + external-feature check
- [ ] **Streamlit demo** (live recommendations)
- [ ] **Statistical significance test** on Precision@K (Wilcoxon signed-rank + bootstrap CI)
- [ ] Stretch: Neural Collaborative Filtering deep baseline

---

# Member tasks

## 🅜 M1 — Paper & Presentation Lead

> **Depends on:** nobody for related work / intro. Needs M2's schema for methodology. Needs M3+M4+M5 results for the Results section.

**Tasks (in order):**
1. Set up Overleaf with the IEEE template from the guidelines.
2. Survey **≥8 papers** on assoc. rule mining + recommender systems (Olist, Instacart, UCI Online Retail, Amazon).
3. Build a **related-work comparison table** (method × dataset × metrics).
4. Draft **Abstract**.
5. Draft **Introduction**.
6. Draft **Related Work** section.
7. Draft **Methodology** section *(once M2 finishes the DWH and the team agrees on the algorithm list — see sync below)*.
8. Draft **Results & Discussion** *(once M5 hands over the comparison table)*.
9. Write **Conclusion + Future Work**.
10. Run **Turnitin / Grammarly** plagiarism + grammar check.
11. Build **7-minute slide deck**.
12. Coordinate **2 rehearsals** with the team.

> ⏸ **Wait points for M1:**
> - Cannot finalize Methodology until **M2 ships the DWH** and **M3/M4/M5 lock their algorithms**.
> - Cannot write Results until **M5 publishes the comparison table** (last step of the project).

---

## 🅜 M2 — Data Warehouse & ETL Engineer

> **Depends on:** nobody. **M2 is the bottleneck — M3, M4, M5 all wait on M2.** Start day 1.

**Tasks (in order):**
1. Spin up **PostgreSQL** locally (guideline links the tutorial).
2. Write **DDL** for `Fact_OrderItems`, `Dim_Customers`, `Dim_Sellers`, `Dim_Products`, `Dim_Date`.
3. Add **`Dim_Region`** (from `geolocation.csv`).
4. Add **holiday columns** to `Dim_Date` (`is_holiday`, `holiday_name`, `is_weekend`, `season`, `payday_window`) using the Python `holidays` library.
5. **Build the data-driven category roll-up** *(replaces the old manual mapping)*:
   - 5a. Construct a 71×71 category co-purchase matrix from delivered orders. Cell `(i, j)` = count of orders containing both categories.
   - 5b. Convert to similarity matrix (cosine on row vectors, or Jaccard on co-occurrence).
   - 5c. Run **hierarchical clustering** (Ward linkage) on the similarity matrix.
   - 5d. Cut the dendrogram at ~10 clusters. Save the dendrogram figure for the paper.
   - 5e. **Validate:** average rule lift within groups must be ≥1.5× cross-group lift on a small sample mining run. If not, re-cut at a different level.
   - 5f. Write `category_mapping.md` documenting (i) the method, (ii) the dendrogram cut, (iii) the validation result, (iv) example categories per group.
   - 5g. Persist the mapping as `Dim_Category_Group` in the DWH, with FK from `Dim_Products`.
6. Write Python (pandas + SQLAlchemy) **ETL scripts**: Extract 9 CSVs → Transform (clean nulls, EN translation, normalize timestamps, join holidays, apply category roll-up) → Load.
7. Run ETL, verify referential integrity, build indexes on FKs.
8. Publish **SQL views** for the rest of the team:
   - `v_baskets_product` (one row per order with array of `product_id`s)
   - `v_baskets_category` (one row per order with array of category-group labels)
   - `v_customer_features` (Frequency, Monetary, avg basket size, #unique categories, region per customer)
   - `v_orders_with_holiday` (orders joined to holiday flags)
9. Write `schema.md` documentation + export an **ER diagram** (PNG).
10. Stay on call for schema fixes.
11. Help M1 write the **DWH section** of the paper with the ER diagram and the dendrogram figure.

> ⏸ **Wait points for M2:** none — M2 is the unblocker. **Must finish steps 1–8 before M3, M4, M5 can start.**

---

## 🅜 M3 — Association Rules (Track A)

> **Depends on:** M2 (needs `v_baskets_product`, `v_baskets_category`, `v_orders_with_holiday`). Later depends on M4 (needs cluster assignments for per-segment rules).

**Tasks (in order):**
1. **Wait for M2 to publish basket views.**
2. Pull baskets into pandas. Use both representations: **product-level** and **category-group-level** (the data-driven 10 groups from M2).
3. Implement **Apriori** (mlxtend).
4. Implement **FP-Growth** (mlxtend).
5. Implement **ECLAT** (pyECLAT).
6. Run all three on both basket representations.
7. **Sensitivity sweep:** `min_support ∈ {0.001, 0.005, 0.01, 0.02}` × `min_confidence ∈ {0.1, 0.3, 0.5, 0.7}`. Plot rule-count + avg-lift surface.
8. **Holiday-conditioned mining — gated on EDA pre-check** *(replaces the old direct mining)*:
   - 8a. **EDA pre-check first:** count delivered orders falling in holiday windows. Compute basket-size distribution and category mix for holiday vs non-holiday orders. Run a quick chi-square test on category proportions.
   - 8b. **Decision gate:**
       - If ≥ 5,000 holiday baskets *and* category-mix differs significantly → proceed with full holiday-conditioned mining.
       - If < 5,000 baskets *or* signal weak → **pivot to seasonal mining** (Q4 vs rest of year, or Black Friday + Christmas window only).
   - 8c. Document the decision and the EDA evidence in the paper. Either outcome is publishable — a negative finding ("Brazilian holidays don't shift category mix in this sample") is still a contribution.
   - 8d. Mine the chosen condition. Compare top-K rules across conditions.
9. **Per-segment mining** *(after M4 ships clusters)*: mine rules per cluster.
10. Export top rules + metrics as **ranked CSV lists** (top-K per query item) → hand to M5 for hybrid integration. *Must be ranked, not just scored — M5's RRF needs ordered lists.*
11. Help M1 write the assoc.-rules subsection.

> ⏸ **Wait points for M3:**
> - Steps 1–8: wait for **M2** to finish DWH.
> - Step 9: wait for **M4** to publish `customer_id → cluster_id` table.

---

## 🅜 M4 — Clustering & Segmentation (Track B)

> **Depends on:** M2 (needs `v_customer_features` + `Dim_Region`). M3 and M5 depend on M4's cluster output.

**Tasks (in order):**
1. **Wait for M2 to publish `v_customer_features` and `Dim_Region`.**
2. Pull customer features. Engineer the clustering input: Frequency, Monetary, avg basket size, #unique categories, region one-hot. *(Note: avg review score and additional features held out for external validation — see step 9.)*
3. Standardize (StandardScaler). Build PCA + t-SNE figures for the paper.
4. Run **K-Means** for k ∈ {2..10}. Pick optimal k via Elbow + Silhouette.
5. Run **DBSCAN** (comparison).
6. Run **Hierarchical / Ward** (comparison).
7. Compare the three with Silhouette + Davies-Bouldin.
8. **Profile and name** each cluster ("high-value loyalists", "one-time bargain hunters", "regional bulk buyers", etc.).
9. **Cluster validation — two checks** *(replaces the old "profile and name" alone)*:
   - 9a. **Stability test:** Run K-Means on 5 different 80% subsamples of the customer table. Compute pairwise **Adjusted Rand Index (ARI)** between cluster assignments. Report mean ARI. **If mean ARI < 0.5, the clustering is unstable** — note this in the paper, do not name clusters as if they were robust.
   - 9b. **External-feature validation:** Take features *not used in clustering* (avg review score, avg delivery delay, avg freight share, payment-installment count). Run **ANOVA / Kruskal-Wallis** to test whether clusters differ significantly on these held-out features. If they do, your cluster names earn empirical backing. If they don't, weaken the naming claims in the paper.
   - 9c. Document both validation results. Honest reporting strengthens the paper — "stable clusters validated externally" is a stronger claim than naming clusters with no support.
10. Export `customer_id → cluster_id` table → hand to **M3** (for per-segment rules) and **M5** (for per-segment hybrid).
11. Build silhouette plot + cluster-profile table + stability + ANOVA results for the paper.
12. Help M1 write the segmentation subsection.

> ⏸ **Wait points for M4:**
> - Steps 1–9: wait for **M2** to finish DWH.
> - **M3 and M5 are blocked** by step 10 — finish it as early as possible.

---

## 🅜 M5 — Collaborative Filter + Hybrid + Evaluation

> **Depends on:** M2 (DWH), M3 (rules CSV), M4 (cluster assignments). **M5 finishes last — owns integration.**
> **Eval harness can be built in parallel with M2 — start it early.**

**Tasks (in order):**
1. Build **evaluation harness** (Precision@K, Recall@K, Hit Rate, Coverage). **Can start day 1 — no dependency.**
2. Implement **chronological train/test split** (train: orders before cutoff; test: after).
3. **Build the two non-ML baselines** *(new — for honest comparison)* — can also start day 1:
   - 3a. **Most-popular baseline:** recommend the global top-N most-purchased products to every user.
   - 3b. **Category-popular baseline:** for each user, identify their most-purchased category; recommend top-N most-purchased products within that category.
   - 3c. Score both with the eval harness from step 1. These set the floor that everything else must beat.
4. **Wait for M2 to publish DWH.**
5. Build **customer × product sparse matrix**.
6. Compute **item-item cosine similarity**.
7. Top-K item-based recommender. **Output as ranked list, not raw scores** (RRF needs rankings).
8. **Content-based cold-start fallback** (product category-group + price band) for long-tail items. Output as ranked list.
9. **Wait for M3's ranked-rules CSV and M4's cluster table.**
10. **Build the hybrid recommender via Reciprocal Rank Fusion (RRF)** *(replaces the old weighted blend)*:
    - 10a. Each component produces a top-K **ranked list** per query (user or seed item):
        - (a) Holiday/seasonal-aware rules from M3
        - (b) Per-segment rules from M3+M4
        - (c) Item-item CF from step 7
        - (d) Content-based fallback from step 8
    - 10b. Combine via RRF: `score(item) = Σᵢ 1 / (k + rankᵢ(item))`, with **k=60** (Cormack et al., 2009 — cite this).
    - 10c. **No weight tuning required** — k=60 is the published default. Document this as a deliberate methodological choice.
    - 10d. *(Optional, time permitting)* Implement a weighted-blend variant for a side-by-side comparison. Frame the comparison as a research finding: "RRF performed comparably with simpler tuning."
11. Run evaluation harness on **all 6 systems** *(updated from 4)*:
    - Most-popular baseline (non-ML)
    - Category-popular baseline (non-ML)
    - Apriori-only
    - FP-Growth-only
    - CF-only
    - **Hybrid (RRF)**
12. Build the final **comparison table** (this is the 6-pt rubric line). Include all 6 systems × {Precision@K, Recall@K, Hit Rate, Coverage, runtime}.
13. **Significance testing — updated method:**
    - 13a. Use **Wilcoxon signed-rank test** (not paired t-test) for Precision@K differences. Per-user Precision@K is bounded [0, 1] and zero-inflated, so it's not normally distributed.
    - 13b. Report **bootstrap 95% confidence intervals** alongside the test.
    - 13c. Report **effect size** (Cliff's delta or rank-biserial correlation), not just p-values.
14. Build **Streamlit demo**: type a customer_id → see live top-N recommendations with explanation of which component(s) drove each result.
15. Curate the final code repo (structure below).
16. Hand the comparison table + demo to M1.

> ⏸ **Wait points for M5:**
> - Steps 1–3 (eval harness + baselines): no dependency, start day 1.
> - Steps 5–8: wait for **M2**.
> - Steps 10–12: wait for **M3** (ranked rules) **and M4** (clusters).
> - **M1 is blocked from writing Results until step 12 is done.**

---

## Dependency map (one-glance)

```
M2 ──┬──► M3 ──┐
     ├──► M4 ──┼──► M5 ──► M1 (Results)
     └──► M5 ──┘
M1 (Related Work + Intro + Abstract): independent, runs in parallel from day 1.
M5 (eval harness + non-ML baselines): independent, runs in parallel from day 1.
```

**Critical path:** **M2 → M4 → (M3 + M5) → M5 hybrid → M1 Results.**
If anyone slips, M2 and M4 are the most expensive — protect those two.

---

## Code repo structure (M5 curates)

```
olist-recommender/
├── etl/                  # M2: extract.py, transform.py, load.py, category_rollup.py
├── dwh/                  # M2: ddl.sql, views.sql, schema.md, ER.png, category_mapping.md
├── models/
│   ├── rules/            # M3: apriori.py, fpgrowth.py, eclat.py, sensitivity.py, holiday_eda.py
│   ├── clustering/       # M4: features.py, kmeans.py, dbscan.py, hierarchical.py, validation.py
│   ├── cf/               # M5: item_cf.py, content_fallback.py
│   ├── baselines/        # M5: most_popular.py, category_popular.py
│   └── hybrid/           # M5: rrf.py (and optional weighted_blend.py)
├── evaluation/           # M5: metrics.py, harness.py, significance.py, comparison_table.ipynb
├── notebooks/            # demo.ipynb, figures.ipynb
├── demo/                 # M5: streamlit_app.py
├── paper/                # M1: main.tex, refs.bib, figures/
└── slides/               # M1: final.pdf
```

---

## Final deliverables checklist

| Deliverable | Owner | Pts |
|---|---|---|
| PostgreSQL DWH + ETL + ER diagram + data-driven category taxonomy | M2 | 3 |
| 6 algorithms (3 rules + 3 clustering) + CF + Hybrid (RRF) + 2 non-ML baselines | M3 + M4 + M5 | 3 |
| Comparison table (6 systems) + related work + significance test (Wilcoxon + bootstrap) | M5 + M1 | 6 |
| IEEE paper (8 sections, ≥8 refs) | M1 | 7 |
| Code repo + 7-min presentation + Streamlit demo | All | — |
| **Bonus hooks shipped** | All | **+3 to +5** |
| **TOTAL** | | **28–30** |

---

## Summary of changes vs original plan

| Weak spot | Original | Revised |
|---|---|---|
| **1. Category roll-up** | Manual mapping by intuition | **Data-driven:** co-purchase matrix → hierarchical clustering → dendrogram cut at ~10 → validation via within-group vs cross-group lift |
| **2. Holiday mining** | Run mining directly | **Gated on EDA pre-check:** count holiday baskets + chi-square on category mix; pivot to seasonal mining if signal weak |
| **3. Hybrid recommender** | Weighted blend with weight tuning | **Reciprocal Rank Fusion (RRF)** with published k=60; no weight tuning, no normalization needed; optional weighted-blend comparison for the paper |
| **4. Baselines** | All 4 systems were ML-based | Added **most-popular** and **category-popular** non-ML baselines; comparison now includes 6 systems |
| **5. Cluster profiling** | Post-hoc naming with no validation | **Stability test (ARI on subsamples)** + **external-feature ANOVA** on held-out features (review score, delivery delay, etc.); honest reporting if checks fail |
