// The helix of the canon in 3D (loaded on demand: three.js is only downloaded when this view opens).
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { MapData, Meta } from "./data";
import type { MapSource } from "./MapView";
import { chapterKey } from "./store";

const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const HEIGHT = 70, SPREAD = 9;

export default function Helix3D({ meta, map, source, readSet, selected, onOpen }: {
  meta: Meta; map: MapData; source: MapSource; readSet: Set<string>; selected: number | null; onOpen: (i: number) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const api = useRef<{ paint: () => void; select: (i: number | null) => void } | null>(null);
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;
  const readRef = useRef(readSet);
  readRef.current = readSet;
  const [tip, setTip] = useState<{ x: number; y: number; t: string } | null>(null);

  useEffect(() => {
    const el = host.current!;
    const P = map.chapters, si = source === "tsk" ? 0 : 1, n = P.length;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    controls.autoRotateSpeed = 0.5;
    camera.position.set(80, 10, 80);

    const pos = P.map((p, i) => new THREE.Vector3(p.hx[si][0] * SPREAD, (i / (n - 1) - 0.5) * HEIGHT, p.hx[si][1] * SPREAD));
    const deg = P.map((p) => (si ? p.de : p.dt)), dmax = Math.max(...deg);
    const mesh = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 10, 8), new THREE.MeshBasicMaterial(), n);
    const m = new THREE.Matrix4();
    P.forEach((_, i) => { const s = 0.25 + 0.6 * Math.sqrt(deg[i] / dmax); m.makeScale(s, s, s).setPosition(pos[i]); mesh.setMatrixAt(i, m); });
    scene.add(mesh);
    const spine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pos), new THREE.LineBasicMaterial({ color: css("--muted"), transparent: true, opacity: 0.25 }));
    scene.add(spine);
    // strongest chapter links; those crossing the Testaments in the accent colour
    const T = map.threads[source], verts: number[] = [], cols: number[] = [];
    const cx = new THREE.Color(css("--thread")), cs = new THREE.Color(css("--muted"));
    for (const [i, j] of T) {
      const c = (P[i].b >= 39) !== (P[j].b >= 39) ? cx : cs;
      verts.push(pos[i].x, pos[i].y, pos[i].z, pos[j].x, pos[j].y, pos[j].z);
      cols.push(c.r, c.g, c.b, c.r, c.g, c.b);
    }
    const tg = new THREE.BufferGeometry();
    tg.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    tg.setAttribute("color", new THREE.Float32BufferAttribute(cols, 3));
    const threads = new THREE.LineSegments(tg, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.35 }));
    scene.add(threads);
    let selLines: THREE.LineSegments | null = null;

    const paint = () => {
      const ot = new THREE.Color(css("--ot")), nt = new THREE.Color(css("--nt")), dim = new THREE.Color(css("--dim"));
      P.forEach((p, i) => {
        const base = p.b >= 39 ? nt : ot, read = readRef.current.has(chapterKey(p.b, p.c));
        mesh.setColorAt(i, read ? base : base.clone().lerp(dim, 0.6));
        // read chapters are drawn larger so they stand out in the column
        const s = (0.25 + 0.6 * Math.sqrt(deg[i] / dmax)) * (read ? 2.2 : 1);
        m.makeScale(s, s, s).setPosition(pos[i]);
        mesh.setMatrixAt(i, m);
      });
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    };
    const select = (i: number | null) => {
      if (selLines) { scene.remove(selLines); selLines.geometry.dispose(); selLines = null; }
      threads.material.opacity = i === null ? 0.35 : 0.08;
      if (i === null) return;
      const v: number[] = [];
      for (const [j] of P[i].g.slice(0, 12)) v.push(pos[i].x, pos[i].y, pos[i].z, pos[j].x, pos[j].y, pos[j].z);
      const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
      selLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: css("--ink"), transparent: true, opacity: 0.9 }));
      scene.add(selLines);
    };
    api.current = { paint, select };
    paint();

    const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
    const pick = (e: PointerEvent) => {
      const r = renderer.domElement.getBoundingClientRect();
      mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(mouse, camera);
      const hit = ray.intersectObject(mesh)[0];
      return hit?.instanceId ?? null;
    };
    let down: [number, number] | null = null;
    const onDown = (e: PointerEvent) => { down = [e.clientX, e.clientY]; controls.autoRotate = false; };
    const onUp = (e: PointerEvent) => {
      if (down && Math.hypot(e.clientX - down[0], e.clientY - down[1]) < 6) { const i = pick(e); if (i !== null) onOpenRef.current(i); }
      down = null;
    };
    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      const i = pick(e), r = el.getBoundingClientRect();
      setTip(i === null ? null : { x: e.clientX - r.left, y: e.clientY - r.top, t: `${meta.books[P[i].b].it} ${P[i].c}` });
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);
    renderer.domElement.addEventListener("pointermove", onMove);
    renderer.domElement.addEventListener("pointerleave", () => setTip(null));

    const resize = () => {
      const w = el.clientWidth, h = el.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
      const far = w < 500 ? 125 : 92;
      if (!controls.target.lengthSq()) camera.position.setLength(far);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    let raf = 0;
    const loop = () => { controls.update(); renderer.render(scene, camera); raf = requestAnimationFrame(loop); };
    loop();
    const mq = matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", paint);
    return () => {
      cancelAnimationFrame(raf); ro.disconnect(); mq.removeEventListener("change", paint);
      controls.dispose(); renderer.dispose();
      scene.traverse((o) => { const x = o as THREE.Mesh; x.geometry?.dispose?.(); });
      el.removeChild(renderer.domElement);
      api.current = null;
    };
  }, [map, meta, source]);

  useEffect(() => { api.current?.paint(); }, [readSet]);
  useEffect(() => { api.current?.select(selected); }, [selected, source]);

  return (
    <div ref={host} className="fill helix" aria-label="Elica del canone: trascina per ruotare">
      {tip && <div className="tooltip" style={{ left: tip.x, top: tip.y }}>{tip.t}</div>}
    </div>
  );
}
