# Bible Network: a che punto siamo

*Aggiornato il 12 novembre 2026, notte. Metodi e risultati in dettaglio nel `README.md`; lo storico della ricerca
iniziale (fonti, licenze, ottobre 2026) è in `info.md`.*

## In una riga
Una web app per esplorare la Bibbia come rete di rimandi mentre si legge su YouVersion, più un laboratorio di analisi
statistica di due tradizioni di rimandi (TSK 1830 ed ESV 2001).

## Obiettivi (concordati l'11/11/2026)
1. **Continuità**: tornare ogni giorno a leggere e segnare.
2. **Comprensione**: trovare in meno di un minuto uno o due collegamenti che fanno vedere qualcosa di nuovo nel capitolo.
3. **Memoria**: diario di letture, collegamenti salvati e note.

Le analisi che non servono a questi obiettivi restano nel laboratorio (`network/`), non nell'app.

## Cosa c'è online
| Cosa | Dove |
|---|---|
| Web app | https://bible-network-615683241662.europe-west8.run.app (Cloud Run `bible-network`, progetto `dani-lab-507314`) |
| Repository (pubblico) | https://github.com/davins90/bible-network |
| Atlante dei rimandi | https://claude.ai/artifact/8rC7dkv9i25EGz9ZAjUvM8 |
| Come si distribuiscono i rimandi | https://claude.ai/artifact/9SdE8G977gwf3LXKfAeDGc |
| Elica del canone (prototipo 3D) | https://claude.ai/artifact/2P1mAQc1ekNoCWTxeEdD1E |
| Disco iperbolico (prototipo) | https://claude.ai/artifact/K9FfkfUFnRoAM3uBpszP17 |

**Web app**: mappa a elica (3D su PC, "canone 2D" su telefono) con i capitoli letti accesi; scheda del capitolo con
pulsanti YouVersion (NR06, NLT), "Segna come letto", due collegamenti **in evidenza** (eco e citazione, dal modello),
rimandi ESV e TSK versetto per versetto con anteprima BSB; **cosa leggo dopo** (seguente, personalized PageRank,
esplorazione); diario con statistiche, copertura della rete, collegamenti salvati con note, esporta/importa.
I dati del lettore stanno nel browser (`localStorage`) dietro un'interfaccia `Backend` pronta per gli account.

**Deploy**: push su `main` che tocca `app/` → GitHub Actions (lint, build, rimandi dal bucket privato, deploy con
Workload Identity, smoke test). Dopo `network/export_app.py`: `infra/sync_licensed_data.sh` (carica i rimandi nel
bucket **prima** del push e rilancia il deploy).

## Risultati principali (dettagli e numeri nel README)
- L'ESV è in gran parte un sottoinsieme curato del TSK (70% dei rimandi ESV è nel TSK, 20% del TSK è nell'ESV); i
  voti di OpenBible anticipano le scelte dei curatori (dal 7% al 36% per fascia di voti).
- Gradi: binomiale negativa (miscela Gamma–Poisson) per tutti i versetti; coda pesante ma **non** scale-free
  (lognormale o potenza troncata battono la legge di potenza).
- Il TSK annota l'AT "in avanti" verso il NT; l'ESV segue di più le citazioni del NT.
- Modello del collegamento in evidenza: gradient boosting, AUC 0,81 fuori campione per libro (0,67 con i soli voti),
  ben calibrato.

## Prossimi passi
1. **Stochastic block model bayesiano** sul grafo dei capitoli (poi eventualmente dei versetti):
   - `graph-tool` (Peixoto), versione *degree-corrected* e **gerarchica** (nested SBM); installazione con conda
     (`conda install -c conda-forge graph-tool`), in un ambiente separato dal `.venv`;
   - output: partizione con numero di gruppi scelto dai dati (lunghezza minima di descrizione), probabilità a
     posteriori di appartenenza per ogni capitolo, capitoli "di confine", gerarchia dei gruppi;
   - confronto con Louvain (5 gruppi TSK, 9 ESV) e con i generi; verificare gruppi definiti da **ruoli** (es.
     capitoli del NT che citano Salmi e Profeti allo stesso modo);
   - se regge, sostituire le comunità Louvain nell'app (suggerimento "Esplora", equilibrio nel diario);
   - **colorare l'elica per regione** (idea piaciuta a Daniele il 12/11): usare il livello alto della gerarchia
     (pochi gruppi, così i colori restano distinguibili) oppure evidenziare una regione alla volta sul resto in grigio;
     i capitoli "di confine" con un tratto diverso;
   - variante preferita da Daniele: **due tinte sfumate**, tinta = Testamento (arancio AT, blu NT), luminosità =
     regione. Massimo 3-4 gradazioni per tinta (livello alto della gerarchia SBM); regioni ordinate per posizione media
     nel canone, così la gradazione segue la salita dell'elica; una regione che attraversa i Testamenti mantiene la
     stessa luminosità nelle due tinte.
2. **Variante continua in PyMC** per confronto (l'SBM con gruppi discreti non è adatto a NUTS):
   - *mixed membership Poisson* (Ball, Karrer e Newman 2011), fattorizzazione Gamma–Poisson con NUTS o ADVI;
   - in alternativa *latent space model* (Hoff, Raftery e Handcock 2002): posizioni latenti con incertezza.
3. **Usare l'app qualche giorno** con letture vere, poi valutare collegamenti in evidenza e suggerimenti
   (quanti aperti, salvati, seguiti).
4. **Account** (Firebase Auth + Firestore, come Eufemy): `switchBackend` in `app/src/store.ts` unisce già i dati locali.
5. Aperti: controllo dell'errore Giona/Giovanni sul **testo originale del TSK**; risposta di **Crossway** sui rimandi ESV
   (se negativa: togliere l'ESV dai dati dell'app).

## Da fare a mano (Daniele)
- Inviare la mail a Crossway (bozza in Gmail, destinatario da trovare).
- Cancellare il repository privato `davins90/bible-network-old` (contiene ancora nella storia i dati con licenza).

## File
- `network/`: `data_checks.py`, `analyze.py`, `embed_kjv.py`, `compare.py`, `fetch_esv.py`, `esv_vs_tsk.py`,
  `distributions.py`, `prototypes.py`, `highlight_model.py`, `export_app.py`, `run_all.sh`; pagine con
  `build_page.py`, `build_dist.py`, `build_protos.py`. Ambiente: `network/.venv` (umap nel Python di sistema va in
  segfault per TensorFlow).
- `app/`: React + Vite; `src/recommend.ts` (PageRank personalizzato e copertura), `src/Helix3D.tsx` (three.js).
- Chiavi in `.env` (ESV, YouVersion, non nel repository).
