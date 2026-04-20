"use client";
import type { ReviewResult } from "@/lib/api";

interface Issue {
  name: string;
  line: number;
  fix: string;
  severity: "critical" | "warning" | "tip";
}

interface ReviewPanelProps {
  result: ReviewResult | null;
  onScrollToLine?: (line: number) => void;
}

function getSeverity(name: string): "critical" | "warning" | "tip" {
  const n = name.toLowerCase();
  if (
    n.includes("infinite") ||
    n.includes("division by zero") ||
    n.includes("syntax") ||
    n.includes("recursion") ||
    n.includes("missing semicolon") ||
    n.includes("compiler error") ||
    n.includes("compiler warning")
  )
    return "critical";
  if (
    n.includes("complexity") ||
    n.includes("nested") ||
    n.includes("tle") ||
    n.includes("sorting") ||
    n.includes("input inside") ||
    n.includes("memory leak") ||
    n.includes("resource") ||
    n.includes("without returning")
  )
    return "warning";
  return "tip";
}

const SEV_CONFIG = {
  critical: {
    bg: "bg-red-500/5",
    border: "border-red-500/20",
    text: "text-red-500",
    icon: "security",
    label: "Critical Issue",
    badgeBg: "bg-red-500/15 text-red-500 border border-red-500/30",
  },
  warning: {
    bg: "bg-orange-500/5",
    border: "border-orange-500/20",
    text: "text-orange-500",
    icon: "warning",
    label: "Potential Bug",
    badgeBg: "bg-orange-500/15 text-orange-500 border border-orange-500/30",
  },
  tip: {
    bg: "bg-blue-500/5",
    border: "border-blue-500/20",
    text: "text-blue-500",
    icon: "lightbulb",
    label: "Refactor Tip",
    badgeBg: "bg-blue-500/15 text-blue-500 border border-blue-500/30",
  },
};

function getScore(result: ReviewResult): number {
  if (result.syntax_error) return 10;
  return Math.max(0, Math.round(100 - result.confidence));
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 50) return "text-orange-500";
  return "text-red-500";
}

function getBarColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 50) return "bg-orange-500";
  return "bg-red-500";
}

export default function ReviewPanel({ result, onScrollToLine }: ReviewPanelProps) {

  if (!result) {
    return (
      <aside className="w-80 hidden xl:flex flex-col border-l border-slate-200 dark:border-border-dark bg-white dark:bg-background-dark/50 overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-border-dark flex items-center justify-between">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">analytics</span>
            Review Insights
          </h3>
          <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-[10px] font-bold">3-LANG MODEL</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <span className="material-symbols-outlined text-slate-600 text-5xl mb-4">analytics</span>
          <p className="text-sm font-semibold text-slate-400">No review yet</p>
          <p className="text-xs text-slate-500 mt-1">Click <strong className="text-slate-400">Review Code</strong> to analyze Python, C++, or Java code</p>
        </div>
      </aside>
    );
  }

  const score = getScore(result);

  const issues: Issue[] = [
    ...(result.syntax_error
      ? [{ name: "Syntax Error", line: result.error_line ?? 0, fix: result.error_msg, severity: "critical" as const }]
      : []),
    ...result.issues.map(([name, line, fix]) => ({
      name,
      line,
      fix,
      severity: getSeverity(name),
    })),
  ];

  return (
    <aside className="w-80 hidden xl:flex flex-col border-l border-slate-200 dark:border-border-dark bg-white dark:bg-background-dark/50 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-border-dark flex items-center justify-between">
        <h3 className="text-sm font-bold flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">analytics</span>
          Review Insights
        </h3>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${issues.length === 0 ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"}`}>
          {issues.length === 0 ? "ALL CLEAR" : `${issues.length} ISSUE${issues.length > 1 ? "S" : ""}`}
        </span>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 code-scrollbar">
        {issues.length === 0 && (
          <div className="p-4 rounded-xl bg-green-500/5 border border-green-500/20 flex items-center gap-3">
            <span className="material-symbols-outlined text-green-500 text-2xl">check_circle</span>
            <div>
              <p className="text-sm font-semibold text-green-500">No issues found</p>
              <p className="text-xs text-slate-400 mt-0.5">Your code looks clean!</p>
            </div>
          </div>
        )}

        {issues.map((issue, idx) => {
          const cfg = SEV_CONFIG[issue.severity];
          return (
            <div
              key={idx}
              className={`p-4 rounded-xl ${cfg.bg} border ${cfg.border} space-y-3 relative overflow-hidden`}
            >
              {/* Glow */}
              <div
                className={`absolute top-0 right-0 w-24 h-24 blur-3xl -mr-12 -mt-12 pointer-events-none opacity-30 ${
                  issue.severity === "critical" ? "bg-red-500" : issue.severity === "warning" ? "bg-orange-500" : "bg-blue-500"
                }`}
              />

              <div className="flex items-start justify-between">
                <div className={`flex items-center gap-2 ${cfg.text}`}>
                  <span className="material-symbols-outlined text-lg">{cfg.icon}</span>
                  <span className="text-xs font-bold uppercase">{cfg.label}</span>
                </div>
                {issue.line > 0 && (
                  <button
                    onClick={() => onScrollToLine?.(issue.line)}
                    className="text-[10px] text-slate-400 hover:text-primary transition-colors"
                    title="Jump to line"
                  >
                    Line {issue.line}
                  </button>
                )}
              </div>

              <p className="text-sm font-medium leading-snug text-slate-900 dark:text-slate-100">{issue.name}</p>

              {/* Tip section */}
              {issue.fix && (
                <div className="flex gap-2 p-2.5 rounded-lg bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5">
                  <span className="material-symbols-outlined text-amber-500 text-sm flex-shrink-0 mt-0.5">lightbulb</span>
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">{issue.fix}</p>
                </div>
              )}

              {/* Non-clickable error badge */}
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold cursor-not-allowed select-none ${cfg.badgeBg}`}
              >
                <span className="material-symbols-outlined text-xs">error</span>
                Error
              </span>
            </div>
          );
        })}
      </div>

      {/* Score */}
      <div className="p-4 bg-primary/5 border-t border-slate-200 dark:border-border-dark">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-bold">Review Score</p>
          <p className={`text-xs font-bold ${getScoreColor(score)}`}>{score} / 100</p>
        </div>
        <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${getBarColor(score)}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>
    </aside>
  );
}
