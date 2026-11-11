"""Export the network data for the web app -> ../app/public/data/

meta.json   books (OSIS, USFM for YouVersion links, Italian names), verse counts per chapter
map.json    one entry per chapter: coordinates (TSK, ESV, text), genre, communities, neighbours, degrees
text.json   preview text per verse: BSB (public domain), KJV where the BSB omits the verse
refs/NN.json  per book: for each verse, ESV references grouped by phrase, plus TSK references (>= 3 votes)
              that the ESV does not already have

Run after run_all.sh. Checks are explicit: every exported reference resolves to existing verses.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from graph import BOOKS, BY_OSIS, GENRE_OF, XREF, parse, quarantined

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DEST = ROOT.parent / "app" / "public" / "data"
(DEST / "refs").mkdir(parents=True, exist_ok=True)

USFM = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN "
        "HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI "
        "TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()
assert len(USFM) == 66
TSK_MIN_VOTES, TSK_MAX_PER_VERSE = 3, 12

kjv = json.load(open(OUT / "kjv_verses.json"))
vid = {(v["b"], v["c"], v["v"]): i for i, v in enumerate(kjv)}
counts = defaultdict(dict)
for v in kjv:
    counts[v["b"]][v["c"]] = max(counts[v["b"]].get(v["c"], 0), v["v"])

# ---------- text: BSB with KJV fallback ----------
bsb = {}
for r in json.load(open(ROOT.parent / "data" / "bsb" / "BSB.json")):
    if r["book"] <= 66:
        t = re.sub(r"<[^>]+>", "", r["text"]).strip()
        if t:
            bsb[(r["book"] - 1, r["chapter"], r["verse"])] = t
text, fallback = [], []
for v in kjv:
    k = (v["b"], v["c"], v["v"])
    if k in bsb:
        text.append(bsb[k])
    else:
        text.append(v["t"])
        fallback.append(len(text) - 1)
extra_bsb = sorted(set(bsb) - set(vid))
print(f"testo: {len(text)} versetti, {len(fallback)} dalla KJV perché la BSB non li ha; versetti BSB fuori dalla KJV: {len(extra_bsb)}")
json.dump({"text": text, "kjv": fallback}, open(DEST / "text.json", "w"), ensure_ascii=False, separators=(",", ":"))


def compact(ref):
    """'Rom.8.28' -> 'Rom.8.28'; ranges kept as 'Rom.8.28-Rom.8.30'. Validates every endpoint."""
    for end in ref.split("-"):
        if parse(end) not in vid:
            raise ValueError(f"versetto inesistente: {ref}")
    return ref


# ---------- refs per book ----------
esv_by_verse = defaultdict(list)  # (b,c,v) -> [[phrase, [refs]]]
for d in map(json.loads, (OUT / "esv_refs.jsonl").open()):
    for verse, phrase, target in d["refs"]:
        key = (d["b"], d["c"], verse or 1)
        groups = esv_by_verse[key]
        if groups and groups[-1][0] == phrase:
            groups[-1][1].append(compact(target))
        else:
            groups.append([phrase, [compact(target)]])


def span(ref):
    lo, hi = ref.split("-")[0], ref.split("-")[-1]
    a, b = vid[parse(lo)], vid[parse(hi)]
    return set(range(a, min(b, a + 60) + 1))


esv_targets = {k: set().union(*(span(r) for _, rs in g for r in rs)) for k, g in esv_by_verse.items()}
tsk_by_verse = defaultdict(list)
skip = quarantined()
# probability that a modern curator would keep the reference (highlight_model.py)
SCORES = json.load(open(OUT / "tsk_scores.json"))
HIGHLIGHTS = json.load(open(OUT / "highlights.json"))
with open(XREF) as f:
    next(f)
    for line in f:
        a, b, votes = line.rstrip("\n").split("\t")[:3]
        if int(votes) < TSK_MIN_VOTES or f"{a}\t{b}" in skip:
            continue
        key = parse(a)
        if key not in vid or span(b) & esv_targets.get(key, set()):
            continue
        tsk_by_verse[key].append((SCORES.get(f"{a}\t{b}", 0.0), int(votes), compact(b)))

chapter_pos = {c: i for i, c in enumerate(sorted({(v["b"], v["c"]) for v in kjv}))}
n_esv = n_tsk = 0
for bi in range(66):
    book = {}
    for ch, last in counts[bi].items():
        verses = {}
        for v in range(1, last + 1):
            e = esv_by_verse.get((bi, ch, v), [])
            t = sorted(tsk_by_verse.get((bi, ch, v), []), reverse=True)[:TSK_MAX_PER_VERSE]
            if e or t:
                verses[v] = {"e": e, "t": [[r, n, p] for p, n, r in t]}
                n_esv += sum(len(rs) for _, rs in e)
                n_tsk += len(t)
        # highlighted connections of the chapter (they include ESV references, so they live with the licensed files)
        verses["_h"] = HIGHLIGHTS[str(chapter_pos[(bi, ch)])]
        book[ch] = verses
    json.dump(book, open(DEST / "refs" / f"{bi:02d}.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(f"rimandi esportati: ESV {n_esv}, TSK in più {n_tsk}")

# ---------- map ----------
nets = {s: json.load(open(OUT / f"network_{s}.json")) for s in ("tsk3", "esv")}
pts = {s: {p["id"]: p for p in n["chapters"]} for s, n in nets.items()}
chapters = [(b, c) for b in range(66) for c in sorted(counts[b])]
label = lambda b, c: f"{BOOKS[b][2]} {c}"  # noqa: E731
index = {label(b, c): i for i, (b, c) in enumerate(chapters)}
helix = json.load(open(OUT / "helix.json"))
assert [(x["b"], x["c"]) for x in helix["chapters"]] == chapters
# chapter graph (TSK >= 3 votes) for the "what to read next" random walk: top 40 neighbours by weight per chapter
from graph import aggregate, load_source_edges  # noqa: E402
cw = aggregate(load_source_edges("tsk3"), "chapter")
nbrs = defaultdict(list)
for (x, y), w in cw.items():
    if x != y:
        nbrs[index[label(*x)]].append((w, index[label(*y)]))
        nbrs[index[label(*y)]].append((w, index[label(*x)]))
rows = []
for b, c in chapters:
    t, e = pts["tsk3"][label(b, c)], pts["esv"][label(b, c)]
    rows.append({
        "b": b, "c": c,
        "tsk": [t["x"], t["y"]], "esv": [e["x"], e["y"]], "txt": [t["tx"], t["ty"]],
        "dt": t["deg"], "de": e["deg"], "ot": [t["ot"], e["ot"]],
        "ct": t["comm"], "ce": e["comm"],
        "nt": [index[x] for x in t["nn"]], "ne": [index[x] for x in e["nn"]], "nx": [index[x] for x in t["tnn"]],
        "hx": [helix["tsk3"]["xy"][len(rows)], helix["esv"]["xy"][len(rows)]],
        "pr": t["pr"],
        "g": [[j, int(w)] for w, j in sorted(nbrs[len(rows)], reverse=True)[:40]],
    })
json.dump({
    "chapters": rows,
    "communities": {"tsk": nets["tsk3"]["communities"], "esv": nets["esv"]["communities"]},
    "threads": {"tsk": helix["tsk3"]["threads"][:600], "esv": helix["esv"]["threads"][:600]},
}, open(DEST / "map.json", "w"), ensure_ascii=False, separators=(",", ":"))

genres = sorted(set(GENRE_OF.values()), key=list(GENRE_OF.values()).index)
json.dump({
    "books": [{"osis": b[0], "usfm": USFM[i], "en": b[1], "it": b[2], "ab": b[3], "genre": GENRE_OF[b[0]],
               "verses": [counts[i][c] for c in sorted(counts[i])]} for i, b in enumerate(BOOKS)],
    "genres": genres,
    "verseOffset": [vid[(b, c, 1)] for b, c in chapters],
}, open(DEST / "meta.json", "w"), ensure_ascii=False, separators=(",", ":"))
sizes = {p.name: round(p.stat().st_size / 1e6, 2) for p in DEST.glob("*.json")}
print("file:", sizes, "| refs:", round(sum(p.stat().st_size for p in (DEST / 'refs').glob('*.json')) / 1e6, 1), "MB")
