"""Step 6 v2 — Cluster categories by DIRECT pairwise co-occurrence (not row similarity).

Fix for v1: v1 used cosine/Jaccard on rows of the co-occurrence matrix, which
captures "similar neighborhoods" but not direct co-purchase. M3 mines rules on
direct co-purchase, so the similarity must reflect that.

similarity formulas:
    cosine_indicator[i,j]  = |orders_i ∩ orders_j| / sqrt(|orders_i| * |orders_j|)
    jaccard_indicator[i,j] = |orders_i ∩ orders_j| / |orders_i ∪ orders_j|

where |orders_i| = number of delivered orders containing category i (multi or single).
"""
from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
ETL  = ROOT / "etl"
DWH  = ROOT / "dwh"
K    = 10


def build_basket_freq_and_cooccur():
    """Return (cats, basket_freq, cooccur_matrix) all aligned on cats order."""
    items  = pd.read_csv(DATA / "olist_order_items_dataset.csv")
    prods  = pd.read_csv(DATA / "olist_products_dataset.csv")
    orders = pd.read_csv(DATA / "olist_orders_dataset.csv")
    delivered = orders.loc[orders.order_status == "delivered", ["order_id"]]
    basket = (
        items.merge(prods[["product_id", "product_category_name"]], on="product_id")
             .merge(delivered, on="order_id")
             [["order_id", "product_category_name"]]
             .dropna().drop_duplicates()
    )

    cats = sorted(basket["product_category_name"].unique())
    idx  = {c: i for i, c in enumerate(cats)}
    n    = len(cats)

    basket_freq = basket["product_category_name"].value_counts().reindex(cats).fillna(0).astype(int).to_numpy()
    M = np.zeros((n, n), dtype=int)
    for _, grp in basket.groupby("order_id"):
        cs = list(grp["product_category_name"].unique())
        for a, b in combinations(cs, 2):
            i, j = idx[a], idx[b]
            M[i, j] += 1
            M[j, i] += 1
    return cats, basket_freq, M


def cosine_indicator(M: np.ndarray, f: np.ndarray) -> np.ndarray:
    denom = np.sqrt(np.outer(f, f))
    out = np.divide(M, denom, out=np.zeros_like(M, dtype=float), where=denom > 0)
    np.fill_diagonal(out, 1.0)
    return out


def jaccard_indicator(M: np.ndarray, f: np.ndarray) -> np.ndarray:
    union = f[:, None] + f[None, :] - M
    out = np.divide(M, union, out=np.zeros_like(M, dtype=float), where=union > 0)
    np.fill_diagonal(out, 1.0)
    return out


def cluster_one(sim: np.ndarray, cats: list[str], name: str) -> np.ndarray:
    dist = np.clip(1 - sim, 0, None)
    np.fill_diagonal(dist, 0)
    Z = linkage(squareform(dist, checks=False), method="ward")
    labels = fcluster(Z, t=K, criterion="maxclust")

    plt.figure(figsize=(16, 8))
    dendrogram(Z, labels=cats, leaf_rotation=90, leaf_font_size=8,
               color_threshold=Z[-(K - 1), 2])
    plt.axhline(Z[-(K - 1), 2], ls="--", color="red", alpha=0.6,
                label=f"k={K} cut (h={Z[-(K - 1), 2]:.3f})")
    plt.title(f"Olist categories — {name} (direct co-occurrence), Ward linkage")
    plt.legend(); plt.tight_layout()
    out = DWH / f"dendrogram_{name}.png"
    plt.savefig(out, dpi=150); plt.close()
    np.save(ETL / f"labels_{name}.npy", labels)
    print(f"✓ {name:8s} clusters: {len(set(labels))}  → {out.name}")
    return labels


def main() -> None:
    cats, f, M = build_basket_freq_and_cooccur()
    print(f"categories: {len(cats)} · multi-item co-occurrence pairs in matrix: {(M > 0).sum() // 2}")

    cluster_one(cosine_indicator(M, f),  cats, "cosine")
    cluster_one(jaccard_indicator(M, f), cats, "jaccard")

    print("\nNext: python3 validate_rollup.py")


if __name__ == "__main__":
    main()
