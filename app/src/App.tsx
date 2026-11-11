import { useCallback, useEffect, useState } from "react";
import type { MapData, Meta } from "./data";
import { loadMap, loadMeta, loadText } from "./data";
import { MapView, type MapMode, type MapSource } from "./MapView";
import { ChapterView } from "./ChapterView";
import { Journal } from "./Journal";

// Routes (hash): #/mappa, #/diario, #/c/ROM.8 (USFM book code + chapter)
type Route = { view: "map" } | { view: "journal" } | { view: "chapter"; index: number };

function parseHash(meta: Meta, map: MapData): Route {
  const h = location.hash.replace(/^#\/?/, "");
  if (h === "diario") return { view: "journal" };
  const m = h.match(/^c\/([0-9A-Z]{3})\.(\d+)$/);
  if (m) {
    const b = meta.books.findIndex((x) => x.usfm === m[1]);
    const index = map.chapters.findIndex((p) => p.b === b && p.c === Number(m[2]));
    if (index >= 0) return { view: "chapter", index };
  }
  return { view: "map" };
}

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [map, setMap] = useState<MapData | null>(null);
  const [text, setText] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  const [route, setRoute] = useState<Route>({ view: "map" });
  const [lastChapter, setLastChapter] = useState<number>(-1);
  const [source, setSource] = useState<MapSource>("tsk");
  const [mode, setMode] = useState<MapMode>(() => (window.innerWidth < 900 ? "2d" : "3d"));

  useEffect(() => {
    Promise.all([loadMeta(), loadMap()])
      .then(([m, mp]) => { setMeta(m); setMap(mp); })
      .catch(() => setError("Non riesco a caricare i dati. Controlla la connessione e ricarica la pagina."));
    loadText().then((t) => setText(t.text)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!meta || !map) return;
    const sync = () => {
      const r = parseHash(meta, map);
      setRoute(r);
      if (r.view === "chapter") setLastChapter(r.index);
    };
    sync();
    addEventListener("hashchange", sync);
    return () => removeEventListener("hashchange", sync);
  }, [meta, map]);

  const openChapter = useCallback((i: number) => {
    if (!meta || !map || i < 0) return;
    const p = map.chapters[i];
    location.hash = `/c/${meta.books[p.b].usfm}.${p.c}`;
  }, [meta, map]);

  if (error) return <div className="splash"><p>{error}</p></div>;
  if (!meta || !map) return <div className="splash"><h1>Bible Network</h1><p className="muted">Carico la mappa…</p></div>;

  const selected = route.view === "chapter" ? route.index : lastChapter >= 0 ? lastChapter : null;
  const panel = route.view === "journal"
    ? <Journal meta={meta} map={map} text={text} onOpen={openChapter} />
    : selected !== null
      ? <ChapterView meta={meta} map={map} index={selected} text={text} onOpen={openChapter} />
      : <Welcome />;

  return (
    <div className={`shell view-${route.view}`}>
      <header className="topbar">
        <a href="#/mappa" className="brand">Bible Network</a>
        <nav className="tabs" aria-label="Sezioni">
          <a href="#/mappa" aria-current={route.view === "map" ? "page" : undefined}>Mappa</a>
          <a href={selected !== null ? `#/c/${meta.books[map.chapters[selected].b].usfm}.${map.chapters[selected].c}` : "#/c/ROM.8"} aria-current={route.view === "chapter" ? "page" : undefined}>Capitolo</a>
          <a href="#/diario" aria-current={route.view === "journal" ? "page" : undefined}>Diario</a>
        </nav>
      </header>
      <main className="layout">
        <section className="pane-map" aria-label="Mappa">
          <MapView meta={meta} map={map} selected={selected} onOpen={openChapter} source={source} setSource={setSource} mode={mode} setMode={setMode} />
        </section>
        <section className="pane-side">{panel}</section>
      </main>
    </div>
  );
}

function Welcome() {
  return (
    <div className="welcome">
      <div className="eyebrow">Benvenuto</div>
      <h1>La Bibbia come una rete</h1>
      <p>La mappa è un'elica: dal basso in alto i capitoli in ordine, da Genesi ad Apocalisse. Capitoli che si richiamano (secondo il <i>Treasury of Scripture Knowledge</i> del 1830 o l'ESV del 2001) stanno sulla stessa verticale, anche se lontani nel tempo. Quelli che leggi si accendono.</p>
      <ol>
        <li>Tocca un capitolo, o cercalo.</li>
        <li>Leggilo su YouVersion con i pulsanti in alto.</li>
        <li>Segnalo come letto: sulla mappa si colora.</li>
        <li>Apri i rimandi e salva nel diario i collegamenti che ti colpiscono.</li>
      </ol>
      <p><a className="btn primary" href="#/c/ROM.8">Comincia da Romani 8</a></p>
    </div>
  );
}
