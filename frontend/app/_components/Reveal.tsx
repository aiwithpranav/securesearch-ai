"use client";

import { motion, useReducedMotion } from "motion/react";
import { ReactNode } from "react";

export function Reveal({ children }: { children: ReactNode }) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <>
      <motion.div
        initial={{ opacity: prefersReducedMotion ? 1 : 0, y: prefersReducedMotion ? 0 : 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-50px" }}
        transition={{ duration: 0.5 }}
        className="reveal-wrapper"
      >
        {children}
      </motion.div>
      <noscript>
        <style dangerouslySetInnerHTML={{ __html: `.reveal-wrapper { opacity: 1 !important; transform: none !important; }` }} />
      </noscript>
    </>
  );
}
