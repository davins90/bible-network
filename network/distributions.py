"""How are cross-references distributed over verses? TSK (>= 3 votes) and ESV.

1. Shape of the degree distribution: power law vs lognormal vs truncated power law vs exponential,
   Clauset-Shalizi-Newman (2009) method via the `powerlaw` package (MLE, xmin by KS, likelihood-ratio tests).
2. Full range including verses with 0 references: Poisson vs negative binomial.
3. What explains the number of references: NB2 regression on verse length, genre, position in the book.
4. Concentration: Lorenz curve and Gini.
5. How far references jump along the canon, and in which direction (OT -> NT or back).

Degree = number of distinct verses a verse is linked to (undirected, target ranges attached to their first verse,
as in the rest of the analysis). Usage: .venv/bin/python distributions.py -> out/distributions.json
"""
import json
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import powerlaw
import statsmodels.api as sm
import statsmodels.formula.api as smf

from graph import BOOKS, GENRE_OF, XREF, esv_lines, parse, quarantined, verse_label

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parent / "out"
kjv = json.load(open(OUT / "kjv_verses.json"))
vid = {(v["b"], v["c"], v["v"]): i for i, v in enumerate(kjv)}
N = len(kjv)
nt_of = np.array([v["b"] >= 39 for v in kjv])


def directed_lines(source):
    """(i, j) global verse indices, in the direction the reference was written."""
    out = []
    if source == "tsk3":
        skip = quarantined()
        with open(XREF) as f:
            next(f)
            for line in f:
                a, b, v = line.rstrip("\n").split("\t")[:3]
                if int(v) >= 3 and f"{a}\t{b}" not in skip:
                    out.append((vid.get(parse(a)), vid.get(parse(b.split("-")[0]))))
    else:
        out = [(vid.get(parse(a)), vid.get(parse(b.split("-")[0]))) for a, b in esv_lines()]
    return [(i, j) for i, j in out if i is not None and j is not None and i != j]


def ccdf(k):
    """Empirical P(K >= x) on a log grid, for plotting."""
    k = np.sort(k[k > 0])
    xs = np.unique(np.round(np.logspace(0, np.log10(k.max()), 60)).astype(int))
    return [[int(x), float((k >= x).mean())] for x in xs]


