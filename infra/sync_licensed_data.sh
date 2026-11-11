#!/bin/bash
# Uploads the licensed data (not in the public repo) to the private bucket, then redeploys the app.
# Run from bible_network/ after network/export_app.py.
set -euo pipefail
B=gs://dani-lab-507314-bible-network-data
test $(ls app/public/data/refs/*.json | wc -l) -eq 66
gcloud storage rsync app/public/data/refs $B/app-data/refs --recursive --delete-unmatched-destination-objects
for f in explorer/romani_data.json explorer/romani1.html; do
  [ -f "$f" ] && gcloud storage cp "$f" $B/explorer/
done
gh workflow run deploy.yml --repo davins90/bible-network
echo "Dati caricati, deploy avviato: gh run watch --repo davins90/bible-network"
