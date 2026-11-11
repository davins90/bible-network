# 🔄 Context Handoff — App lettura biblica con riferimenti incrociati — Session #1

**Data**: 2026-10-28
**Progetto**: App per la lettura quotidiana della Bibbia guidata da riferimenti incrociati *validati* (non generati), con lente teologica riformata/presbiteriana in linea con Tim Keller e Redeemer NYC.
**Stack/Ambiente**: da definire. Candidati: YouVersion Platform API/SDK (React, core TypeScript), NLT API (Tyndale), dataset locali (TSK, OpenBible.info, Riveduta 1927 in Parquet).

---

## 📌 Obiettivo della sessione

Valutare la sensatezza dell'idea e mappare fonti dati (riferimenti incrociati e testo biblico in inglese e italiano), licenze e API disponibili prima di iniziare lo sviluppo.

## 👤 Contesto utente rilevante

- Evangelico, protestante, presbiteriano; segue Tim Keller e le chiese Redeemer di New York.
- Vuole l'**NLT (New Living Translation)** come traduzione inglese di lettura, più un testo **italiano**.
- Ha ipotizzato di fare "embedding" con YouVersion (ambiguo: vettori semantici o lettore incorporato, vedi Note).

## ✅ Orientamenti emersi (proposti, non ancora confermati dall'utente)

- **"Validati" = fonti curate, non LLM.** I riferimenti generati da un LLM allucinano versetti e collegamenti plausibili ma falsi. Un LLM al massimo *spiega* un collegamento già presente in una fonte curata.
- **Grafo dei riferimenti indicizzato per indirizzo** (libro.capitolo.versetto, es. formato USFM `JHN.3.16`). È indipendente dalla lingua, quindi la traduzione diventa solo un layer di visualizzazione intercambiabile.
- **Embedding semantici al massimo per generare candidati**, da filtrare contro TSK/OpenBible. Due versetti simili negli embedding non sono per forza collegati teologicamente, e i collegamenti tipologici o di promessa/compimento spesso non si somigliano affatto.
- **Architettura proposta**: grafo in locale + testo da API (YouVersion e/o NLT API) + Riveduta 1927 locale come fallback italiano libero.
- **Differenziatore del prodotto**: le app di lettura quotidiana esistono già (YouVersion in testa). Il valore sta nel grafo curato con lente storico-redentiva, in italiano; il testo si prende da fuori.

## 📊 Analisi e risultati

### Fonti per i riferimenti incrociati
| Fonte | Dimensione/natura | Licenza | Note |
|---|---|---|---|
| Treasury of Scripture Knowledge (TSK) | ~500k riferimenti | Dominio pubblico | Standard storico, rumoroso: molti collegamenti lessicali basati sulla KJV |
| OpenBible.info cross-references | Derivato da TSK + voti utenti | CC-BY | I voti servono come segnale di rilevanza per filtro/ranking (validazione per consenso, non teologica) |
| Proof texts della Confessione di Westminster e dei Catechismi | Pochi, curati | Pubblico | Layer confessionale più coerente con la tradizione presbiteriana |
| LLM | — | — | **Escluso** come fonte primaria |

### Lente "Keller"
- Lettura cristocentrica e storico-redentiva (influenza di Edmund Clowney): ogni testo letto alla luce di creazione, caduta, redenzione e restaurazione.
- Idea: etichettare i collegamenti per **tipo**: tipologia, promessa/compimento, citazione NT dell'AT, parallelo tematico.
- Ossatura giornaliera candidata: **piano M'Cheyne** (raccomandato da Keller; commentato da D.A. Carson in *For the Love of God*). Alternativa: *The Songs of Jesus* (Keller), protetto da copyright: usabile solo la struttura, non i testi.

### Testo biblico — Inglese
- **NLT API (Tyndale)**, `https://api.nlt.to/`
  - Senza chiave: max 50 versetti/richiesta, 500 richieste/giorno, solo uso non commerciale.
  - Con chiave: max 500 versetti/richiesta, 5000 richieste/giorno; uso commerciale da motivare in fase di iscrizione.
  - Espone anche i piani di lettura e il testo del giorno per piano.
  - Restituisce **HTML** con tag `<verse_export orig="john_3_16" bk="john" ch="3" vn="16">`, da parsare.
