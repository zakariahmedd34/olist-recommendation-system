"""Step 7 — Validate within vs cross-group lift; pick the winner of cosine/jaccard."""
from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
ETL  = ROOT / "etl"
DWH  = ROOT / "dwh"
PASS_RATIO = 1.5  # within / cross-group lift must beat this


def basket_pairs():
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
    n_orders = basket["order_id"].nunique()
    cat_counts = basket["product_category_name"].value_counts().to_dict()

    pair_counts: dict[tuple[str, str], int] = {}
    for _, grp in basket.groupby("order_id"):
        cs = sorted(grp["product_category_name"].unique())
        for a, b in combinations(cs, 2):
            pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1
    return n_orders, cat_counts, pair_counts


def avg_lift(labels: np.ndarray, cats: list[str],
             n_orders: int, cat_counts: dict, pair_counts: dict):
    cat2grp = dict(zip(cats, labels))
    within, cross = [], []
    for (a, b), c_ab in pair_counts.items():
        sup_ab = c_ab / n_orders
        sup_a  = cat_counts[a] / n_orders
        sup_b  = cat_counts[b] / n_orders
        if sup_a * sup_b == 0:
            continue
        lift = sup_ab / (sup_a * sup_b)
        (within if cat2grp[a] == cat2grp[b] else cross).append(lift)
    return (np.mean(within) if within else 0.0,
            np.mean(cross)  if cross  else 0.0)


def main() -> None:
    cats = (ETL / "categories.txt").read_text().splitlines()
    n_orders, cat_counts, pair_counts = basket_pairs()

    results = {}
    for name in ["cosine", "jaccard"]:
        labels = np.load(ETL / f"labels_{name}.npy")
        w, c = avg_lift(labels, cats, n_orders, cat_counts, pair_counts)
        ratio = (w / c) if c > 0 else float("inf")
        verdict = "PASS" if ratio >= PASS_RATIO else "FAIL"
        results[name] = (w, c, ratio)
        print(f"{name:8s}  within={w:6.2f}  cross={c:6.2f}  ratio={ratio:5.2f}x  [{verdict}]")

    winner = max(results, key=lambda k: results[k][2])
    print(f"\n→ Winner: {winner}  (ratio {results[winner][2]:.2f}x)")

    out_lines = [
        f"{name}: within_lift={w:.4f}, cross_lift={c:.4f}, ratio={r:.4f}"
        for name, (w, c, r) in results.items()
    ]
    out_lines.append(f"winner: {winner}")
    (DWH / "validation_results.txt").write_text("\n".join(out_lines) + "\n")
    print(f"✓ wrote {DWH / 'validation_results.txt'}")


if __name__ == "__main__":
    main()
