# Bible Network: a che punto siamo

*Aggiornato il 29 ottobre 2026, notte. Lo storico completo della ricerca è in `info.md`.*

## In una riga
Un esploratore personale delle relazioni tra versetti: leggi un capitolo in NLT e vedi con cosa si collega nel resto della Bibbia.

**Pagina:** https://claude.ai/artifact/35LjnLL8T4eMRPyKH3JR5A (privata; `#c8` apre direttamente il capitolo 8)

## Cosa c'è
- **Romani 1–16**, con un selettore dei capitoli.
- **Mappa a barre** dei 66 libri (AT arancio, NT blu): quanti collegamenti partono dal capitolo verso ciascun libro. Un clic su un libro filtra la pagina su quel libro.
- **Grafo a due colonne versetti ↔ libri**: lo spessore delle linee indica il numero di rimandi; un clic su un versetto o un libro lo evidenzia.
- **Testo NLT** del capitolo con i titoli di sezione e il numero di collegamenti per versetto.
- **Pannello del versetto**: i rimandi ESV raggruppati per frase (per esempio su "The righteous shall live by" → Ab 2:4, Gal 3:11, Eb 10:38), ognuno con il testo NLT.
- **Interruttore OpenBible**: fino a 4 collegamenti in più per versetto (almeno 10 voti, esclusi quelli già nella ESV).

Numeri di Romani: 1.697 rimandi ESV e 1.740 passi con testo NLT, nessuno mancante.

## Fonti scelte (e perché)
| Cosa | Fonte | Note |
|---|---|---|
| Collegamenti principali | **ESV API** (Crossway), `include-crossrefs=true` | Rimandi editoriali curati, agganciati alla frase. Chiave in `.env` (`ESV_API_KEY`) |
| Collegamenti extra | **OpenBible.info** (`data/cross_references.txt`) | ~340k, derivati dal TSK, con voti degli utenti, CC BY |
| Testo | **NLT API** (Tyndale), `api.nlt.to` | Senza chiave, uso non commerciale |

Scartate: YouVersion Platform API (in italiano solo Diodati 1885, NLT vietata), Bible Gateway e Bibleserver (nessuna API). La Nuova Riveduta 2006 c'è su bolls.life, ma senza licenza chiara.

## File
- `explorer/build_data.py` + `explorer/books.py`: costruiscono i dati di un libro. Uso:
  `cd explorer && python3 build_data.py Romans 1-16 ../data/cross_references.txt romani_data.json` (circa 10 minuti per Romani).
- `explorer/template.html`: la pagina, con il segnaposto `__DATA__`.
- `explorer/romani1.html`: la pagina finale (template + dati), quella pubblicata.
- `explorer/romani_data.json`: i dati di Romani.
- `.env`: chiavi ESV e YouVersion (non condividere).

Per ripubblicare dopo una modifica: sostituire `__DATA__` nel template con il JSON, poi pubblicare `explorer/romani1.html` sullo stesso link.

## Prossimi passi
1. **Metriche sul grafo** (proposte, non ancora fatte):
   - quota AT per versetto e per capitolo, con un grafico della "forma" di Romani su 16 capitoli;
   - concentrazione (entropia o Herfindahl): versetti "citazione" contro versetti "tema";
   - osservato/atteso per libro con **shrinkage Gamma-Poisson**, per correggere i libri grandi come i Salmi;
   - somiglianza di Jaccard tra versetti, da confrontare con i titoli di sezione NLT.
2. **Secondo salto**: aprire un passo collegato (per esempio Abacuc 2:4) e vedere i suoi collegamenti.
3. **Altri libri**: basta lanciare `build_data.py` con un altro nome inglese (per esempio `Hebrews 1-13`).
4. Più avanti, sul grafo intero: PageRank, ponti tra AT e NT (betweenness), comunità tematiche.

## Da ricordare
- Non l'ho vista visualizzata: controllare la mappa e il grafo sul telefono.
- Le chiavi ESV e YouVersion sono state incollate in chat: rigenerarle se serve.
- Lezione della sessione: partire dalla cosa minima che serve allo scopo, non dall'architettura. Le idee "email quotidiana" e "app di lettura" sono state scartate.
