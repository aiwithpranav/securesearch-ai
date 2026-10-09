"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ReactNode } from "react";

const MotionLink = motion.create(Link);
const MotionButton = motion.create("button");

export function AnimatedButton({ children, href, className = "", onClick }: { children: ReactNode; href?: string; className?: string; onClick?: () => void }) {
  const prefersReducedMotion = useReducedMotion();
  
  if (href) {
    if (href.startsWith("#") || href.startsWith("http")) {
      const MotionA = motion.create("a");
      return (
        <MotionA href={href} className={className} whileTap={{ scale: prefersReducedMotion ? 1 : 0.98 }} transition={{ duration: 0.12 }}>
          {children}
        </MotionA>
      );
    }
    return (
      <MotionLink href={href} className={className} whileTap={{ scale: prefersReducedMotion ? 1 : 0.98 }} transition={{ duration: 0.12 }}>
        {children}
      </MotionLink>
    );
  }

  return (
    <MotionButton className={className} onClick={onClick} whileTap={{ scale: prefersReducedMotion ? 1 : 0.98 }} transition={{ duration: 0.12 }}>
      {children}
    </MotionButton>
  );
}
