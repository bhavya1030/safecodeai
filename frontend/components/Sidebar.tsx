"use client";
import type { HistoryItem } from "@/lib/api";

interface SidebarProps {
  history: HistoryItem[];
  selectedId: number | null;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSelect: (item: HistoryItem) => void;
  onNew: () => void;
  loading: boolean;
}

function groupByDate(items: HistoryItem[]) {
  const now = new Date();
  const todayStr = now.toDateString();
  const yesterdayStr = new Date(now.getTime() - 86400000).toDateString();
  const groups: Record<string, HistoryItem[]> = {};
  for (const item of items) {
    const d = new Date(item.created_at).toDateString();
    const label = d === todayStr ? "Today" : d === yesterdayStr ? "Yesterday" : "Earlier";
    if (!groups[label]) groups[label] = [];
    groups[label].push(item);
  }
  return groups;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins || 1} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs > 1 ? "s" : ""} ago`;
  return `${Math.floor(hrs / 24)} day${Math.floor(hrs / 24) > 1 ? "s" : ""} ago`;
}

function issueLabel(item: HistoryItem): string {
  if (item.result.syntax_error) return "Syntax error";
  const n = item.result.issues.length;
  if (n === 0) return "Fixed";
  return `${n} issue${n > 1 ? "s" : ""}`;
}

export default function Sidebar({
  history,
  selectedId,
  searchQuery,
  onSearchChange,
  onSelect,
  onNew,
  loading,
}: SidebarProps) {
  const filtered = history.filter((h) =>
    h.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const groups = groupByDate(filtered);
  const ORDER = ["Today", "Yesterday", "Earlier"];

  return (
    <aside className="w-72 hidden lg:flex flex-col border-r border-slate-200 dark:border-border-dark bg-white dark:bg-background-dark/50">
      {/* Search */}
      <div className="p-4 border-b border-slate-200 dark:border-border-dark">
        <div className="relative group">
          <span className="material-symbols-outlined absolute left-3 top-2.5 text-slate-400 group-focus-within:text-primary text-xl">
            search
          </span>
          <input
            className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-surface-dark border-none rounded-lg text-sm focus:ring-1 focus:ring-primary transition-all placeholder:text-slate-400 text-slate-900 dark:text-slate-100 outline-none"
            placeholder="Search sessions..."
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto code-scrollbar">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <span className="material-symbols-outlined text-slate-500 text-3xl animate-spin">autorenew</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <span className="material-symbols-outlined text-slate-600 text-4xl mb-3">history</span>
            <p className="text-sm text-slate-500">No sessions yet</p>
            <p className="text-xs text-slate-600 mt-1">Reviews will appear here</p>
          </div>
        ) : (
          <div className="p-4 space-y-6">
            {ORDER.filter((g) => groups[g]).map((label) => (
              <div key={label}>
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-3 px-2">
                  {label}
                </h3>
                <div className="space-y-1">
                  {groups[label].map((item) => (
                    <button
                      key={item.id}
                      onClick={() => onSelect(item)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left ${
                        selectedId === item.id
                          ? "bg-primary/10 border border-primary/20 text-primary"
                          : "hover:bg-slate-100 dark:hover:bg-surface-dark text-slate-600 dark:text-slate-300 border border-transparent"
                      }`}
                    >
                      <span className="material-symbols-outlined text-xl flex-shrink-0">history</span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{item.filename}</p>
                        <p className={`text-[11px] ${selectedId === item.id ? "opacity-70" : "text-slate-400"}`}>
                          {timeAgo(item.created_at)} • {issueLabel(item)}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New session */}
      <div className="p-4 border-t border-slate-200 dark:border-border-dark">
        <button
          onClick={onNew}
          className="w-full py-2.5 flex items-center justify-center gap-2 bg-primary text-white rounded-lg font-bold text-sm hover:bg-primary/90 transition-all shadow-lg shadow-primary/20"
        >
          <span className="material-symbols-outlined text-lg">add</span>
          New Review Session
        </button>
      </div>
    </aside>
  );
}
