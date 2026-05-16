"""M5 Streamlit demo — type a customer_unique_id, see top-10 from each component + the RRF fusion.

Run:  streamlit run demo/streamlit_app.py
Prereq: local Postgres with olist_dwh restored; psycopg2-binary installed.
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

RRF_K = 60
TOP_K = 10
CUTOFF = pd.Timestamp("2018-04-01")
RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "rules",
                          "ranked_rules_for_m5_with_segments.csv")
CLUSTERS_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "clustering",
                             "customer_cluster_assignments.csv")


@st.cache_resource
def load_everything():
    engine = create_engine(os.environ.get("DATABASE_URL", "postgresql://localhost/olist_dwh"),
                           future=True)
    interactions = pd.read_sql(text("SELECT customer_id, product_id, orderdate FROM fact_orderitems"), engine)
    customers = pd.read_sql(text("SELECT customer_id, customer_unique_id FROM dim_customers"), engine)
    products = pd.read_sql(text(
        "SELECT product_id, product_category_name_english, category_group_id FROM dim_products"), engine)
    prices = pd.read_sql(text("SELECT product_id, AVG(price) AS avg_price FROM fact_orderitems GROUP BY product_id"),
                         engine)
    rules = pd.read_csv(RULES_PATH)
    clusters = pd.read_csv(CLUSTERS_PATH)

    interactions = interactions.merge(customers, on="customer_id", how="left")
    interactions["orderdate"] = pd.to_datetime(interactions["orderdate"])

    train = interactions[interactions["orderdate"] < CUTOFF].copy()
    train_user_items = train.groupby("customer_unique_id")["product_id"].apply(set).to_dict()
    popular_items = train["product_id"].value_counts().index.tolist()
    user_last_product = (train.sort_values("orderdate")
                              .drop_duplicates("customer_unique_id", keep="last")
                              .set_index("customer_unique_id")["product_id"].to_dict())

    # Item-CF
    tu = train[["customer_unique_id", "product_id"]].dropna().drop_duplicates()
    u2i = {u: i for i, u in enumerate(tu["customer_unique_id"].unique())}
    p2i = {p: i for i, p in enumerate(tu["product_id"].unique())}
    i2p = {i: p for p, i in p2i.items()}
    rows = tu["customer_unique_id"].map(u2i).to_numpy()
    cols = tu["product_id"].map(p2i).to_numpy()
    ui = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(len(u2i), len(p2i)))
    iu = ui.T.tocsr()
    item_neighbors = _topk_neighbors(iu, n=200, chunk=500)

    # Content
    prod_prices = prices.copy()
    prod_prices["price_bucket"] = pd.qcut(prod_prices["avg_price"].rank(method="first"),
                                          q=5, labels=False, duplicates="drop")
    catalog = set(train["product_id"].unique())
    cf = (products[["product_id", "category_group_id"]]
          .merge(prod_prices[["product_id", "price_bucket"]], on="product_id", how="left"))
    cf = cf[cf["product_id"].isin(catalog)].reset_index(drop=True)
    cf["category_group_id"] = cf["category_group_id"].fillna(-1).astype(int)
    cf["price_bucket"] = cf["price_bucket"].fillna(-1).astype(int)
    feat = pd.concat([pd.get_dummies(cf["category_group_id"], prefix="cat"),
                      pd.get_dummies(cf["price_bucket"], prefix="price")], axis=1).to_numpy(dtype=np.float32)
    content_p2i = {p: i for i, p in enumerate(cf["product_id"].values)}
    content_i2p = {i: p for p, i in content_p2i.items()}
    content_neighbors = _topk_neighbors(csr_matrix(feat), n=200, chunk=500)

    # Rules dedup + segment index
    rules_dedup = (rules.assign(_priority=rules["algorithm"].map({"FP-Growth": 0, "Apriori": 1, "ECLAT-style": 2}).fillna(3))
                        .sort_values(["query_item", "recommended_item", "condition", "segment_id", "_priority"])
                        .drop_duplicates(subset=["query_item", "recommended_item", "condition", "segment_id"], keep="first")
                        .drop(columns=["_priority"]))
    seg_idx = {}
    seg_rows = rules_dedup[rules_dedup["condition"] == "segment"].copy()
    if len(seg_rows):
        seg_rows["segment_id"] = seg_rows["segment_id"].astype(int)
        for (seg, q), grp in seg_rows.sort_values("rank").groupby(["segment_id", "query_item"]):
            seg_idx[(int(seg), q)] = grp["recommended_item"].tolist()

    last_cid = (interactions.sort_values("orderdate")
                            .drop_duplicates("customer_unique_id", keep="last")
                            .set_index("customer_unique_id")["customer_id"].to_dict())
    cid_to_cluster = clusters.set_index("customer_id")["cluster_id"].to_dict()
    cid_to_cluster_label = clusters.set_index("customer_id")["cluster_label"].to_dict()

    product_name = products.set_index("product_id")["product_category_name_english"].to_dict()

    return dict(
        train_user_items=train_user_items, popular_items=popular_items, user_last_product=user_last_product,
        p2i=p2i, i2p=i2p, item_neighbors=item_neighbors,
        content_p2i=content_p2i, content_i2p=content_i2p, content_neighbors=content_neighbors,
        seg_idx=seg_idx, last_cid=last_cid, cid_to_cluster=cid_to_cluster,
        cid_to_cluster_label=cid_to_cluster_label, product_name=product_name,
    )


def _topk_neighbors(mat, n=200, chunk=500):
    out = {}
    total = mat.shape[0]
    for start in range(0, total, chunk):
        end = min(start + chunk, total)
        block = cosine_similarity(mat[start:end], mat, dense_output=True)
        for r in range(end - start):
            block[r, start + r] = 0.0
        for r in range(end - start):
            row = block[r]
            if row.max() == 0:
                out[start + r] = []
                continue
            k_eff = min(n, total - 1)
            top = np.argpartition(-row, k_eff)[:k_eff]
            top = top[np.argsort(-row[top])]
            top = top[row[top] > 0]
            out[start + r] = [(int(j), float(row[j])) for j in top]
    return out


def most_popular(user, ctx, k=TOP_K):
    bought = ctx["train_user_items"].get(user, set())
    return [p for p in ctx["popular_items"] if p not in bought][:k]


def cf(user, ctx, k=TOP_K):
    bought = ctx["train_user_items"].get(user, set())
    bi = [ctx["p2i"][p] for p in bought if p in ctx["p2i"]]
    if not bi:
        return most_popular(user, ctx, k)
    bs = set(bi)
    scores = {}
    for s in bi:
        for nbr, sim in ctx["item_neighbors"].get(s, []):
            if nbr in bs: continue
            scores[nbr] = scores.get(nbr, 0.0) + sim
    if not scores:
        return most_popular(user, ctx, k)
    return [ctx["i2p"][i] for i, _ in sorted(scores.items(), key=lambda x: -x[1])[:k]]


def content(user, ctx, k=TOP_K):
    bought = ctx["train_user_items"].get(user, set())
    bi = [ctx["content_p2i"][p] for p in bought if p in ctx["content_p2i"]]
    if not bi:
        return most_popular(user, ctx, k)
    bs = set(bi)
    scores = {}
    for s in bi:
        for nbr, sim in ctx["content_neighbors"].get(s, []):
            if nbr in bs: continue
            scores[nbr] = scores.get(nbr, 0.0) + sim
    if not scores:
        return most_popular(user, ctx, k)
    return [ctx["content_i2p"][i] for i, _ in sorted(scores.items(), key=lambda x: -x[1])[:k]]


def segment_rules(user, ctx, k=TOP_K):
    cid = ctx["last_cid"].get(user)
    seg = ctx["cid_to_cluster"].get(cid) if cid else None
    last_p = ctx["user_last_product"].get(user)
    if seg is None or last_p is None:
        return []
    recs = ctx["seg_idx"].get((int(seg), last_p), [])
    bought = ctx["train_user_items"].get(user, set())
    return [p for p in recs if p not in bought][:k]


def rrf(lists, k_param=RRF_K, top_k=TOP_K):
    scores = {}
    contrib = {}  # item -> list of component indexes that recommended it
    for ci, lst in enumerate(lists):
        for r, item in enumerate(lst, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k_param + r)
            contrib.setdefault(item, []).append(ci)
    ordered = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
    return [(item, score, contrib[item]) for item, score in ordered]


# ───────── UI ─────────
st.set_page_config(page_title="Olist M5 — Hybrid Recommender", layout="wide")
st.title("Olist Hybrid Recommender Demo (M5)")

ctx = load_everything()
example_ids = list(ctx["train_user_items"].keys())[:5]
st.caption("Example customer_unique_ids: " + " · ".join(f"`{u}`" for u in example_ids))

user_id = st.text_input("customer_unique_id", value=example_ids[0] if example_ids else "")

if user_id:
    if user_id not in ctx["train_user_items"]:
        st.warning("No purchase history for this customer in the training period — recommendations fall back to most-popular.")

    cid = ctx["last_cid"].get(user_id)
    seg = ctx["cid_to_cluster"].get(cid) if cid else None
    seg_label = ctx["cid_to_cluster_label"].get(cid) if cid else None
    last_p = ctx["user_last_product"].get(user_id, "—")

    cols = st.columns(2)
    cols[0].metric("Cluster", f"{seg} — {seg_label}" if seg is not None else "—")
    cols[1].metric("Most-recent train purchase", last_p)

    seg_list = segment_rules(user_id, ctx, TOP_K)
    cf_list = cf(user_id, ctx, TOP_K)
    co_list = content(user_id, ctx, TOP_K)
    fused = rrf([seg_list, cf_list, co_list], k_param=RRF_K, top_k=TOP_K)

    component_names = ["Segment Rules", "Item-CF", "Content Fallback"]
    c1, c2, c3 = st.columns(3)
    for col, name, lst in zip([c1, c2, c3], component_names, [seg_list, cf_list, co_list]):
        with col:
            st.subheader(name)
            if not lst:
                st.write("_(empty)_")
            else:
                for r, p in enumerate(lst, 1):
                    st.write(f"{r}. `{p[:8]}…` — {ctx['product_name'].get(p, '?')}")

    st.divider()
    st.subheader(f"Hybrid (RRF, k={RRF_K})")
    if not fused:
        st.write("_(empty — using most-popular fallback)_")
    else:
        for r, (p, score, src) in enumerate(fused, 1):
            sources = ", ".join(component_names[i] for i in src)
            st.write(f"{r}. `{p[:8]}…` — {ctx['product_name'].get(p, '?')}  "
                     f"*(score={score:.4f}, from: {sources})*")
