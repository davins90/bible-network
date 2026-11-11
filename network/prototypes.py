"""Data for two prototype views.

Helix of the canon (chapters, 3D): height = canonical order; plane = diffusion map of the chapter graph
(eigenvectors 2-3 of the random-walk matrix); threads = strongest chapter links.

Hyperbolic disk (verses): LaBNE (Alanis-Lobato, Mier, Andrade-Navarro 2016, "Efficient embedding of complex
networks to hyperbolic space via their Laplacian"): angle from 2-D Laplacian eigenmaps, radius from degree rank
(popularity-similarity model: r_i = 2/zeta * (beta ln i + (1-beta) ln N); here beta = 1, see below).
Quality check: AUC of hyperbolic distance at telling linked pairs from random pairs.

Usage: .venv/bin/python prototypes.py -> out/helix.json, out/disk.json
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

from graph import BOOKS, GENRE_OF, aggregate, load_source_edges

OUT = Path(__file__).resolve().parent / "out"
kjv = json.load(open(OUT / "kjv_verses.json"))
vid = {(v["b"], v["c"], v["v"]): i for i, v in enumerate(kjv)}
N_ALL = len(kjv)
chapters = sorted({(v["b"], v["c"]) for v in kjv})
cidx = {c: i for i, c in enumerate(chapters)}
rng = np.random.default_rng(0)


def norm_adj_eigs(A, k):
    """Top-k eigenpairs of D^-1/2 A D^-1/2 (A symmetric sparse, no isolated nodes)."""
    d = np.asarray(A.sum(1)).ravel()
    Dm = sparse.diags(1 / np.sqrt(d))
    vals, vecs = eigsh(Dm @ A @ Dm, k=k, which="LA")
    order = np.argsort(-vals)
    return vals[order], (Dm @ vecs[:, order]), d  # right eigenvectors of the random-walk matrix


# ---------- helix ----------
helix = {"chapters": [{"b": b, "c": c} for b, c in chapters], "books": [b[2] for b in BOOKS],
         "abbr": [b[3] for b in BOOKS], "genres": [GENRE_OF[b[0]] for b in BOOKS]}
for src in ("tsk3", "esv"):
    w = aggregate(load_source_edges(src), "chapter")
    rows, cols, vals = [], [], []
    for (a, b), x in w.items():
        if a != b:
            rows += [cidx[a], cidx[b]]
            cols += [cidx[b], cidx[a]]
            vals += [x, x]
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(len(chapters),) * 2)
    vals_, vecs, d = norm_adj_eigs(A, 4)
    # diffusion map, t = 1: coordinates = lambda_k * psi_k, k = 2, 3
    xy = vecs[:, 1:3] * vals_[1:3]
    xy = (xy - xy.mean(0)) / xy.std(0)
    xy = np.clip(xy, -3, 3)
    # threads: chapter pairs with the most references relative to expectation (configuration model), min 6 refs
    m2 = A.sum()
    pairs = []
    for (a, b), x in w.items():
        if a == b or x < 6:
            continue
        i, j = cidx[a], cidx[b]
        pairs.append((x / (d[i] * d[j] / m2), i, j, x))
    pairs.sort(reverse=True)
    helix[src] = {"xy": xy.round(3).tolist(), "eig": vals_.round(4).tolist(), "deg": d.astype(int).tolist(),
                  "threads": [[i, j, int(x), round(float(r), 1)] for r, i, j, x in pairs[:900]]}
    print(f"elica {src}: autovalori {vals_.round(3)}, fili {min(900, len(pairs))} su {len(pairs)}")
json.dump(helix, open(OUT / "helix.json", "w"), separators=(",", ":"))

# ---------- hyperbolic disk ----------
disk = {}
for src in ("tsk3", "esv"):
    pairs = {tuple(sorted((vid[a], vid[b]))) for a, b in load_source_edges(src) if a in vid and b in vid}
    nodes = sorted({i for p in pairs for i in p})
    loc = {g: k for k, g in enumerate(nodes)}
    n = len(nodes)
    r_, c_ = zip(*[(loc[a], loc[b]) for a, b in pairs])
    A = sparse.csr_matrix((np.ones(2 * len(pairs)), (r_ + c_, c_ + r_)), shape=(n, n))
    # keep the largest connected component
    ncomp, lab = sparse.csgraph.connected_components(A, directed=False)
    big = np.argmax(np.bincount(lab))
    keep = np.where(lab == big)[0]
    A = A[keep][:, keep]
    nodes = [nodes[k] for k in keep]
    n = len(nodes)
    deg = np.asarray(A.sum(1)).ravel()
    # Laplacian eigenmaps (2-D): smallest non-trivial eigenvectors of the normalized Laplacian
    # = largest non-trivial of D^-1/2 A D^-1/2
    vals_, vecs, _ = norm_adj_eigs(A, 3)
    theta_raw = np.arctan2(vecs[:, 2], vecs[:, 1])
    # equidistant adjustment (Muscoloni et al. 2017, coalescent embedding): keep the angular order, spread uniformly
    theta = np.empty(n)
    theta[np.argsort(theta_raw, kind="stable")] = np.linspace(-np.pi, np.pi, n, endpoint=False)
    # radii from degree rank, popularity-similarity model; gamma from the tail fit, zeta = 1
    gamma = json.load(open(OUT / "distributions.json"))[src]["tail"]["alpha"]
    # beta = 1/(gamma-1) leaves even the top hub at half the maximum radius (empty centre); beta = 1 puts hubs at the
    # centre and gives the same link-prediction AUC (TSK 0.836 vs 0.829, ESV 0.924 vs 0.935), so we use it for display
    beta = 1.0
    rank = np.empty(n)
    rank[np.argsort(-deg, kind="stable")] = np.arange(1, n + 1)
    r = 2 * (beta * np.log(rank) + (1 - beta) * np.log(n))
    # quality: hyperbolic distance of linked vs random pairs (AUC, lower distance = more likely linked)
    def hdist(i, j):
        dth = np.pi - np.abs(np.pi - np.abs(theta[i] - theta[j]))
        x = np.cosh(r[i]) * np.cosh(r[j]) - np.sinh(r[i]) * np.sinh(r[j]) * np.cos(dth)
        return np.arccosh(np.maximum(x, 1))
    Acoo = sparse.triu(A, 1).tocoo()
    s = rng.choice(len(Acoo.row), size=min(50000, len(Acoo.row)), replace=False)
    dl = hdist(Acoo.row[s], Acoo.col[s])
    ri, rj = rng.integers(0, n, 50000), rng.integers(0, n, 50000)
    dr = hdist(ri, rj)
    allv = np.concatenate([-dl, -dr])
    ranks = allv.argsort().argsort() + 1
    auc = (ranks[: len(dl)].sum() - len(dl) * (len(dl) + 1) / 2) / (len(dl) * len(dr))
    # Poincare disk of curvature -1/s^2: rho = tanh(r / 2s), with s chosen so the outermost node sits at 0.98.
    # A change of curvature keeps it an exact hyperbolic space (distances scale by s), so Mobius maps stay exact.
    R = r.max()
    s_curv = R / (2 * np.arctanh(0.98))
    rho = np.tanh(r / (2 * s_curv))
    adj = [[] for _ in range(n)]
    for i, j in zip(Acoo.row, Acoo.col):
        adj[i].append(int(j))
        adj[j].append(int(i))
    theta_eq = theta
    theta = theta_raw
    dl_raw, dr_raw = hdist(Acoo.row[s], Acoo.col[s]), hdist(ri, rj)
    theta = theta_eq
    allv = np.concatenate([-dl_raw, -dr_raw]); ranks = allv.argsort().argsort() + 1
    auc_raw = (ranks[: len(dl_raw)].sum() - len(dl_raw) * (len(dl_raw) + 1) / 2) / (len(dl_raw) * len(dr_raw))
    print(f"  AUC con angoli originali {auc_raw:.3f}, con aggiustamento equidistante {auc:.3f}")
    disk[src] = {"verse": nodes, "auc_raw": round(float(auc_raw), 3), "theta": theta.round(4).tolist(), "rho": rho.round(4).tolist(), "deg": deg.astype(int).tolist(),
                 "adj": adj, "auc": round(float(auc), 3), "s_curv": round(float(s_curv), 4), "gamma": gamma, "n_components": int(ncomp), "kept": n}
    print(f"disco {src}: {n} versetti nella componente principale (componenti {ncomp}), gamma {gamma}, AUC {auc:.3f}")
disk["labels"] = [[v["b"], v["c"], v["v"]] for v in kjv]
disk["abbr"] = [b[3] for b in BOOKS]
disk["usfm"] = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN "
                "HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI "
                "TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()
json.dump(disk, open(OUT / "disk.json", "w"), separators=(",", ":"))
print("dimensioni:", round((OUT / "helix.json").stat().st_size / 1e6, 2), "MB e", round((OUT / "disk.json").stat().st_size / 1e6, 2), "MB")
