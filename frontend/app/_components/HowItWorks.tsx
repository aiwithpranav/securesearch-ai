"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform, useReducedMotion, MotionValue } from "motion/react";

function StepItem({ title, desc, index, progress, prefersReducedMotion }: { title: string, desc: string, index: number, progress: MotionValue<number>, prefersReducedMotion: boolean | null }) {
  const start = index * 0.25;
  const end = (index + 1) * 0.25;
  const opacity = useTransform(progress, [start, end], [0.4, 1]);
  return (
    <motion.li
      className="rounded-2xl border border-line bg-surface p-6"
      style={prefersReducedMotion ? undefined : { opacity }}
    >
      <span className="text-sm text-accent2">Step {index + 1}</span>
      <h3 className="mt-2 text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted">{desc}</p>
    </motion.li>
  );
}

export function HowItWorks({ steps }: { steps: [string, string][] }) {
  const containerRef = useRef<HTMLOListElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 80%", "end 50%"]
  });
  const prefersReducedMotion = useReducedMotion();

  return (
    <ol ref={containerRef} className="grid gap-4 md:grid-cols-4">
      {steps.map(([title, desc], i) => (
        <StepItem key={title} title={title} desc={desc} index={i} progress={scrollYProgress} prefersReducedMotion={prefersReducedMotion} />
      ))}
    </ol>
  );
}
