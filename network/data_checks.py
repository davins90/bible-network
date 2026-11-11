"""Deterministic integrity checks on the OpenBible cross-references, against the KJV text.

1. every book code is known and every referenced verse exists in the KJV (66 books);
2. self-references and duplicate lines;
3. Jonah read as John: OpenBible maps the TSK abbreviation "Jon" to John in some lines.
   Rule (lexical, no model): the target chapter:verse also exists in Jonah, and the words the source
   shares with Jonah c:v weigh more than those it shares with John c:v, by at least IDF_MARGIN, where each
   word weighs its IDF over the 31k KJV verses (rare words count, "lord" almost nothing). The embedding
   margin is a second, independent opinion; a line is quarantined only when both point to Jonah.

Output: out/quarantine.json with the line keys ("From\tTo") excluded by load_edges, plus a report.
Usage: .venv/bin/python data_checks.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "explorer"))
from books import BY_OSIS  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
XREF = ROOT.parent / "data" / "cross_references.txt"

STOP = set("""a an and are as at be but by for from had hath have he her him his i if in into is it its
let me my no not now o of on or our out shall she so that the thee their them then there these they thine
this thou thy to unto heb up upon us was we were what when which who whom will with ye you your all also because
did do even every hast him how may more must nor one said saith say say should than therefore those thus
until went were whose why yet come came made make go man men day""".split())


IDF_MARGIN = 5.0  # about one word that appears in fewer than 0.7% of verses


def words(t):
    return {w for w in re.findall(r"[a-z]+", t.lower()) if len(w) >= 3 and w not in STOP}


def main():
    kjv = json.load(open(OUT / "kjv_verses.json"))
    vid = {(v["b"], v["c"], v["v"]): i for i, v in enumerate(kjv)}
    W = [words(v["t"]) for v in kjv]
    df = Counter(w for ws in W for w in ws)
    idf = {w: float(np.log(len(W) / n)) for w, n in df.items()}
    weight = lambda ws: sum(idf[w] for w in ws)  # noqa: E731
    E = np.load(OUT / "kjv_emb.npy") if (OUT / "kjv_emb.npy").exists() else None

    def ix(ref):
        bk, c, v = ref.split(".")
        return vid.get((BY_OSIS[bk], int(c), int(v))) if bk in BY_OSIS else None

    report = Counter()
    quarantine, invalid, jonah = [], [], []
    seen = set()
    JN = BY_OSIS["Jonah"]
    with open(XREF) as f:
        next(f)
        for line in f:
            a, b, votes = line.rstrip("\n").split("\t")[:3]
            key = f"{a}\t{b}"
            report["righe"] += 1
            refs = [a] + b.split("-")
            if any(r.split(".")[0] not in BY_OSIS for r in refs):
                report["codice libro sconosciuto"] += 1
                quarantine.append(key)
                continue
            if any(ix(r) is None for r in refs):
                report["versetto inesistente nella KJV"] += 1
                invalid.append(key)
                quarantine.append(key)
                continue
            if a == b.split("-")[0]:
                report["rimando a se stesso"] += 1
            if key in seen:
                report["righe duplicate"] += 1
            seen.add(key)
            t = b.split("-")[0]
            bk, c, v = t.split(".")
            if bk == "John" and (JN, int(c), int(v)) in vid:
                report["verso Giovanni, c:v esistente anche in Giona"] += 1
                ia, ijn, ijo = ix(a), vid[(JN, int(c), int(v))], ix(t)
                lex = weight(W[ia] & W[ijn]) - weight(W[ia] & W[ijo])
                if lex >= IDF_MARGIN:
                    emb = round(float(E[ia] @ E[ijn] - E[ia] @ E[ijo]), 3) if E is not None else None
                    jonah.append({"from": a, "to": t, "votes": int(votes), "lex_margin": round(lex, 2),
                                  "shared_jonah": sorted(W[ia] & W[ijn], key=lambda w: -idf[w]),
                                  "shared_john": sorted(W[ia] & W[ijo], key=lambda w: -idf[w]), "emb_margin": emb})
                    if emb is not None and emb > 0:
                        quarantine.append(key)
    report["Giona letto come Giovanni (regola lessicale)"] = len(jonah)
    report["…di cui confermati anche dagli embedding"] = sum(1 for x in jonah if (x["emb_margin"] or 0) > 0)
    json.dump({"report": report, "invalid": invalid, "jonah_as_john": jonah, "quarantine": quarantine},
              open(OUT / "quarantine.json", "w"), ensure_ascii=False, indent=1)
    for k, n in report.items():
        print(f"{k}: {n}")
    for x in sorted(jonah, key=lambda x: -x["lex_margin"])[:40]:
        print(f'{x["from"]:>11} -> {x["to"]:<9} voti {x["votes"]:>3} lex {x["lex_margin"]:>5}  Giona: {", ".join(x["shared_jonah"])}  | Giov: {", ".join(x["shared_john"]) or "-"}  emb {x["emb_margin"]}')
    print("inesistenti:", invalid)


if __name__ == "__main__":
    main()
