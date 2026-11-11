"""out/helix.json, out/disk.json + templates -> elica.html, disco.html"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for tpl, data, out in (("helix_template.html", "helix.json", "elica.html"), ("disk_template.html", "disk.json", "disco.html")):
    d = json.load(open(ROOT / "out" / data))
    page = (ROOT / tpl).read_text().replace("__DATA__", json.dumps(d, separators=(",", ":")))
    (ROOT / out).write_text(page)
    print(out, round(len(page) / 1e6, 2), "MB")
