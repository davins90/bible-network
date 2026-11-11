// Static network data produced by bible_network/network/export_app.py, loaded once and cached.

export interface Book {
  osis: string;
  usfm: string;
  en: string;
  it: string;
  ab: string;
  genre: string;
  verses: number[]; // verse count per chapter
}
export interface Meta {
  books: Book[];
  genres: string[];
  verseOffset: number[]; // global index of verse 1 of each chapter, in map order
}
export interface MapChapter {
  b: number;
  c: number;
  tsk: [number, number];
  esv: [number, number];
  txt: [number, number];
  dt: number; // TSK degree
  de: number; // ESV degree
  ot: [number, number]; // share of references towards the OT (TSK, ESV)
  ct: number;
  ce: number;
  nt: number[]; // neighbour chapter indices: TSK map, ESV map, text map
  ne: number[];
  nx: number[];
  hx: [[number, number], [number, number]]; // helix plane (diffusion map axes 1-2): TSK, ESV
  pr: number; // PageRank in the TSK chapter graph (x number of chapters)
  g: [number, number][]; // strongest neighbours in the TSK chapter graph: [chapter index, references]
}
export interface Community {
  id: number;
  size: number;
  books: [string, number][];
}
export interface MapData {
  chapters: MapChapter[];
  communities: { tsk: Community[]; esv: Community[] };
  threads: { tsk: [number, number, number, number][]; esv: [number, number, number, number][] }; // [i, j, refs, observed/expected]
}
export interface Highlight {
  kind: "eco" | "citazione";
  from: string;
  to: string;
  p: number; // probability that a modern curator keeps it (model trained on the ESV)
  votes: number;
  sim: number;
  esv: boolean;
  cross: boolean;
}
export interface VerseRefs {
  e: [string, string[]][]; // ESV groups [phrase, refs]
  t: [string, number, number][]; // TSK [ref, votes, curator probability], best first
}
// chapter -> verse -> refs, plus the key "_h": highlighted connections of the chapter
export type ChapterRefs = Record<string, VerseRefs | Highlight[]>;
export type BookRefs = Record<string, ChapterRefs>;
export const verseRefs = (ch: ChapterRefs | undefined, v: number) => ch?.[String(v)] as VerseRefs | undefined;
export const highlightsOf = (ch: ChapterRefs | undefined) => (ch?._h as Highlight[] | undefined) ?? [];

const cache = new Map<string, Promise<unknown>>();
function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(
      path,
      fetch(`${import.meta.env.BASE_URL}data/${path}`).then((r) => {
        if (!r.ok) throw new Error(`${path}: ${r.status}`);
        return r.json();
      })
    );
  }
  return cache.get(path) as Promise<T>;
}

export const loadMeta = () => load<Meta>("meta.json");
export const loadMap = () => load<MapData>("map.json");
export const loadText = () => load<{ text: string[]; kjv: number[] }>("text.json");
export const loadBookRefs = (b: number) => load<BookRefs>(`refs/${String(b).padStart(2, "0")}.json`);

// ---------- references ----------
export interface VerseRef {
  b: number;
  c: number;
  v: number;
}
export interface RefRange {
  from: VerseRef;
  to: VerseRef;
}

export function parseRef(meta: Meta, ref: string): RefRange {
  const one = (s: string): VerseRef => {
    const [osis, c, v] = s.split(".");
    const b = meta.books.findIndex((x) => x.osis === osis);
    return { b, c: Number(c), v: Number(v) };
  };
  const [a, z] = ref.split("-");
  return { from: one(a), to: one(z ?? a) };
}

export function refLabel(meta: Meta, r: RefRange): string {
  const ab = meta.books[r.from.b].ab;
  const head = `${ab} ${r.from.c}:${r.from.v}`;
  if (r.to.c === r.from.c && r.to.v === r.from.v) return head;
  if (r.to.c === r.from.c) return `${head}–${r.to.v}`;
  return `${head}–${r.to.c}:${r.to.v}`;
}

export function chapterIndex(meta: Meta, b: number, c: number): number {
  let i = 0;
  for (let k = 0; k < b; k++) i += meta.books[k].verses.length;
  return i + c - 1;
}

export function globalVerse(meta: Meta, r: VerseRef): number {
  return meta.verseOffset[chapterIndex(meta, r.b, r.c)] + r.v - 1;
}

/** Up to `max` verses of a range, with their numbers. */
export function rangeVerses(meta: Meta, text: string[], r: RefRange, max = 3): { label: string; text: string }[] {
  const out: { label: string; text: string }[] = [];
  const b = r.from.b;
  let { c, v } = r.from;
  while (out.length < max) {
    out.push({ label: c === r.from.c ? String(v) : `${c}:${v}`, text: text[globalVerse(meta, { b, c, v })] ?? "" });
    if (c === r.to.c && v === r.to.v) break;
    if (v < meta.books[b].verses[c - 1]) v++;
    else if (c < meta.books[b].verses.length) {
      c++;
      v = 1;
    } else break;
  }
  return out;
}

export const isNT = (b: number) => b >= 39;

export function youVersionUrl(meta: Meta, b: number, c: number, version: "NR06" | "NLT"): string {
  const id = version === "NR06" ? 122 : 116;
  const lang = version === "NR06" ? "it" : "en";
  return `https://www.bible.com/${lang}/bible/${id}/${meta.books[b].usfm}.${c}.${version}`;
}
