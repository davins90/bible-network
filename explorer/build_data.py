"""Costruisce i dati dell'esploratore per un libro: rimandi ESV per frase, rimandi OpenBible extra, testi NLT.

Uso:
    python3 build_data.py Romans 1-16 ../data/cross_references.txt romani_data.json
Legge ESV_API_KEY da ../.env. Il testo NLT viene dall'API pubblica di Tyndale (uso non commerciale).
"""
import csv, html, json, re, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from books import BOOKS, BY_EN, BY_OSIS

BOOK_EN, RANGE, XREF, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
lo, hi = map(int, RANGE.split("-"))
BI = BY_EN[BOOK_EN]
OSIS = BOOKS[BI][0]
ESV_KEY = next(l.split("=", 1)[1].strip() for l in (HERE.parent / ".env").read_text().splitlines() if l.startswith("ESV_API_KEY="))
UA = {"User-Agent": "curl/8.0"}


def get(url, headers=None):
    for attempt in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=60).read().decode()
        except Exception as e:
            print("  riprovo:", e, file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(url)


def ref_key(bi, c1, v1, c2, v2):
    return f"{BOOKS[bi][0]}.{c1}.{v1}" + (f"-{c2}.{v2}" if (c2, v2) != (c1, v1) else "")


def parse_esv(r):
    r = r.strip().replace("–", "-")
    m = re.match(r"^(.+?) (\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$", r)
    name, a, b, c, d = m.groups()
    bi = BY_EN[name]
    if b is None:  # libro di un solo capitolo: "Jude 1", "Philemon 4"
        c1, v1 = 1, int(a)
        c2, v2 = (1, int(c)) if c else (c1, v1)
    else:
        c1, v1 = int(a), int(b)
        if c is None:
            c2, v2 = c1, v1
        elif d is None:
            c2, v2 = c1, int(c)
        else:
            c2, v2 = int(c), int(d)
    return bi, c1, v1, c2, v2


def parse_ob(r):
    parts = r.split("-")
    b, c, v = parts[0].split(".")
    c2, v2 = parts[1].split(".")[1:] if len(parts) == 2 else (c, v)
    return BY_OSIS[b], int(c), int(v), int(c2), int(v2)


def start_of(k):
    return k.split("-")[0]


def n_verses(k):
    a = k.split("-")
    if len(a) == 1:
        return 1
    _, c, v = a[0].split(".")
    c2, v2 = a[1].split(".")
    return int(v2) - int(v) + 1 if c2 == c else 40


def nlt_q(k):
    a = k.split("-")
    b, c, v = a[0].split(".")
    q = f"{BOOKS[BY_OSIS[b]][1]} {c}:{v}"
    if len(a) == 2:
        c2, v2 = a[1].split(".")
        q += f"-{v2}" if c2 == c else f"-{c2}:{v2}"
    return q


def clean(fragment):
    fragment = re.sub(r'<a class="a-tn">\*</a><span class="tn"><span class="tn-ref">[^<]*</span>.*?</span>', "", fragment, flags=re.S)
    fragment = re.sub(r'<(h[2-4]) class="(?:chapter-number|subhead)">.*?</\1>', "", fragment, flags=re.S)
    fragment = re.sub(r'<p class="psa-title">.*?</p>', "", fragment, flags=re.S)
    out = []
    for m in re.finditer(r'<verse_export[^>]*vn="(\d+)"[^>]*>(.*?)</verse_export>', fragment, re.S):
        s = re.sub(r'<span class="vn">\d+</span>', "", m.group(2))
        out.append([int(m.group(1)), " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())])
    return out


ob_all = defaultdict(list)
with open(XREF) as f:
    next(f)
    for a, b, v in csv.reader(f, delimiter="\t"):
        if a.startswith(OSIS + "."):
            _, c, vv = a.split(".")
            ob_all[(int(c), int(vv))].append((int(v), ref_key(*parse_ob(b))))

chapters, wanted = {}, set()
for ch in range(lo, hi + 1):
    print(f"{BOOK_EN} {ch}", file=sys.stderr)
    q = urllib.parse.urlencode({"q": f"{BOOK_EN} {ch}", "include-crossrefs": "true", "include-footnotes": "false",
                                "include-headings": "false", "include-audio-link": "false"})
    h = json.loads(get(f"https://api.esv.org/v3/passage/html/?{q}", {"Authorization": f"Token {ESV_KEY}"}))["passages"][0]
    pref = f"{BI + 1:02d}{ch:03d}"
    esv, cur = defaultdict(list), None
    for m in re.finditer(rf'id="v{pref}(\d{{3}})-1"|<a class="cf" href="([^"]+)/" title="[^"]*">\w+</a></sup>([^<]{{0,80}})', h):
        if m.group(1):
            cur = int(m.group(1))
            continue
        phrase = html.unescape(m.group(3)).strip().lstrip("“‘\"")
        phrase = " ".join(re.split(r"[,;:.!?”’]", phrase)[0].split()[:5])
        esv[cur].append({"phrase": phrase, "refs": [ref_key(*parse_esv(r)) for r in m.group(2).split(";")]})

    extra = {}
    for (c, verse), items in ob_all.items():
        if c != ch:
            continue
        seen = {start_of(r) for g in esv.get(verse, []) for r in g["refs"]}
        items = sorted([x for x in items if x[0] >= 10 and start_of(x[1]) not in seen], reverse=True)[:4]
        if items:
            extra[verse] = [{"ref": r, "votes": v} for v, r in items]

    body = get("https://api.nlt.to/api/passages?" + urllib.parse.urlencode({"ref": f"{BOOK_EN} {ch}", "version": "NLT"}))
    heads = {}
    for m in re.finditer(r'<verse_export[^>]*vn="(\d+)"[^>]*>(.*?)</verse_export>', body, re.S):
        sh = re.search(r'<h[2-4] class="subhead">(.*?)</h[2-4]>', m.group(2), re.S)
        if sh:
            heads[int(m.group(1))] = html.unescape(re.sub(r"<[^>]+>", "", sh.group(1)))

    chapters[ch] = {
        "verses": clean(body), "heads": heads, "esv": esv, "extra": extra,
        "countEsv": dict(Counter(bk for g in esv.values() for x in g for bk in (r.split(".")[0] for r in x["refs"]))),
        "countExtra": dict(Counter(x["ref"].split(".")[0] for xs in extra.values() for x in xs)),
    }
    wanted |= {r for g in esv.values() for x in g for r in x["refs"]} | {x["ref"] for xs in extra.values() for x in xs}
    time.sleep(0.5)

# testi NLT dei passi collegati, a gruppi di massimo 45 versetti per richiesta
texts, batch, size = {}, [], 0
todo = sorted(wanted)


def flush(batch):
    body = get("https://api.nlt.to/api/passages?" + urllib.parse.urlencode({"ref": ";".join(nlt_q(k) for k in batch), "version": "NLT"}))
    chunks = re.split(r'<h2 class="bk_ch_vs_header">', body)[1:]
    if len(chunks) != len(batch):
        print("ATTENZIONE: risposte", len(chunks), "per", len(batch), file=sys.stderr)
    for k, chunk in zip(batch, chunks):
        texts[k] = clean(chunk)
    time.sleep(0.4)


print(f"testi NLT da scaricare: {len(todo)}", file=sys.stderr)
for k in todo:
    n = n_verses(k)
    if batch and (size + n > 45 or len(batch) >= 15):
        flush(batch)
        batch, size = [], 0
    batch.append(k)
    size += n
if batch:
    flush(batch)

json.dump({"bookIt": BOOKS[BI][2], "books": [{"osis": b[0], "it": b[2], "ab": b[3], "nt": i >= 39} for i, b in enumerate(BOOKS)],
           "chapters": chapters, "texts": texts}, open(OUT, "w"), ensure_ascii=False)
print("capitoli", len(chapters), "| rimandi ESV", sum(len(x["refs"]) for c in chapters.values() for g in c["esv"].values() for x in g),
      "| extra", sum(len(x) for c in chapters.values() for x in c["extra"].values()), "| testi", len(texts),
      "| vuoti", [k for k, v in texts.items() if not v][:10])
