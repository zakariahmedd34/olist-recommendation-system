"""Step 6 — Ward hierarchical clustering on cosine + Jaccard, cut at k=10, save dendrograms."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).parent.parent
ETL  = ROOT / "etl"
DWH  = ROOT / "dwh"
K    = 10  # target number of category groups


def jaccard_similarity(M: np.ndarray) -> np.ndarray:
    B = (M > 0).astype(int)
    inter = B @ B.T
    sums  = B.sum(axis=1, keepdims=True)
    union = sums + sums.T - inter
    out   = np.zeros_like(inter, dtype=float)
    np.divide(inter, union, out=out, where=union > 0)
    return out


def cluster_one(sim: np.ndarray, name: str, cats: list[str]) -> np.ndarray:
    np.fill_diagonal(sim, 1.0)
    dist = np.clip(1 - sim, 0, None)
    np.fill_diagonal(dist, 0)
    Z = linkage(squareform(dist, checks=False), method="ward")
    labels = fcluster(Z, t=K, criterion="maxclust")

    plt.figure(figsize=(16, 8))
    dendrogram(Z, labels=cats, leaf_rotation=90, leaf_font_size=8,
               color_threshold=Z[-(K - 1), 2])
    plt.axhline(Z[-(K - 1), 2], ls="--", color="red", alpha=0.6,
                label=f"k={K} cut (h={Z[-(K - 1), 2]:.3f})")
    plt.title(f"Olist categories — {name} similarity, Ward linkage")
    plt.legend(); plt.tight_layout()
    out = DWH / f"dendrogram_{name}.png"
    plt.savefig(out, dpi=150); plt.close()

    np.save(ETL / f"labels_{name}.npy", labels)
    print(f"✓ {name:8s} clusters: {len(set(labels))}, dendrogram → {out.name}")
    return labels


def main() -> None:
    M    = np.load(ETL / "cooccur.npy")
    cats = (ETL / "categories.txt").read_text().splitlines()

    cluster_one(cosine_similarity(M),  "cosine",  cats)
    cluster_one(jaccard_similarity(M), "jaccard", cats)

    print("\nNext: run validate_rollup.py to pick the winner (cosine vs jaccard).")


if __name__ == "__main__":
    main()
