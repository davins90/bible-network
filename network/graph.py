"""Load the OpenBible cross-reference graph at verse, chapter and book level.

Edges are undirected; a target range (e.g. Jer.32.17-Jer.32.19) is attached to its first verse.
Weight of an edge = 1 per cross-reference (votes only used as a filter).
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "explorer"))
from books import BOOKS, BY_OSIS  # noqa: E402

XREF = Path(__file__).resolve().parent.parent / "data" / "cross_references.txt"

# Genre for colouring, by OSIS code
GENRES = [
    ("Pentateuco", "Gen Exod Lev Num Deut"),
    ("Storici", "Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth"),
    ("Poetici e sapienziali", "Job Ps Prov Eccl Song"),
    ("Profeti maggiori", "Isa Jer Lam Ezek Dan"),
    ("Profeti minori", "Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal"),
    ("Vangeli e Atti", "Matt Mark Luke John Acts"),
    ("Lettere di Paolo", "Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm"),
    ("Lettere generali e Apocalisse", "Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev"),
]
GENRE_OF = {b: g for g, codes in GENRES for b in codes.split()}


def parse(ref: str):
    book, ch, v = ref.split("-")[0].split(".")
    return BY_OSIS[book], int(ch), int(v)


QUARANTINE = Path(__file__).resolve().parent / "out" / "quarantine.json"


def quarantined() -> set:
    """Lines excluded by data_checks.py (non-existent verses, Jonah read as John)."""
    import json

    return set(json.load(open(QUARANTINE))["quarantine"]) if QUARANTINE.exists() else set()


def load_edges(min_votes: int = 3):
    """List of (verse_a, verse_b) with verse = (book_idx, chapter, verse); self-loops and quarantined lines dropped."""
    edges = []
    skip = quarantined()
    with open(XREF) as f:
        next(f)
        for line in f:
            a, b, votes = line.rstrip("\n").split("\t")[:3]
            if int(votes) < min_votes or f"{a}\t{b}" in skip:
                continue
            va, vb = parse(a), parse(b)
            if va != vb:
                edges.append((va, vb))
    return edges


def aggregate(edges, level: str):
    """Undirected weighted edge counts at 'chapter' or 'book' level (self-loops kept for book×book)."""
    key = (lambda v: v[:2]) if level == "chapter" else (lambda v: v[0])
    w = Counter()
    for a, b in edges:
        ka, kb = key(a), key(b)
        w[tuple(sorted((ka, kb)))] += 1
    return w


def verse_label(v):
    return f"{BOOKS[v[0]][3]} {v[1]}:{v[2]}"


def chapter_label(c):
    return f"{BOOKS[c[0]][2]} {c[1]}"


def degree(edges):
    d = defaultdict(int)
    for a, b in edges:
        d[a] += 1
        d[b] += 1
    return d


def load_linked_pairs(min_votes: int, verse_index: dict):
    """Set of (i, j) verse-index pairs linked by a reference, with target ranges expanded to every verse.

    verse_index maps (book, chapter, verse) -> int in canonical order, so a range is the run of indices.
    """
    pairs = set()
    with open(XREF) as f:
        next(f)
        for line in f:
            a, b, votes = line.rstrip("\n").split("\t")[:3]
            if int(votes) < min_votes:
                continue
            if any(r.split(".")[0] not in BY_OSIS for r in [a] + b.split("-")):
                continue
            ia = verse_index.get(parse(a))
            lo, hi = b.split("-")[0], b.split("-")[-1]
            ilo, ihi = verse_index.get(parse(lo)), verse_index.get(parse(hi))
            if ia is None or ilo is None or ihi is None:
                continue
            for j in range(ilo, min(ihi, ilo + 60) + 1):
                pairs.add((ia, j))
                pairs.add((j, ia))
    return pairs


ESV = Path(__file__).resolve().parent / "out" / "esv_refs.jsonl"
# last verse of each psalm in the KJV numbering (titles are not numbered)
PSALM_LAST = {}
if (Path(__file__).resolve().parent / "out" / "kjv_verses.json").exists():
    import json as _json

    for _v in _json.load(open(Path(__file__).resolve().parent / "out" / "kjv_verses.json")):
        if _v["b"] == BY_OSIS["Ps"]:
            PSALM_LAST[_v["c"]] = max(PSALM_LAST.get(_v["c"], 0), _v["v"])


def esv_lines():
    """(from 'OSIS.c.v', to 'OSIS.c.v[-OSIS.c.v]') for every ESV cross-reference, duplicates kept once."""
    import json

    seen = []
    for d in map(json.loads, ESV.open()):
        book = BOOKS[d["b"]][0]
        for verse, _phrase, target in d["refs"]:
            # a reference on a psalm title (before verse 1) is attached to verse 1
            seen.append((f"{book}.{d['c']}.{verse or 1}", target))
    # references the fetcher could not read, recovered with an explicit rule: "Psalms 73–83" = Ps 73:1 – 83:last
    problems = ESV.parent / "esv_problems.json"
    for p in (json.load(open(problems)) if problems.exists() else []):
        m = re.fullmatch(r"\s*Psalms (\d+)[–-](\d+)", p.get("raw", ""))
        if m:
            seen.append((p["from"], f"Ps.{m.group(1)}.1-Ps.{m.group(2)}.{PSALM_LAST[int(m.group(2))]}"))
        elif p.get("raw", "").strip() == "Obadiah":  # the whole one-chapter book
            seen.append((p["from"], "Obad.1.1-Obad.1.21"))
    return list(dict.fromkeys(seen))


def load_source_edges(source: str):
    """'tsk3' / 'tsk10' -> OpenBible with that vote threshold; 'esv' -> ESV cross-references."""
    if source.startswith("tsk"):
        return load_edges(int(source[3:]))
    edges = []
    for a, b in esv_lines():
        va, vb = parse(a), parse(b)
        if va != vb:
            edges.append((va, vb))
    return edges


def load_source_linked_pairs(source: str, verse_index: dict):
    if source.startswith("tsk"):
        return load_linked_pairs(int(source[3:]), verse_index)
    pairs = set()
    for a, b in esv_lines():
        ia = verse_index.get(parse(a))
        lo, hi = b.split("-")[0], b.split("-")[-1]
        ilo, ihi = verse_index.get(parse(lo)), verse_index.get(parse(hi))
        if ia is None or ilo is None or ihi is None:
            continue
        for j in range(ilo, min(ihi, ilo + 60) + 1):
            pairs.add((ia, j))
            pairs.add((j, ia))
    return pairs
