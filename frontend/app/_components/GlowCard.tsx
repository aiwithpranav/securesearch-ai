"use client";

import { motion } from "motion/react";
import { useState, useRef, useEffect, ReactNode } from "react";

export function GlowCard({ children, className = "", as = "div" }: { children: ReactNode; className?: string, as?: any }) {
  const [isTouchActive, setIsTouchActive] = useState(false);
  const cardRef = useRef<HTMLElement>(null);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });

  const handlePointerMove = (e: React.PointerEvent<HTMLElement>) => {
    if (e.pointerType === "touch") return;
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    setCursorPos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLElement>) => {
    if (e.pointerType === "touch") {
      setIsTouchActive(true);
      if (!cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      setCursorPos({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    }
  };

  useEffect(() => {
    if (!isTouchActive) return;

    const timeout = setTimeout(() => {
      setIsTouchActive(false);
    }, 1500);

    const handleOutside = (e: Event) => {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) {
        setIsTouchActive(false);
      }
    };

    const handleBlur = () => setIsTouchActive(false);

    document.addEventListener("pointerdown", handleOutside);
    document.addEventListener("touchstart", handleOutside);
    window.addEventListener("blur", handleBlur);

    return () => {
      clearTimeout(timeout);
      document.removeEventListener("pointerdown", handleOutside);
      document.removeEventListener("touchstart", handleOutside);
      window.removeEventListener("blur", handleBlur);
    };
  }, [isTouchActive]);

  const Component = motion.create(as as any);

  return (
    <Component
      ref={cardRef}
      data-active={isTouchActive}
      className={`group relative transition-transform duration-200 [@media(hover:hover)]:hover:scale-[1.025] motion-reduce:hover:!scale-100 data-[active=true]:scale-[1.025] motion-reduce:data-[active=true]:!scale-100 ${className}`}
      onPointerMove={handlePointerMove}
      onPointerDown={handlePointerDown}
      onPointerCancel={() => setIsTouchActive(false)}
    >
      <div className="relative z-10 h-full w-full">{children}</div>
      
      {/* Radial soft light */}
      <div
        className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-[inherit] opacity-0 transition-opacity duration-200 [@media(hover:hover)]:group-hover:opacity-100 group-data-[active=true]:opacity-100"
      >
        <div 
          className="absolute inset-0"
          style={{
            background: `radial-gradient(circle 200px at ${cursorPos.x}px ${cursorPos.y}px, rgba(59, 130, 246, 0.15) 0%, transparent 100%)`,
          }}
        />
      </div>
      
      {/* Border glow */}
      <div
        className="pointer-events-none absolute inset-0 z-20 rounded-[inherit] border border-blue-500 dark:border-blue-400 opacity-0 transition-opacity duration-200 [@media(hover:hover)]:group-hover:opacity-100 group-data-[active=true]:opacity-100"
      />
    </Component>
  );
}
