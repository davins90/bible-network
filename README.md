# Bible Network

La Bibbia come una rete di rimandi tra versetti: un'analisi statistica di due tradizioni di rimandi e una web app
per esplorarle mentre si legge.

**Web app:** https://bible-network-615683241662.europe-west8.run.app — si installa sul telefono; la lettura vera e
propria resta su YouVersion (pulsanti Nuova Riveduta 2006 e NLT su ogni capitolo).

| Cartella | Cosa contiene |
|---|---|
| `app/` | Web app (Vite + React + TypeScript): mappa a elica, scheda del capitolo con i collegamenti in evidenza, "cosa leggo dopo", diario. |
| `network/` | Analisi in Python: controlli sui dati, metriche di rete, distribuzioni, embedding, confronto TSK/ESV, modello dei collegamenti, prototipi di visualizzazione, export dei dati per l'app. |
| `explorer/` | Il primo esploratore di Romani (ottobre 2026). |
| `infra/` | Script una tantum per il deploy (Workload Identity) e per i dati con licenza. |
| `data/` | `cross_references.txt` di OpenBible.info (CC BY). KJV e BSB si riscaricano (vedi in fondo). |

**Obiettivi della web app**, in quest'ordine: *continuità* (tornare ogni giorno a leggere), *comprensione* (trovare
in meno di un minuto uno o due collegamenti che fanno vedere qualcosa di nuovo nel capitolo appena letto), *memoria*
(un diario di letture e scoperte). Le analisi che non servono a questi tre obiettivi restano nel laboratorio
(`network/`), non nell'app.

---

## Indice

