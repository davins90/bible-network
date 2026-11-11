"""TSK (OpenBible, 1830s + votes) vs ESV cross-references (Crossway, 2001): overlap, votes, structure.

A reference matches the other network when the source verse is the same (or the reference exists in the
opposite direction) and the target ranges share at least one verse. Purely set-based, no model involved;
embeddings are used only to order the example lists.

Needs: out/network_tsk3.json, out/network_esv.json (with text fields), out/kjv_*.
Usage: .venv/bin/python esv_vs_tsk.py -> out/esv_vs_tsk.json
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

from graph import BOOKS, XREF, esv_lines, parse, quarantined, verse_label

OUT = Path(__file__).resolve().parent / "out"
K = 10
kjv = json.load(open(OUT / "kjv_verses.json"))
E = np.load(OUT / "kjv_emb.npy")
vid = {(v["b"], v["c"], v["v"]): i for i, v in enumerate(kjv)}


def expand(a, b):
    ia = vid.get(parse(a))
    lo, hi = vid.get(parse(b.split("-")[0])), vid.get(parse(b.split("-")[-1]))
    if ia is None or lo is None or hi is None:
        return None, []
    return ia, list(range(lo, min(hi, lo + 60) + 1))


# ---------- TSK lines with votes ----------
skip = quarantined()
tsk = []  # (ia, targets, votes, a, b)
with open(XREF) as f:
    next(f)
    for line in f:
        a, b, v = line.rstrip("\n").split("\t")[:3]
        if f"{a}\t{b}" in skip:
            continue
        ia, ts = expand(a, b)
        if ia is not None:
            tsk.append((ia, ts, int(v), a, b))
tsk_pairs = defaultdict(lambda: -10**9)  # (i, j) -> max votes, both directions
for ia, ts, v, _, _ in tsk:
    for j in ts:
        tsk_pairs[(ia, j)] = max(tsk_pairs[(ia, j)], v)
        tsk_pairs[(j, ia)] = max(tsk_pairs[(j, ia)], v)

esv = []
for a, b in esv_lines():
    ia, ts = expand(a, b)
    if ia is not None:
        esv.append((ia, ts, a, b))
esv_pairs = set()
for ia, ts, _, _ in esv:
    for j in ts:
        esv_pairs.add((ia, j))
        esv_pairs.add((j, ia))


def best_votes(ia, ts):
    return max((tsk_pairs[(ia, j)] for j in ts if (ia, j) in tsk_pairs), default=None)


# ---------- ESV -> TSK ----------
esv_votes = [best_votes(ia, ts) for ia, ts, _, _ in esv]
in_tsk_any = np.array([v is not None for v in esv_votes])
in_tsk_3 = np.array([v is not None and v >= 3 for v in esv_votes])

# ---------- TSK -> ESV by vote bin ----------
bins = [(-10**9, -1, "negativi"), (0, 2, "0–2"), (3, 5, "3–5"), (6, 10, "6–10"), (11, 20, "11–20"), (21, 50, "21–50"), (51, 10**9, "oltre 50")]
tsk_in_esv = np.array([any((ia, j) in esv_pairs for j in ts) for ia, ts, _, _, _ in tsk])
tsk_votes = np.array([v for _, _, v, _, _ in tsk])
vote_curve = []
for lo, hi, lab in bins:
    m = (tsk_votes >= lo) & (tsk_votes <= hi)
    vote_curve.append({"bin": lab, "n": int(m.sum()), "share_in_esv": round(float(tsk_in_esv[m].mean()), 4) if m.any() else None})

nt = lambda i: kjv[i]["b"] >= 39  # noqa: E731
cross = lambda ia, ts: nt(ia) != nt(ts[0])  # noqa: E731
lab = lambda i: verse_label((kjv[i]["b"], kjv[i]["c"], kjv[i]["v"]))  # noqa: E731


def example(ia, ts, extra=None):
    j = ts[0]
    d = {"a": lab(ia), "b": lab(j) + (f"–{kjv[ts[-1]]['v']}" if len(ts) > 1 and kjv[ts[-1]]["c"] == kjv[j]["c"] else ""),
         "ta": kjv[ia]["t"], "tb": kjv[j]["t"], "s": round(float(E[ia] @ E[j]), 3)}
    if extra:
        d.update(extra)
    return d


# ESV references that the TSK does not have at all, NT -> OT, most similar text first (likely quotations or allusions)
new_in_esv = [(float(E[ia] @ E[ts[0]]), ia, ts) for (ia, ts, _, _), v in zip(esv, esv_votes)
              if v is None and nt(ia) and not nt(ts[0])]
new_in_esv.sort(reverse=True)
# well-voted TSK references that the ESV does not have
popular_missing = sorted(((v, ia, ts) for (ia, ts, v, _, _), hit in zip(tsk, tsk_in_esv) if not hit and v >= 30), reverse=True)

# ---------- structure: book matrices and chapter neighbourhoods ----------
nt3, ne = json.load(open(OUT / "network_tsk3.json")), json.load(open(OUT / "network_esv.json"))
iu = np.triu_indices(len(BOOKS), 1)
Mt, Me = np.array(nt3["book"]["matrix_log2_shrunk"])[iu], np.array(ne["book"]["matrix_log2_shrunk"])[iu]
rho = stats.spearmanr(Mt, Me).statistic


# the two chapter lists can differ (a chapter with no reference is absent): align rows by chapter id
ids_t, ids_e = [p["id"] for p in nt3["chapters"]], [p["id"] for p in ne["chapters"]]
common = [c for c in ids_t if c in set(ids_e)]


def knn(path, ids):
    X = np.load(path)
    assert len(X) == len(ids)
    X = X[[ids.index(c) for c in common]]
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    S = X @ X.T
    np.fill_diagonal(S, -2)
    return np.argsort(-S, axis=1)[:, :K]


kt, ke = knn(OUT / "chapter_graph_emb_tsk3.npy", ids_t), knn(OUT / "chapter_graph_emb_esv.npy", ids_e)
agree_te = float(np.mean([len(set(a) & set(b)) / K for a, b in zip(kt, ke)]))

res = {
    "n_esv": len(esv), "n_tsk_all": len(tsk), "n_tsk3": int((tsk_votes >= 3).sum()),
    "esv_verses_with_refs": len({ia for ia, _, _, _ in esv}),
    "esv_in_tsk_any": round(float(in_tsk_any.mean()), 4),
    "esv_in_tsk3": round(float(in_tsk_3.mean()), 4),
    "tsk3_in_esv": round(float(tsk_in_esv[tsk_votes >= 3].mean()), 4),
    "cross_share_esv": round(float(np.mean([cross(ia, ts) for ia, ts, _, _ in esv])), 4),
    "cross_share_tsk3": round(float(np.mean([cross(ia, ts) for (ia, ts, v, _, _) in tsk if v >= 3])), 4),
    "vote_curve": vote_curve,
    "book_spearman": round(float(rho), 3),
    "chapter_knn_agree_tsk_esv": round(agree_te, 3),
    "chapters_tsk": len(ids_t), "chapters_esv": len(ids_e),
    "new_in_esv": [example(ia, ts) for _, ia, ts in new_in_esv[:12]],
    "popular_missing_in_esv": [example(ia, ts, {"votes": int(v)}) for v, ia, ts in popular_missing[:12]],
}
json.dump(res, open(OUT / "esv_vs_tsk.json", "w"), ensure_ascii=False, indent=1)
for k, v in res.items():
    if k not in ("new_in_esv", "popular_missing_in_esv", "vote_curve"):
        print(f"{k}: {v}")
for x in res["vote_curve"]:
    print("  voti", x["bin"], x["n"], x["share_in_esv"])
print("ESV nuovi:", [(x["a"], x["b"], x["s"]) for x in res["new_in_esv"][:6]])
print("TSK popolari assenti:", [(x["a"], x["b"], x["votes"]) for x in res["popular_missing_in_esv"][:6]])
