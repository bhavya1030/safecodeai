"use client";
import type { HistoryItem } from "@/lib/api";

interface WorkspaceViewProps {
  history: HistoryItem[];
  onOpenReview: (item: HistoryItem) => void;
  onNewSession: () => void;
  username: string;
}

function getScore(item: HistoryItem): number {
  if (item.result.syntax_error) return 10;
  return Math.max(0, Math.round(100 - item.result.confidence));
}

function scoreColor(s: number) {
  if (s >= 80) return "text-green-500";
  if (s >= 50) return "text-orange-500";
  return "text-red-500";
}

function scoreBg(s: number) {
  if (s >= 80) return "bg-green-500";
  if (s >= 50) return "bg-orange-500";
  return "bg-red-500";
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins || 1}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function issueTag(item: HistoryItem) {
  if (item.result.syntax_error)
    return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-500 border border-red-500/20">Syntax Error</span>;
  const n = item.result.issues.length;
  if (n === 0)
    return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/10 text-green-500 border border-green-500/20">Clean</span>;
  return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-orange-500/10 text-orange-500 border border-orange-500/20">{n} issue{n > 1 ? "s" : ""}</span>;
}

export default function WorkspaceView({ history, onOpenReview, onNewSession, username }: WorkspaceViewProps) {
  const totalReviews = history.length;
  const totalIssues = history.reduce((s, h) => s + (h.result.syntax_error ? 1 : 0) + h.result.issues.length, 0);
  const avgScore = totalReviews > 0
    ? Math.round(history.reduce((s, h) => s + getScore(h), 0) / totalReviews)
    : 0;
  const uniqueFiles = new Set(history.map((h) => h.filename)).size;
  const recentMonthReviews = history.filter(
    (h) => Date.now() - new Date(h.created_at).getTime() < 30 * 86400000
  ).length;

  return (
    <div className="flex-1 overflow-y-auto code-scrollbar bg-slate-50 dark:bg-background-dark">
      <div className="max-w-5xl mx-auto px-8 py-8">

        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Welcome back, <span className="text-primary">{username}</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">Here&apos;s an overview of your code review activity.</p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { icon: "history", label: "Total Reviews", value: totalReviews, sub: `${recentMonthReviews} this month` },
            { icon: "bug_report", label: "Issues Found", value: totalIssues, sub: "across all files" },
            { icon: "analytics", label: "Avg Score", value: `${avgScore}/100`, sub: avgScore >= 70 ? "Good standing" : "Needs attention" },
            { icon: "folder_open", label: "Files Analysed", value: uniqueFiles, sub: "unique filenames" },
          ].map((stat) => (
            <div key={stat.label} className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-widest text-slate-400">{stat.label}</span>
                <span className="material-symbols-outlined text-primary text-xl">{stat.icon}</span>
              </div>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{stat.value}</p>
              <p className="text-xs text-slate-400 mt-1">{stat.sub}</p>
            </div>
          ))}
        </div>

        {/* Quick actions */}
        <div className="flex items-center gap-3 mb-8">
          <button
            onClick={onNewSession}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg font-bold text-sm hover:bg-primary/90 transition-all shadow-lg shadow-primary/20"
          >
            <span className="material-symbols-outlined text-lg">add</span>
            New Review Session
          </button>
          <button
            onClick={() => history[0] && onOpenReview(history[0])}
            disabled={history.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 dark:bg-surface-dark text-slate-700 dark:text-slate-300 rounded-lg font-bold text-sm hover:bg-slate-200 dark:hover:bg-border-dark transition-all border border-slate-200 dark:border-border-dark disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-lg">open_in_new</span>
            Open Last Review
          </button>
        </div>

        {/* Review history table */}
        <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-border-dark">
            <h2 className="text-sm font-bold flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-xl">table_view</span>
              Review History
            </h2>
            <span className="text-xs text-slate-400">{totalReviews} total</span>
          </div>

          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <span className="material-symbols-outlined text-slate-500 text-5xl mb-3">history</span>
              <p className="text-sm font-semibold text-slate-400">No reviews yet</p>
              <p className="text-xs text-slate-500 mt-1">Start by reviewing some code in the Reviewer tab</p>
              <button
                onClick={onNewSession}
                className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-xs font-bold hover:bg-primary/90 transition-all"
              >
                Start Reviewing
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-border-dark">
                    <th className="text-left px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-400">File</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-400">Status</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-400">Score</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-400">Model Risk</th>
                    <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-400">Date</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => {
                    const score = getScore(item);
                    return (
                      <tr
                        key={item.id}
                        className="border-b border-slate-50 dark:border-border-dark/50 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors"
                      >
                        <td className="px-6 py-3.5">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-slate-400 text-base">description</span>
                            <span className="font-medium text-slate-900 dark:text-slate-100 truncate max-w-[160px]">
                              {item.filename}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5">{issueTag(item)}</td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${scoreBg(score)}`} style={{ width: `${score}%` }} />
                            </div>
                            <span className={`text-xs font-bold ${scoreColor(score)}`}>{score}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="text-xs font-mono text-slate-500">
                            {item.result.confidence.toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-xs text-slate-400">{timeAgo(item.created_at)}</td>
                        <td className="px-4 py-3.5">
                          <button
                            onClick={() => onOpenReview(item)}
                            className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider bg-primary/10 text-primary rounded hover:bg-primary/20 transition-colors border border-primary/20"
                          >
                            Open
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Score distribution */}
        {history.length > 0 && (
          <div className="mt-6 bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl p-6">
            <h2 className="text-sm font-bold mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-xl">bar_chart</span>
              Score Distribution
            </h2>
            <div className="flex items-end gap-2 h-20">
              {history.slice(0, 14).reverse().map((item, i) => {
                const s = getScore(item);
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 group cursor-pointer" onClick={() => onOpenReview(item)}>
                    <div className="relative w-full">
                      <div
                        className={`w-full rounded-t transition-all group-hover:opacity-80 ${scoreBg(s)}`}
                        style={{ height: `${Math.max(8, s * 0.64)}px` }}
                        title={`${item.filename}: ${s}/100`}
                      />
                    </div>
                    <span className="text-[9px] text-slate-500 group-hover:text-primary transition-colors">{s}</span>
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-slate-400 mt-3">Last {Math.min(history.length, 14)} reviews (newest on right)</p>
          </div>
        )}
      </div>
    </div>
  );
}
