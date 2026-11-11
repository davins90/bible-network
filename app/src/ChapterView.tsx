import { useEffect, useMemo, useState } from "react";
import type { BookRefs, Highlight, MapData, Meta } from "./data";
import { highlightsOf, isNT, loadBookRefs, parseRef, rangeVerses, refLabel, verseRefs, youVersionUrl } from "./data";
import { chapterKey, linkId, todayISO, toggleReadToday, toggleSaved, useReader } from "./store";
import { suggest } from "./recommend";

type Filter = "all" | "esv" | "tsk";
const WHY = { sequenza: "Il seguente", vicino: "Vicino a ciò che hai letto", esplora: "Esplora", inizio: "Per iniziare" } as const;

export function ChapterView({
  meta, map, index, text, onOpen,
}: {
  meta: Meta;
  map: MapData;
  index: number;
  text: string[] | null;
  onOpen: (i: number) => void;
}) {
  const p = map.chapters[index];
  const book = meta.books[p.b];
  const reader = useReader();
  const [refs, setRefs] = useState<BookRefs | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [crossOnly, setCrossOnly] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setRefs(null);
    loadBookRefs(p.b).then((r) => alive && setRefs(r));
    return () => { alive = false; };
  }, [p.b]);
  useEffect(() => { setOpen(null); window.scrollTo?.({ top: 0 }); }, [index]);

  const dates = reader.read[chapterKey(p.b, p.c)] ?? [];
  const readToday = dates.includes(todayISO());
  const savedIds = useMemo(() => new Set(reader.saved.map((s) => s.id)), [reader.saved]);
  const label = (i: number) => `${meta.books[map.chapters[i].b].it} ${map.chapters[i].c}`;
  const nVerses = book.verses[p.c - 1];
  const chRefs = refs?.[String(p.c)];
  const highlights = highlightsOf(chRefs);
  const suggestions = useMemo(() => suggest(map, reader.read, (b) => meta.books[b].it, index), [map, reader.read, meta, index]);
  const fromOsis = (v: number) => `${book.osis}.${p.c}.${v}`;
  const crosses = (ref: string) => isNT(parseRef(meta, ref).from.b) !== isNT(p.b);

  const rows = [];
  for (let v = 1; v <= nVerses; v++) {
    const vr = verseRefs(chRefs, v);
    let esv = filter !== "tsk" && vr ? vr.e.map(([ph, rs]) => [ph, rs.filter((r) => !crossOnly || crosses(r))] as [string, string[]]).filter(([, rs]) => rs.length) : [];
    let tsk = filter !== "esv" && vr ? vr.t.filter(([r]) => !crossOnly || crosses(r)) : [];
    if (!esv.length && !tsk.length) { esv = []; tsk = []; }
    rows.push({ v, esv, tsk });
  }
  const anyRefs = rows.some((r) => r.esv.length || r.tsk.length);

  const Chip = ({ from, to, source, votes, p: prob }: { from: string; to: string; source: "esv" | "tsk"; votes?: number; p?: number }) => {
    const key = `${from}|${to}`;
    const r = parseRef(meta, to);
    return (
      <button className={`chip ${source} to-${isNT(r.from.b) ? "nt" : "ot"}`} aria-expanded={open === key} onClick={() => setOpen(open === key ? null : key)} title={votes !== undefined ? `${votes} voti su OpenBible · probabilità che un curatore lo tenga ${Math.round((prob ?? 0) * 100)}%` : "Rimando ESV"}>
        {refLabel(meta, r)}
        {savedIds.has(linkId(from, to)) && <span aria-label="salvato"> ★</span>}
      </button>
    );
  };
  const Preview = ({ from, to, source }: { from: string; to: string; source: "esv" | "tsk" }) => {
    const r = parseRef(meta, to);
    const target = map.chapters.findIndex((c) => c.b === r.from.b && c.c === r.from.c);
    const saved = savedIds.has(linkId(from, to));
    return (
      <div className="preview">
        <div className="preview-head">
          <b>{meta.books[r.from.b].it} {r.from.c}:{r.from.v}{r.to.v !== r.from.v || r.to.c !== r.from.c ? `–${r.to.c !== r.from.c ? r.to.c + ":" : ""}${r.to.v}` : ""}</b>
          <span className="muted">{source === "esv" ? "rimando ESV" : "rimando TSK"}</span>
        </div>
        {text ? rangeVerses(meta, text, r).map((x) => <p key={x.label}><sup>{x.label}</sup> {x.text}</p>) : <p className="muted">Carico il testo…</p>}
        <div className="preview-actions">
          <button className={saved ? "btn on" : "btn"} onClick={() => toggleSaved(from, to, source)}>{saved ? "★ Salvato nel diario" : "☆ Salva il collegamento"}</button>
          <button className="btn ghost" onClick={() => onOpen(target)}>Vai a {meta.books[r.from.b].it} {r.from.c} →</button>
        </div>
      </div>
    );
  };

  const HighlightCard = ({ h }: { h: Highlight }) => {
    const f = parseRef(meta, h.from), t = parseRef(meta, h.to);
    const target = map.chapters.findIndex((c) => c.b === t.from.b && c.c === t.from.c);
    const saved = savedIds.has(linkId(h.from, h.to));
    return (
      <div className={`hl ${h.kind}`}>
        <div className="hl-head">
          <span className="hl-kind">{h.kind === "eco" ? "Eco" : "Citazione"}</span>
          <span className="muted small">{h.kind === "eco" ? "stesso tema con parole diverse" : "parole quasi uguali"}</span>
        </div>
        <div className="hl-pair">
          <div><b>{refLabel(meta, f)}</b>{text && <p>{rangeVerses(meta, text, f, 1)[0]?.text}</p>}</div>
          <div className="hl-arrow" aria-hidden="true">↓</div>
          <div><b>{refLabel(meta, t)}</b>{text && <p>{rangeVerses(meta, text, t, 2).map((x) => x.text).join(" ")}</p>}</div>
        </div>
        <p className="muted small">Probabilità che un curatore moderno lo tenga: {Math.round(h.p * 100)}%{h.esv ? " · presente anche nell'ESV" : ""} · {h.votes.toLocaleString("it-IT")} voti su OpenBible</p>
        <div className="preview-actions">
          <button className={saved ? "btn on" : "btn"} onClick={() => toggleSaved(h.from, h.to, h.esv ? "esv" : "tsk")}>{saved ? "★ Salvato" : "☆ Salva"}</button>
          <button className="btn ghost" onClick={() => onOpen(target)}>Vai a {meta.books[t.from.b].it} {t.from.c} →</button>
        </div>
      </div>
    );
  };

  return (
    <article className="chapter">
      <header className="chapter-head">
        <div className="eyebrow">{isNT(p.b) ? "Nuovo" : "Antico"} Testamento · {book.genre}</div>
        <div className="title-row">
          <button className="nav" aria-label="Capitolo precedente" disabled={index === 0} onClick={() => onOpen(index - 1)}>‹</button>
          <h1>{book.it} {p.c}</h1>
          <button className="nav" aria-label="Capitolo successivo" disabled={index === map.chapters.length - 1} onClick={() => onOpen(index + 1)}>›</button>
        </div>
        <div className="actions">
          <a className="btn" href={youVersionUrl(meta, p.b, p.c, "NR06")} target="_blank" rel="noopener noreferrer">Leggi in YouVersion · NR06</a>
          <a className="btn" href={youVersionUrl(meta, p.b, p.c, "NLT")} target="_blank" rel="noopener noreferrer">NLT</a>
          <button className={readToday ? "btn primary on" : "btn primary"} onClick={() => toggleReadToday(p.b, p.c)}>{readToday ? "✓ Letto oggi" : "Segna come letto"}</button>
        </div>
        {dates.length > 0 && <p className="muted small">Letto {dates.length === 1 ? "il" : "le volte:"} {dates.map((d) => new Date(d + "T12:00").toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" })).join(", ")}</p>}
        <dl className="facts">
          <div><dt>Rimandi TSK</dt><dd>{p.dt.toLocaleString("it-IT")}</dd></div>
          <div><dt>Rimandi ESV</dt><dd>{p.de.toLocaleString("it-IT")}</dd></div>
          <div><dt>Verso l'AT (TSK)</dt><dd>{Math.round(p.ot[0] * 100)}%</dd></div>
        </dl>
      </header>

      <section className="highlights" aria-label="Collegamenti in evidenza">
        <div className="eyebrow">In evidenza</div>
        {!refs && <p className="muted small">Carico…</p>}
        {refs && highlights.length === 0 && <p className="muted small">Nessun collegamento in evidenza per questo capitolo.</p>}
        {highlights.map((h) => <HighlightCard key={h.kind} h={h} />)}
      </section>

      <section className="neighbours">
        {([["Vicini nei rimandi TSK", p.nt], ["Vicini nei rimandi ESV", p.ne], ["Vicini nel testo", p.nx]] as [string, number[]][]).map(([t, ids]) => (
          <div key={t}>
            <div className="eyebrow">{t}</div>
            <div className="chips">{ids.map((i) => <button key={i} className="chip plain" onClick={() => onOpen(i)}>{label(i)}</button>)}</div>
          </div>
        ))}
      </section>

      <section className="verses">
        <div className="verses-bar">
          <div className="eyebrow">Collegamenti versetto per versetto</div>
          <div className="seg small" role="group" aria-label="Fonte">
            {([["all", "Tutti"], ["esv", "ESV"], ["tsk", "TSK"]] as [Filter, string][]).map(([f, l]) => (
              <button key={f} aria-pressed={filter === f} onClick={() => setFilter(f)}>{l}</button>
            ))}
          </div>
          <label className="check"><input id="cross-only" type="checkbox" checked={crossOnly} onChange={(e) => setCrossOnly(e.target.checked)} /> solo tra AT e NT</label>
          <span className="key small muted"><i className="dot ot" />verso l'AT <i className="dot nt" />verso il NT</span>
        </div>
        {!refs && <p className="muted">Carico i rimandi…</p>}
        {refs && !anyRefs && <p className="muted">Nessun rimando con questi filtri.</p>}
        {refs && rows.filter((r) => r.esv.length || r.tsk.length).map(({ v, esv, tsk }) => {
          const from = fromOsis(v);
          const openTo = open?.startsWith(from + "|") ? open.split("|")[1] : null;
          const openSource = openTo && esv.some(([, rs]) => rs.includes(openTo)) ? "esv" : "tsk";
          return (
            <div className="verse" key={v}>
              <div className="verse-text"><sup>{v}</sup> {text ? text[meta.verseOffset[index] + v - 1] : ""}</div>
              {esv.map(([ph, rs], k) => (
                <div className="group" key={k}>
                  <span className="phrase">{ph}</span>
                  {rs.map((r) => <Chip key={r} from={from} to={r} source="esv" />)}
                </div>
              ))}
              {tsk.length > 0 && (
                <div className="group">
                  <span className="phrase tsk-label">TSK</span>
                  {tsk.map(([r, n, pk]) => <Chip key={r} from={from} to={r} source="tsk" votes={n} p={pk} />)}
                </div>
              )}
              {openTo && <Preview from={from} to={openTo} source={openSource} />}
            </div>
          );
        })}
      </section>
      <section className="next" aria-label="Cosa leggo dopo">
        <div className="eyebrow">Cosa leggo dopo</div>
        <div className="next-list">
          {suggestions.map((sg) => (
            <button key={sg.why} className="next-item" onClick={() => onOpen(sg.index)}>
              <span className="next-why">{WHY[sg.why]}</span>
              <b>{meta.books[map.chapters[sg.index].b].it} {map.chapters[sg.index].c}</b>
              <span className="muted small">{sg.detail}</span>
            </button>
          ))}
        </div>
      </section>

      <footer className="attribution">
        Rimandi: ESV® cross-references © 2001 Crossway, dall'ESV API (<a href="https://www.esv.org" target="_blank" rel="noopener noreferrer">esv.org</a>) · Treasury of Scripture Knowledge via OpenBible.info (CC BY). Testo delle anteprime: Berean Standard Bible (dominio pubblico); KJV dove la BSB omette il versetto.
      </footer>
    </article>
  );
}
