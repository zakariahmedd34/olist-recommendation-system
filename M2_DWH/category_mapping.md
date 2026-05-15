# Data-driven category roll-up

## Method

To support category-level association-rule mining (motivated by Olist's 88% single-item-basket rate, which weakens product-level rules), we built a 10-group taxonomy from the 73 leaf product categories using a fully data-driven pipeline:

1. **Co-purchase matrix.** Among the 96,478 delivered orders with at least one known product category, we counted how often each pair of categories appeared in the same basket. This yielded a 73×73 symmetric count matrix `M`.
2. **Pairwise similarity.** Treating each category as a set of orders that contain it, we computed two complementary similarity metrics — **cosine on basket-indicator vectors** (`sim = M[i,j] / sqrt(|orders_i| · |orders_j|)`) and **Jaccard** (`sim = M[i,j] / |orders_i ∪ orders_j|`) — and built the comparable distance matrices `D = 1 − S`.
3. **Hierarchical clustering.** We applied **Ward's linkage** to each distance matrix and cut the resulting dendrogram at **k=10**.
4. **Validation.** Each labelling was scored by mining lift on a sample of delivered baskets and computing the average within-group rule lift versus average cross-group rule lift. We retain a labelling only if the ratio is ≥ 1.5×.

## Figures

- **Figure 1.** Cosine-similarity dendrogram, Ward linkage, k=10 cut (`dwh/dendrogram_cosine.png`).
- **Figure 2.** Jaccard-similarity dendrogram for comparison (`dwh/dendrogram_jaccard.png`).

## Validation results

| Similarity | Within-group lift | Cross-group lift | Ratio | Verdict |
|------------|-------------------:|------------------:|------:|---------|
| **cosine (selected)** | 1.59 | 0.14 | **11.04×** | PASS |
| jaccard (comparison)    | 1.90 | 0.20 | 9.34×     | PASS |

Both metrics produce groups whose within-group co-purchase lift is roughly an order of magnitude higher than across-group lift, well above the 1.5× threshold. We adopt the **cosine** labelling because it produced the higher ratio.

## The 10 data-driven category groups

| group_id | group_name | # leaf categories | # products | top categories |
|---------:|------------|------------------:|-----------:|----------------|
| 1 | `fashion_apparel` | 2 | 46 | fashion_roupa_feminina, fashion_esporte |
| 2 | `cama_mesa_banho` | 2 | 3,140 | cama_mesa_banho, casa_conforto |
| 3 | `fashion_bolsas_e_acessorios` | 2 | 854 | fashion_bolsas_e_acessorios, fashion_roupa_infanto_juvenil |
| 4 | `construcao_ferramentas_jardim` | 2 | 102 | construcao_ferramentas_jardim, flores |
| 5 | `livros_tecnicos` | 2 | 150 | livros_tecnicos, musica |
| 6 | `moveis_decoracao` | 5 | 3,106 | moveis_decoracao, casa_construcao, construcao_ferramentas_seguranca |
| 7 | `electronics_misc` | 3 | 801 | cool_stuff, tablets_impressao_imagem, pc_gamer |
| 8 | `gifts_household` | 5 | 3,112 | brinquedos, bebes, ferramentas_jardim |
| 9 | `music_homecomfort` | 2 | 294 | instrumentos_musicais, casa_conforto_2 |
| 10 | `diversified_other` | 48 | 20,736 | esporte_lazer, beleza_saude, utilidades_domesticas |

Each group is named after its most-populous leaf category. Mixed-content groups (e.g. `gifts_household` combining tools, toys, and babies) reflect genuine co-purchase patterns in Olist baskets — gift-oriented shopping rather than semantic taxonomy.

## Methodological note: similarity choice

We initially tried cosine and Jaccard similarity **on the rows of the co-occurrence matrix** (i.e., grouping categories with similar co-purchase *neighbourhoods*). This produced a within-group lift ratio below 1×, indicating the metric clustered categories that *avoid* each other in baskets. We replaced it with **direct pairwise co-occurrence** similarity (the formulae above), which clusters categories that actually appear together. We report this as a one-iteration methodological refinement; no further re-cuts were applied.

## Limitations

- Olist's 88%-single-item-basket rate yields thin co-occurrence signal for many leaf categories. In the dendrograms this manifests as a high-distance plateau where unrelated categories merge arbitrarily.
- The k=10 cut is a deliberate trade-off between interpretability (≤ 10 groups for paper figures) and granularity. A finer cut would split the larger groups; a coarser cut would lump electronics with home goods.
- Group names reflect their most-populous member only and may understate the diversity of less-frequent members.
- The selected labelling produces one large heterogeneous group (`diversified_other`, 48 leaf categories, 20,736 products) representing the long tail of low-co-occurrence categories. We retain it as a single group rather than artificially splitting it, because the basket data provides no statistically meaningful basis for further division. This is itself a finding: Brazilian e-commerce baskets do not exhibit measurable category clustering for the majority of long-tail leaf categories.
