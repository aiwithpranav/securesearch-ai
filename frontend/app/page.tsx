import Link from "next/link";
import { DEMO_HREF } from "@/lib/site";
import { GlowCard } from "./_components/GlowCard";
import { Reveal } from "./_components/Reveal";
import { HowItWorks } from "./_components/HowItWorks";
import { HeroDemo } from "./_components/HeroDemo";
import { AnimatedButton } from "./_components/AnimatedButton";

const btnPrimary = "inline-flex items-center justify-center rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2";
const btnGhost = "inline-flex items-center justify-center rounded-lg border border-line px-5 py-3 font-medium text-text hover:border-accent2";
const card = "rounded-2xl border border-line bg-surface p-6";
const wrap = "mx-auto w-full max-w-6xl px-5";

function Section({ id, title, intro, children }: { id: string; title: string; intro?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-line py-20">
      <div className={wrap}>
        <Reveal>
          <h2 className="max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h2>
          {intro && <p className="mt-4 max-w-2xl text-muted">{intro}</p>}
          <div className="mt-10">{children}</div>
        </Reveal>
      </div>
    </section>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/90 backdrop-blur">
      <div className={`${wrap} flex h-16 items-center justify-between gap-4`}>
        <Link href="/" className="font-semibold">SecureSearch AI</Link>
        <nav aria-label="Main" className="hidden items-center gap-6 text-sm text-muted md:flex">
          <a href="#how" className="hover:text-text">How it works</a>
          <a href="#security" className="hover:text-text">Security</a>
          <a href="#features" className="hover:text-text">Features</a>
          <a href="#faq" className="hover:text-text">FAQ</a>
        </nav>
        <div className="flex items-center gap-2 text-sm">
          <AnimatedButton href="/login" className="rounded-lg px-3 py-2 text-muted hover:text-text">Sign in</AnimatedButton>
          <AnimatedButton href={DEMO_HREF} className="rounded-lg bg-accent px-4 py-2 font-medium text-bg hover:bg-accent2">Request demo</AnimatedButton>
        </div>
      </div>
    </header>
  );
}

function AnswerCard({ question, who, stages, answer, source }: { question: string; who?: string; stages: [string, string][]; answer: string; source?: string }) {
  return (
    <GlowCard className="rounded-2xl border border-line bg-surface p-5">
      {who && <p className="mb-3 text-sm text-muted">{who}</p>}
      <div className="rounded-lg bg-surface2 px-4 py-3 text-sm">{question}</div>
      <ul className="mt-4 space-y-2 text-sm text-muted">
        {stages.map(([l, t]) => (
          <li key={l} className="flex justify-between"><span><span className="text-ok" aria-hidden>✓</span> {l}</span><span>{t}</span></li>
        ))}
      </ul>
      <p className="mt-5 border-t border-line pt-4">{answer}</p>
      {source && <p className="mt-2 text-sm text-accent2">{source}</p>}
    </GlowCard>
  );
}

const steps: [string, string][] = [
  ["You ask", "Type a question in your own words."],
  ["We check your access", "Your permissions are read from the database, fresh, on every search."],
  ["We search only what you may read", "Documents you cannot read are never searched, scored or shown to the AI."],
  ["You get an answer with sources", "Every answer names its document and section. If nothing readable fits, it says so."],
];
const features = [
  ["Citations on every answer", "See the document, section and page behind each statement."],
  ["A record of every search", "Who asked what, which documents were used, and the outcome. Document text is not stored in the log."],
  ["Access changes apply on the next search", "Remove someone from a group and their next question reflects it."],
  ["Documents stay current", "Only changed files are re-processed, and the latest version is preferred."],
];
const teams = ["HR", "Finance", "Engineering", "Sales", "Legal", "Security", "Support"];
const faq = [
  ["Does the AI see documents I can't access?", "No. Access is decided in the database before any search runs, so the language model only receives passages you are allowed to read."],
  ["Where does my data go?", "Search models run on your own infrastructure. The first version plans to use a hosted language model (OpenAI) to write answers, and it receives only the permitted passages. The demo uses synthetic documents only."],
  ["How fast do permission changes apply?", "By design, on the very next search. Permissions are read at query time, not copied into caches."],
  ["Which file types are supported?", "PDF, Word (DOCX), plain text and Markdown. Scanned documents (OCR) are not supported yet."],
  ["Is single sign-on supported?", "Not in the first version. It is planned next, together with automatic user provisioning."],
  ["What if the answer isn't in my documents?", "You get a plain 'could not find enough accessible source material' message. The system does not guess."],
];

