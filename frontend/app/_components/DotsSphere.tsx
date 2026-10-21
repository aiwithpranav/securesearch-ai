"use client";

import { useEffect, useRef } from "react";
import { colorAt, dotCount, introProgress, seededRandom, spherePoint, sphereRadius, wobble } from "@/lib/sphere";

// Decorative background: a sphere made of glowing dots. Dots fly in from both sides when the page opens, then the
// sphere turns slowly and tilts a little towards the mouse. It is used on the landing page and the sign-in pages only.
// Safe by design: aria-hidden, ignores the mouse and keyboard, pauses when the tab is hidden or scrolled out of
// view, uses fewer dots on small screens, and shows one still picture for people who asked for reduced motion.

type Dot = { x: number; y: number; z: number; delay: number; fromRight: boolean; spread: number; color: string };

const INTRO_END = 0.9 + 1.6; // seconds until every dot has arrived

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
    const start = performance.now();
    let tiltX = 0;
    let tiltY = 0;
    let wantX = 0;
    let wantY = 0;

    function build() {
      const rnd = seededRandom(11);
      const n = dotCount(window.innerWidth);
      dots = Array.from({ length: n }, (_, i) => {
        const [x, y, z] = spherePoint(i, n);
        const [r, g, b] = colorAt(-y); // screen y points down, so the top of the sphere is y = -1
        return { x, y, z, delay: rnd() * 0.9, fromRight: rnd() > 0.5, spread: rnd(), color: `${r | 0},${g | 0},${b | 0}` };
      });
    }

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
      for (const pass of [0, 1]) {
        for (const d of dots) {
          const w = wobble([d.x, d.y, d.z], t);
          const x = d.x * w, y = d.y * w, z = d.z * w;
          const x1 = x * cosY + z * sinY;
          const z1 = -x * sinY + z * cosY;
          const y2 = y * cosX - z1 * sinX;
          const z2 = y * sinX + z1 * cosX;
          if ((z2 >= 0 ? 1 : 0) !== pass) continue; // far side first, near side on top
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
          c.fillStyle = `rgba(${d.color},${alpha})`;
          c.beginPath();
          c.arc(sx, sy, (0.8 + ((z2 + 1) / 2) * 1.5) * persp, 0, 6.2832);
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
    if (!reduced) {
      window.addEventListener("pointermove", onMove, { passive: true });
      raf = requestAnimationFrame(frame);
    }
    return () => {
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
