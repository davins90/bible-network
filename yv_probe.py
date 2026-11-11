"""Prova della YouVersion Platform API: quali Bibbie italiane sono accessibili con la nostra chiave.

Uso:
    export YVP_APP_KEY=...        # oppure una riga YVP_APP_KEY=... nel file .env accanto allo script
    python3 yv_probe.py           # elenca le versioni in italiano e prova a scaricare Romani 1
    python3 yv_probe.py 122       # scarica Romani 1 da una versione precisa (ID)
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.youversion.com/v1"
HERE = Path(__file__).parent


def load_key():
    key = os.environ.get("YVP_APP_KEY")
    env = HERE / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("YVP_APP_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        sys.exit("Manca la chiave: imposta YVP_APP_KEY o scrivila in bible_network/.env")
    return key


def get(path, key, params=None):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"X-YVP-App-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode(errors="replace")[:500]}


def list_bibles(key, all_available):
    out, token = [], None
    while True:
        params = {"language_ranges[]": ["it"], "page_size": 99, "all_available": str(all_available).lower()}
        if token:
            params["page_token"] = token
        res = get("/bibles", key, params)
        if "_error" in res:
            print(f"  errore {res['_error']}: {res['_body']}")
            return out
        out += res.get("data", [])
        token = res.get("next_page_token")
        if not token:
            return out


def show_passage(key, bible_id, ref="ROM.1"):
    res = get(f"/bibles/{bible_id}/passages/{ref}", key, {"format": "text"})
    if "_error" in res:
        print(f"  {ref} da {bible_id}: errore {res['_error']} {res['_body']}")
        return False
    text = res.get("content") or json.dumps(res, ensure_ascii=False)
    print(f"  {ref} da {bible_id}: OK, {len(text)} caratteri")
    print("  " + text[:400].replace("\n", " ") + " …")
    return True


def main():
    key = load_key()
    if len(sys.argv) > 1:
        show_passage(key, sys.argv[1])
        return
    for all_available in (False, True):
        label = "accessibili con la chiave" if not all_available else "tutte (anche non ancora licenziate)"
        bibles = list_bibles(key, all_available)
        print(f"\nBibbie in italiano, {label}: {len(bibles)}")
        for b in bibles:
            print(f"  {b.get('id'):>6}  {b.get('abbreviation', ''):<10} {b.get('title') or b.get('local_title', '')}")
    print("\nProva di lettura di Romani 1 dalle versioni accessibili:")
    for b in list_bibles(key, False):
        show_passage(key, b["id"])


if __name__ == "__main__":
    main()
