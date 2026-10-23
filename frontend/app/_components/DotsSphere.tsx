"use client";

import { useEffect, useRef } from "react";
import { angles, colorAt, dotCount, introProgress, level, seededRandom, spherePoint, sphereRadius, wobbleAt } from "@/lib/sphere";

// Decorative background: a sphere made of glowing dots. Dots fly in from both sides when the page opens, then the
// sphere turns slowly and tilts a little towards the mouse. It is used on the landing page and the sign-in pages only.
// Safe by design: aria-hidden, ignores the mouse and keyboard, pauses when the tab is hidden or scrolled out of
// view, uses fewer dots on small screens, and shows one still picture for people who asked for reduced motion.

type Dot = { x: number; y: number; z: number; theta: number; phi: number; delay: number; fromRight: boolean; spread: number; color: number };

const INTRO_END = 0.9 + 1.6; // seconds until every dot has arrived
// Dots that share a colour and a brightness step are drawn in ONE path, so the browser fills a few dozen shapes per frame instead
// of thousands (this is what keeps the page smooth on a slow computer). The steps are fine enough to look the same.
const COLORS = 12;
const ALPHAS = 10;
const MAX_ALPHA = 0.84;

export function DotsSphere({ strength = 1, className = "" }: { strength?: number; className?: string }) {
  const boxRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const box = boxRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!box || !canvas || !ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let dots: Dot[] = [];
    let visible = true;
    let raf = 0;
    let start = performance.now();
    let tiltX = 0;
    let tiltY = 0;
    let wantX = 0;
    let wantY = 0;

    function build() {
      const rnd = seededRandom(11);
      const n = dotCount(window.innerWidth);
      dots = Array.from({ length: n }, (_, i) => {
        const [x, y, z] = spherePoint(i, n);
        const [theta, phi] = angles([x, y, z]);
        return { x, y, z, theta, phi, delay: rnd() * 0.9, fromRight: rnd() > 0.5, spread: rnd(), color: level(-y + 1, 2, COLORS) };
      });
    }

    // one list of circles for every colour, brightness step and side of the sphere (far side first, near side on top)
    const palette = Array.from({ length: COLORS }, (_, i) => {
      const [r, g, b] = colorAt(-1 + ((i + 0.5) / COLORS) * 2); // step i is the colour for height -y in this step (as before: colorAt(-y))
      return `${r | 0},${g | 0},${b | 0}`;
    });
    const bucket = (): number[][] => Array.from({ length: COLORS * ALPHAS }, () => []);
    const sides = [bucket(), bucket()];

    function resize() {
      const rect = box!.getBoundingClientRect();
      width = Math.max(1, Math.round(rect.width));
      height = Math.max(1, Math.round(rect.height));
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas!.width = Math.round(width * dpr);
      canvas!.height = Math.round(height * dpr);
      if (dots.length === 0 || Math.abs(dotCount(window.innerWidth) - dots.length) > 0) build();
      draw(reduced ? INTRO_END + 1 : (performance.now() - start) / 1000);
    }

    function draw(t: number) {
      const c = ctx!;
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.clearRect(0, 0, width, height);
      const cx = width * 0.5;
      const cy = width < 640 ? height * 0.24 : height * 0.48; // on a phone the sphere sits above the form
      const radius = sphereRadius(width, height);
      const glow = c.createRadialGradient(cx, cy, radius * 0.2, cx, cy, radius * 1.5);
      glow.addColorStop(0, `rgba(139,92,246,${0.22 * strength})`);
      glow.addColorStop(1, "rgba(139,92,246,0)");
      c.fillStyle = glow;
      c.fillRect(0, 0, width, height);

      const ry = t * 0.25 + tiltX;
      const rx = -0.25 + tiltY;
      const cosY = Math.cos(ry), sinY = Math.sin(ry), cosX = Math.cos(rx), sinX = Math.sin(rx);
      for (const side of sides) for (const list of side) list.length = 0;
      for (const d of dots) {
        const w = wobbleAt(d.theta, d.phi, t);
        const x = d.x * w, y = d.y * w, z = d.z * w;
        const x1 = x * cosY + z * sinY;
        const z1 = -x * sinY + z * cosY;
        const y2 = y * cosX - z1 * sinX;
        const z2 = y * sinX + z1 * cosX;
        const persp = 1 / (1 - z2 * 0.25);
        let sx = cx + x1 * radius * persp;
        let sy = cy + y2 * radius * persp;
        let alpha = (0.12 + ((z2 + 1) / 2) * 0.72) * strength;
        if (t < INTRO_END) {
          const p = introProgress(t, d.delay);
          if (p <= 0) continue;
          const startX = d.fromRight ? width + 40 + d.spread * 160 : -40 - d.spread * 160;
          const startY = cy + (d.spread - 0.5) * height * 0.9;
          sx = startX + (sx - startX) * p;
          sy = startY + (sy - startY) * p;
          alpha *= p;
        }
        sides[z2 >= 0 ? 1 : 0][d.color * ALPHAS + level(alpha, MAX_ALPHA * strength, ALPHAS)].push(sx, sy, (0.8 + ((z2 + 1) / 2) * 1.5) * persp);
      }
      for (const side of sides) {
        for (let k = 0; k < side.length; k++) {
          const list = side[k];
          if (list.length === 0) continue;
          const color = Math.floor(k / ALPHAS);
          const step = k % ALPHAS;
          c.fillStyle = `rgba(${palette[color]},${(((step + 0.5) / ALPHAS) * MAX_ALPHA * strength).toFixed(3)})`;
          c.beginPath();
          for (let m = 0; m < list.length; m += 3) {
            c.moveTo(list[m] + list[m + 2], list[m + 1]);
            c.arc(list[m], list[m + 1], list[m + 2], 0, 6.2832);
          }
          c.fill();
        }
      }
    }

    function frame(now: number) {
      raf = requestAnimationFrame(frame);
      if (!visible || document.hidden) return;
      tiltX += (wantX - tiltX) * 0.05;
      tiltY += (wantY - tiltY) * 0.05;
      draw((now - start) / 1000);
    }

    const onMove = (e: PointerEvent) => {
      wantX = (e.clientX / window.innerWidth - 0.5) * 0.4;
      wantY = (e.clientY / window.innerHeight - 0.5) * 0.25;
    };

    build();
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(box);
    const io = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; });
    io.observe(box);
    let kickoff = 0;
    if (!reduced) {
      window.addEventListener("pointermove", onMove, { passive: true });
      // Start moving a moment after the page has shown its text, so the animation never delays the first paint.
      kickoff = window.setTimeout(() => {
        start = performance.now();
        raf = requestAnimationFrame(frame);
      }, 300);
    }
    return () => {
      window.clearTimeout(kickoff);
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      window.removeEventListener("pointermove", onMove);
    };
  }, [strength]);

  return (
    <div ref={boxRef} aria-hidden="true" className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      <canvas ref={canvasRef} className="h-full w-full" />
    </div>
  );
}
