import { describe, expect, it } from "vitest";
import { colorAt, dotCount, easeOutCubic, introProgress, seededRandom, spherePoint, sphereRadius, wobble } from "./sphere";

describe("spherePoint", () => {
  it("puts every point on the unit sphere and covers top and bottom", () => {
    const n = 500;
    let top = -2;
    let bottom = 2;
    for (let i = 0; i < n; i++) {
      const [x, y, z] = spherePoint(i, n);
      expect(Math.hypot(x, y, z)).toBeCloseTo(1, 6);
      top = Math.max(top, y);
      bottom = Math.min(bottom, y);
    }
    expect(top).toBeGreaterThan(0.99);
    expect(bottom).toBeLessThan(-0.99);
  });
});

describe("seededRandom", () => {
  it("gives the same numbers for the same seed and stays between 0 and 1", () => {
    const a = seededRandom(7);
    const b = seededRandom(7);
    for (let i = 0; i < 50; i++) {
      const v = a();
      expect(v).toBe(b());
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });
});

describe("wobble", () => {
  it("keeps the surface close to a sphere at any time", () => {
    for (let t = 0; t < 20; t += 0.7) {
      for (let i = 0; i < 40; i++) {
        const w = wobble(spherePoint(i, 40), t);
        expect(w).toBeGreaterThan(0.85);
        expect(w).toBeLessThan(1.15);
      }
    }
  });
});

describe("colorAt", () => {
  it("is pinkish at the top and blue-violet at the bottom, and never leaves 0 to 255", () => {
    const top = colorAt(1);
    const bottom = colorAt(-1);
    expect(top[0]).toBeGreaterThan(bottom[0]);
    expect(bottom[2]).toBeGreaterThan(bottom[0]);
    for (const y of [-5, -1, -0.3, 0, 0.4, 1, 5]) for (const c of colorAt(y)) expect(c >= 0 && c <= 255).toBe(true);
  });
});

describe("intro", () => {
  it("starts at 0, ends at 1 and never goes backwards", () => {
    expect(introProgress(0, 0.5)).toBe(0);
    expect(introProgress(10, 0.5)).toBe(1);
    let last = 0;
    for (let t = 0; t <= 3; t += 0.1) {
      const p = introProgress(t, 0.3);
      expect(p).toBeGreaterThanOrEqual(last);
      last = p;
    }
    expect(easeOutCubic(-1)).toBe(0);
    expect(easeOutCubic(2)).toBe(1);
  });
});

describe("dotCount and sphereRadius", () => {
  it("uses fewer dots on small screens", () => {
    expect(dotCount(360)).toBeLessThan(dotCount(800));
    expect(dotCount(800)).toBeLessThan(dotCount(1440));
  });
  it("keeps the sphere medium on every screen", () => {
    expect(sphereRadius(360, 640)).toBeGreaterThanOrEqual(90);
    expect(sphereRadius(3000, 2000)).toBeLessThanOrEqual(290);
    expect(sphereRadius(1280, 900)).toBe(290);
    expect(sphereRadius(360, 800)).toBeGreaterThan(sphereRadius(1280, 900) * 0.4); // visible on a phone
  });
});
