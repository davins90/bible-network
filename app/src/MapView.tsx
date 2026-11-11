import { useEffect, useMemo, useRef, useState } from "react";
import type { MapData, Meta } from "./data";
import { isNT } from "./data";
import { chapterKey, useReader } from "./store";

export type MapSource = "tsk" | "esv" | "txt";
const SOURCES: [MapSource, string][] = [
  ["tsk", "Rimandi TSK"],
  ["esv", "Rimandi ESV"],
  ["txt", "Testo"],
];

const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

export function MapView({
  meta, map, selected, onOpen, source, setSource,
}: {
  meta: Meta;
  map: MapData;
  selected: number | null;
  onOpen: (i: number) => void;
  source: MapSource;
  setSource: (s: MapSource) => void;
}) {
  const reader = useReader();
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [theme, setTheme] = useState(0);
  const P = map.chapters;
  const readSet = useMemo(() => new Set(Object.keys(reader.read)), [reader.read]);
  const nRead = readSet.size;

  useEffect(() => {
    const el = wrap.current!;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const bump = () => setTheme((t) => t + 1);
    mq.addEventListener("change", bump);
    return () => { ro.disconnect(); mq.removeEventListener("change", bump); };
  }, []);

  // scale: 2nd-98th percentile + 10% margin, isolated chapters pinned to the border
  const scale = useMemo(() => {
    const xs = P.map((p) => p[source][0]), ys = P.map((p) => p[source][1]);
    const q = (a: number[], t: number) => { const s = [...a].sort((m, n) => m - n); return s[Math.floor(t * (s.length - 1))]; };
    const sp = (lo: number, hi: number) => [lo - (hi - lo) * 0.1, hi + (hi - lo) * 0.1];
    const [x0, x1] = sp(q(xs, 0.02), q(xs, 0.98)), [y0, y1] = sp(q(ys, 0.02), q(ys, 0.98));
    const pad = 16, { w, h } = size;
    const s = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0));
    const ox = (w - s * (x1 - x0)) / 2, oy = (h - s * (y1 - y0)) / 2;
    const cl = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
    return (i: number): [number, number] => {
      const [x, y] = P[i][source];
      return [ox + (cl(x, x0, x1) - x0) * s, h - (oy + (cl(y, y0, y1) - y0) * s)];
    };
  }, [P, source, size]);

  useEffect(() => {
    const cv = canvas.current!, dpr = window.devicePixelRatio || 1, { w, h } = size;
    if (!w) return;
    cv.width = w * dpr; cv.height = h * dpr;
    const g = cv.getContext("2d")!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const r = w < 500 ? 3.2 : 3.8;
    const ot = css("--ot"), nt = css("--nt"), surface = css("--surface"), hi = css("--ink");
    const order = P.map((_, i) => i).sort((a, b) => Number(readSet.has(chapterKey(P[a].b, P[a].c))) - Number(readSet.has(chapterKey(P[b].b, P[b].c))));
    for (const i of order) {
      const p = P[i], [x, y] = scale(i);
      const read = readSet.has(chapterKey(p.b, p.c));
      g.beginPath(); g.arc(x, y, read ? r + 1 : r, 0, 7);
      g.fillStyle = isNT(p.b) ? nt : ot;
      g.globalAlpha = read ? 1 : 0.22; g.fill(); g.globalAlpha = 1;
      if (read) { g.lineWidth = 1; g.strokeStyle = surface; g.stroke(); }
    }
    const focus = hover ?? selected;
    if (focus !== null) {
      const nn = source === "tsk" ? P[focus].nt : source === "esv" ? P[focus].ne : P[focus].nx;
      const [fx, fy] = scale(focus);
      g.strokeStyle = hi; g.lineWidth = 1;
      for (const j of nn) {
        const [x, y] = scale(j);
        g.globalAlpha = 0.45; g.beginPath(); g.moveTo(fx, fy); g.lineTo(x, y); g.stroke(); g.globalAlpha = 1;
        g.beginPath(); g.arc(x, y, r + 1.8, 0, 7); g.stroke();
      }
      g.lineWidth = 2; g.beginPath(); g.arc(fx, fy, r + 4, 0, 7); g.stroke();
    }
  }, [P, scale, size, readSet, hover, selected, source, theme]);

  const nearest = (e: React.PointerEvent | React.MouseEvent) => {
    const rect = canvas.current!.getBoundingClientRect(), x = e.clientX - rect.left, y = e.clientY - rect.top;
    let best: number | null = null, bd = 20 * 20;
    P.forEach((_, i) => { const [px, py] = scale(i); const d = (px - x) ** 2 + (py - y) ** 2; if (d < bd) { bd = d; best = i; } });
    return best;
  };
  const tipAt = hover ?? null;
  const tipPos = tipAt !== null ? scale(tipAt) : null;
  const label = (i: number) => `${meta.books[P[i].b].it} ${P[i].c}`;

  return (
    <div className="map">
      <div className="map-bar">
        <div className="seg" role="group" aria-label="Mappa">
          {SOURCES.map(([s, l]) => (
            <button key={s} aria-pressed={source === s} onClick={() => setSource(s)}>{l}</button>
          ))}
        </div>
        <ChapterSearch meta={meta} map={map} onOpen={onOpen} />
      </div>
      <div className="map-canvas" ref={wrap}>
        <canvas
          ref={canvas}
          aria-label="Mappa dei capitoli"
          onPointerMove={(e) => e.pointerType === "mouse" && setHover(nearest(e))}
          onPointerLeave={() => setHover(null)}
          onClick={(e) => { const i = nearest(e); if (i !== null) onOpen(i); }}
        />
        {tipPos && tipAt !== null && (
          <div className="tooltip" style={{ left: tipPos[0], top: tipPos[1] }}>{label(tipAt)}</div>
        )}
      </div>
      <div className="legend">
        <span><i style={{ background: "var(--ot)" }} />Antico Testamento</span>
        <span><i style={{ background: "var(--nt)" }} />Nuovo Testamento</span>
        <span className="muted">colore pieno = già letto · {nRead.toLocaleString("it-IT")} {nRead === 1 ? "capitolo letto" : "capitoli letti"} su 1.189</span>
      </div>
    </div>
  );
}

export function ChapterSearch({ meta, map, onOpen }: { meta: Meta; map: MapData; onOpen: (i: number) => void }) {
  const [q, setQ] = useState("");
  const labels = useMemo(() => map.chapters.map((p) => `${meta.books[p.b].it} ${p.c}`), [meta, map]);
  const go = () => {
    const s = q.trim().toLowerCase();
    let i = labels.findIndex((l) => l.toLowerCase() === s);
    if (i < 0) {
      // "rm 8", "romani 8", "Rom 8": match the book by Italian name, abbreviation or OSIS prefix
      const m = s.match(/^(.+?)\s+(\d+)$/);
      if (m) {
        const b = meta.books.findIndex((x) => [x.it, x.ab, x.osis].some((n) => n.toLowerCase().startsWith(m[1])));
        if (b >= 0) i = map.chapters.findIndex((p) => p.b === b && p.c === Number(m[2]));
      }
    }
    if (i >= 0) { onOpen(i); setQ(""); }
  };
  return (
    <form className="search" onSubmit={(e) => { e.preventDefault(); go(); }}>
      <input id="chapter-search" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca: Romani 8, Is 53" list="chapter-list" aria-label="Cerca un capitolo" />
      <datalist id="chapter-list">{labels.map((l) => <option key={l} value={l} />)}</datalist>
    </form>
  );
}