1. [Dati e controlli](#1-dati-e-controlli)
2. [Due reti a confronto: TSK e ESV](#2-due-reti-a-confronto-tsk-e-esv)
3. [Come si distribuiscono i rimandi](#3-come-si-distribuiscono-i-rimandi)
4. [Struttura della rete](#4-struttura-della-rete)
5. [Rimandi e testo](#5-rimandi-e-testo)
6. [Visualizzare la rete](#6-visualizzare-la-rete)
7. [Il modello del collegamento in evidenza](#7-il-modello-del-collegamento-in-evidenza)
8. ["Cosa leggo dopo" e copertura](#8-cosa-leggo-dopo-e-copertura)
9. [Limiti noti](#9-limiti-noti)
10. [Riprodurre tutto](#10-riprodurre-tutto)

---

## 1. Dati e controlli

| Fonte | Cosa | Licenza |
|---|---|---|
| **TSK** via OpenBible.info | 344.799 rimandi del *Treasury of Scripture Knowledge* (circa 1830), con i voti degli utenti di OpenBible | CC BY |
| **ESV** via ESV API (Crossway) | 67.058 rimandi editoriali dell'English Standard Version (2001), scaricati capitolo per capitolo (solo i rimandi, non il testo) | uso non commerciale |
| **KJV** | Testo King James, base della versificazione (31.102 versetti) e degli embedding | dominio pubblico |
| **BSB** | Berean Standard Bible, per le anteprime nell'app (la KJV per i 16 versetti che la BSB omette) | dominio pubblico |
| **Embedding** | `gemini-embedding-001`, 768 dimensioni, un vettore per versetto KJV | — |

Salvo dove indicato, la "rete TSK" usa i rimandi con **almeno 3 voti** (214.366 rimandi su 28.684 versetti). Un
rimando verso un intervallo di versetti è attaccato al primo versetto dell'intervallo; dove conta (sovrapposizioni,
citazioni), l'intervallo viene espanso.

**Controlli deterministici** (`network/data_checks.py`, `network/fetch_esv.py`), mai scarti silenziosi:

- *Versificazione.* Il testo KJV usato ha esattamente 31.102 versetti, il numero canonico, dopo aver tolto gli
  apocrifi e le aggiunte greche di Ester (10:4–13 e capitoli 11–16). Le aggiunte di Ester 10 sono state trovate
  proprio perché l'ESV non le ha. Dal testo KJV sono state tolte anche le note a margine dei traduttori ("Heb. …",
  "or, …") presenti in 6.587 versetti del file sorgente.
- *Riferimenti.* Ogni rimando deve corrispondere a un libro noto e a versetti esistenti nella KJV. TSK: 5 righe con
  versetti inesistenti (intervalli da 2 a 3 Giovanni), escluse. ESV: i casi anomali sono registrati in
  `out/esv_problems.json` e risolti con regole esplicite (rimandi sui titoli dei Salmi assegnati al versetto 1;
  "Psalms 73–83" e "Obadiah" citati come blocco intero) oppure sono differenze reali di critica testuale (Mt 17:21,
  Gv 5:4… che l'ESV mette in nota).
- *Un errore sistematico di OpenBible.* In alcune righe l'abbreviazione del TSK "Jon" (Giona) è stata letta come
  Giovanni: per esempio Gn 30:1, "dammi figli, altrimenti muoio", rimanda a "Gv 4:3" e "Gv 4:8", mentre il senso è
  Giona 4:3 e 4:8, "è meglio per me morire che vivere". Regola: il capitolo:versetto di arrivo esiste anche in Giona
  e le parole rare in comune (pesate con l'IDF sui 31.102 versetti) puntano a Giona per almeno 5 unità di IDF
  (circa una parola che compare in meno dello 0,7% dei versetti) più che a Giovanni; la riga viene esclusa solo se
  anche gli embedding sono d'accordo. Oggi sono escluse 9 righe. È un controllo prudente: altri casi plausibili
  restano nella rete. Il controllo definitivo richiederebbe il testo originale del TSK.

---

## 2. Due reti a confronto: TSK e ESV

`network/esv_vs_tsk.py`. Un rimando di una rete "c'è" anche nell'altra quando parte dallo stesso versetto (o esiste
nella direzione opposta) e i versetti di arrivo si sovrappongono. È un confronto tra insiemi, senza modelli.

| | TSK (≥ 3 voti) | ESV |
|---|---|---|
| Rimandi | 214.366 | 67.058 |
| Versetti con almeno un rimando | 28.684 | 17.225 |
| Rimandi tra AT e NT | 21,7% | 11,6% |

- **L'ESV è in gran parte un sottoinsieme curato del TSK.** Il 70,4% dei rimandi ESV c'è già nel TSK (61,6% con
  almeno 3 voti); solo il 20,1% dei rimandi TSK con almeno 3 voti c'è nell'ESV.
- **I voti di OpenBible anticipano le scelte dei curatori.** Quota di rimandi TSK presenti anche nell'ESV per fascia
  di voti: negativi 3,9% · 0–2 7,2% · 3–5 15,3% · 6–10 24,3% · 11–20 27,5% · 21–50 32,2% · oltre 50 36,0%. La
  crescita è monotona: i voti contengono un segnale, ma anche una componente di popolarità (Ger 29:11 → Is 55:8–12,
  1.312 voti, non è nell'ESV).
- **Stessa struttura generale.** La correlazione di Spearman tra le due matrici libro × libro (sezione 4) è 0,78; in
  media un capitolo ha 5,1 vicini su 10 in comune nelle due mappe.
- **L'ESV collega la metà delle volte i due Testamenti** (11,6% contro 21,7%). È coerente con una lettura
  tipologica più ampia nella tradizione ottocentesca.

---

## 3. Come si distribuiscono i rimandi

`network/distributions.py`. Il **grado** di un versetto è il numero di versetti distinti a cui è collegato
(rimandi non orientati, coppie duplicate contate una volta).

### 3.1 Tutti i versetti: binomiale negativa

| | TSK | ESV |
|---|---|---|
| Media / mediana / 99° percentile / massimo | 11,98 / 8 / 64 / 177 | 3,28 / 2 / 18 / 46 |
| Varianza / media (indice di dispersione) | 14,9 | 5,4 |
| Versetti con 0 rimandi: osservati | 2.418 | 10.234 |
| … attesi da una Poisson | 0 | 1.173 |
| … attesi da una binomiale negativa | 2.490 | 9.666 |
| AIC Poisson / binomiale negativa | 481.232 / 219.206 | 211.701 / 143.195 |

Una Poisson (rimandi distribuiti a caso, ogni versetto con lo stesso tasso) è esclusa. La **binomiale negativa**
(NB2) descrive bene tutta la distribuzione, zeri compresi. La sua lettura più utile è come miscela Gamma–Poisson:

$$
K_i \mid \lambda_i \sim \text{Poisson}(\lambda_i), \qquad \lambda_i \sim \text{Gamma}\!\left(\tfrac{1}{\alpha},\ \tfrac{1}{\alpha\mu}\right)
\;\;\Rightarrow\;\; K_i \sim \text{NB}(\mu, \alpha), \quad \operatorname{Var}(K_i) = \mu + \alpha\mu^2 .
$$

Ogni versetto ha una sua "rimandabilità" $\lambda_i$. Con $\hat\alpha = 1{,}02$ (TSK) e $1{,}54$ (ESV) la deviazione
standard dei tassi è dell'ordine della loro media: i versetti sono molto eterogenei.

### 3.2 La coda: pesante, ma non una legge di potenza

Metodo di Clauset, Shalizi e Newman (2009) con la libreria `powerlaw`: stima di massima verosimiglianza della legge
di potenza discreta $P(k) \propto k^{-\gamma}$ per $k \ge k_{\min}$, con $k_{\min}$ scelto minimizzando la distanza
di Kolmogorov–Smirnov, poi test del rapporto di verosimiglianza normalizzato (Vuong) contro le alternative
($R < 0$: l'alternativa spiega meglio i dati).

| | TSK | ESV |
|---|---|---|
| $k_{\min}$ (quota di versetti nella coda) | 18 (24%) | 5 (41%) |
| $\hat\gamma$ | 2,99 ± 0,02 | 2,77 ± 0,02 |
| Legge di potenza contro lognormale | $R = -14{,}2$, $p \approx 10^{-46}$ | $R = -21{,}2$, $p \approx 10^{-100}$ |
| Legge di potenza contro potenza troncata | $R = -14{,}8$ | $R = -21{,}5$ |
| Lognormale contro potenza troncata | $R = -2{,}55$, $p = 0{,}01$ | $R = -0{,}66$, $p = 0{,}51$ |

Su scala log-log i dati piegano verso il basso: la rete **non è scale-free**. Ci sono versetti molto più collegati
della media, ma non hub senza limite come nelle reti generate da *preferential attachment*. Questo è coerente con
un'opera curata a mano e con Broido e Clauset (2019), secondo cui le reti davvero scale-free sono rare.

### 3.3 Da cosa dipende il numero di rimandi: regressione binomiale negativa

$$
\log \mathbb{E}[K_i] = \beta_0 + \beta_1 \log(\text{parole}_i) + \textstyle\sum_g \gamma_g \,\mathbb{1}[\text{genere}_i = g] + \delta_1\,\text{pos}_i + \delta_2\,\text{pos}_i^2
$$

con `pos` la posizione relativa nel libro (0 = inizio, 1 = fine) e il Pentateuco come riferimento. Rapporti di
tassi (IRR) con intervallo di confidenza al 95%:

| | TSK | ESV |
|---|---|---|
| Versetto lungo il doppio | × 1,70 | × 1,63 |
| Lettere di Paolo | 4,11 (3,93–4,30) | 2,17 (2,03–2,31) |
| Lettere generali e Apocalisse | 4,17 (3,95–4,40) | 1,87 (1,72–2,02) |
| Poetici e sapienziali | 2,59 (2,50–2,68) | 1,21 (1,15–1,28) |
| Vangeli e Atti | 2,22 (2,14–2,30) | 1,34 (1,28–1,41) |
| Profeti minori | 2,12 (2,01–2,25) | 1,11 (1,02–1,21) |
| Profeti maggiori | 1,66 (1,61–1,72) | 0,91 (0,86–0,96) |
| Libri storici | 0,69 (0,67–0,71) | 0,69 (0,66–0,73) |
| Pseudo-$R^2$ | 0,05 | 0,02 |

- I rimandi crescono meno che in proporzione alla lunghezza: elasticità circa 0,75.
- Il TSK "gonfia" soprattutto i testi dottrinali e devozionali (Paolo, lettere, Salmi); l'ESV molto meno.
- L'inizio di un libro è la parte più collegata (a metà libro circa × 0,83, minimo intorno al 73% del libro).
- Lo pseudo-$R^2$ è basso: lunghezza, genere e posizione spiegano poco. Il grosso della variabilità dipende dal
  contenuto del singolo versetto.

### 3.4 Concentrazione

Il 10% dei versetti più collegati raccoglie il 36% dei rimandi nel TSK e il 40% nell'ESV (indici di Gini 0,53 e
0,62). Gli hub sono diversi: nel TSK versetti teologici e molto amati (Is 9:6 con 177, 1 Pt 2:9, Is 41:10); nell'ESV
le formule dell'alleanza ripetute (Gn 26:3, Gn 12:7, Es 6:7), perché i curatori collegano tra loro tutte le
ripetizioni.

### 3.5 Distanza e direzione

| | TSK | ESV |
|---|---|---|
| Distanza mediana lungo il canone | 2.672 versetti | 1.207 versetti |
| Nello stesso capitolo | 4,4% | 3,3% |
| Nello stesso libro, altro capitolo | 19,6% | 32,4% |
| Nello stesso Testamento, altro libro | 54,2% | 52,8% |
| Tra Antico e Nuovo Testamento | 21,7% | 11,6% |
| Scritti su un versetto dell'AT, verso il NT | 25.632 | 3.211 |
| Scritti su un versetto del NT, verso l'AT | 20.966 | 4.580 |

I rimandi attraversano la Bibbia: pochissimi restano nello stesso capitolo. La differenza più interessante è la
direzione: il TSK annota l'Antico Testamento **in avanti**, verso il compimento (più rimandi AT → NT che NT → AT),
mentre l'ESV segue soprattutto le citazioni che il Nuovo fa dell'Antico.

---

## 4. Struttura della rete

`network/analyze.py`.

### 4.1 Quali libri si parlano più del previsto: Gamma–Poisson con empirical Bayes

Per ogni coppia di libri $(i, j)$, $O_{ij}$ rimandi osservati e un atteso dal **configuration model** (ogni libro
tiene il suo totale di rimandi $k_i$ ma li distribuisce a caso): $E_{ij} = k_i k_j / 2m$. Il rapporto grezzo
$O/E$ è instabile per i libri piccoli, quindi:

$$
O_{ij} \sim \text{Poisson}(\lambda_{ij} E_{ij}), \qquad \lambda_{ij} \sim \text{Gamma}(\alpha, \alpha), \qquad
\hat\lambda_{ij} = \mathbb{E}[\lambda_{ij} \mid O_{ij}] = \frac{O_{ij} + \alpha}{E_{ij} + \alpha}.
$$

$\alpha$ è stimato massimizzando la verosimiglianza marginale (binomiale negativa) sulle 2.145 coppie: empirical
Bayes. $\hat\alpha = 1{,}15$ (TSK) e $0{,}46$ (ESV). In cima ci sono libri "gemelli": Esdra–Neemia (14,6×),
1 Timoteo–Tito, 2 Pietro–Giuda, 1–2 Giovanni. Sono passi paralleli più che temi.

### 4.2 Comunità e centralità

- **Comunità** (Louvain sul grafo dei capitoli). TSK: 5 gruppi (Legge e storici; Profeti; Salmi e sapienziali;
  tutto il NT tranne l'Apocalisse; un gruppo apocalittico con Apocalisse, Daniele, parti di Ezechiele). ESV: 9 gruppi,
  più fini (Paolo con Ebrei si separa dai Vangeli, Genesi a sé, il Cantico isolato). Con il TSK a ≥ 10 voti il NT si
  spezza in tre. Louvain non fornisce un'incertezza; il passo naturale è uno stochastic block model bayesiano.
- **PageRank** sui versetti. TSK: Is 9:6, 1 Pt 2:9, Is 41:10. Alzando la soglia a 10 voti salgono versetti molto
  amati oggi (Gc 5:16, 1 Pt 5:8, Rm 8:28): i voti spostano la rete verso la devozione contemporanea, un motivo per
  non usare soglie alte. ESV: dominano i versetti "formula" ("fece ciò che è male agli occhi del Signore", 1 Re 11:6).

---

## 5. Rimandi e testo

`network/embed_kjv.py`, `network/compare.py`. Ogni versetto KJV diventa un vettore (`gemini-embedding-001`);
somiglianza = coseno.

| | TSK | ESV |
|---|---|---|
| AUC: una coppia con rimando è più simile di una a caso | 0,936 | 0,971 |
| Somiglianza mediana: con rimando / a caso | 0,808 / 0,728 | 0,829 / 0,728 |
| … rimandi nello stesso Testamento / tra AT e NT | 0,814 / 0,790 | 0,831 / 0,813 |
| Vicini comuni per capitolo tra mappa dei rimandi e mappa del testo | 3,9 su 10 | 3,5 su 10 |

Il caso sarebbe 0,08 su 10. I rimandi seguono molto il testo, ma meno quando attraversano i Testamenti: è lo spazio
della tipologia, che le parole da sole non vedono. L'ESV è più "testuale" del TSK. Le coppie collegate ma con testo
molto diverso sono state anche un controllo di qualità: è così che è emerso l'errore Giona/Giovanni.

---

## 6. Visualizzare la rete

### 6.1 Perché non UMAP o t-SNE come mappa principale

t-SNE e UMAP sono *neighbor embedding*: costruiscono un grafo dei vicini nello spazio originale e cercano una
disposizione in 2D con attrazione tra vicini e repulsione tra tutti. La letteratura è concorde su cosa se ne può
leggere: i vicinati locali sì; gli assi, le dimensioni e le distanze tra gruppi no (Wattenberg et al. 2016;
Kobak e Berens 2019; Chari e Pachter 2023). Le differenze tra i due dipendono soprattutto dall'inizializzazione
(Kobak e Linderman 2021) e i due stanno su un unico spettro attrazione–repulsione (Böhm, Berens e Kobak 2022). La
prima mappa dell'atlante (NetMF ≈ DeepWalk + UMAP) è quindi servita per esplorare, ma non è la mappa dell'app.

### 6.2 Elica del canone (la mappa dell'app)

Assi con un significato:

- **altezza** = ordine canonico dei capitoli (Genesi in basso, Apocalisse in alto);
- **piano** = *diffusion map* del grafo dei capitoli, cioè gli autovettori $\psi_2, \psi_3$ della matrice di
  transizione $P = D^{-1}A$ moltiplicati per i loro autovalori, standardizzati e limitati a ±3 deviazioni standard.
  Si calcolano dagli autovettori di $D^{-1/2} A D^{-1/2}$ (autovalori TSK 0,63 e 0,56; ESV 0,88 e 0,83).

Nel TSK il primo asse separa il Nuovo Testamento (Atti, Giovanni, Marco) dalla storia d'Israele (Cronache, Numeri,
Giosuè); il secondo la Legge e il culto (Levitico, Esodo) dai Profeti (Ezechiele, Isaia, Geremia). I fili sono le
coppie di capitoli con il rapporto osservati/attesi più alto (almeno 6 rimandi). Nell'app c'è anche la versione 2D
"srotolata" (ordine canonico × primo asse), più leggibile sul telefono.

### 6.3 Disco iperbolico (prototipo)

Le reti con code pesanti hanno una geometria iperbolica latente (Krioukov et al. 2010). **LaBNE** (Alanis-Lobato,
Mier e Andrade-Navarro 2016):

- angolo $\theta_i$ dalle *Laplacian eigenmaps* in 2D, poi **aggiustamento equidistante** (Muscoloni et al. 2017):
  si mantiene l'ordine degli angoli ma li si distribuisce in modo uniforme;
- raggio dal rango per grado, modello popolarità–somiglianza: $r_i = 2\,[\beta \ln i + (1-\beta)\ln N]$. Con
  $\beta = 1/(\gamma - 1)$ anche l'hub principale finisce a metà del raggio massimo e il centro resta vuoto; con
  $\beta = 1$ gli hub vanno al centro e la qualità resta la stessa, quindi si usa $\beta = 1$;
- disco di Poincaré di curvatura $-1/s^2$: $\rho_i = \tanh(r_i / 2s)$. Cambiare curvatura lascia lo spazio
  esattamente iperbolico, quindi le trasformazioni di Möbius che portano un versetto al centro sono isometrie.

Qualità, come AUC della distanza iperbolica nel distinguere coppie collegate da coppie a caso: TSK 0,80 → 0,84 con
l'aggiustamento equidistante, ESV 0,90 → 0,92. Resta un prototipo (`network/disco.html`): utile per esplorare, non
serve agli obiettivi dell'app.

---

## 7. Il modello del collegamento in evidenza

`network/highlight_model.py`. **Scopo:** in cima a ogni capitolo mostrare uno o due rimandi che valga davvero la pena
aprire. Romani 8 ha 1.790 rimandi TSK e i voti da soli premiano la popolarità.

**Formulazione.** L'ESV fa da "giudice esterno": per ogni rimando TSK, qual è la probabilità che un curatore
moderno lo terrebbe?

- unità: 344.740 righe TSK (tutti i voti, esclusa la quarantena);
- etichetta $y = 1$ se il rimando è anche nell'ESV (stessa definizione della sezione 2): 15,2%;
- variabili: $\log(1+\text{voti})$ e voti negativi; somiglianza del testo (massimo coseno sui primi 5 versetti
  d'arrivo); $\log$ osservati/attesi tra i due capitoli (configuration model, con +0,5 di smoothing); $\log(1+\text{grado})$
  dei due versetti; $\log$ distanza lungo il canone; attraversa AT e NT; stesso libro; $\log$ lunghezza dell'intervallo.

**Modelli confrontati**: logistica con i soli voti (riferimento); logistica con penalità L2 (stima MAP con prior
gaussiane) ed effetti fissi per libro; gradient boosting (`HistGradientBoostingClassifier`, 300 alberi, learning
rate 0,08).

**Validazione**: `GroupKFold` a 5 gruppi **per libro di partenza**. Il modello viene sempre valutato su libri che
non ha visto, così non impara "Romani 8" e lo ritrova in verifica.

| Modello | AUC | Log-loss | Brier |
|---|---|---|---|
| Solo voti | 0,673 | 0,407 | 0,124 |
| Logistica | 0,786 | 0,360 | 0,112 |
| **Gradient boosting** (scelto) | **0,808** | **0,341** | **0,105** |

**Calibrazione** del boosting fuori campione, per decili di probabilità prevista (prevista → osservata):
0,008 → 0,009 · 0,038 → 0,039 · 0,110 → 0,115 · 0,214 → 0,216 · 0,323 → 0,314 · 0,546 → 0,517. Le probabilità si
possono leggere come tali; il decile più alto è leggermente ottimista.

**Cosa ha imparato** (logistica, rapporto di quote per una deviazione standard): somiglianza del testo × 1,93; voti
× 1,58; osservati/attesi tra capitoli × 1,49; distanza × 1,32; stesso libro × 1,26; attraversa AT e NT × 0,86. I
curatori moderni preferiscono collegamenti testuali e strutturali e sono più prudenti con quelli tipologici. Tra gli
effetti per libro, il TSK sui Salmi è il meno ripreso dall'ESV.

**Dal modello all'app.** Due categorie, definite sulla somiglianza dei rimandi tenuti dall'ESV:

- **citazione**: somiglianza ≥ 0,879 (il 20% più alto), cioè parole quasi uguali;
- **eco**: somiglianza ≤ 0,830 (il 40% più basso), cioè stesso tema con parole diverse.

In ogni categoria si sceglie il rimando del capitolo con il punteggio più alto:
$\text{punteggio} = \hat p + 0{,}25\cdot\mathbb{1}[\text{nell'ESV}] + 0{,}15\cdot\mathbb{1}[\text{AT}\leftrightarrow\text{NT}]$.
I due bonus sono una regola editoriale scelta a mano, non stimata: privilegiano ciò che l'ESV conferma e ciò che
attraversa i Testamenti, coerentemente con gli obiettivi di lettura. Esempi: Romani 8, eco Rm 8:28 → Gn 50:20 e
citazione Rm 8:36 → Sal 44:22; Isaia 53, eco Is 53:9 → Mc 15:43 e citazione Is 53:1 → Gv 12:38. Nell'app anche gli
altri rimandi TSK di ogni versetto sono ordinati per $\hat p$.

---

## 8. "Cosa leggo dopo" e copertura

`app/src/recommend.ts`, calcolato nel browser. Non è un modello addestrato ma un algoritmo su grafo.

**Grafo**: i 1.189 capitoli, con peso pari al numero di rimandi TSK tra i loro versetti; per ogni capitolo i 40 vicini
più forti.

**Personalized PageRank** (passeggiata casuale con ripartenza):

$$
r = (1-a)\,s + a\,P^{\top} r, \qquad a = 0{,}85, \qquad
s_i \propto \mathbb{1}[i \text{ letto}]\cdot 2^{-\Delta t_i / 30\ \text{giorni}},
$$

con $P$ la matrice dei pesi normalizzata per riga e $\Delta t_i$ il tempo dall'ultima lettura del capitolo $i$
(emivita 30 giorni). Si risolve con 40 iterazioni del metodo delle potenze; i nodi senza archi uscenti ridistribuiscono
la loro massa su $s$. $r_j$ è quanto spesso un lettore che "abita" le tue letture recenti passa dal capitolo $j$, e
conta anche i cammini indiretti.

**Tre suggerimenti**: (1) il seguente non letto nell'ordine canonico; (2) il capitolo non letto con $r$ massimo;
(3) *esplorazione*: tra le comunità TSK quella con la minore quota di PageRank globale già letta, e al suo interno il
capitolo non letto più centrale. Il punto 3 bilancia lo sfruttamento del punto 2.

**Copertura nel diario**: *centralità coperta* = $\sum_{i\,\text{letto}} \text{PR}_i / \sum_i \text{PR}_i$ (leggere
un capitolo centrale conta di più); *equilibrio* = entropia della distribuzione delle letture tra le comunità divisa
per $\ln K$ (1 = letture distribuite uniformemente su tutte le zone).

Non c'è un'AUC da calcolare: si potrà valutare solo con l'uso, per esempio la quota di suggerimenti seguiti.

---

## 9. Limiti noti

- La rete descrive la **tradizione dei rimandi** (un'opera ottocentesca più i voti di oggi; una scelta editoriale
  del 2001), non una proprietà "oggettiva" del testo.
- I rimandi verso un intervallo sono attaccati al primo versetto nelle metriche di grado; questo sottostima la
  centralità dei versetti interni alle citazioni lunghe.
- Il modello del collegamento in evidenza imita i curatori dell'ESV, non una lente teologica: un collegamento
  tipologico importante che l'ESV non ha riceve una probabilità bassa. Le probabilità mostrate nell'app vengono dal
  modello addestrato su tutti i dati, quindi per i rimandi visti in addestramento sono un po' ottimiste; le metriche
  della tabella sono quelle fuori campione.
- Comunità di Louvain senza misura di incertezza.
- Gli embedding vedono parole e senso letterale (in inglese, KJV), non la teologia.

### Prossimi passi

1. **Stochastic block model bayesiano** al posto di Louvain. Modello generativo *degree-corrected*
   (Karrer e Newman 2011):

   $$A_{ij} \sim \text{Poisson}\!\left(\theta_i\,\theta_j\,\omega_{z_i z_j}\right),$$

   con $z_i$ il gruppo latente del capitolo $i$, $\omega$ la matrice di intensità tra gruppi e $\theta_i$ la
   propensione del capitolo (necessaria visti i gradi molto eterogenei, sezione 3). Inferenza bayesiana sulla
   partizione con MCMC merge-split e numero di gruppi scelto dalla lunghezza minima di descrizione, in versione
   gerarchica (*nested SBM*, Peixoto), con `graph-tool`. Rispetto a Louvain dà l'incertezza (probabilità a posteriori
   di appartenenza, capitoli "di confine"), non trova struttura dove non c'è e riconosce gruppi definiti dal ruolo
   (con chi si collegano) e non solo dalla densità interna.
2. **Varianti continue in PyMC**, per confronto: i gruppi discreti dell'SBM non si prestano a NUTS, ma una
   *mixed membership* Gamma–Poisson (Ball, Karrer e Newman 2011) o un *latent space model* (Hoff, Raftery e
   Handcock 2002) sì.
3. **Valutare l'app con l'uso** (collegamenti in evidenza aperti e salvati, suggerimenti seguiti), poi gli account
   (Firebase Auth + Firestore).
4. Controllo dell'errore Giona/Giovanni sul testo originale del TSK.

---

## 10. Riprodurre tutto

```bash
cd network
python3 -m venv .venv && .venv/bin/pip install umap-learn networkx scipy scikit-learn pandas requests powerlaw statsmodels
# testi di dominio pubblico
mkdir -p ../data/kjv ../data/bsb
curl -s -o ../data/kjv/KJV.zip https://bolls.life/static/translations/KJV.zip && unzip -o ../data/kjv/KJV.zip -d ../data/kjv
curl -s -o ../data/bsb/BSB.zip https://bolls.life/static/translations/BSB.zip && unzip -o ../data/bsb/BSB.zip -d ../data/bsb
.venv/bin/python embed_kjv.py            # embedding Gemini (chiave in ../.env)
.venv/bin/python fetch_esv.py            # rimandi ESV (ESV_API_KEY in ../.env), circa 75 minuti
./run_all.sh                             # controlli, metriche, testo, confronto TSK/ESV, atlante
.venv/bin/python distributions.py        # sezione 3
.venv/bin/python prototypes.py           # elica e disco (sezione 6)
.venv/bin/python highlight_model.py      # sezione 7
.venv/bin/python export_app.py           # -> ../app/public/data
cd .. && infra/sync_licensed_data.sh     # carica i rimandi nel bucket privato e rilancia il deploy
```

Pagine di analisi generate in locale (non nel repository): `network/atlante.html` (`build_page.py`),
`network/distribuzioni.html` (`build_dist.py`), `network/elica.html` e `network/disco.html` (`build_protos.py`).

## Deploy

Ogni push su `main` che tocca `app/` lancia `.github/workflows/deploy.yml`: lint e build, poi scarica i rimandi dal
bucket privato e fa `gcloud run deploy` con Workload Identity Federation (nessuna chiave salvata), infine controlla
che il sito risponda. Il servizio gira con l'account `bible-network-run`, senza permessi. Il collegamento
GitHub → Google Cloud si crea una volta con `infra/setup_github_deploy.sh`.

## Licenze dei dati

Rimandi ESV © 2001 Crossway, via ESV API (uso non commerciale; richiesta di conferma inviata a Crossway).
Treasury of Scripture Knowledge via OpenBible.info (CC BY). Testi BSB e KJV di dominio pubblico.

Il repository è pubblico, ma due cose **non** sono qui perché non vanno ridistribuite: i rimandi ESV
(`app/public/data/refs/`, che contengono anche quelli TSK e i collegamenti in evidenza) e il testo NLT
dell'esploratore di Romani (`explorer/romani_data.json`, `explorer/romani1.html`). Stanno nel bucket privato
`gs://dani-lab-507314-bible-network-data`; la pipeline li prende da lì al momento del deploy.

## Riferimenti

Alanis-Lobato, Mier, Andrade-Navarro (2016), *Efficient embedding of complex networks to hyperbolic space via their
Laplacian*, Sci. Rep. · Böhm, Berens, Kobak (2022), *Attraction-repulsion spectrum in neighbor embeddings*, JMLR ·
Broido, Clauset (2019), *Scale-free networks are rare*, Nat. Commun. · Chari, Pachter (2023), *The specious art of
single-cell genomics*, PLoS Comput. Biol. · Clauset, Shalizi, Newman (2009), *Power-law distributions in empirical
data*, SIAM Review · Coifman, Lafon (2006), *Diffusion maps*, ACHA · Harrison, Römhild (2007), visualizzazione dei
rimandi biblici · Kobak, Berens (2019), *The art of using t-SNE for single-cell transcriptomics*, Nat. Commun. ·
Kobak, Linderman (2021), *Initialization is critical for preserving global data structure in both t-SNE and UMAP*,
Nat. Biotechnol. · Krioukov et al. (2010), *Hyperbolic geometry of complex networks*, Phys. Rev. E · McInnes, Healy,
Melville (2018), *UMAP* · Muscoloni et al. (2017), *Machine learning meets complex networks via coalescent embedding
in the hyperbolic space*, Nat. Commun. · Qiu et al. (2018), *Network embedding as matrix factorization* (NetMF),
WSDM · van der Maaten, Hinton (2008), *t-SNE*, JMLR · Wattenberg, Viégas, Johnson (2016), *How to use t-SNE
effectively*, Distill.
