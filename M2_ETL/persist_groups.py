"""Step 8 — Persist Dim_Category_Group with named groups; save mapping CSV for ETL."""
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import text
from db import engine

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
ETL  = ROOT / "etl"
DWH  = ROOT / "dwh"


def read_winner() -> str:
    txt = (DWH / "validation_results.txt").read_text()
    for line in txt.splitlines():
        if line.startswith("winner:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("No 'winner:' line in validation_results.txt — run Step 7 first.")


def main() -> None:
    winner = read_winner()
    cats   = (ETL / "categories.txt").read_text().splitlines()
    labels = np.load(ETL / f"labels_{winner}.npy")

    items = pd.read_csv(DATA / "olist_order_items_dataset.csv")
    prods = pd.read_csv(DATA / "olist_products_dataset.csv")
    cat_freq = (
        items.merge(prods[["product_id", "product_category_name"]], on="product_id")
             ["product_category_name"]
             .value_counts()
    )

    df = pd.DataFrame({"category": cats, "label": labels})
    df["freq"] = df["category"].map(cat_freq).fillna(0).astype(int)

    label_to_dbid: dict[int, int] = {}

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE dim_category_group RESTART IDENTITY CASCADE"))
        for label in sorted(df["label"].unique()):
            members = df[df.label == label].sort_values("freq", ascending=False)
            top3     = members.head(3)["category"].tolist()
            name     = members.iloc[0]["category"]   # representative = most-frequent member
            desc     = "top categories: " + ", ".join(top3)
            new_id = conn.execute(
                text("""INSERT INTO dim_category_group (group_name, description)
                        VALUES (:n, :d) RETURNING group_id"""),
                {"n": name, "d": desc},
            ).scalar()
            label_to_dbid[label] = new_id
            print(f"  group_id={new_id:2d}  name={name:30s}  top3={top3}")

    mapping = pd.DataFrame({
        "product_category_name": cats,
        "category_group_id": [label_to_dbid[l] for l in labels],
    })
    mapping.to_csv(ETL / "category_to_group.csv", index=False)
    print(f"\n✓ dim_category_group populated: {len(label_to_dbid)} groups")
    print(f"✓ mapping saved → {ETL / 'category_to_group.csv'}")


if __name__ == "__main__":
    main()
