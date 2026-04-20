"use client";
import { useState } from "react";

const SECTIONS = [
  { id: "getting-started", label: "Getting Started", icon: "rocket_launch" },
  { id: "issue-types", label: "Issue Types", icon: "category" },
  { id: "how-it-works", label: "How It Works", icon: "settings" },
  { id: "shortcuts", label: "Keyboard Shortcuts", icon: "keyboard" },
  { id: "api", label: "API Reference", icon: "api" },
  { id: "faq", label: "FAQ", icon: "help" },
];

function Section({ id, children }: { id: string; children: React.ReactNode }) {
  return <section id={id} className="scroll-mt-4">{children}</section>;
}

function SectionTitle({ icon, children }: { icon: string; children: React.ReactNode }) {
  return (
    <h2 className="text-lg font-bold flex items-center gap-2 text-slate-900 dark:text-slate-100 mb-4">
      <span className="material-symbols-outlined text-primary">{icon}</span>
      {children}
    </h2>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="bg-slate-100 dark:bg-surface-dark border border-slate-200 dark:border-border-dark px-1.5 py-0.5 rounded text-xs font-mono text-primary">
      {children}
    </code>
  );
}

function IssueCard({ color, icon, label, description, example }: {
  color: string; icon: string; label: string; description: string; example: string;
}) {
  return (
    <div className={`p-4 rounded-xl border ${color} space-y-2`}>
      <div className="flex items-center gap-2">
        <span className={`material-symbols-outlined text-lg`}>{icon}</span>
        <span className="text-xs font-bold uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">{description}</p>
      <div className="bg-black/20 dark:bg-black/30 rounded-lg p-3 font-mono text-xs text-slate-300 border border-white/5">
        {example}
      </div>
    </div>
  );
}

