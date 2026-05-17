"""
Compare original M5 results against the multi-item M5 experiment.

Run after executing notebooks/M5_Hybrid_Recommender_Multi_Item.ipynb:
    python scripts/compare_full_vs_multi_item.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd


def find_project_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in [cwd] + list(cwd.parents):
        if (candidate / "M2_DWH").exists() or (candidate / "olist_dwh.dump").exists():
            return candidate
    return cwd


def main() -> int:
    root = find_project_root()
    full_path = root / "outputs" / "m5" / "comparison_table.csv"
    multi_path = root / "outputs" / "m5_multi_item" / "comparison_table.csv"
    out_dir = root / "outputs" / "m5_multi_item"
    out_dir.mkdir(parents=True, exist_ok=True)

    missing = [p for p in [full_path, multi_path] if not p.exists()]
    if missing:
        print("Missing required comparison file(s):")
        for p in missing:
            print(" -", p)
        print("Run the original M5 and the multi-item M5 notebooks first.")
        return 1

    full = pd.read_csv(full_path)
    multi = pd.read_csv(multi_path)
    full.insert(0, "experiment", "Full Dataset")
    multi.insert(0, "experiment", "Multi-Item Orders Only")
    combined = pd.concat([full, multi], ignore_index=True)
    combined.to_csv(out_dir / "full_vs_multi_item_comparison.csv", index=False)

    metric_cols = [c for c in ["precision_at_10", "recall_at_10", "hit_rate_at_10", "coverage"] if c in combined.columns]
    print("\n=== Full vs Multi-Item M5 Comparison ===")
    print(combined[["experiment", "system"] + metric_cols].to_string(index=False))
    print("\nSaved:", out_dir / "full_vs_multi_item_comparison.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
