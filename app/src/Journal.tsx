import { useMemo, useRef, useState } from "react";
import type { MapData, Meta } from "./data";
import { parseRef, rangeVerses, refLabel } from "./data";
import { exportState, importState, removeSaved, setNote, useReader } from "./store";
import { coverage, suggest } from "./recommend";

export function Journal({ meta, map, text, onOpen }: { meta: Meta; map: MapData; text: string[] | null; onOpen: (i: number) => void }) {
  const reader = useReader();
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const idx = (b: number, c: number) => map.chapters.findIndex((p) => p.b === b && p.c === c);

  const stats = useMemo(() => {
    const keys = Object.keys(reader.read).map((k) => k.split(".").map(Number) as [number, number]);
    const perBook = meta.books.map(() => 0);
    keys.forEach(([b]) => perBook[b]++);
    const ot = keys.filter(([b]) => b < 39).length;
    return { n: keys.length, ot, nt: keys.length - ot, perBook, booksStarted: perBook.filter((x) => x > 0).length, booksDone: perBook.filter((x, i) => x === meta.books[i].verses.length).length };
  }, [reader.read, meta]);

  const cov = useMemo(() => coverage(map, reader.read), [map, reader.read]);
  const next = useMemo(() => suggest(map, reader.read, (b) => meta.books[b].it), [map, reader.read, meta]);
  const byDate = useMemo(() => {
    const m = new Map<string, [number, number][]>();
    for (const [k, ds] of Object.entries(reader.read)) for (const d of ds) {
      const [b, c] = k.split(".").map(Number);
      m.set(d, [...(m.get(d) ?? []), [b, c]]);
    }
    return [...m.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [reader.read]);

  const download = async () => {
    const data = exportState();
    try {
      await navigator.clipboard.writeText(data);
      setMsg("Copia di sicurezza copiata negli appunti: incollala in una nota o in un file.");
    } catch {
      const blob = new Blob([data], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "bible-network-diario.json"; a.click();
      setMsg("Copia di sicurezza scaricata.");
    }
  };
  const upload = async (f: File) => {
    try { setMsg(importState(await f.text()) ? "Copia unita al diario: nulla è stato cancellato." : "Il file non è una copia del diario."); }
    catch { setMsg("Il file non è leggibile."); }
  };
  const fmtDate = (d: string) => new Date(d + "T12:00").toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "long", year: "numeric" });

  return (
    <div className="journal">
      <header>
        <div className="eyebrow">Il tuo diario</div>
        <h1>Dove sei arrivato</h1>
        <p className="muted small">Salvato su questo dispositivo. Presto potrai creare un account per ritrovarlo ovunque.</p>
      </header>

      <section className="stat-row">
        <div><b>{stats.n.toLocaleString("it-IT")}</b><span>capitoli letti su 1.189 ({(stats.n / 1189 * 100).toLocaleString("it-IT", { maximumFractionDigits: 1 })}%)</span></div>
        <div><b>{stats.ot} · {stats.nt}</b><span>Antico · Nuovo Testamento</span></div>
        <div><b>{stats.booksStarted} · {stats.booksDone}</b><span>libri iniziati · completati</span></div>
        <div><b>{reader.saved.length}</b><span>collegamenti salvati</span></div>
        <div><b>{Math.round(cov.centrality * 100)}%</b><span>della "centralità" della rete coperta (quota di PageRank dei capitoli letti)</span></div>
        <div><b>{cov.regions} su {cov.regionsTotal}</b><span>regioni della rete toccate · equilibrio {Math.round(cov.evenness * 100)}%</span></div>
      </section>

      <section>
        <div className="eyebrow">Cosa leggo dopo</div>
        <div className="next-list">
          {next.map((sg) => (
            <button key={sg.why} className="next-item" onClick={() => onOpen(sg.index)}>
              <b>{meta.books[map.chapters[sg.index].b].it} {map.chapters[sg.index].c}</b>
              <span className="muted small">{sg.detail}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <div className="eyebrow">Libro per libro</div>
        <div className="bookgrid">
          {meta.books.map((b, i) => {
            const tot = b.verses.length, n = stats.perBook[i];
            return (
              <button key={b.osis} className="bookcell" title={`${b.it}: ${n} di ${tot}`} onClick={() => onOpen(idx(i, 1))}>
                <span>{b.ab}</span>
                <span className="bar"><span className={i >= 39 ? "fill nt" : "fill ot"} style={{ width: `${(n / tot) * 100}%` }} /></span>
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <div className="eyebrow">Collegamenti salvati</div>
        {reader.saved.length === 0 && <p className="muted">Nessuno per ora. Apri un capitolo, tocca un rimando e premi "Salva il collegamento".</p>}
        <div className="saved">
          {[...reader.saved].sort((a, b) => b.created.localeCompare(a.created)).map((s) => {
            const f = parseRef(meta, s.from), t = parseRef(meta, s.to);
            return (
              <div className="saved-item" key={s.id}>
                <div className="saved-head">
                  <button className="link" onClick={() => onOpen(idx(f.from.b, f.from.c))}>{refLabel(meta, f)}</button>
                  <span className="muted">→</span>
                  <button className="link" onClick={() => onOpen(idx(t.from.b, t.from.c))}>{refLabel(meta, t)}</button>
                  <span className="muted small">{s.source.toUpperCase()}</span>
                  <button className="btn ghost small" onClick={() => removeSaved(s.id)} aria-label="Togli dal diario">Togli</button>
                </div>
                {text && <p className="quote">{rangeVerses(meta, text, f, 1)[0]?.text}</p>}
                {text && <p className="quote">{rangeVerses(meta, text, t, 2).map((x) => x.text).join(" ")}</p>}
                <textarea id={`note-${s.id}`} value={s.note} placeholder="Una nota: perché ti ha colpito?" onChange={(e) => setNote(s.id, e.target.value)} rows={2} />
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <div className="eyebrow">Letture</div>
        {byDate.length === 0 && <p className="muted">Quando segni un capitolo come letto compare qui, e sulla mappa si colora.</p>}
        <ul className="days">
          {byDate.map(([d, cs]) => (
            <li key={d}><span className="muted">{fmtDate(d)}</span>
              <span className="chips">{cs.map(([b, c]) => <button key={`${b}.${c}`} className="chip plain" onClick={() => onOpen(idx(b, c))}>{meta.books[b].it} {c}</button>)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="backup">
        <div className="eyebrow">Copia di sicurezza</div>
        <div className="actions">
          <button className="btn" onClick={download}>Esporta il diario</button>
          <button className="btn" onClick={() => fileRef.current?.click()}>Importa una copia</button>
          <input ref={fileRef} id="import-file" type="file" accept="application/json" hidden onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        </div>
        {msg && <p className="small" role="status">{msg}</p>}
      </section>
    </div>
  );
}