export default function Home() {
  return (
    <>
      <Header />
      <main id="main">
        <div className="border-b border-line bg-surface2 py-2 text-center text-sm text-muted">
          In development. This page describes the planned product; examples use sample data.
        </div>

        <section className="py-20 sm:py-28">
          <Reveal>
            <div className={`${wrap} grid items-center gap-12 lg:grid-cols-2`}>
              <div>
                <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">Search everything you&apos;re allowed to see. Nothing you&apos;re not.</h1>
                <p className="mt-6 max-w-xl text-lg text-muted">Answers from your company&apos;s documents, with sources, and only from what you have permission to read.</p>
                <div className="mt-8 flex flex-wrap gap-3">
                  <AnimatedButton href="#how" className={btnPrimary}>See how it works</AnimatedButton>
                  <AnimatedButton href="/login" className={btnGhost}>Sign in</AnimatedButton>
                </div>
              </div>
              <HeroDemo
                question="How many leave days do I get in India?"
                stages={[["Checking your access", "0.1 s"], ["Searching 18 documents you can read", "0.4 s"]]}
                answer="Employees in India receive 18 paid leave days per calendar year."
                source="Leave Policy, Section 2.1 · sample data"
              />
            </div>
          </Reveal>
        </section>

        <Section id="problem" title="AI search is fast. It can also be a leak." intro="Ordinary AI search may pull confidential text into an answer for someone who must not see it. Questions like these are where it goes wrong:">
          <ul className="grid gap-4 md:grid-cols-3">
            {["What are the salary bands for senior engineers?", "What is in the FY2026 budget forecast?", "Summarise last month's security incident report."].map((q) => (
              <GlowCard as="li" key={q} className={card}>“{q}”<p className="mt-3 text-sm text-muted">If the AI has read everything, it may answer anyone who asks.</p></GlowCard>
            ))}
          </ul>
        </Section>

        <Section id="how" title="Four steps. One rule: check access first.">
          <HowItWorks steps={steps} />
        </Section>

        <Section id="demo" title="Same question. Different people. Different answers.">
          <div className="grid gap-6 md:grid-cols-2">
            <AnswerCard who="Rahul, Finance" question="How does Q3 budget approval work?" stages={[["Checking your access", "0.1 s"], ["Ranking the best matches", "0.3 s"]]} answer="Q3 budget approvals follow the steps in the Finance Budget Policy." source="Finance Budget Policy · sample data" />
            <AnswerCard who="Aisha, Engineering" question="How does Q3 budget approval work?" stages={[["Checking your access", "0.1 s"], ["Ranking the best matches", "0.3 s"]]} answer="Could not find enough current, accessible source material to answer this." />
          </div>
        </Section>

        <Section id="start" title="Get started in two minutes">
          <div className="grid gap-4 md:grid-cols-2">
            <GlowCard className={card}><h3 className="text-lg font-semibold">Employees</h3><p className="mt-2 text-muted">Sign in, ask a question, read the answer, open a source, rate the result.</p></GlowCard>
            <GlowCard className={card}><h3 className="text-lg font-semibold">Admins</h3><p className="mt-2 text-muted">Upload a document, choose who can read it, check that it is ready.</p></GlowCard>
          </div>
        </Section>

        <Section id="security" title="The badge check happens before the search." intro="Permissions are enforced in the database, not in a prompt. A prompt can be talked around. A database rule cannot.">
          <ul className="grid gap-4 md:grid-cols-3">
            {[["Authorize first", "Access is checked in the database before any search."], ["Deny by default", "No matching rule means no access. One deny rule overrides any allow."], ["Prove it", "Automated tests plant secret markers in restricted documents and fail the build if one ever appears for the wrong person."]].map(([t, d]) => (
              <GlowCard as="li" key={t} className={card}><h3 className="font-semibold">{t}</h3><p className="mt-2 text-sm text-muted">{d}</p></GlowCard>
            ))}
          </ul>
          <Link href="/security" className="mt-6 inline-block text-accent2 underline underline-offset-4">Read the security overview</Link>
        </Section>

        <Section id="features" title="Built for real teams">
          <ul className="grid gap-4 md:grid-cols-2">
            {features.map(([t, d]) => (<GlowCard as="li" key={t} className={card}><h3 className="font-semibold">{t}</h3><p className="mt-2 text-sm text-muted">{d}</p></GlowCard>))}
          </ul>
        </Section>

        <Section id="teams" title="Every department, safely">
          <ul className="flex flex-wrap gap-3">{teams.map((t) => (<li key={t} className="rounded-full border border-line bg-surface2 px-4 py-2 text-sm">{t}</li>))}</ul>
        </Section>

        <Section id="faq" title="Questions people ask first">
          <div className="max-w-3xl divide-y divide-line rounded-2xl border border-line bg-surface">
            {faq.map(([q, a]) => (
              <details key={q} className="group p-5">
                <summary className="cursor-pointer list-none font-medium">{q}</summary>
                <p className="mt-3 text-muted">{a}</p>
              </details>
            ))}
          </div>
        </Section>

        <section className="border-t border-line py-24">
          <div className={`${wrap} text-center`}>
            <Reveal>
              <h2 className="text-3xl font-semibold sm:text-4xl">See it in action</h2>
              <div className="mt-8 flex justify-center gap-3">
                <AnimatedButton href={DEMO_HREF} className={btnPrimary}>Request demo</AnimatedButton>
                <AnimatedButton href="/login" className={btnGhost}>Sign in</AnimatedButton>
              </div>
            </Reveal>
          </div>
        </section>
      </main>
      <footer className="border-t border-line py-10 text-sm text-muted">
        <div className={`${wrap} flex flex-wrap items-center justify-between gap-4`}>
          <span>© SecureSearch AI</span>
          <nav aria-label="Footer" className="flex gap-5">
            <Link href="/privacy" className="hover:text-text">Privacy</Link>
            <Link href="/terms" className="hover:text-text">Terms</Link>
            <Link href="/security" className="hover:text-text">Security</Link>
          </nav>
        </div>
      </footer>
    </>
  );
}
