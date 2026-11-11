# Bible Network

La Bibbia come una rete di rimandi tra versetti. Due parti:

| Cartella | Cosa contiene |
|---|---|
| `app/` | La web app (Vite + React + TypeScript): mappa dei capitoli, scheda del capitolo, diario. Online su Cloud Run (`bible-network`, progetto `dani-lab-507314`, europe-west8). |
| `network/` | Analisi in Python: controlli sui dati, metriche di rete, embedding, confronto TSK/ESV, export dei dati per l'app. |
| `explorer/` | Il primo esploratore di Romani (ottobre 2026). |
| `data/` | `cross_references.txt` di OpenBible.info (CC BY). KJV e BSB si riscaricano (vedi sotto). |

## Deploy
Ogni push su `main` che tocca `app/` lancia `.github/workflows/deploy.yml`: lint e build, poi scarica i rimandi
dal bucket privato e fa `gcloud run deploy` con Workload Identity Federation (nessuna chiave salvata), infine
controlla che il sito risponda. Il servizio gira con l'account `bible-network-run`, senza permessi.
Il collegamento GitHub → Google Cloud si crea una volta con `infra/setup_github_deploy.sh`.

## Rigenerare i dati dell'app
```bash
cd network
python3 -m venv .venv && .venv/bin/pip install umap-learn networkx scipy scikit-learn pandas requests
# testi di dominio pubblico
mkdir -p ../data/kjv ../data/bsb
curl -s -o ../data/kjv/KJV.zip https://bolls.life/static/translations/KJV.zip && unzip -o ../data/kjv/KJV.zip -d ../data/kjv
curl -s -o ../data/bsb/BSB.zip https://bolls.life/static/translations/BSB.zip && unzip -o ../data/bsb/BSB.zip -d ../data/bsb
.venv/bin/python embed_kjv.py      # embedding Gemini (chiave in ../.env)
.venv/bin/python fetch_esv.py      # rimandi ESV (ESV_API_KEY in ../.env), circa 75 minuti
./run_all.sh                       # controlli, metriche, confronto, atlante
.venv/bin/python export_app.py     # -> ../app/public/data
cd .. && infra/sync_licensed_data.sh   # carica i rimandi nel bucket privato e rilancia il deploy
```

## Licenze dei dati
Rimandi ESV © 2001 Crossway, via ESV API (uso non commerciale; richiesta di conferma inviata a Crossway).
Treasury of Scripture Knowledge via OpenBible.info (CC BY). Testi BSB e KJV di dominio pubblico.

Il repository è pubblico, ma due cose **non** sono qui perché non vanno ridistribuite: i rimandi ESV
(`app/public/data/refs/`, che contengono anche quelli TSK) e il testo NLT dell'esploratore di Romani
(`explorer/romani_data.json`, `explorer/romani1.html`). Stanno nel bucket privato
`gs://dani-lab-507314-bible-network-data`; la pipeline li prende da lì al momento del deploy.
