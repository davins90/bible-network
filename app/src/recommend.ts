// "What to read next": a personalized PageRank (random walk with restart) on the chapter graph,
// restarting from the chapters the reader has read, weighted by how recently.
import type { MapData } from "./data";

const DAY = 86400000;

/** Restart distribution: read chapters weighted by recency (half-life 30 days). */
function restartVector(map: MapData, read: Record<string, string[]>, now = Date.now()): Float64Array | null {
  const s = new Float64Array(map.chapters.length);
  map.chapters.forEach((p, i) => {
    const dates = read[`${p.b}.${p.c}`];
    if (!dates?.length) return;
    const last = Math.max(...dates.map((d) => new Date(d + "T12:00").getTime()));
    s[i] = Math.pow(0.5, Math.max(0, now - last) / DAY / 30);
  });
  const tot = s.reduce((a, b) => a + b, 0);
  if (!tot) return null;
  return s.map((v) => v / tot);
}

/** r = (1 - a) s + a P^T r, P = row-normalized chapter graph. 40 power iterations are plenty for 1,189 nodes. */
export function personalizedPageRank(map: MapData, s: Float64Array, a = 0.85, iters = 40): Float64Array {
  const n = map.chapters.length;
  const out = map.chapters.map((p) => p.g.reduce((t, [, w]) => t + w, 0));
  let r = Float64Array.from(s);
  for (let k = 0; k < iters; k++) {
    const next = new Float64Array(n);
    let dangling = 0;
    for (let i = 0; i < n; i++) {
      if (!out[i]) { dangling += r[i]; continue; }
      for (const [j, w] of map.chapters[i].g) next[j] += (a * r[i] * w) / out[i];
    }
    for (let i = 0; i < n; i++) next[i] += (1 - a) * s[i] + a * dangling * s[i];
    r = next;
  }
  return r;
}

export interface Suggestion {
  index: number;
  why: "sequenza" | "vicino" | "esplora" | "inizio";
  detail: string;
}

/** Three suggestions: the next chapter in sequence, the closest unread chapter in the network, and a new region. */
export function suggest(map: MapData, read: Record<string, string[]>, bookName: (b: number) => string, current?: number): Suggestion[] {
  const n = map.chapters.length;
  const isRead = (i: number) => !!read[`${map.chapters[i].b}.${map.chapters[i].c}`]?.length;
  const out: Suggestion[] = [];
  const s = restartVector(map, read);

  // 1. sequence: after the current chapter, or after the most recently read one
  let last = current ?? -1;
  if (last < 0 && s) {
    let best = -1;
    map.chapters.forEach((p, i) => {
      const d = read[`${p.b}.${p.c}`];
      if (d?.length) {
        const t = Math.max(...d.map((x) => new Date(x + "T12:00").getTime()));
        if (t > best) { best = t; last = i; }
      }
    });
  }
  if (last >= 0) {
    let i = last + 1;
    while (i < n && isRead(i)) i++;
    if (i < n) out.push({ index: i, why: "sequenza", detail: `continua ${bookName(map.chapters[i].b)}` });
  }

  if (!s) {
    // nothing read yet: the most central chapters of the network
    const order = [...map.chapters.keys()].sort((x, y) => map.chapters[y].pr - map.chapters[x].pr);
    for (const i of order) if (!out.some((o) => o.index === i)) { out.push({ index: i, why: "inizio", detail: "uno dei capitoli più collegati di tutta la Bibbia" }); break; }
    return out;
  }

  // 2. near what you read: highest personalized PageRank among unread chapters
  const r = personalizedPageRank(map, s);
  let bestNear = -1;
  for (let i = 0; i < n; i++) if (!isRead(i) && !out.some((o) => o.index === i) && (bestNear < 0 || r[i] > r[bestNear])) bestNear = i;
  if (bestNear >= 0) out.push({ index: bestNear, why: "vicino", detail: "il più collegato a ciò che hai letto" });

  // 3. explore: the community you have covered least, its most central unread chapter
  const comm = new Map<number, { tot: number; read: number }>();
  map.chapters.forEach((p, i) => {
    const c = comm.get(p.ct) ?? { tot: 0, read: 0 };
    c.tot += p.pr; if (isRead(i)) c.read += p.pr;
    comm.set(p.ct, c);
  });
  const least = [...comm.entries()].sort((x, y) => x[1].read / x[1].tot - y[1].read / y[1].tot)[0]?.[0];
  let bestFar = -1;
  map.chapters.forEach((p, i) => {
    if (p.ct === least && !isRead(i) && !out.some((o) => o.index === i) && (bestFar < 0 || p.pr > map.chapters[bestFar].pr)) bestFar = i;
  });
  if (bestFar >= 0) out.push({ index: bestFar, why: "esplora", detail: "una zona della rete che non hai ancora visitato" });
  return out;
}

/** Coverage of the network: share of PageRank mass read, and evenness across communities (normalized entropy). */
export function coverage(map: MapData, read: Record<string, string[]>) {
  let prRead = 0, prTot = 0;
  const per = new Map<number, number>();
  map.chapters.forEach((p) => {
    prTot += p.pr;
    if (read[`${p.b}.${p.c}`]?.length) { prRead += p.pr; per.set(p.ct, (per.get(p.ct) ?? 0) + 1); }
  });
  const k = map.communities.tsk.length, tot = [...per.values()].reduce((a, b) => a + b, 0);
  const H = tot ? -[...per.values()].reduce((h, c) => h + (c / tot) * Math.log(c / tot), 0) : 0;
  return { centrality: prRead / prTot, evenness: k > 1 ? H / Math.log(k) : 0, regions: per.size, regionsTotal: k };
}
