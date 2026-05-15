"""Step 5 — Build the 71×71 category co-purchase matrix from delivered orders."""
from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
OUT  = ROOT / "etl"


def main() -> None:
    items  = pd.read_csv(DATA / "olist_order_items_dataset.csv")
    prods  = pd.read_csv(DATA / "olist_products_dataset.csv")
    orders = pd.read_csv(DATA / "olist_orders_dataset.csv")

    delivered = orders.loc[orders.order_status == "delivered", ["order_id"]]

    basket = (
        items.merge(prods[["product_id", "product_category_name"]], on="product_id")
             .merge(delivered, on="order_id")
             [["order_id", "product_category_name"]]
             .dropna()
             .drop_duplicates()
    )

    cats = sorted(basket["product_category_name"].unique())
    idx  = {c: i for i, c in enumerate(cats)}
    n    = len(cats)
    M    = np.zeros((n, n), dtype=int)

    for _, grp in basket.groupby("order_id"):
        cs = list(grp["product_category_name"].unique())
        for a, b in combinations(cs, 2):
            i, j = idx[a], idx[b]
            M[i, j] += 1
            M[j, i] += 1

    np.save(OUT / "cooccur.npy", M)
    (OUT / "categories.txt").write_text("\n".join(cats))

    print(f"✓ co-purchase matrix: shape={M.shape}, sum={M.sum():,}, nonzero={(M > 0).sum():,}")
    print(f"  → {OUT / 'cooccur.npy'}")
    print(f"  → {OUT / 'categories.txt'}  ({n} categories)")


if __name__ == "__main__":
    main()
