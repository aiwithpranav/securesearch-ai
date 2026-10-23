// Maths for the dots sphere background (pure functions, no browser needed, so they are easy to test).
// The sphere is decoration only: it never reads or sends any data.

export type Vec3 = [number, number, number];
export type Rgb = [number, number, number];

/** Small seeded random numbers, so the sphere looks the same on every visit. */
export function seededRandom(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const GOLDEN_ANGLE = 2.399963229728653;

/** Point i of n, spread evenly over a unit sphere (Fibonacci sphere). */
export function spherePoint(i: number, n: number): Vec3 {
  const y = 1 - (2 * (i + 0.5)) / n;
  const radius = Math.sqrt(Math.max(0, 1 - y * y));
  const theta = i * GOLDEN_ANGLE;
  return [Math.cos(theta) * radius, y, Math.sin(theta) * radius];
}

/** The two angles of a point on the sphere. They never change, so they are worked out once per dot, not on every frame. */
export function angles(p: Vec3): [number, number] {
  return [Math.atan2(p[2], p[0]), Math.asin(Math.max(-1, Math.min(1, p[1])))];
}

/** Soft, slow "breathing" of the surface from the angles of a point (see `wobble`). */
export function wobbleAt(theta: number, phi: number, t: number): number {
  return 1 + 0.09 * Math.sin(3 * theta + t * 1.1 + phi * 2) * Math.cos(2 * phi - t * 0.8) + 0.04 * Math.sin(5 * phi + t * 1.6 + theta);
}

/** Soft, slow "breathing" of the surface: the sphere is slightly lumpy and the lumps move. */
export function wobble(p: Vec3, t: number): number {
  const [theta, phi] = angles(p);
  return wobbleAt(theta, phi, t);
}

/** Which of `levels` steps a value between 0 and `max` falls into (0 to levels - 1). Dots in the same step are drawn together. */
export function level(value: number, max: number, levels: number): number {
  if (max <= 0) return 0;
  return Math.max(0, Math.min(levels - 1, Math.floor((value / max) * levels)));
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const PINK: Rgb = [255, 125, 200];
const PURPLE: Rgb = [139, 92, 246];
const BLUE: Rgb = [96, 110, 255];

/** Colour by height: pink at the top, purple in the middle, blue-violet at the bottom. y is -1 (bottom) to 1 (top). */
export function colorAt(y: number): Rgb {
  const t = (Math.max(-1, Math.min(1, y)) + 1) / 2;
  const [from, to, k] = t > 0.5 ? [PURPLE, PINK, (t - 0.5) * 2] : [BLUE, PURPLE, t * 2];
  return [lerp(from[0], to[0], k), lerp(from[1], to[1], k), lerp(from[2], to[2], k)];
}

export const easeOutCubic = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

/** Intro: how far (0 to 1) a point has travelled from the side of the screen to its place on the sphere. */
export function introProgress(timeSeconds: number, delay: number, duration = 1.6): number {
  return easeOutCubic((timeSeconds - delay) / duration);
}

/** How many dots to draw: fewer on phones and small screens so the page stays smooth. */
export function dotCount(viewportWidth: number): number {
  if (viewportWidth < 640) return 2200;
  if (viewportWidth < 1024) return 3800;
  return 5600;
}

/** Sphere radius in pixels: "medium", never more than a quarter of the width and never huge.
 *  On a phone it is wider relative to the screen, so it stays visible above the form. */
export function sphereRadius(width: number, height: number): number {
  if (width < 640) return Math.round(Math.max(90, Math.min(width * 0.4, height * 0.3)));
  return Math.round(Math.max(90, Math.min(width * 0.24, height * 0.38, 290)));
}
