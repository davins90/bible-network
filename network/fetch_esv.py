"""Download the ESV cross-references (Crossway API) for the whole Bible, resumable.

Only the references are kept (no ESV text is stored). One request per chapter, paced under the
API limits (60/min, 1000/hour, 5000/day).
Every reference must parse to a known book and an existing KJV verse: failures are recorded in
out/esv_problems.json, never dropped silently.

Usage: .venv/bin/python fetch_esv.py [chapter filter, e.g. "Jude" or "Psalm 23"]
Output: out/esv_refs.jsonl, one line per chapter: {"b","c","refs": [[verse, phrase, "OSIS.c.v[-c.v]"], ...]}
"""
import html
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "explorer"))
from books import BOOKS, BY_EN, SINGLE  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
KEY = next(l.split("=", 1)[1].strip() for l in (ROOT.parent / ".env").read_text().splitlines() if l.startswith("ESV_API_KEY="))
PACE = 3.7  # seconds between requests: < 1000/hour

kjv = json.load(open(OUT / "kjv_verses.json"))
LAST = {}
for v in kjv:
    LAST[(v["b"], v["c"])] = max(LAST.get((v["b"], v["c"]), 0), v["v"])
EXISTS = {(v["b"], v["c"], v["v"]) for v in kjv}


def parse_ref(r):
    """'Romans 1:17' | 'Genesis 1:1-2:3' | 'Psalm 23' (whole chapter) | 'Jude 3' -> (book, c1, v1, c2, v2)"""
    r = r.strip().replace("–", "-")
    m = re.match(r"^(.+?) (\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$", r)
    if not m:
        raise ValueError(f"formato sconosciuto: {r!r}")
    name, a, b, c, d = m.groups()
    if name not in BY_EN:
        raise ValueError(f"libro sconosciuto: {name!r}")
    bi = BY_EN[name]
    single = BOOKS[bi][0] in SINGLE
    if b is None and single:  # "Jude 3", "Jude 3-5"
        c1, v1, c2, v2 = 1, int(a), 1, int(c) if c else int(a)
    elif b is None:  # "Psalm 23" or "Psalm 23-24": whole chapters
        c1, v1 = int(a), 1
        c2 = int(c) if c else c1
        v2 = LAST.get((bi, c2), 0)
    else:
        c1, v1 = int(a), int(b)
        if c is None:
            c2, v2 = c1, v1
        elif d is None:
            c2, v2 = c1, int(c)
        else:
            c2, v2 = int(c), int(d)
    for (cc, vv) in ((c1, v1), (c2, v2)):
        if (bi, cc, vv) not in EXISTS:
            raise ValueError(f"versetto inesistente nella KJV: {r!r} -> {BOOKS[bi][0]}.{cc}.{vv}")
    return bi, c1, v1, c2, v2


def osis(bi, c1, v1, c2, v2):
    return f"{BOOKS[bi][0]}.{c1}.{v1}" + (f"-{BOOKS[bi][0]}.{c2}.{v2}" if (c2, v2) != (c1, v1) else "")


def fetch(bi, ch):
    name = BOOKS[bi][1]
    q = name if BOOKS[bi][0] in SINGLE else f"{name} {ch}"
    params = urllib.parse.urlencode({"q": q, "include-crossrefs": "true", "include-footnotes": "false",
                                     "include-headings": "false", "include-audio-link": "false",
                                     "include-passage-references": "false"})
    for attempt in range(6):
        r = requests.get(f"https://api.esv.org/v3/passage/html/?{params}", headers={"Authorization": f"Token {KEY}"}, timeout=60)
        if r.status_code == 200:
            return r.json()["passages"][0]
        wait = int(r.headers.get("Retry-After", 0)) or 30 * (attempt + 1)
        print(f"  {r.status_code}, riprovo tra {wait}s", flush=True)
        time.sleep(wait)
    r.raise_for_status()


def parse_chapter(h, bi, ch):
    pref = f"{bi + 1:02d}{ch:03d}"
    refs, problems, cur, verses_seen = [], [], None, set()
    pat = rf'id="v{pref}(\d{{3}})-1"|<a class="cf" href="([^"]+)/" title="[^"]*">\w+</a></sup>([^<]{{0,80}})'
    for m in re.finditer(pat, h):
        if m.group(1):
            cur = int(m.group(1))
            verses_seen.add(cur)
            continue
        phrase = html.unescape(m.group(3)).strip().lstrip("“‘\"")
        phrase = " ".join(re.split(r"[,;:.!?”’]", phrase)[0].split()[:5])
        for raw in m.group(2).split(";"):
            raw = urllib.parse.unquote(raw)
            try:
                refs.append([cur, phrase, osis(*parse_ref(raw))])
            except ValueError as e:
                problems.append({"from": f"{BOOKS[bi][0]}.{ch}.{cur}", "raw": raw, "error": str(e)})
    # every KJV verse of the chapter should have been found in the ESV page (versification differences are reported)
    missing = sorted(set(range(1, LAST[(bi, ch)] + 1)) - verses_seen)
    if missing:
        problems.append({"from": f"{BOOKS[bi][0]}.{ch}", "error": f"versetti KJV non trovati nella pagina ESV: {missing}"})
    if None in {r[0] for r in refs}:
        problems.append({"from": f"{BOOKS[bi][0]}.{ch}", "error": "rimando prima del primo versetto"})
    return refs, problems


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else None
    done_path, prob_path = OUT / "esv_refs.jsonl", OUT / "esv_problems.json"
    done = set()
    if done_path.exists() and not flt:
        done = {(d["b"], d["c"]) for d in map(json.loads, done_path.open())}
    problems = json.load(open(prob_path)) if prob_path.exists() and not flt else []
    todo = [(b, c) for (b, c) in sorted(LAST) if (b, c) not in done]
    if flt:
        todo = [(b, c) for (b, c) in todo if f"{BOOKS[b][1]} {c}" == flt or BOOKS[b][1] == flt]
    print(f"capitoli da scaricare: {len(todo)}", flush=True)
    out = done_path.open("a") if not flt else None
    for k, (bi, ch) in enumerate(todo):
        t0 = time.time()
        refs, probs = parse_chapter(fetch(bi, ch), bi, ch)
        problems += probs
        if out:
            out.write(json.dumps({"b": bi, "c": ch, "refs": refs}, ensure_ascii=False) + "\n")
            out.flush()
            json.dump(problems, open(prob_path, "w"), ensure_ascii=False, indent=1)
        else:
            print(BOOKS[bi][1], ch, "rimandi", len(refs), "| esempi", refs[:3], "| problemi", probs)
        if k % 50 == 0:
            print(f"{k}/{len(todo)} {BOOKS[bi][1]} {ch}: {len(refs)} rimandi, problemi totali {len(problems)}", flush=True)
        time.sleep(max(0, PACE - (time.time() - t0)))
    print("fatto", flush=True)


if __name__ == "__main__":
    main()
