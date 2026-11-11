"""out/distributions.json + dist_template.html -> distribuzioni.html"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.load(open(ROOT / "out" / "distributions.json"))
page = (ROOT / "dist_template.html").read_text().replace("__DATA__", json.dumps(data, separators=(",", ":")))
(ROOT / "distribuzioni.html").write_text(page)
print("distribuzioni.html", round(len(page) / 1e3), "kB")
