import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { MapData, Meta } from "./data";
import { isNT } from "./data";
import { chapterKey, useReader } from "./store";

const Helix3D = lazy(() => import("./Helix3D"));
export type MapSource = "tsk" | "esv";
export type MapMode = "3d" | "2d";
const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

export function MapView({
  meta, map, selected, onOpen, source, setSource, mode, setMode,
}: {
  meta: Meta;
  map: MapData;
  selected: number | null;
  onOpen: (i: number) => void;
  source: MapSource;
  setSource: (s: MapSource) => void;
  mode: MapMode;
  setMode: (m: MapMode) => void;
}) {
  const reader = useReader();
  const readSet = useMemo(() => new Set(Object.keys(reader.read)), [reader.read]);
  const nRead = readSet.size;
  return (
    <div className="map">
      <div className="map-bar">
        <div className="seg" role="group" aria-label="Vista">
          <button aria-pressed={mode === "3d"} onClick={() => setMode("3d")}>Elica 3D</button>
          <button aria-pressed={mode === "2d"} onClick={() => setMode("2d")}>Canone 2D</button>
        </div>
        <div className="seg" role="group" aria-label="Rete">
          <button aria-pressed={source === "tsk"} onClick={() => setSource("tsk")}>TSK</button>
          <button aria-pressed={source === "esv"} onClick={() => setSource("esv")}>ESV</button>
        </div>
        <ChapterSearch meta={meta} map={map} onOpen={onOpen} />
      </div>
      <div className="map-canvas">
        {mode === "3d"
          ? <Suspense fallback={<p className="muted center">Carico l'elica…</p>}><Helix3D meta={meta} map={map} source={source} readSet={readSet} selected={selected} onOpen={onOpen} /></Suspense>
          : <Canon2D meta={meta} map={map} source={source} readSet={readSet} selected={selected} onOpen={onOpen} />}
      </div>
      <div className="legend">
        <span><i style={{ background: "var(--ot)" }} />Antico Testamento</span>
        <span><i style={{ background: "var(--nt)" }} />Nuovo Testamento</span>
        <span className="muted">colore pieno = già letto · {nRead.toLocaleString("it-IT")} {nRead === 1 ? "capitolo letto" : "capitoli letti"} su 1.189</span>
      </div>
      <p className="map-note muted">{mode === "3d"
        ? "L'altezza è l'ordine dei capitoli, da Genesi in basso ad Apocalisse in alto. Sul piano, capitoli vicini si richiamano. Trascina per ruotare."
        : "Da sinistra a destra i capitoli in ordine; in verticale la direzione principale della rete (in alto la storia d'Israele, in basso il Nuovo Testamento)."}</p>
    </div>
  );
}

/** The helix unrolled: x = canonical order, y = first diffusion-map axis. */
function Canon2D({ meta, map, source, readSet, selected, onOpen }: {
  meta: Meta; map: MapData; source: MapSource; readSet: Set<string>; selected: number | null; onOpen: (i: number) => void;
}) {
  const wrap = useRef<HTMLDivElement>(null), canvas = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [hover, setHover] = useState<number | null>(null);
  const [theme, setTheme] = useState(0);
  const P = map.chapters, si = source === "tsk" ? 0 : 1;
  useEffect(() => {
    const el = wrap.current!;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    const mq = matchMedia("(prefers-color-scheme: dark)"), bump = () => setTheme((t) => t + 1);
    mq.addEventListener("change", bump);
    return () => { ro.disconnect(); mq.removeEventListener("change", bump); };
  }, []);
  const pos = useMemo(() => {
    const { w, h } = size, padX = 12, padTop = 22, padBottom = 14;
    // sign chosen so the history of Israel is at the top and the New Testament at the bottom
    const ys = P.map((p) => p.hx[si][0]);
    const ntMean = ys.filter((_, i) => P[i].b >= 39).reduce((a, b) => a + b, 0) / P.filter((p) => p.b >= 39).length;
    const sign = ntMean > 0 ? -1 : 1;
    return P.map((p, i): [number, number] => [padX + (i / (P.length - 1)) * (w - 2 * padX), padTop + ((3 - sign * p.hx[si][0]) / 6) * (h - padTop - padBottom)]);
  }, [P, si, size]);
  useEffect(() => {
    const cv = canvas.current!, dpr = window.devicePixelRatio || 1, { w, h } = size;
    if (!w) return;
    cv.width = w * dpr; cv.height = h * dpr;
    const g = cv.getContext("2d")!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const ot = css("--ot"), nt = css("--nt"), ink = css("--ink"), muted = css("--muted"), rule = css("--rule");
    // book boundaries and a few labels
    g.font = `11px ${css("--f-ui")}`; g.textAlign = "left";
    let prev = -1;
    P.forEach((p, i) => {
      if (p.b !== prev) {
        prev = p.b;
        const x = pos[i][0];
        g.strokeStyle = rule; g.globalAlpha = p.b === 39 ? 1 : 0.5; g.lineWidth = p.b === 39 ? 1.5 : 1;
        g.beginPath(); g.moveTo(x, 16); g.lineTo(x, h); g.stroke(); g.globalAlpha = 1;
        if ([0, 18, 22, 39, 44, 65].includes(p.b)) { g.fillStyle = muted; g.fillText(meta.books[p.b].ab, x + 3, 12); }
      }
    });
    const focus = hover ?? selected;
    if (focus !== null) {
      g.strokeStyle = ink; g.lineWidth = 1; g.globalAlpha = 0.5;
      for (const [j] of P[focus].g.slice(0, 10)) { g.beginPath(); g.moveTo(...pos[focus]); g.lineTo(...pos[j]); g.stroke(); }
      g.globalAlpha = 1;
    }
    const r = w < 500 ? 2.4 : 3;
    const readIdx: number[] = [];
    for (let i = 0; i < P.length; i++) {
      if (readSet.has(chapterKey(P[i].b, P[i].c))) { readIdx.push(i); continue; }
      g.beginPath(); g.arc(pos[i][0], pos[i][1], r, 0, 7);
      g.fillStyle = isNT(P[i].b) ? nt : ot; g.globalAlpha = 0.25; g.fill();
    }
    g.globalAlpha = 1;
    // read chapters on top, larger, with a ring in the page colour
    const surface = css("--surface");
    for (const i of readIdx) {
      g.beginPath(); g.arc(pos[i][0], pos[i][1], r + 2.5, 0, 7);
      g.fillStyle = isNT(P[i].b) ? nt : ot; g.fill();
      g.lineWidth = 1.5; g.strokeStyle = surface; g.stroke();
    }
    if (focus !== null) { g.strokeStyle = ink; g.lineWidth = 2; g.beginPath(); g.arc(pos[focus][0], pos[focus][1], r + 4, 0, 7); g.stroke(); }
  }, [P, pos, size, readSet, hover, selected, theme, meta]);
  const nearest = (e: React.PointerEvent | React.MouseEvent) => {
    const rect = canvas.current!.getBoundingClientRect(), x = e.clientX - rect.left, y = e.clientY - rect.top;
    let best: number | null = null, bd = 18 * 18;
    pos.forEach(([px, py], i) => { const d = (px - x) ** 2 + (py - y) ** 2; if (d < bd) { bd = d; best = i; } });
    return best;
  };
  return (
    <div ref={wrap} className="fill">
      <canvas ref={canvas} aria-label="I capitoli in ordine canonico" onPointerMove={(e) => e.pointerType === "mouse" && setHover(nearest(e))} onPointerLeave={() => setHover(null)} onClick={(e) => { const i = nearest(e); if (i !== null) onOpen(i); }} />
      {hover !== null && <div className="tooltip" style={{ left: pos[hover][0], top: pos[hover][1] }}>{meta.books[P[hover].b].it} {P[hover].c}</div>}
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
