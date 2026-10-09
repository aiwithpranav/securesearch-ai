"use client";

import { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { GlowCard } from "./GlowCard";
import { TourDialog } from "./TourDialog";

type Person = "Aisha, Engineering" | "Rahul, Finance";

type Question = {
  id: string;
  text: string;
};

const QUESTIONS: Question[] = [
  { id: "q1", text: "How does Q3 budget approval work?" },
  { id: "q2", text: "How do I request production database access?" },
  { id: "q3", text: "What is the leave policy for employees in India?" },
];

function getResult(person: Person, qId: string) {
  const isRefusal = 
    (person === "Aisha, Engineering" && qId === "q1") ||
    (person === "Rahul, Finance" && qId === "q2");
    
  let stages: [string, string][] = [
    ["Checking your access", "0.1 s"],
    ["Ranking the best matches", "0.3 s"]
  ];
  if (qId === "q3") {
    stages = [
      ["Checking your access", "0.1 s"],
      ["Searching 18 documents you can read", "0.4 s"]
    ];
  }

  if (isRefusal) {
    return {
      stages,
      answerText: "Could not find enough current, accessible source material to answer this."
    };
  }

  if (qId === "q1") {
    return {
      stages,
      answerText: "Q3 budget approvals follow the steps in the Finance Budget Policy.",
      source: "Finance Budget Policy · sample data"
    };
  } else if (qId === "q2") {
    return {
      stages,
      answerText: "To request production database access, submit a ticket via the internal IT portal with approval from your engineering manager.",
      source: "Production Access Runbook · sample data"
    };
  } else {
    return {
      stages,
      answerText: "Employees in India receive 18 paid leave days per calendar year.",
      source: "Leave Policy, Section 2.1 · sample data"
    };
  }
}

export function InteractiveDemo() {
  const [activePerson, setActivePerson] = useState<Person>("Rahul, Finance");
  const [activeQuestion, setActiveQuestion] = useState<string>("q1");
  const [isTourOpen, setIsTourOpen] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const people: Person[] = ["Aisha, Engineering", "Rahul, Finance"];
    const currentIndex = people.indexOf(activePerson);
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % people.length;
      setActivePerson(people[nextIndex]);
      document.getElementById(`tab-${people[nextIndex].split(',')[0]}`)?.focus();
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      const nextIndex = (currentIndex - 1 + people.length) % people.length;
      setActivePerson(people[nextIndex]);
      document.getElementById(`tab-${people[nextIndex].split(',')[0]}`)?.focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      setActivePerson(people[0]);
      document.getElementById(`tab-${people[0].split(',')[0]}`)?.focus();
    } else if (e.key === "End") {
      e.preventDefault();
      setActivePerson(people[1]);
      document.getElementById(`tab-${people[1].split(',')[0]}`)?.focus();
    }
  };

  const result = getResult(activePerson, activeQuestion);

  return (
    <>
      <div className="flex flex-col gap-8 md:flex-row">
        <div className="flex-1 space-y-6">
          <div>
            <h3 className="mb-3 text-sm font-medium text-muted" id="tablist-label">Select a person</h3>
            <div 
              role="tablist" 
              aria-labelledby="tablist-label"
              className="inline-flex rounded-lg bg-surface2 p-1"
              onKeyDown={handleKeyDown}
            >
              {(["Aisha, Engineering", "Rahul, Finance"] as Person[]).map((person) => {
                const isSelected = activePerson === person;
                const id = `tab-${person.split(',')[0]}`;
                return (
                  <button
                    key={person}
                    id={id}
                    role="tab"
                    aria-selected={isSelected}
                    aria-controls="tabpanel"
                    tabIndex={isSelected ? 0 : -1}
                    onClick={() => setActivePerson(person)}
                    className={`rounded-md px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent ${isSelected ? "bg-surface text-text shadow-sm" : "text-muted hover:text-text"}`}
                  >
                    {person}
                  </button>
                );
              })}
            </div>
          </div>
          
          <div>
            <h3 className="mb-3 text-sm font-medium text-muted">Select a question</h3>
            <div className="flex flex-wrap gap-2">
              {QUESTIONS.map((q) => {
                const isSelected = activeQuestion === q.id;
                return (
                  <button
                    key={q.id}
                    aria-pressed={isSelected}
                    onClick={() => setActiveQuestion(q.id)}
                    className={`rounded-full border px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent ${isSelected ? "border-accent bg-accent/10 text-accent" : "border-line bg-surface text-text hover:border-accent2"}`}
                  >
                    {q.text}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="pt-4">
            <button 
              onClick={() => setIsTourOpen(true)}
              className="inline-flex items-center justify-center rounded-lg border border-line px-5 py-3 font-medium text-text hover:border-accent2 focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Take the 60-second tour
            </button>
            <p className="mt-4 text-xs text-muted">Sample data. This demo runs in your browser with no server.</p>
          </div>
        </div>

        <div className="flex-1">
          <GlowCard className="rounded-2xl border border-line bg-surface p-5 min-h-[250px] flex flex-col relative overflow-hidden" as="div">
            <div className="rounded-lg bg-surface2 px-4 py-3 text-sm mb-4">
              {QUESTIONS.find((q) => q.id === activeQuestion)?.text}
            </div>
            
            <div id="tabpanel" role="tabpanel" aria-live="polite" className="relative flex-1">
              <AnimatePresence mode="wait">
                <motion.div
                  key={`${activePerson}-${activeQuestion}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: prefersReducedMotion ? 0 : 0.3 }}
                >
                  <ul className="space-y-2 text-sm text-muted">
                    {result.stages.map(([l, t]) => (
                      <li key={l} className="flex justify-between">
                        <span><span className="text-ok" aria-hidden>✓</span> {l}</span>
                        <span>{t}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-5 border-t border-line pt-4">
                    <p>{result.answerText}</p>
                    {result.source && <p className="mt-2 text-sm text-accent2">{result.source}</p>}
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </GlowCard>
        </div>
      </div>
      
      <TourDialog isOpen={isTourOpen} onClose={() => setIsTourOpen(false)} />
    </>
  );
}
