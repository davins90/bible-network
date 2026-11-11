// The reader's own data: chapters read and saved connections.
// Today it lives in this browser (localStorage). The storage sits behind `Backend` so that an
// account backend (Firebase Auth + Firestore, as in Eufemy) can be added later: on first login the
// local data is merged into the account with `mergeStates`.
import { useSyncExternalStore } from "react";

export interface SavedLink {
  id: string;
  from: string; // OSIS, e.g. "Rom.8.28"
  to: string; // OSIS, possibly a range "Gen.50.20-Gen.50.21"
  source: "esv" | "tsk";
  note: string;
  created: string; // ISO date-time
}
export interface ReaderState {
  version: 1;
  read: Record<string, string[]>; // chapter key "b.c" -> ISO dates (yyyy-mm-dd) it was marked as read
  saved: SavedLink[];
  updated: string;
}

export interface Backend {
  load(): ReaderState | null;
  save(state: ReaderState): void;
}

const KEY = "bible-network:v1";
const empty = (): ReaderState => ({ version: 1, read: {}, saved: [], updated: new Date().toISOString() });

export const localBackend: Backend = {
  load() {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? sanitize(JSON.parse(raw)) : null;
    } catch {
      return null;
    }
  },
  save(state) {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch {
      /* storage full or blocked: the session keeps working in memory */
    }
  },
};

export function sanitize(input: unknown): ReaderState | null {
  if (typeof input !== "object" || input === null) return null;
  const o = input as Partial<ReaderState>;
  const read: Record<string, string[]> = {};
  for (const [k, dates] of Object.entries(o.read ?? {})) {
    if (/^\d{1,2}\.\d{1,3}$/.test(k) && Array.isArray(dates)) {
      read[k] = dates.filter((d) => typeof d === "string" && /^\d{4}-\d{2}-\d{2}$/.test(d));
    }
  }
  const saved = (Array.isArray(o.saved) ? o.saved : []).filter(
    (s): s is SavedLink => !!s && typeof s.id === "string" && typeof s.from === "string" && typeof s.to === "string"
  );
  return { version: 1, read, saved, updated: typeof o.updated === "string" ? o.updated : new Date().toISOString() };
}

/** Union of two states: every reading date and every saved link survives; for a link saved on both, the newer note wins. */
export function mergeStates(a: ReaderState, b: ReaderState): ReaderState {
  const read: Record<string, string[]> = { ...a.read };
  for (const [k, ds] of Object.entries(b.read)) read[k] = [...new Set([...(read[k] ?? []), ...ds])].sort();
  const byId = new Map(a.saved.map((s) => [s.id, s]));
  for (const s of b.saved) {
    const old = byId.get(s.id);
    if (!old || s.created >= old.created) byId.set(s.id, s);
  }
  return { version: 1, read, saved: [...byId.values()], updated: new Date().toISOString() };
}

// ---------- tiny global store ----------
let backend: Backend = localBackend;
let state: ReaderState = backend.load() ?? empty();
const listeners = new Set<() => void>();
function set(next: ReaderState) {
  state = { ...next, updated: new Date().toISOString() };
  backend.save(state);
  listeners.forEach((l) => l());
}
export function useReader(): ReaderState {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => state
  );
}

export const todayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const chapterKey = (b: number, c: number) => `${b}.${c}`;

export function toggleReadToday(b: number, c: number) {
  const k = chapterKey(b, c), today = todayISO();
  const dates = state.read[k] ?? [];
  const next = dates.includes(today) ? dates.filter((d) => d !== today) : [...dates, today].sort();
  const read = { ...state.read };
  if (next.length) read[k] = next;
  else delete read[k];
  set({ ...state, read });
}

export const linkId = (from: string, to: string) => `${from}>${to}`;
export function toggleSaved(from: string, to: string, source: "esv" | "tsk") {
  const id = linkId(from, to);
  const saved = state.saved.some((s) => s.id === id)
    ? state.saved.filter((s) => s.id !== id)
    : [...state.saved, { id, from, to, source, note: "", created: new Date().toISOString() }];
  set({ ...state, saved });
}
export function setNote(id: string, note: string) {
  set({ ...state, saved: state.saved.map((s) => (s.id === id ? { ...s, note } : s)) });
}
export function removeSaved(id: string) {
  set({ ...state, saved: state.saved.filter((s) => s.id !== id) });
}
export function exportState(): string {
  return JSON.stringify(state, null, 2);
}
/** Merges a backup into the current data (nothing is lost on either side). */
export function importState(json: string): boolean {
  const incoming = sanitize(JSON.parse(json));
  if (!incoming) return false;
  set(mergeStates(state, incoming));
  return true;
}
/** For a future account backend: switch storage and merge what this browser already has. */
export function switchBackend(next: Backend) {
  const remote = next.load();
  backend = next;
  set(remote ? mergeStates(remote, state) : state);
}