export default function DocsView({ onNavToReviewer }: { onNavToReviewer: () => void }) {
  const [activeSection, setActiveSection] = useState("getting-started");

  function scrollTo(id: string) {
    setActiveSection(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="flex-1 overflow-hidden flex bg-slate-50 dark:bg-background-dark">
      {/* Docs sidebar nav */}
      <nav className="w-56 flex-shrink-0 border-r border-slate-200 dark:border-border-dark bg-white dark:bg-surface-dark/30 py-6 hidden md:flex flex-col">
        <p className="px-4 text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">Documentation</p>
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => scrollTo(s.id)}
            className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-left transition-colors ${
              activeSection === s.id
                ? "text-primary bg-primary/5 border-r-2 border-primary"
                : "text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-white/5"
            }`}
          >
            <span className="material-symbols-outlined text-base">{s.icon}</span>
            {s.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <div className="flex-1 overflow-y-auto code-scrollbar px-8 py-8 space-y-12">
        <div className="max-w-3xl">

          {/* Getting Started */}
          <Section id="getting-started">
            <SectionTitle icon="rocket_launch">Getting Started</SectionTitle>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed mb-6">
              SafeCodeAI is an AI-powered code review tool that analyses your code for bugs, security issues, and
              performance problems in seconds. Here&apos;s how to get started.
            </p>
            <div className="space-y-4">
              {[
                { step: "1", title: "Write or upload your code", desc: "Paste your code directly into the editor or upload a source file, then choose the review language from the toolbar. SafeCodeAI reviews Python, C++, and Java." },
                { step: "2", title: "Click Review Code", desc: "Hit the green Review Code button in the top-right of the editor. SafeCodeAI scores risk with a calibrated per-language model and then applies language-aware static checks." },
                { step: "3", title: "Read the Review Insights", desc: "The right panel shows all detected issues with severity levels — Critical, Warning, and Tip. Each card includes a description and a fix suggestion." },
                { step: "4", title: "Navigate & Fix", desc: "Review issues in the panel. Critical issues are marked as 'Error', while Warnings and Tips allow you to 'Apply Fix' or 'Apply' to jump directly to the code. Click Dismiss to hide a resolved issue." },
              ].map((item) => (
                <div key={item.step} className="flex gap-4">
                  <div className="size-7 rounded-full bg-primary text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                    {item.step}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={onNavToReviewer}
              className="mt-6 flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg text-sm font-bold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20"
            >
              <span className="material-symbols-outlined text-lg">play_arrow</span>
              Open the Reviewer
            </button>
          </Section>

          <hr className="border-slate-200 dark:border-border-dark" />

          {/* Issue Types */}
          <Section id="issue-types">
            <SectionTitle icon="category">Issue Types</SectionTitle>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
              SafeCodeAI categorises every detected problem into one of three severity levels.
            </p>
            <div className="space-y-4">
              <IssueCard
                color="bg-red-500/5 border-red-500/20 text-red-500"
                icon="security"
                label="Critical Issue"
                description="Crashes, infinite loops, division by zero, syntax errors, or recursion without a base case. These must be fixed before the code can safely run."
                example={`while True:          # Infinite loop — no break\n    process(data)`}
              />
              <IssueCard
                color="bg-orange-500/5 border-orange-500/20 text-orange-500"
                icon="warning"
                label="Potential Bug / Warning"
                description="Code that is likely to cause a TLE (Time Limit Exceeded), such as nested loops, sorting inside loops, or repeated input calls inside loops."
                example={`for i in range(n):\n    arr.sort()       # O(n² log n) — sort inside loop`}
              />
              <IssueCard
                color="bg-blue-500/5 border-blue-500/20 text-blue-500"
                icon="lightbulb"
                label="Refactor Tip"
                description="Suggestions for cleaner or safer code — like adding a return value to a function, or avoiding mutation of a list during iteration."
                example={`def greet(name):     # Function has no return\n    print(f"Hi, {name}")`}
              />
            </div>
          </Section>

          <hr className="border-slate-200 dark:border-border-dark" />

          {/* How It Works */}
          <Section id="how-it-works">
            <SectionTitle icon="settings">How It Works</SectionTitle>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed mb-5">
              SafeCodeAI combines a trained machine learning model with deterministic rule-based analysis for accurate, explainable results.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { icon: "account_tree", title: "Syntax Checks", desc: "Python code is parsed with the built-in ast module, while C++ and Java files get delimiter and statement-level syntax checks before deeper analysis." },
                { icon: "psychology", title: "ML Bug Risk Model", desc: "Calibrated RandomForest models run for Python, C++, and Java to produce language-aware risk confidence (0-100%)." },
                { icon: "rule", title: "Rule-Based Detection", desc: "Language-specific detectors then scan for infinite loops, division by zero, nested loops, sorting inside loops, recursion risks, missing returns, and resource cleanup issues." },
                { icon: "manage_search", title: "Issue Triage", desc: "Each detected issue is classified by severity (Critical, Warning, Tip) and mapped to the exact line number in your source code." },
              ].map((item) => (
                <div key={item.title} className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl p-4">
                  <span className="material-symbols-outlined text-primary text-2xl mb-2 block">{item.icon}</span>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1">{item.title}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </Section>

          <hr className="border-slate-200 dark:border-border-dark" />

          {/* Shortcuts */}
          <Section id="shortcuts">
            <SectionTitle icon="keyboard">Keyboard Shortcuts</SectionTitle>
            <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl overflow-hidden">
              {[
                { keys: ["Ctrl", "Enter"], action: "Run code review" },
                { keys: ["Ctrl", "T"], action: "Open new tab" },
                { keys: ["Ctrl", "W"], action: "Close current tab" },
                { keys: ["Ctrl", "U"], action: "Upload a file" },
                { keys: ["Ctrl", "/"], action: "Toggle comment in editor" },
                { keys: ["Ctrl", "Z"], action: "Undo last change" },
                { keys: ["Ctrl", "Shift", "Z"], action: "Redo last change" },
                { keys: ["Alt", "↑ / ↓"], action: "Move line up / down" },
              ].map((s, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between px-5 py-3 border-b border-slate-100 dark:border-border-dark/50 last:border-0"
                >
                  <span className="text-sm text-slate-600 dark:text-slate-300">{s.action}</span>
                  <div className="flex items-center gap-1">
                    {s.keys.map((k) => (
                      <kbd
                        key={k}
                        className="px-2 py-0.5 text-xs font-bold bg-slate-100 dark:bg-background-dark border border-slate-200 dark:border-border-dark rounded font-mono text-slate-600 dark:text-slate-300"
                      >
                        {k}
                      </kbd>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <hr className="border-slate-200 dark:border-border-dark" />

          {/* API Reference */}
          <Section id="api">
            <SectionTitle icon="api">API Reference</SectionTitle>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
              The SafeCodeAI backend is a FastAPI service running at <Code>http://localhost:8000</Code>. All protected routes require a Bearer token.
            </p>
            <div className="space-y-4">
              {[
                {
                  method: "POST", path: "/api/auth/signup", auth: false,
                  desc: "Create a new account.",
                  body: `{ "email": "you@example.com", "username": "dev", "password": "••••••••" }`,
                },
                {
                  method: "POST", path: "/api/auth/login", auth: false,
                  desc: "Sign in and receive a JWT token.",
                  body: `{ "email": "you@example.com", "password": "••••••••" }`,
                },
                {
                  method: "POST", path: "/api/review", auth: true,
                  desc: "Submit code for review. Returns issues and a bug risk confidence score.",
                  body: `{ "code": "int main() {\\n  return 0;\\n}", "filename": "main.cpp", "language": "cpp" }`,
                },
                {
                  method: "GET", path: "/api/reviews", auth: true,
                  desc: "Retrieve the authenticated user's review history (latest 50).",
                  body: null,
                },
              ].map((ep) => (
                <div key={ep.path} className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl overflow-hidden">
                  <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100 dark:border-border-dark">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${ep.method === "GET" ? "bg-green-500/10 text-green-500 border border-green-500/20" : "bg-primary/10 text-primary border border-primary/20"}`}>
                      {ep.method}
                    </span>
                    <Code>{ep.path}</Code>
                    {ep.auth && <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-orange-500/10 text-orange-500 border border-orange-500/20 ml-auto">Auth required</span>}
                  </div>
                  <div className="px-4 py-3">
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{ep.desc}</p>
                    {ep.body && (
                      <pre className="bg-slate-50 dark:bg-background-dark border border-slate-100 dark:border-border-dark rounded-lg p-3 text-xs font-mono text-slate-600 dark:text-slate-300 overflow-x-auto">
                        {ep.body}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <hr className="border-slate-200 dark:border-border-dark" />

          {/* FAQ */}
          <Section id="faq">
            <SectionTitle icon="help">FAQ</SectionTitle>
            <div className="space-y-4">
              {[
                {
                  q: "What languages does SafeCodeAI support?",
                  a: "SafeCodeAI currently reviews Python, C++, and Java. All three languages use calibrated ML scoring plus language-specific static analysis checks.",
                },
                {
                  q: "Where is my data stored?",
                  a: "All reviews and user accounts are stored in a local SQLite database (safecodeai.db) on the machine running the backend. No data is sent to external servers.",
                },
                {
                  q: "How accurate is the bug risk score?",
                  a: "The score is model-based for Python, C++, and Java and is calibrated per language. Results are combined with static checks for stronger issue detection and fewer blind spots.",
                },
                {
                  q: "Can I use my own ML model?",
                  a: "Yes — train a scikit-learn model and save it as bug_risk_model.pkl in the root padosi/ folder. The backend will automatically load it on startup.",
                },
                {
                  q: "Is there a file size limit?",
                  a: "There is no hard limit, but very large files (> 10,000 lines) may increase review time. For best results, review individual modules rather than entire codebases at once.",
                },
                {
                  q: "How do I log in for testing?",
                  a: "A demo user is automatically created on startup. Use Email: demo@example.com and Password: demo123 to log in and test the full review workflow.",
                },
              ].map((item) => (
                <div key={item.q} className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl p-5">
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-start gap-2">
                    <span className="material-symbols-outlined text-primary text-base flex-shrink-0 mt-0.5">help_outline</span>
                    {item.q}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed mt-2 ml-6">{item.a}</p>
                </div>
              ))}
            </div>
          </Section>

        </div>
      </div>
    </div>
  );
}