- **ESV API** (Crossway): gratuita con limiti, non commerciale.
- **Attenzione**: l'NLT è una traduzione dinamica, quindi i collegamenti lessicali del TSK (basati sulla KJV) spesso non sono visibili nel testo NLT. Proposta: NLT per la lettura, traduzione letterale (KJV/ESV/BSB) come "vista del collegamento".

### Testo biblico — Italiano
L'NLT non esiste in italiano.

| Traduzione | Stato | Note |
|---|---|---|
| Riveduta Luzzi 1924/1927 | **Dominio pubblico** | Dataset Parquet su Hugging Face (`k-mktr/riveduta_bible_it`), ID tipo `Gen_1_1`. Scelta ovvia per l'MVP |
| Diodati 1607 | Dominio pubblico | Testo storico di riferimento del protestantesimo italiano, lingua troppo arcaica |
| Nuova Riveduta 2006 | Protetta (Società Biblica di Ginevra) | La più usata tra gli evangelici; nessuna API pubblica nota; serve permesso SBG per distribuire |
| Nuova Diodati 1991 | Protetta (La Buona Novella) | Letterale, chiese evangeliche più conservatrici |
| Parola del Signore / TILC | Protetta | La più vicina all'NLT come filosofia (dinamica), interconfessionale |
| CEI 2008 | Protetta | Cattolica, non pertinente |

### API multi-traduzione
- **YouVersion Platform**: chiave su `platform.youversion.com`. SDK React (`@youversion/platform-react-ui`, `-react-hooks`, `-core`), Flutter/Dart, React Native. Filtro versioni per lingua.
  - ⚠️ Le traduzioni disponibili **dipendono dalle licenze della singola app key**: altri sviluppatori hanno trovato NIV e CUV non licenziate via API pur presenti nell'app. Che la Nuova Riveduta sia nell'app YouVersion **non garantisce** l'accesso via API.
- Altre da verificare per l'italiano: **API.Bible** (American Bible Society; Tyndale è partner), **Bible Brain** (Faith Comes By Hearing), **Biblia.com API** (Faithlife), **fetch.bible** (1100+ traduzioni, USX/USFM/HTML/testo).

