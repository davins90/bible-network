#!/bin/bash
# Whole pipeline, from checks to page. Run from bible_network/network.
set -euo pipefail
PY=.venv/bin/python
$PY data_checks.py | sed -n 1,8p
for s in tsk3 esv; do
  $PY analyze.py $s 2>&1 | grep -E "^(tsk3|esv):|alpha|pagerank|'id'"
  $PY compare.py $s 2>&1 | grep -E "AUC|accordo|LINK|SIMILE"
done
$PY esv_vs_tsk.py
$PY build_page.py
