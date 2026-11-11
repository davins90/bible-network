"""Which TSK references would a modern curator keep? A model trained on the ESV as label.

Unit: one TSK reference line (OpenBible, all votes, quarantined lines excluded).
Label: the ESV has the same reference (same source verse or the reverse direction, overlapping target verses).
Features: votes, text similarity (Gemini embeddings of the KJV), how much the two chapters are linked beyond
expectation (configuration model, TSK >= 3 votes), degree of both verses, distance along the canon, cross-testament,
same book, length of the target range, source book (as fixed effects with an L2 penalty = Gaussian prior, MAP).
Validation: GroupKFold by source book (the model never sees the book it is tested on).
Two models compared: penalised logistic regression and gradient boosting (sklearn HistGradientBoosting).

Then, for every chapter: a "highlight" of two kinds among its references, ranked by the model:
  citazione = very similar text (likely quotation or verbal parallel)
  eco       = low text similarity (theme, type, promise and fulfilment)
preferring references that cross the two Testaments and that the ESV also has.

Usage: .venv/bin/python highlight_model.py -> out/highlight_model.json (report), out/highlights.json (per chapter),
       out/tsk_scores.json (score per TSK line used by export_app.py)
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from graph import BOOKS, XREF, esv_lines, parse, quarantined

OUT = Path(__file__).resolve().parent / "out"
kjv = json.load(open(OUT / "kjv_verses.json"))
E = np.load(OUT / "kjv_emb.npy")
vid = {(v["b"], v["c"], v["v"]): i for i, v in enumerate(kjv)}
N = len(kjv)
chapters = sorted({(v["b"], v["c"]) for v in kjv})
cmap = {c: i for i, c in enumerate(chapters)}
ch_of = np.array([cmap[(v["b"], v["c"])] for v in kjv])
book_of = np.array([v["b"] for v in kjv])


def span(ref):
    lo, hi = ref.split("-")[0], ref.split("-")[-1]
    a, b = vid.get(parse(lo)), vid.get(parse(hi))
    if a is None or b is None:
        return None
    return list(range(a, min(b, a + 60) + 1))


# ---------- ESV pairs (label) ----------
esv_pairs = set()
esv_refs = []
for a, b in esv_lines():
    ia, ts = vid.get(parse(a)), span(b)
    if ia is None or not ts:
        continue
    esv_refs.append((ia, ts, a, b))
    for j in ts:
        esv_pairs.add((ia, j))
        esv_pairs.add((j, ia))

# ---------- TSK lines ----------
skip = quarantined()
rows = []
with open(XREF) as f:
    next(f)
    for line in f:
        a, b, v = line.rstrip("\n").split("\t")[:3]
        if f"{a}\t{b}" in skip:
            continue
        ia, ts = vid.get(parse(a)), span(b)
        if ia is None or not ts or ia == ts[0]:
            continue
        rows.append((ia, ts, int(v), a, b))
print(f"righe TSK: {len(rows)}, rimandi ESV: {len(esv_refs)}")

# degrees and chapter-level observed/expected on TSK >= 3 votes
deg = np.zeros(N)
chw = defaultdict(float)
for ia, ts, v, _, _ in rows:
    if v >= 3:
        deg[ia] += 1
        deg[ts[0]] += 1
        chw[tuple(sorted((ch_of[ia], ch_of[ts[0]])))] += 1
chdeg = defaultdict(float)
for (x, y), w in chw.items():
    chdeg[x] += w
    chdeg[y] += w
m2 = sum(chdeg.values())


def oe(ci, cj):
    w = chw.get(tuple(sorted((ci, cj))), 0.0)
    e = chdeg[ci] * chdeg[cj] / m2 if m2 else 0
    return np.log((w + 0.5) / (e + 0.5))  # smoothed log observed/expected


def features(ia, ts, votes):
    j = ts[0]
    sims = E[ts[:5]] @ E[ia]
    return [
        np.log1p(max(votes, 0)), float(votes < 0), float(sims.max()), oe(ch_of[ia], ch_of[j]),
        np.log1p(deg[ia]), np.log1p(deg[j]), np.log1p(abs(j - ia)), float((book_of[ia] >= 39) != (book_of[j] >= 39)),
        float(book_of[ia] == book_of[j]), np.log(len(ts)),
    ]


FEAT = ["log(1+voti)", "voti negativi", "somiglianza del testo", "log osservati/attesi tra capitoli",
        "log(1+grado sorgente)", "log(1+grado arrivo)", "log distanza", "tra AT e NT", "stesso libro", "log lunghezza intervallo"]
X = np.array([features(ia, ts, v) for ia, ts, v, _, _ in rows])
y = np.array([any((ia, j) in esv_pairs for j in ts) for ia, ts, _, _, _ in rows]).astype(int)
groups = np.array([book_of[ia] for ia, _, _, _, _ in rows])
print(f"quota nell'ESV: {y.mean():.3f}")

enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(groups.reshape(-1, 1))
scaler = StandardScaler().fit(X)


def design(Xr, g, with_book=True):
    Z = scaler.transform(Xr)
    return np.hstack([Z, enc.transform(g.reshape(-1, 1))]) if with_book else Z


# ---------- cross-validation by book ----------
gkf = GroupKFold(n_splits=5)
oof = {"logistica": np.zeros(len(y)), "boosting": np.zeros(len(y)), "solo voti": np.zeros(len(y))}
for tr, te in gkf.split(X, y, groups):
    # book effects cannot be learned for unseen books: in CV the logistic uses the continuous features only
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(design(X[tr], groups[tr], False), y[tr])
    oof["logistica"][te] = lr.predict_proba(design(X[te], groups[te], False))[:, 1]
    gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=0).fit(X[tr], y[tr])
    oof["boosting"][te] = gb.predict_proba(X[te])[:, 1]
    lv = LogisticRegression(max_iter=1000).fit(X[tr][:, :2], y[tr])
    oof["solo voti"][te] = lv.predict_proba(X[te][:, :2])[:, 1]


def calib(p, yy, bins=10):
    q = np.quantile(p, np.linspace(0, 1, bins + 1))
    out = []
    for lo, hi in zip(q[:-1], q[1:]):
        m = (p >= lo) & (p <= hi)
        out.append([round(float(p[m].mean()), 4), round(float(yy[m].mean()), 4), int(m.sum())])
    return out


report = {"n": int(len(y)), "positive_rate": round(float(y.mean()), 4), "cv": {}}
for k, p in oof.items():
    report["cv"][k] = {"auc": round(float(roc_auc_score(y, p)), 4), "log_loss": round(float(log_loss(y, p)), 4),
                       "brier": round(float(brier_score_loss(y, p)), 4), "calibration": calib(p, y)}
    print(f"CV per libro, {k}: AUC {report['cv'][k]['auc']}, log-loss {report['cv'][k]['log_loss']}, Brier {report['cv'][k]['brier']}")

# ---------- final models on all data ----------
lr = LogisticRegression(C=1.0, max_iter=3000).fit(design(X, groups), y)
coef = lr.coef_[0]
report["logistic_coefs"] = [{"term": f, "coef_per_sd": round(float(c), 3), "odds_ratio_per_sd": round(float(np.exp(c)), 3)}
                            for f, c in zip(FEAT, coef[:len(FEAT)])]
report["book_effects"] = sorted([{"book": BOOKS[int(b)][2], "coef": round(float(c), 3)}
                                 for b, c in zip(enc.categories_[0], coef[len(FEAT):])], key=lambda d: d["coef"])
best = max(("logistica", "boosting"), key=lambda k: report["cv"][k]["auc"])
report["chosen"] = best
if best == "boosting":
    final = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=0).fit(X, y)
    p_all = final.predict_proba(X)[:, 1]
else:
    p_all = lr.predict_proba(design(X, groups))[:, 1]
print("modello scelto:", best)
for c in report["logistic_coefs"]:
    print(f"  {c['term']:<36} OR per dev. std. {c['odds_ratio_per_sd']}")

# ---------- highlights per chapter ----------
sim_all = X[:, 2]
q_cit = float(np.quantile(sim_all[y == 1], 0.80))  # "citazione": top 20% similarity among curated references
q_eco = float(np.quantile(sim_all[y == 1], 0.40))  # "eco": bottom 40%
report["thresholds"] = {"citazione_sim_min": round(q_cit, 3), "eco_sim_max": round(q_eco, 3)}
cands = defaultdict(list)
for k, (ia, ts, v, a, b) in enumerate(rows):
    if v < 1:
        continue
    cross = (book_of[ia] >= 39) != (book_of[ts[0]] >= 39)
    kind = "citazione" if sim_all[k] >= q_cit else "eco" if sim_all[k] <= q_eco else None
    if kind:
        # rank by one score: model probability, plus a bonus if the ESV also has it and if it crosses the Testaments
        score = float(p_all[k]) + 0.25 * int(y[k]) + 0.15 * int(cross)
        cands[(ch_of[ia], kind)].append((score, int(y[k]), int(cross), float(p_all[k]), a, b, v, float(sim_all[k])))
highlights = {}
for ci in range(len(chapters)):
    h = []
    for kind in ("eco", "citazione"):
        lst = sorted(cands.get((ci, kind), []), reverse=True)
        if lst:
            _, inesv, cross, p, a, b, v, s = lst[0]
            h.append({"kind": kind, "from": a, "to": b, "p": round(p, 3), "votes": v, "sim": round(s, 3), "esv": bool(inesv), "cross": bool(cross)})
    highlights[ci] = h
covered = sum(1 for h in highlights.values() if h)
report["chapters_with_highlight"] = covered
print(f"capitoli con almeno un collegamento in evidenza: {covered} su {len(chapters)}")
json.dump(report, open(OUT / "highlight_model.json", "w"), ensure_ascii=False, indent=1)
json.dump({str(k): v for k, v in highlights.items()}, open(OUT / "highlights.json", "w"), ensure_ascii=False)
json.dump({f"{a}\t{b}": round(float(p), 3) for (_, _, _, a, b), p in zip(rows, p_all)}, open(OUT / "tsk_scores.json", "w"))
for name in ("Romani 8", "Isaia 53", "Genesi 22", "Salmi 22", "Giovanni 3"):
    bk, c = name.rsplit(" ", 1)
    ci = cmap[(next(i for i, x in enumerate(BOOKS) if x[2] == bk), int(c))]
    print(name, "->", [(h["kind"], h["from"], h["to"], h["p"], "ESV" if h["esv"] else "", h["votes"]) for h in highlights[ci]])
