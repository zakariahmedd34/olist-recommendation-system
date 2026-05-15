"""Step 6c — Re-render dendrograms zoomed to the meaningful range for the paper.

Re-uses the same direct-co-occurrence similarity as cluster_categories_v2.py;
only the visualization changes (Y-axis zoom, gray-out above-threshold links,
ratio annotation pulled from validation_results.txt).
"""
from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
DWH  = ROOT / "dwh"
K    = 10


def read_ratios() -> dict[str, float]:
    out = {}
    for line in (DWH / "validation_results.txt").read_text().splitlines():
        if "ratio=" in line and ":" in line and not line.startswith("winner"):
            name  = line.split(":")[0].strip()
            ratio = float(line.split("ratio=")[1].split(",")[0].strip().rstrip())
            out[name] = ratio
    return out


def build_inputs():
    items  = pd.read_csv(DATA / "olist_order_items_dataset.csv")
    prods  = pd.read_csv(DATA / "olist_products_dataset.csv")
    orders = pd.read_csv(DATA / "olist_orders_dataset.csv")
    delivered = orders.loc[orders.order_status == "delivered", ["order_id"]]
    basket = (items.merge(prods[["product_id", "product_category_name"]], on="product_id")
                   .merge(delivered, on="order_id")
                   [["order_id", "product_category_name"]]
                   .dropna().drop_duplicates())
    cats = sorted(basket["product_category_name"].unique())
    idx  = {c: i for i, c in enumerate(cats)}
    n    = len(cats)
    f = basket["product_category_name"].value_counts().reindex(cats).fillna(0).astype(int).to_numpy()
    M = np.zeros((n, n), dtype=int)
    for _, grp in basket.groupby("order_id"):
        cs = list(grp["product_category_name"].unique())
        for a, b in combinations(cs, 2):
            i, j = idx[a], idx[b]
            M[i, j] += 1
            M[j, i] += 1
    return cats, f, M


def cosine_sim(M, f):
    denom = np.sqrt(np.outer(f, f))
    out = np.divide(M, denom, out=np.zeros_like(M, dtype=float), where=denom > 0)
    np.fill_diagonal(out, 1.0)
    return out


def jaccard_sim(M, f):
    union = f[:, None] + f[None, :] - M
    out = np.divide(M, union, out=np.zeros_like(M, dtype=float), where=union > 0)
    np.fill_diagonal(out, 1.0)
    return out


def render(name: str, sim: np.ndarray, cats: list[str], ratio: float) -> None:
    dist = np.clip(1 - sim, 0, None)
    np.fill_diagonal(dist, 0)
    Z = linkage(squareform(dist, checks=False), method="ward")
    cut_h = Z[-(K - 1), 2]

    plt.figure(figsize=(18, 8))
    dendrogram(
        Z, labels=cats,
        leaf_rotation=90, leaf_font_size=8,
        color_threshold=cut_h,
        above_threshold_color="#bbbbbb",
    )
    plt.axhline(cut_h, ls="--", color="red", linewidth=1.5,
                label=f"k={K} cut · h={cut_h:.3f}")
    plt.ylim(0.85, 1.02)
    plt.ylabel("Ward linkage distance  (1 − similarity)")
    plt.title(
        f"Olist 73-category hierarchical clustering — {name} (direct co-occurrence)\n"
        f"within / cross-group lift ratio = {ratio:.2f}×"
    )
    plt.legend(loc="upper right")
    plt.tight_layout()
    out = DWH / f"dendrogram_{name}.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"✓ {out.name}")


def main() -> None:
    ratios = read_ratios()
    cats, f, M = build_inputs()
    render("cosine",  cosine_sim(M, f),  cats, ratios.get("cosine",  float("nan")))
    render("jaccard", jaccard_sim(M, f), cats, ratios.get("jaccard", float("nan")))
    print("\nPaper-quality PNGs ready in dwh/.")


if __name__ == "__main__":
    main()
