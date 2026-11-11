"""First pass on the full cross-reference graph: stats, centrality, book×book observed/expected
with Gamma-Poisson shrinkage, chapter embedding (NetMF ≈ DeepWalk) + UMAP, Louvain communities.

Usage: .venv/bin/python analyze.py [tsk3|tsk10|esv]   -> out/network_{source}.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
from scipy import optimize, sparse, special, stats

from graph import BOOKS, GENRE_OF, aggregate, chapter_label, degree, load_source_edges, verse_label

SOURCE = sys.argv[1] if len(sys.argv) > 1 else "tsk3"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(0)

edges = load_source_edges(SOURCE)
verses = sorted({v for e in edges for v in e})
deg = degree(edges)
nt = lambda v: v[0] >= 39  # noqa: E731
print(f"{SOURCE}: {len(edges)} archi, {len(verses)} versetti")

# ---------- verse level: degree, PageRank, OT↔NT bridges ----------
G = nx.Graph()
for a, b in edges:
    G.add_edge(a, b, weight=G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1)
pr = nx.pagerank(G, weight="weight")
cross = Counter()
for a, b in edges:
    if nt(a) != nt(b):
        cross[a] += 1
        cross[b] += 1
degs = np.array([deg[v] for v in verses])
top = lambda d, n=15: [{"v": verse_label(v), "x": round(float(x), 6)} for v, x in sorted(d.items(), key=lambda t: -t[1])[:n]]  # noqa: E731
verse_stats = {
    "n_edges": len(edges),
    "n_verses": len(verses),
    "share_cross_testament": round(sum(nt(a) != nt(b) for a, b in edges) / len(edges), 4),
    "degree_quantiles": {q: int(np.quantile(degs, q / 100)) for q in (10, 25, 50, 75, 90, 99)},
    "degree_hist": np.histogram(np.log10(degs), bins=30)[0].tolist(),
    "degree_hist_edges": np.histogram(np.log10(degs), bins=30)[1].round(3).tolist(),
    "top_degree": top({v: deg[v] for v in verses}),
    "top_pagerank": top(pr),
    "top_bridges": top({v: c for v, c in cross.items() if not nt(v)}, 10) + top({v: c for v, c in cross.items() if nt(v)}, 10),
}

# ---------- book × book: observed / expected with Gamma-Poisson shrinkage ----------
nb = len(BOOKS)
A = np.zeros((nb, nb))
for (i, j), w in aggregate(edges, "book").items():
    A[i, j] += w
    A[j, i] += w  # diagonal ends up 2× internal edges, as in the configuration model
k = A.sum(1)
E = np.outer(k, k) / k.sum()
iu = np.triu_indices(nb, 1)
O_, E_ = A[iu], E[iu]


def neg_marglik(log_a):
    a = np.exp(log_a)  # O ~ Poisson(λE), λ ~ Gamma(a, a): marginal is negative binomial
    return -np.sum(special.gammaln(O_ + a) - special.gammaln(a) - special.gammaln(O_ + 1)
                   + a * np.log(a / (a + E_)) + O_ * np.log(E_ / (a + E_)))


alpha = float(np.exp(optimize.minimize_scalar(neg_marglik, bounds=(-6, 6), method="bounded").x))
post_mean = (A + alpha) / (E + alpha)
p_above = 1 - stats.gamma.cdf(1.0, a=A + alpha, scale=1 / (E + alpha))
pairs = sorted(
    ({"a": BOOKS[i][2], "b": BOOKS[j][2], "O": int(A[i, j]), "E": round(E[i, j], 1),
      "raw": round(A[i, j] / E[i, j], 2), "shrunk": round(post_mean[i, j], 2),
      "p_gt1": round(float(p_above[i, j]), 3)} for i, j in zip(*iu)),
    key=lambda d: -d["shrunk"])
book_stats = {
    "alpha": round(alpha, 3),
    "matrix_log2_shrunk": np.log2(post_mean).round(2).tolist(),
    "degree": k.astype(int).tolist(),
    "top_pairs": pairs[:25],
    "top_pairs_raw_only": sorted(pairs, key=lambda d: -d["raw"])[:10],
}

# ---------- chapter level: embedding + UMAP + communities ----------
chapters = sorted({v[:2] for v in verses})
cidx = {c: i for i, c in enumerate(chapters)}
cw = aggregate(edges, "chapter")
rows, cols, vals = [], [], []
for (a, b), w in cw.items():
    if a == b:
        continue
    rows += [cidx[a], cidx[b]]
    cols += [cidx[b], cidx[a]]
    vals += [w, w]
n = len(chapters)
Ac = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n)).toarray()
d = Ac.sum(1)
d[d == 0] = 1
# NetMF (Qiu et al. 2018): DeepWalk with window T is implicitly factorising log(vol/(bT) Σ_r P^r D^-1)
T, b_neg = 5, 1.0
P = Ac / d[:, None]
S, Pr = np.zeros_like(P), np.eye(n)
for _ in range(T):
    Pr = Pr @ P
    S += Pr
M = d.sum() / (b_neg * T) * S / d[None, :]
M = np.log(np.maximum(M, 1.0))
U, sv, _ = np.linalg.svd(M)
dim = 64
emb = U[:, :dim] * np.sqrt(sv[:dim])

np.save(OUT / f"chapter_graph_emb_{SOURCE}.npy", emb)

import umap  # noqa: E402  (slow import)

xy = umap.UMAP(n_neighbors=20, min_dist=0.25, metric="cosine", random_state=0).fit_transform(emb)

Gc = nx.Graph()
for (a, b), w in cw.items():
    if a != b:
        Gc.add_edge(cidx[a], cidx[b], weight=w)
comms = nx.community.louvain_communities(Gc, weight="weight", resolution=1.0, seed=0)
comm_of = {c: ci for ci, cs in enumerate(sorted(comms, key=len, reverse=True)) for c in cs}
prc = nx.pagerank(Gc, weight="weight")

# nearest neighbours in embedding space (cosine), to show on hover
en = emb / np.linalg.norm(emb, axis=1, keepdims=True)
sim = en @ en.T
np.fill_diagonal(sim, -1)
nn = np.argsort(-sim, axis=1)[:, :5]

ch_deg = defaultdict(int)
for a, b in edges:
    ch_deg[a[:2]] += 1
    ch_deg[b[:2]] += 1
points = []
for c, i in cidx.items():
    tot = sum(Ac[i])
    ot_share = sum(Ac[i, j] for j, c2 in enumerate(chapters) if c2[0] < 39) / tot if tot else 0
    points.append({
        "id": chapter_label(c), "book": c[0], "ch": c[1], "genre": GENRE_OF[BOOKS[c[0]][0]],
        "x": round(float(xy[i, 0]), 3), "y": round(float(xy[i, 1]), 3), "deg": ch_deg[c],
        "pr": round(prc.get(i, 0) * n, 3), "comm": comm_of.get(i, -1), "ot": round(ot_share, 3),
        "nn": [chapter_label(chapters[j]) for j in nn[i]],
    })
# describe each community by its most frequent books
comm_desc = []
for ci in range(len(comms)):
    members = [chapters[i] for i, c in comm_of.items() if c == ci]
    top_books = Counter(BOOKS[m[0]][2] for m in members).most_common(4)
    comm_desc.append({"id": ci, "size": len(members), "books": top_books})

json.dump({
    "source": SOURCE, "books": [b[2] for b in BOOKS], "abbr": [b[3] for b in BOOKS],
    "genre_of_book": [GENRE_OF[b[0]] for b in BOOKS],
    "verse": verse_stats, "book": book_stats, "chapters": points, "communities": comm_desc,
}, open(OUT / f"network_{SOURCE}.json", "w"), ensure_ascii=False)
print("alpha", round(alpha, 3), "| comunità", len(comms), "| top coppie:",
      [(p["a"], p["b"], p["shrunk"]) for p in pairs[:5]])
print("top pagerank:", [t["v"] for t in verse_stats["top_pagerank"][:8]])
print("ponti AT:", [t["v"] for t in verse_stats["top_bridges"][:5]], "NT:", [t["v"] for t in verse_stats["top_bridges"][10:15]])
for c in comm_desc[:12]:
    print(c)
