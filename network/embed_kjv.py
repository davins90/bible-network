"""Embed every KJV verse (66 books) with gemini-embedding-001, resumable.

Usage: .venv/bin/python embed_kjv.py   -> out/kjv_verses.json (text) + out/kjv_emb.npy (float32, L2-normalised)
API key read from ../.env (GEMINI_API_KEY) or the newsletter-digest .env.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
MODEL = "gemini-embedding-001"
DIM = 768
BATCH = 100


def api_key():
    for env in (ROOT.parent / ".env", Path("/home/jupyter/newsletter-digest/.env")):
        if env.exists():
            for line in env.read_text().splitlines():
                k, _, v = line.partition("=")
                if k.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v.strip():
                    return v.strip().strip('"')
    return os.environ["GEMINI_API_KEY"]


def load_kjv():
    raw = json.load(open(ROOT.parent / "data" / "kjv" / "KJV.json"))
    out = []
    for r in raw:
        if r["book"] > 66 or (r["book"] == 17 and (r["chapter"] > 10 or (r["chapter"] == 10 and r["verse"] > 3))):
            continue  # apocrypha and the Greek additions to Esther (10:4-13, 11-16): 31,102 verses remain
        t = re.sub(r"<S>\d+</S>", "", r["text"])
        t = re.sub(r"<sup>.*?</sup>", "", t)  # translators' marginal notes ("Heb. ...", "or, ...")
        t = re.sub(r"<[^>]+>", "", t)
        t = re.sub(r"\s+([,.;:?!])", r"\1", re.sub(r"\s+", " ", t)).strip()
        out.append({"b": r["book"] - 1, "c": r["chapter"], "v": r["verse"], "t": t})
    out.sort(key=lambda x: (x["b"], x["c"], x["v"]))
    return out


def main():
    verses = load_kjv()
    json.dump(verses, open(OUT / "kjv_verses.json", "w"), ensure_ascii=False)
    part = OUT / "kjv_emb_partial.npy"
    emb = np.load(part) if part.exists() else np.zeros((0, DIM), dtype=np.float32)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchEmbedContents"
    headers = {"x-goog-api-key": api_key(), "Content-Type": "application/json"}
    print(f"{len(verses)} versetti, già fatti {len(emb)}")
    while len(emb) < len(verses):
        chunk = verses[len(emb): len(emb) + BATCH]
        body = {"requests": [{"model": f"models/{MODEL}", "content": {"parts": [{"text": v["t"]}]},
                              "taskType": "SEMANTIC_SIMILARITY", "outputDimensionality": DIM} for v in chunk]}
        for attempt in range(6):
            r = requests.post(url, headers=headers, json=body, timeout=60)
            if r.status_code == 200:
                break
            print("retry", r.status_code, r.text[:200])
            time.sleep(2 ** attempt * 5)
        r.raise_for_status()
        vecs = np.array([e["values"] for e in r.json()["embeddings"]], dtype=np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        emb = np.vstack([emb, vecs])
        np.save(part, emb)
        if len(emb) % 2000 < BATCH:
            print(len(emb), flush=True)
    np.save(OUT / "kjv_emb.npy", emb)
    part.unlink()
    print("fatto", emb.shape)


def refresh_changed():
    """Re-embed only the verses whose cleaned text changed since kjv_verses.json was written."""
    old = json.load(open(OUT / "kjv_verses.json"))
    new = load_kjv()
    assert [(v["b"], v["c"], v["v"]) for v in old] == [(v["b"], v["c"], v["v"]) for v in new]
    changed = [i for i, (a, b) in enumerate(zip(old, new)) if a["t"] != b["t"]]
    print("versetti cambiati:", len(changed), flush=True)
    emb = np.load(OUT / "kjv_emb.npy")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchEmbedContents"
    headers = {"x-goog-api-key": api_key(), "Content-Type": "application/json"}
    for s in range(0, len(changed), BATCH):
        idx = changed[s:s + BATCH]
        body = {"requests": [{"model": f"models/{MODEL}", "content": {"parts": [{"text": new[i]["t"]}]},
                              "taskType": "SEMANTIC_SIMILARITY", "outputDimensionality": DIM} for i in idx]}
        for attempt in range(6):
            r = requests.post(url, headers=headers, json=body, timeout=60)
            if r.status_code == 200:
                break
            time.sleep(2 ** attempt * 5)
        r.raise_for_status()
        vecs = np.array([e["values"] for e in r.json()["embeddings"]], dtype=np.float32)
        emb[idx] = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    np.save(OUT / "kjv_emb.npy", emb)
    json.dump(new, open(OUT / "kjv_verses.json", "w"), ensure_ascii=False)
    print("fatto")


if __name__ == "__main__":
    refresh_changed() if "--refresh" in sys.argv else main()