### Progetti e dataset simili (ricerca del 2026-10-28)
| Progetto | Cosa fa | Rilevanza / licenza |
|---|---|---|
| [Viz.Bible](https://viz.bible/bible-data/) (Robert Rouse) | Analisi e visualizzazione di dati biblici; [dati scaricabili](https://viz.bible/downloads); [remake interattivo della viz dei riferimenti](https://viz.bible/remaking-influential-cross-reference-visualization/) | Riferimento principale. Nota: i riferimenti di Torrey (base del TSK) sono soprattutto *tematici*, non citazioni (~11 per versetto), il che conferma il rumore del TSK |
| [Theographic](https://theographic.notion.site/About-Theographic-bb40cb93b1ac43bd98252abce225d530) | Grafo della conoscenza: persone, luoghi, eventi → versetti; API GraphQL | CC BY-SA 4.0 (share-alike: obbliga a ridistribuire con la stessa licenza) |
| [NuBerea/intertextuality](https://huggingface.co/datasets/NuBerea/intertextuality) | Collegamenti intertestuali, incluso l'AT nel NT, classificati come **citazione / allusione / eco** | Il più vicino alla tassonomia dei collegamenti. Accesso previo login; usa dati STEPBible (CC BY 4.0) |
| [Bible Quotation Database](https://lukeplant.me.uk/bible-quotation-database/) (Luke Plant) | Citazioni interne alla Bibbia, soprattutto NT→AT | Base per lo strato "citazione NT→AT" |
| [OT Quotations in the NT](https://b2find.eudat.eu/dataset/fa997dbd-0af0-5972-bad5-f9d94592217a) (Univ. Amburgo) | Citazioni dell'AT nel NT | CC BY 4.0 |
| [BibleViz](https://www.chrisharrison.net/index.php/Visualizations/BibleViz) (Chris Harrison, 2007) | Diagramma ad archi dei 63.779 riferimenti | Capostipite; ha ispirato il dataset OpenBible (~340k) |
| [CrossRefViz](https://github.com/lggcs/crossrefviz) | Diagramma ad archi interattivo sui dati OpenBible, con i voti | Codice riutilizzabile per esplorare il grafo |
| [Progetto di un corso UBC](https://www.cs.ubc.ca/~tmm/courses/547-25/projects2/haeji_yuri/update.pdf) | Esplorazione semantica della Bibbia | Panoramica di cosa esiste |

- STEPBible: non è stato trovato un file dedicato alle citazioni dell'AT nel NT nel loro repository ([STEPBible-Data](https://github.com/STEPBible/STEPBible-Data)); da verificare direttamente.
- Spazio libero individuato: nessun lettore quotidiano in italiano con collegamenti *tipizzati* e lente storico-redentiva.

### Obiettivo chiarito dall'utente (2026-10-28)
App per leggere la Bibbia con **collegamenti multipli tra libri e versetti, AT e NT**. **Uso personale (confermato).** Le licenze non sono più un vincolo. Punto di partenza indicato: lettura per libri, da Romani 1.

**Scopo dichiarato (tre obiettivi):** 1) leggere la Bibbia *di più* (abitudine); 2) scoprire collegamenti; 3) andare per argomenti.
- Il primo obiettivo è il principale: l'app deve ridurre l'attrito della lettura quotidiana, non aggiungere funzioni.
- Struttura proposta in tre modalità: **Leggi** (capitolo del giorno, breve), **Scopri** (un collegamento in evidenza al giorno), **Argomenti** (percorsi tematici, scelti ogni tanto, non ogni giorno).
- Fonti per gli argomenti: Nave's Topical Bible (dominio pubblico, ~20k voci), OpenBible.info Topical Bible (voti degli utenti, CC-BY), Catechismo Minore di Westminster come indice tematico confessionale (107 domande, con i versetti di supporto).

### Decisione proposta: per libri o per riferimenti?
**Lettura per libri come ossatura, riferimenti incrociati come strato laterale.** Motivi: il contesto letterario viene prima (lettura grammaticale-storica, poi *analogia Scripturae*); leggere solo per riferimenti frammenta il testo e porta al proof-texting; seguire i collegamenti in catena non finisce mai (TSK ~11 per versetto). Il piano M'Cheyne affianca già ogni giorno AT e NT. Per ogni capitolo: 2–3 collegamenti selezionati e tipizzati, con una "deviazione" facoltativa per approfondire.

### Mockup Romani 1 (2026-10-28)
Tre schermate da telefono (Leggi / Scopri / Argomenti) con testi veri: https://claude.ai/artifact/BwLg7m5RZUkYWjR9mwpza6
**Esito: la UX non è piaciuta.** Proposta successiva: niente app per ora, prima un "collegamento del giorno" via email. Mockup dell'email aggiunto sulla stessa tela (si apre per primo).

### Testo italiano: verifiche del 2026-10-28
- **Nuova Riveduta 2006 (NR06)**: completa; su YouVersion (bible.com, versione 122) e laparola.net, con testo coincidente sulle due fonti. Nessuna API pubblica. **Scelta per il mockup.**
- **NTVi, Nuova Traduzione Vivente** (Società Biblica di Ginevra): è l'equivalente italiano della NLT. NT uscito nel 2023; l'AT era in lavorazione e la data della Bibbia completa non è confermata. Si legge nell'app "Study Bible" di Ginevra. Testo non recuperato in formato utilizzabile.
- **"Nuova Riveduta 2020"**: non trovata. Esiste una "Riveduta 2020" (R2) di ADI-Media, che è un'altra revisione.
- Per uso personale l'email può *linkare* il capitolo su bible.com e citare solo i 2–3 versetti del collegamento.

### YouVersion Platform API: provata il 2026-10-28 (esito negativo per NR06/NLT)
- Chiave in `bible_network/.env` (`YVP_APP_KEY`), script di prova `yv_probe.py`. Base `https://api.youversion.com/v1`, header `X-YVP-App-Key`.
- Italiano: **solo Diodati 1885** (id 54), anche con `all_available=true`. La NR06 (id 122 sull'app) **non esiste nel catalogo API** (404).
- Inglese: 11 versioni libere (BSB 3034, WEB, ASV, LSV…). **NLT (116) → 403 Forbidden**.
- Le licenze disponibili sono solo "Public Domain/CC" più licenze "fast-track" di alcuni editori (Biblica, Lockman, SIL, Wycliffe…). Né Società Biblica di Ginevra né Tyndale ci sono.
- **Conclusione (superata, vedi sotto):** NLT dall'API Tyndale (`api.nlt.to`, già funzionante); NR06 dall'ebook ePub (Libraccio, 7,99 €, DRM da verificare).

### Decisione sul testo (2026-10-28)
**Capitolo intero = link all'app YouVersion** (`https://www.bible.com/it/bible/122/ROM.1.NR06`, si apre nell'app sul telefono; NLT = versione 116). Nell'email vanno solo i 2–3 versetti del collegamento del giorno in NR06 (da bolls.life). **NLT esclusa dall'email** (decisione del 2026-10-28).

### bolls.life: NR06 disponibile via API aperta (2026-10-28)
- `GET https://bolls.life/get-text/NR06/{libro}/{capitolo}/` → JSON `[{verse, text}]`, senza chiave. Libro numerato 1–66 (Romani = 45, Abacuc = 35). Testato: Romani 1 = 32 versetti.
- Ha anche **NLT**, ESV, BSB e decine di altre versioni inglesi (elenco: `https://bolls.life/static/bolls/app/views/languages.json`).
- Altre API aperte provate: getbible.net (solo Diodati 1649 e Riveduta 1927), fetch.bible (nessuna versione italiana).
- ⚠️ Romani 1:16–18 coincide con bible.com. **Abacuc 2:4 invece differisce** ("Egli è pieno d'orgoglio… ma il giusto vivrà per la sua fede" contro "Ecco, egli si è inorgoglito… ma il giusto per la sua fede vivrà" su bible.com/laparola). Bolls potrebbe avere un'altra revisione della NR in alcuni punti: da verificare a campione.
- Ripulire gli apostrofi con spazio (`com' è` → `com'è`).
- Non è chiaro se bolls abbia una licenza della Società Biblica di Ginevra: va bene per uso personale, scaricando un capitolo al giorno e tenendolo in cache. L'ebook resta il riferimento "pulito" se servisse.

## 🚧 Lavoro in corso

Nessun codice scritto. Fase di discovery completata a livello di fonti e licenze.

## ❌ Problemi aperti e bloccanti

- ~~Uso personale o distribuzione?~~ Risolto: uso personale (2026-10-28).
- **Cosa intende l'utente per "embedding" su YouVersion**: vettori semantici o incorporamento del lettore/SDK?
- **Disponibilità della Nuova Riveduta via YouVersion API**: da verificare con una chiave reale.
- **Definizione operativa di "validato"**: soglia di voti OpenBible? Solo TSK ∩ OpenBible? Layer Westminster prioritario?

## 📋 Prossimi passi

1. ~~Decidere il perimetro~~ Fatto: uso personale.
2. Ottenere la chiave YouVersion Platform e lanciare `getVersions('it*')` per vedere quali traduzioni italiane sono licenziate per la propria key; idem per NLT.
3. Richiedere la chiave NLT API (Tyndale).
4. Scaricare e normalizzare i dataset dei riferimenti (TSK + OpenBible con voti) in uno schema per indirizzo (USFM), più i proof texts di Westminster.
5. Definire la regola di "validazione" (es. soglia di voti, intersezione delle fonti) e la tassonomia dei collegamenti (tipologia, promessa/compimento, citazione NT→AT, parallelo tematico).
6. Scegliere il piano di lettura base (M'Cheyne) e costruire il motore "lettura del giorno → riferimenti filtrati".
7. MVP: Riveduta 1927 locale + NLT via API, affiancate.

## 🧩 Artefatti e riferimenti

```ts
// YouVersion Platform — core client (TypeScript)
import { ApiClient, BibleClient } from '@youversion/platform-core';
const apiClient = new ApiClient({ appKey: 'YOUR_APP_KEY' });
const bibleClient = new BibleClient(apiClient);
const versions = await bibleClient.getVersions('it*');   // verificare traduzioni italiane licenziate
const passage = await bibleClient.getPassage(111, 'JHN.3.16'); // ID versione + riferimento USFM
```

- NLT API: https://api.nlt.to/
- Pacchetto Dart NLT (riferimento per il formato di risposta): https://github.com/arielmagbanua/nlt_bible
- YouVersion React SDK: https://github.com/youversion/platform-sdk-react
- Esempio di app di lettura con piano giornaliero su YouVersion SDK: https://github.com/AndreiLucaci/bible
- Riveduta 1927 dataset: https://huggingface.co/datasets/k-mktr/riveduta_bible_it
- Panoramica API/dataset biblici: https://get.bible/bible-data-sets/
- API.Bible – Tyndale: https://api.bible/partners/tyndale
- OpenBible.info cross-references (CC-BY): https://www.openbible.info/labs/cross-references/

## 💡 Note e contesto aggiuntivo

- Il principio teologico di fondo è l'*analogia Scripturae*, «la Scrittura interpreta la Scrittura» (Confessione di Westminster 1.9): giustifica l'approccio basato sui riferimenti incrociati.
- Approccio esplicitamente scartato: LLM come generatore primario di riferimenti.
- Approccio da trattare con cautela: similarità semantica via embedding come criterio di collegamento (solo per generare candidati).
- L'utente preferisce rigore metodologico a soluzioni ad hoc e risposte dirette, senza over-validation.
---

## 🔄 Sessione #2 (2026-10-28 sera → 29/10): nuova direzione

Email e regole automatiche abbandonate (risultato giudicato piatto). **Nuova idea:** strumento che **mostra le relazioni tra i versetti**: apro Romani 1 e vedo con cosa si collega tutto il capitolo, poi navigo i collegamenti. Testo di lettura: **NLT** (API Tyndale).

### ESV API: rimandi editoriali ufficiali (verificata il 2026-10-29)
- Chiave in `.env` (`ESV_API_KEY`), header `Authorization: Token <chiave>`. Uso non commerciale: 5000 richieste/giorno, max 500 versetti per pagina, sigla "ESV" e link a esv.org.
- `GET https://api.esv.org/v3/passage/html/?q=Romans+1&include-crossrefs=true&include-footnotes=false&include-headings=false`
- Ogni rimando è `<a class="cf" href="Habakkuk 2:4; Galatians 3:11/" title="…">`, **agganciato alla frase precisa** del versetto. Gli ID versetto sono numerici (`v45001017` = libro 45, cap. 1, v. 17).
- **Romani 1: 144 rimandi curati su 27 versetti** (OpenBible: 729). Esempio, 1:17: "righteousness of God" → Rm 3:21–26, Rm 10:3, 2 Cor 5:21, Sal 98:2, Is 56:1; "The righteous shall live" → Ab 2:4, Gal 3:11, Eb 10:38.
- Architettura proposta: **ESV crossrefs = strato principale curato**; OpenBible = strato esteso filtrato per voti; NLT = testo da leggere.

### Esploratore di Romani 1 (2026-10-29)
Pagina funzionante con dati veri: https://claude.ai/artifact/35LjnLL8T4eMRPyKH3JR5A
- File in `explorer/`: `build_data.py` + `books.py` (costruiscono `romani1_data.json` da ESV, OpenBible e NLT), `template.html` (pagina con `__DATA__`), `romani1.html` (pagina finale).
- Contenuto: mappa a barre dei 66 libri (AT arancio / NT blu) con i collegamenti per libro, cliccabile per filtrare; testo NLT del capitolo; pannello del versetto con i rimandi ESV raggruppati per frase e il testo NLT dei passi; interruttore "Aggiungi OpenBible" (fino a 4 collegamenti extra per versetto, almeno 10 voti, esclusi quelli già nella ESV).
- Numeri: 144 rimandi ESV, 70 extra OpenBible, 199 passi con testo NLT.
- Prossimi passi possibili: secondo salto (aprire un passo collegato e vedere i suoi collegamenti), estendere ad altri capitoli.

### Aggiornamento del 2026-10-29: tutto Romani, grafo, capitoli
- Stessa pagina (stesso link), ora **Romani 1–16** con un selettore dei capitoli (link diretto: `#c8` per il capitolo 8).
- Aggiunto il **grafo a due colonne versetti ↔ libri**: lo spessore delle linee indica il numero di rimandi; un clic su un versetto o un libro lo evidenzia.
- `build_data.py <Libro> <da-a> ../data/cross_references.txt <out.json>` costruisce i dati per qualsiasi libro (chiave ESV da `.env`). Romani: 1.697 rimandi ESV, 1.740 passi con testo NLT, nessuno mancante.
- Prossimo passo proposto: **metriche** (quota AT per versetto e capitolo, concentrazione per entropia o Herfindahl, osservato/atteso per libro con shrinkage Gamma-Poisson, somiglianza di Jaccard tra versetti confrontata con i titoli di sezione NLT). Poi, sul grafo intero: PageRank, betweenness tra AT e NT, comunità.
