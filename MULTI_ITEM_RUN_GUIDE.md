# Multi-Item Recommendation Experiment — Ready Run Guide

This adds a separate experiment without replacing the original project.

Original results stay in:

```text
outputs/rules/
outputs/m5/
```

New multi-item experiment results go to:

```text
outputs/rules_multi_item/
outputs/figures_multi_item/
outputs/m5_multi_item/
```

## What changed

Added files:

```text
scripts/create_multi_item_dataset.py
scripts/compare_full_vs_multi_item.py
notebooks/00_Create_Multi_Item_Dataset.ipynb
notebooks/M3_Association_Rules_Multi_Item.ipynb
notebooks/M5_Hybrid_Recommender_Multi_Item.ipynb
notebooks/M5_Compare_Full_vs_Multi_Item.ipynb
run_multi_item_experiment.ps1
```

Updated:

```text
requirements.txt
```

## Option A — Run everything from PowerShell

Open PowerShell in the project root and run:

```powershell
.\run_multi_item_experiment.ps1
```

It will ask for the PostgreSQL password, install requirements, run M3 multi-item, run M5 multi-item, and create the comparison file.

## Option B — Run manually in Jupyter

Run these notebooks in order:

```text
1. notebooks/M3_Association_Rules_Multi_Item.ipynb
2. notebooks/M5_Hybrid_Recommender_Multi_Item.ipynb
3. notebooks/M5_Compare_Full_vs_Multi_Item.ipynb
```

Optional only if `shared_data/` exists and you want filtered raw CSVs:

```text
notebooks/00_Create_Multi_Item_Dataset.ipynb
```

## Final files to check

After running, check:

```text
outputs/rules_multi_item/multi_item_filter_summary_from_db.csv
outputs/rules_multi_item/ranked_rules_for_m5.csv
outputs/rules_multi_item/ranked_rules_for_m5_with_segments.csv
outputs/m5_multi_item/comparison_table.csv
outputs/m5_multi_item/full_vs_multi_item_comparison.csv
```

## What to say in the discussion

Do not say: “We removed single-item orders from the whole project.”

Say:

```text
We kept the full dataset for the main DWH/business analysis, then added a controlled multi-item basket experiment for the recommendation task. Since many Olist orders contain only one product, we filtered the recommendation experiment to orders with more than one distinct product and compared the new results against the original full-dataset results.
```
