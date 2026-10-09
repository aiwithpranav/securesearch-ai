"use client";

import { useState, useEffect } from "react";
import { motion, useReducedMotion } from "motion/react";

export function HeroDemo({ 
  question, stages, answer, source 
}: { 
  question: string; stages: [string, string][]; answer: string; source: string 
}) {
  const prefersReducedMotion = useReducedMotion();
  const [phase, setPhase] = useState(0); 
  const [typedQuestion, setTypedQuestion] = useState("");
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    if (prefersReducedMotion) return;
    if (isPaused) return;

    let timeout: NodeJS.Timeout;

    if (phase === 0) {
      if (typedQuestion.length < question.length) {
        timeout = setTimeout(() => {
          setTypedQuestion(question.slice(0, typedQuestion.length + 1));
        }, 40);
      } else {
        timeout = setTimeout(() => setPhase(1), 300);
      }
    } else if (phase === 1) {
      timeout = setTimeout(() => setPhase(2), 200);
    } else if (phase === 2) {
      timeout = setTimeout(() => setPhase(3), 500);
    } else if (phase === 3) {
      timeout = setTimeout(() => setPhase(4), 500);
    } else if (phase === 4) {
      timeout = setTimeout(() => setPhase(5), 4000);
    } else if (phase === 5) {
      setTypedQuestion("");
      setPhase(0);
    }

    return () => clearTimeout(timeout);
  }, [phase, typedQuestion, isPaused, prefersReducedMotion, question]);

  const showStage1 = prefersReducedMotion || phase >= 2;
  const showStage2 = prefersReducedMotion || phase >= 3;
  const showAnswer = prefersReducedMotion || phase >= 4;
  const displayQuestion = prefersReducedMotion ? question : typedQuestion;

  return (
    <>
      <div className="sr-only">
        <p>Demo Question: {question}</p>
        <p>Stages:</p>
        <ul>
          <li>{stages[0][0]} - {stages[0][1]}</li>
          <li>{stages[1][0]} - {stages[1][1]}</li>
        </ul>
        <p>Answer: {answer}</p>
        <p>Source: {source}</p>
      </div>

      <div 
        className="rounded-2xl border border-line bg-surface p-5 hero-demo-visual"
        aria-hidden="true"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
        onTouchStart={() => setIsPaused(true)}
        onTouchEnd={() => setIsPaused(false)}
      >
        <div className="rounded-lg bg-surface2 px-4 py-3 text-sm min-h-[44px]">
          {displayQuestion}
          {phase === 0 && !prefersReducedMotion && <span className="animate-pulse">|</span>}
        </div>
        <ul className="mt-4 space-y-2 text-sm text-muted min-h-[52px]">
          <motion.li 
            initial={{ opacity: 0 }} 
            animate={{ opacity: showStage1 ? 1 : 0 }} 
            className="flex justify-between"
          >
            <span><span className="text-ok">✓</span> {stages[0][0]}</span>
            <span>{stages[0][1]}</span>
          </motion.li>
          <motion.li 
            initial={{ opacity: 0 }} 
            animate={{ opacity: showStage2 ? 1 : 0 }} 
            className="flex justify-between"
          >
            <span><span className="text-ok">✓</span> {stages[1][0]}</span>
            <span>{stages[1][1]}</span>
          </motion.li>
        </ul>
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: showAnswer ? 1 : 0 }}
          className="mt-5 border-t border-line pt-4"
        >
          <p>{answer}</p>
          <p className="mt-2 text-sm text-accent2">{source}</p>
        </motion.div>
      </div>
      <noscript>
        <style dangerouslySetInnerHTML={{ __html: `.hero-demo-visual { display: none; } .sr-only { position: static !important; width: auto !important; height: auto !important; overflow: visible !important; clip: auto !important; white-space: normal !important; }` }} />
      </noscript>
    </>
  );
}
