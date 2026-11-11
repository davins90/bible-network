"""Inject out/network_tsk3.json, out/network_esv.json, out/esv_vs_tsk.json and notes.html into template.html -> atlante.html"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
load = lambda name: json.load(open(OUT / name)) if (OUT / name).exists() else None  # noqa: E731
data = {"tsk": load("network_tsk3.json"), "esv": load("network_esv.json"), "cmp": load("esv_vs_tsk.json")}
notes = (ROOT / "notes.html").read_text() if (ROOT / "notes.html").exists() else ""
page = (ROOT / "template.html").read_text()
page = page.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
page = page.replace("__NOTES__", json.dumps(notes, ensure_ascii=False).replace("</", "<\\/"))
(ROOT / "atlante.html").write_text(page)
print("atlante.html", round(len(page) / 1e6, 2), "MB", {k: v is not None for k, v in data.items()})
