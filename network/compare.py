"""Text world (Gemini embeddings of KJV) vs reference world (OpenBible graph).

Needs out/kjv_emb.npy, out/kjv_verses.json, out/network_{source}.json, out/chapter_graph_emb_{source}.npy.
Usage: .venv/bin/python compare.py [tsk3|esv]  -> adds "text" fields to out/network_{source}.json
"""
import json
import sys
from pathlib import Path

import numpy as np

from graph import BOOKS, chapter_label, load_source_edges, load_source_linked_pairs, verse_label

V = sys.argv[1] if len(sys.argv) > 1 else "tsk3"
OUT = Path(__file__).resolve().parent / "out"
rng = np.random.default_rng(0)
K = 10

net = json.load(open(OUT / f"network_{V}.json"))
verses = json.load(open(OUT / "kjv_verses.json"))
E = np.load(OUT / "kjv_emb.npy")
vid = {(v["b"], v["c"], v["v"]): i for i, v in enumerate(verses)}

# ---------- chapter text embedding = mean of verse embeddings ----------
chapters = sorted({(p["book"], p["ch"]) for p in net["chapters"]})
order = [(p["book"], p["ch"]) for p in net["chapters"]]
assert order == chapters
groups = {}
for i, v in enumerate(verses):
    groups.setdefault((v["b"], v["c"]), []).append(i)
T = np.stack([E[groups[c]].mean(0) for c in chapters])
T /= np.linalg.norm(T, axis=1, keepdims=True)

import umap  # noqa: E402

xy = umap.UMAP(n_neighbors=20, min_dist=0.25, metric="cosine", random_state=0).fit_transform(T)

G = np.load(OUT / f"chapter_graph_emb_{V}.npy")
G /= np.linalg.norm(G, axis=1, keepdims=True)


def knn(X):
    S = X @ X.T
    np.fill_diagonal(S, -2)
    return np.argsort(-S, axis=1)[:, :K]


nt, ng = knn(T), knn(G)
overlap = np.array([len(set(a) & set(b)) / K for a, b in zip(nt, ng)])
# chance level: K/(n-1)
for p, i in zip(net["chapters"], range(len(chapters))):
    p["tx"], p["ty"] = round(float(xy[i, 0]), 3), round(float(xy[i, 1]), 3)
    p["tnn"] = [chapter_label(chapters[j]) for j in nt[i][:5]]
    p["agree"] = round(float(overlap[i]), 2)

# ---------- verse level: does text similarity predict a cross-reference? ----------
edges = [(vid[a], vid[b]) for a, b in load_source_edges(V) if a in vid and b in vid]
ea = np.array(edges)
sim_linked = np.einsum("ij,ij->i", E[ea[:, 0]], E[ea[:, 1]])
rand = rng.integers(0, len(verses), size=(len(edges), 2))
sim_rand = np.einsum("ij,ij->i", E[rand[:, 0]], E[rand[:, 1]])
# AUC = P(sim of a linked pair > sim of a random pair)
allv = np.concatenate([sim_linked, sim_rand])
ranks = allv.argsort().argsort() + 1
auc = (ranks[: len(sim_linked)].sum() - len(sim_linked) * (len(sim_linked) + 1) / 2) / (len(sim_linked) * len(sim_rand))
hist_bins = np.linspace(0.3, 1.0, 36)

nt_of = lambda i: verses[i]["b"] >= 39  # noqa: E731
cross_mask = np.array([nt_of(a) != nt_of(b) for a, b in edges])
lab = lambda i: verse_label((verses[i]["b"], verses[i]["c"], verses[i]["v"]))  # noqa: E731
pair = lambda a, b, s: {"a": lab(a), "b": lab(b), "s": round(float(s), 3), "ta": verses[a]["t"], "tb": verses[b]["t"]}  # noqa: E731

# linked across testaments, least similar text: links the words alone would not suggest
idx = np.where(cross_mask)[0]
low, seen_pairs = [], set()
for i in idx[np.argsort(sim_linked[idx])]:
    key = frozenset(edges[i])
    if key not in seen_pairs:
        seen_pairs.add(key)
        low.append(i)
    if len(low) == 12:
        break
# most similar OT↔NT pairs with no cross-reference, among each NT verse's top text neighbour in the OT
linked = load_source_linked_pairs(V, vid)
ot_ids = np.array([i for i in range(len(verses)) if not nt_of(i)])
nt_ids = np.array([i for i in range(len(verses)) if nt_of(i)])
best = []
for s in range(0, len(nt_ids), 2000):
    blk = nt_ids[s:s + 2000]
    S = E[blk] @ E[ot_ids].T
    j = S.argmax(1)
    for a, jj, sv in zip(blk, j, S[np.arange(len(blk)), j]):
        b = ot_ids[jj]
        # a quotation is often referenced once, from its first verse: neighbours within 4 verses count as linked
        near = any((a + d, b + e) in linked for d in range(-4, 5) for e in range(-4, 5)
                   if 0 <= a + d < len(verses) and 0 <= b + e < len(verses))
        if not near and len(verses[a]["t"]) > 60:
            best.append((sv, a, b))
best.sort(reverse=True)

net["text"] = {
    "model": "gemini-embedding-001 (768 dim), KJV",
    "auc": round(float(auc), 3),
    "hist_linked": np.histogram(sim_linked, bins=hist_bins)[0].tolist(),
    "hist_random": np.histogram(sim_rand, bins=hist_bins)[0].tolist(),
    "hist_bins": hist_bins.round(3).tolist(),
    "median_linked": round(float(np.median(sim_linked)), 3),
    "median_random": round(float(np.median(sim_rand)), 3),
    "median_linked_cross": round(float(np.median(sim_linked[cross_mask])), 3),
    "median_linked_same": round(float(np.median(sim_linked[~cross_mask])), 3),
    "agree_mean": round(float(overlap.mean()), 3),
    "agree_chance": round(K / (len(chapters) - 1), 4),
    "linked_dissimilar": [pair(edges[i][0], edges[i][1], sim_linked[i]) for i in low],
    "similar_unlinked": [pair(a, b, s) for s, a, b in best[:12]],
}
json.dump(net, open(OUT / f"network_{V}.json", "w"), ensure_ascii=False)
t = net["text"]
print("AUC", t["auc"], "| mediane linked/random", t["median_linked"], t["median_random"],
      "| cross/same", t["median_linked_cross"], t["median_linked_same"])
print("accordo vicini capitoli", t["agree_mean"], "caso", t["agree_chance"])
lo = sorted(net["chapters"], key=lambda p: p["agree"])
print("meno d'accordo:", [p["id"] for p in lo[:8]])
print("più d'accordo:", [p["id"] for p in lo[-8:]])
for x in t["linked_dissimilar"][:5]:
    print("LINK/diverso", x["a"], x["b"], x["s"])
for x in t["similar_unlinked"][:5]:
    print("SIMILE/no link", x["a"], x["b"], x["s"])
