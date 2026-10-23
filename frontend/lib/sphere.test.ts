import { describe, expect, it } from "vitest";
import { angles, colorAt, dotCount, easeOutCubic, introProgress, level, seededRandom, spherePoint, sphereRadius, wobble, wobbleAt } from "./sphere";

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

describe("angles and wobbleAt", () => {
  it("give exactly the same wobble as wobble() (the angles are only worked out once)", () => {
    for (let i = 0; i < 60; i++) {
      const p = spherePoint(i, 60);
      const [theta, phi] = angles(p);
      for (const t of [0, 0.4, 3.3, 17]) expect(wobbleAt(theta, phi, t)).toBe(wobble(p, t));
    }
  });
});

describe("level", () => {
  it("sorts a value into one of the steps and never leaves the range", () => {
    expect(level(0, 1, 10)).toBe(0);
    expect(level(0.55, 1, 10)).toBe(5);
    expect(level(1, 1, 10)).toBe(9);
    expect(level(5, 1, 10)).toBe(9);
    expect(level(-1, 1, 10)).toBe(0);
  });
  it("copes with a maximum of zero", () => expect(level(0.3, 0, 10)).toBe(0));
  it("uses every step across the range", () => {
    const used = new Set(Array.from({ length: 101 }, (_, i) => level(i / 100, 1, 10)));
    expect(used.size).toBe(10);
  });
});