def analyse(source):
    lines = directed_lines(source)
    pairs = {tuple(sorted(p)) for p in lines}
    deg = np.zeros(N, int)
    for i, j in pairs:
        deg[i] += 1
        deg[j] += 1
    k = deg[deg > 0]

    # ---------- 1. tail shape (CSN) ----------
    fit = powerlaw.Fit(k, discrete=True, verbose=False)
    comps = {}
    for alt in ("lognormal", "truncated_power_law", "exponential"):
        R, p = fit.distribution_compare("power_law", alt, normalized_ratio=True)
        comps[alt] = {"R": round(float(R), 2), "p": float(f"{p:.3g}")}  # R < 0: the alternative fits better
    R_lt, p_lt = fit.distribution_compare("lognormal", "truncated_power_law", normalized_ratio=True)
    tail = {
        "xmin": int(fit.xmin), "alpha": round(float(fit.power_law.alpha), 3), "alpha_se": round(float(fit.power_law.sigma), 3),
        "ks_D": round(float(fit.power_law.D), 4), "n_tail": int((k >= fit.xmin).sum()), "share_tail": round(float((k >= fit.xmin).mean()), 3),
        "lognormal_mu": round(float(fit.lognormal.mu), 3), "lognormal_sigma": round(float(fit.lognormal.sigma), 3),
        "tpl_alpha": round(float(fit.truncated_power_law.alpha), 3), "tpl_lambda": float(f"{fit.truncated_power_law.Lambda:.3g}"),
        "vs_power_law": comps, "lognormal_vs_tpl": {"R": round(float(R_lt), 2), "p": float(f"{p_lt:.3g}")},
    }
    # model CCDFs on the tail, scaled to the empirical share above xmin, for the plot
    xs = np.unique(np.round(np.logspace(np.log10(fit.xmin), np.log10(k.max()), 40)).astype(int))
    tail["model_ccdf"] = {
        name: [[int(x), float(y * tail["share_tail"])] for x, y in zip(xs, getattr(fit, name).ccdf(xs))]
        for name in ("power_law", "lognormal", "truncated_power_law")
    }

    # ---------- 2. full range, zeros included ----------
    y = deg
    pois = sm.GLM(y, np.ones((N, 1)), family=sm.families.Poisson()).fit()
    nb = sm.NegativeBinomial(y, np.ones((N, 1))).fit(disp=0)
    mu, a = float(np.exp(nb.params[0])), float(nb.params[1])  # NB2: var = mu + a mu^2
    full = {
        "n_verses": N, "zeros": int((y == 0).sum()), "mean": round(float(y.mean()), 2), "var": round(float(y.var()), 1),
        "median": float(np.median(y)), "p90": float(np.quantile(y, 0.9)), "p99": float(np.quantile(y, 0.99)), "max": int(y.max()),
        "dispersion_index": round(float(y.var() / y.mean()), 1),
        "aic_poisson": round(float(pois.aic), 0), "aic_nb": round(float(nb.aic), 0), "nb_mu": round(mu, 2), "nb_alpha": round(a, 3),
        "zeros_expected_nb": int(N * (1 + a * mu) ** (-1 / a)), "zeros_expected_poisson": int(N * np.exp(-mu)),
        "ccdf": ccdf(y),
        "obs_counts": np.bincount(y).tolist(),
    }

    # ---------- 3. regression ----------
    words = np.array([len(v["t"].split()) for v in kjv])
    book_len = Counter(v["b"] for v in kjv)
    first = {}
    for i, v in enumerate(kjv):
        first.setdefault(v["b"], i)
    df = pd.DataFrame({
        "deg": y, "logw": np.log(words), "genre": [GENRE_OF[BOOKS[v["b"]][0]] for v in kjv],
        "pos": [(i - first[v["b"]]) / max(1, book_len[v["b"]] - 1) for i, v in enumerate(kjv)],
    })
    m = smf.negativebinomial("deg ~ logw + C(genre, Treatment('Pentateuco')) + pos + I(pos**2)", df).fit(disp=0, maxiter=200)
    ci = m.conf_int()
    coefs = []
    for name in m.params.index:
        if name in ("Intercept", "alpha"):
            continue
        label = name.replace("C(genre, Treatment('Pentateuco'))[T.", "").rstrip("]")
        coefs.append({"term": label, "irr": round(float(np.exp(m.params[name])), 3),
                      "lo": round(float(np.exp(ci.loc[name, 0])), 3), "hi": round(float(np.exp(ci.loc[name, 1])), 3)})
    reg = {"n": int(m.nobs), "alpha": round(float(m.params["alpha"]), 3), "pseudo_r2": round(float(m.prsquared), 3), "coefs": coefs}

    # ---------- 4. concentration ----------
    s = np.sort(y)[::-1]
    cum = np.cumsum(s) / s.sum()
    lorenz = [[round(q, 3), round(float(cum[max(0, int(q * N) - 1)]), 3)] for q in np.linspace(0, 1, 41)[1:]]
    ys = np.sort(y)
    gini = float(1 - 2 * np.sum(np.cumsum(ys) / ys.sum()) / N + 1 / N)
    conc = {"gini": round(gini, 3), "top1": round(float(cum[int(0.01 * N) - 1]), 3), "top10": round(float(cum[int(0.10 * N) - 1]), 3), "lorenz": lorenz}

    # ---------- 5. distance and direction ----------
    li = np.array(lines)
    dist = np.abs(li[:, 0] - li[:, 1])
    same_ch = np.array([kjv[i]["b"] == kjv[j]["b"] and kjv[i]["c"] == kjv[j]["c"] for i, j in lines])
    same_bk = np.array([kjv[i]["b"] == kjv[j]["b"] for i, j in lines])
    cross = nt_of[li[:, 0]] != nt_of[li[:, 1]]
    bins = np.logspace(0, np.log10(N), 31)
    direction = Counter(("NT" if nt_of[i] else "AT") + "→" + ("NT" if nt_of[j] else "AT") for i, j in lines)
    fwd = li[:, 1] > li[:, 0]
    jump = {
        "n": len(lines), "median": int(np.median(dist)),
        "same_chapter": round(float(same_ch.mean()), 3), "same_book_other_chapter": round(float((same_bk & ~same_ch).mean()), 3),
        "same_testament_other_book": round(float((~same_bk & ~cross).mean()), 3), "cross_testament": round(float(cross.mean()), 3),
        "forward_share": round(float(fwd.mean()), 3),
        "hist": np.histogram(dist, bins=bins)[0].tolist(), "hist_bins": bins.round(1).tolist(),
        "direction": dict(direction),
    }
    hubs = [{"v": verse_label((kjv[i]["b"], kjv[i]["c"], kjv[i]["v"])), "k": int(deg[i]), "w": int(words[i])} for i in np.argsort(-deg)[:12]]
    return {"tail": tail, "full": full, "regression": reg, "concentration": conc, "jump": jump, "hubs": hubs}


res = {s: analyse(s) for s in ("tsk3", "esv")}
json.dump(res, open(OUT / "distributions.json", "w"), ensure_ascii=False)
for s, r in res.items():
    t, f, c, j, g = r["tail"], r["full"], r["concentration"], r["jump"], r["regression"]
    print(f"\n=== {s} ===")
    print(f"gradi: media {f['mean']} varianza {f['var']} (indice di dispersione {f['dispersion_index']}), mediana {f['median']}, p99 {f['p99']}, max {f['max']}, zeri {f['zeros']}")
    print(f"AIC Poisson {f['aic_poisson']:.0f} vs NB {f['aic_nb']:.0f}; NB mu={f['nb_mu']} alpha={f['nb_alpha']}; zeri attesi NB {f['zeros_expected_nb']} Poisson {f['zeros_expected_poisson']}")
    print(f"coda: xmin {t['xmin']} (copre {t['share_tail']:.0%}), alpha {t['alpha']}±{t['alpha_se']}, KS {t['ks_D']}")
    print("power law contro:", t["vs_power_law"], "| lognormale vs tpl:", t["lognormal_vs_tpl"])
    print(f"Gini {c['gini']}, top 1% = {c['top1']:.0%} dei rimandi, top 10% = {c['top10']:.0%}")
    print(f"salti: mediana {j['median']} versetti; stesso capitolo {j['same_chapter']:.0%}, stesso libro {j['same_book_other_chapter']:.0%}, stesso testamento {j['same_testament_other_book']:.0%}, tra testamenti {j['cross_testament']:.0%}; in avanti {j['forward_share']:.0%}")
    print("direzioni:", j["direction"])
    print(f"regressione NB (pseudo R2 {g['pseudo_r2']}):", [(x["term"], x["irr"], x["lo"], x["hi"]) for x in g["coefs"]])
    print("hub:", [(h["v"], h["k"]) for h in r["hubs"][:8]])
