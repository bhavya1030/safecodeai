"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import Sidebar from "@/components/Sidebar";
import ReviewPanel from "@/components/ReviewPanel";
import WorkspaceView from "@/components/WorkspaceView";
import DocsView from "@/components/DocsView";
import { api, type HistoryItem, type ReviewResult } from "@/lib/api";
import type * as Monaco from "monaco-editor";

const CodeEditor = dynamic(() => import("@/components/CodeEditor"), { ssr: false });

type View = "reviewer" | "workspace" | "docs";
type ReviewLanguage = "python" | "cpp" | "java";

interface Tab {
  id: string;
  filename: string;
  code: string;
  language: string;
  reviewLanguage: ReviewLanguage;
}

const REVIEW_LANGUAGE_META: Record<ReviewLanguage, { label: string; extension: string; icon: string }> = {
  python: { label: "Python", extension: "py", icon: "code" },
  cpp: { label: "C++", extension: "cpp", icon: "memory_alt" },
  java: { label: "Java", extension: "java", icon: "coffee" },
};

function detectLanguage(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    py: "python", ts: "typescript", tsx: "typescript",
    js: "javascript", jsx: "javascript", java: "java",
    sql: "sql", cpp: "cpp", c: "cpp", cs: "csharp",
  };
  return map[ext] || "plaintext";
}

function detectReviewLanguage(filename: string): ReviewLanguage {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  const map: Partial<Record<string, ReviewLanguage>> = {
    py: "python",
    c: "cpp",
    cpp: "cpp",
    cc: "cpp",
    cxx: "cpp",
    java: "java",
  };
  return map[ext] || "python";
}

function syncFilenameWithReviewLanguage(filename: string, reviewLanguage: ReviewLanguage): string {
  const extension = REVIEW_LANGUAGE_META[reviewLanguage].extension;
  const baseName = filename.replace(/\.[^.]+$/, "");
  return `${baseName}.${extension}`;
}

function getTabIcon(language: string): string {
  const iconMap: Record<string, string> = {
    python: "code",
    cpp: "memory_alt",
    java: "coffee",
    sql: "database",
    javascript: "javascript",
    typescript: "javascript",
  };
  return iconMap[language] || "description";
}

const DEFAULT_CODE = `# Write your Python code here and click "Review Code"

def calculate_average(numbers):
    total = 0
    for num in numbers:
        total = total + num
    return total / len(numbers)   # Bug: division by zero if list is empty

def find_item(items, target):
    for i in range(len(items)):
        for j in range(len(items)):  # Nested loop — O(n²)
            if items[j] == target:
                return j
`;

let tabCounter = 2;

const MOCK_NOTIFICATIONS = [
  { id: 1, icon: "check_circle", color: "text-green-500", title: "Review complete", sub: "untitled.py analysed — 2 issues found", time: "2m ago" },
  { id: 2, icon: "warning", color: "text-orange-500", title: "High complexity detected", sub: "Nested loops found in last review", time: "1h ago" },
  { id: 3, icon: "info", color: "text-primary", title: "Welcome to SafeCodeAI", sub: "Start by reviewing your first file", time: "today" },
];

export default function Dashboard() {
  const router = useRouter();
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [user, setUser] = useState<{ username: string; email: string } | null>(null);
  const [isDark, setIsDark] = useState(true);
  const [activeView, setActiveView] = useState<View>("reviewer");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [showDropzone, setShowDropzone] = useState(true);
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS);

  const [tabs, setTabs] = useState<Tab[]>([
    { id: "1", filename: "untitled.py", code: DEFAULT_CODE, language: "python", reviewLanguage: "python" },
  ]);
  const [activeTabId, setActiveTabId] = useState("1");

  const [reviewing, setReviewing] = useState(false);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const [error, setError] = useState("");

  const activeTab = tabs.find((t) => t.id === activeTabId) ?? tabs[0];

  // ── Auth + bootstrap ──────────────────────────────────────
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.replace("/login"); return; }
    const u = localStorage.getItem("user");
    if (u) setUser(JSON.parse(u));
    loadHistory();
  }, [router]);

  // ── Theme ─────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  // ── Keyboard shortcuts ────────────────────────────────────
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); handleReview(); }
      if ((e.ctrlKey || e.metaKey) && e.key === "t") { e.preventDefault(); addTab(); }
      if ((e.ctrlKey || e.metaKey) && e.key === "w") {
        e.preventDefault();
        if (tabs.length > 1) closeTab(activeTabId, { stopPropagation: () => {} } as React.MouseEvent);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "u") { e.preventDefault(); fileInputRef.current?.click(); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // ── Data ──────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try { setHistory(await api.getHistory()); }
    catch { /* silent */ }
    finally { setHistoryLoading(false); }
  }, []);

  // ── Tab helpers ───────────────────────────────────────────
  function updateActiveTabCode(code: string) {
    setTabs((prev) => prev.map((t) => t.id === activeTabId ? { ...t, code } : t));
    setResult(null);
  }

  function addTab() {
    const id = String(tabCounter++);
    setTabs((prev) => [
      ...prev,
      { id, filename: `untitled-${id}.py`, code: "", language: "python", reviewLanguage: "python" },
    ]);
    setActiveTabId(id);
    setResult(null);
    setShowDropzone(true);
    setActiveView("reviewer");
  }

  function closeTab(id: string, e: Pick<React.MouseEvent, "stopPropagation">) {
    e.stopPropagation();
    if (tabs.length === 1) return;
    const remaining = tabs.filter((t) => t.id !== id);
    setTabs(remaining);
    if (activeTabId === id) { setActiveTabId(remaining[remaining.length - 1].id); setResult(null); }
  }

  // ── Review ────────────────────────────────────────────────
  async function handleReview() {
    if (!activeTab.code.trim() || reviewing) return;
    setActiveView("reviewer");
    setReviewing(true);
    setError("");
    setResult(null);
    try {
      const res = await api.review(activeTab.code, activeTab.filename, activeTab.reviewLanguage);
      setResult(res.result);
      setSelectedHistoryId(res.id);
      loadHistory();
      // Add notification
      setNotifications((prev) => [
        { id: Date.now(), icon: "check_circle", color: "text-green-500", title: "Review complete", sub: `${activeTab.filename} — ${res.result.issues.length} issue(s) found`, time: "just now" },
        ...prev.slice(0, 4),
      ]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setReviewing(false);
    }
  }

  // ── History selection ─────────────────────────────────────
  function handleSelectHistory(item: HistoryItem) {
    setSelectedHistoryId(item.id);
    setResult(item.result);
    setTabs((prev) =>
      prev.map((t) =>
        t.id === activeTabId
          ? {
              ...t,
              filename: item.filename,
              code: item.code,
              language: detectLanguage(item.filename),
              reviewLanguage: detectReviewLanguage(item.filename),
            }
          : t
      )
    );
    setShowDropzone(false);
    setActiveView("reviewer");
    setShowMobileSidebar(false);
  }

  function handleNew() {
    addTab();
    setResult(null);
    setSelectedHistoryId(null);
    setError("");
  }

  function handleReviewLanguageChange(reviewLanguage: ReviewLanguage) {
    setTabs((prev) =>
      prev.map((tab) =>
        tab.id === activeTabId
          ? {
              ...tab,
              reviewLanguage,
              language: reviewLanguage,
              filename: syncFilenameWithReviewLanguage(tab.filename, reviewLanguage),
            }
          : tab
      )
    );
    setResult(null);
    setSelectedHistoryId(null);
  }

  // ── File upload ───────────────────────────────────────────
  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const lang = detectLanguage(file.name);
    const reviewLanguage = detectReviewLanguage(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setTabs((prev) =>
        prev.map((t) =>
          t.id === activeTabId
            ? {
                ...t,
                filename: file.name,
                code: ev.target?.result as string,
                language: lang,
                reviewLanguage,
              }
            : t
        )
      );
      setShowDropzone(false);
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const lang = detectLanguage(file.name);
    const reviewLanguage = detectReviewLanguage(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setTabs((prev) =>
        prev.map((t) =>
          t.id === activeTabId
            ? {
                ...t,
                filename: file.name,
                code: ev.target?.result as string,
                language: lang,
                reviewLanguage,
              }
            : t
        )
      );
      setShowDropzone(false);
    };
    reader.readAsText(file);
  }

  function handleLogout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.replace("/login");
  }

  function scrollToLine(line: number) {
    if (editorRef.current) {
      setActiveView("reviewer");
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
      editorRef.current.focus();
    }
  }

  function dismissNotification(id: number) {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }

  const langLabel = REVIEW_LANGUAGE_META[activeTab.reviewLanguage].label;
  const hasUnread = notifications.length > 0;

  return (
    <div
      className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 antialiased overflow-hidden h-screen flex flex-col"
      onClick={() => { setShowUserMenu(false); setShowNotifications(false); }}
    >
      {/* ════════════════ HEADER ════════════════ */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-slate-200 dark:border-border-dark bg-white dark:bg-background-dark shrink-0 z-20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-primary">
            <span className="material-symbols-outlined text-3xl">terminal</span>
            <h2 className="text-xl font-bold tracking-tight">SafeCodeAI</h2>
          </div>

          <nav className="hidden md:flex items-center gap-6 ml-10">
            {(["reviewer", "workspace", "docs"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setActiveView(v)}
                className={`text-sm font-medium capitalize pb-1 transition-colors ${
                  activeView === v
                    ? "text-primary border-b-2 border-primary"
                    : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 border-b-2 border-transparent"
                }`}
              >
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* Theme toggle */}
          <div className="flex bg-slate-100 dark:bg-surface-dark p-1 rounded-lg">
            <button
              onClick={(e) => { e.stopPropagation(); setIsDark(false); }}
              className={`p-1.5 rounded-md transition-all ${!isDark ? "bg-white shadow-sm text-slate-800" : "text-slate-400 hover:text-slate-600"}`}
              title="Light mode"
            >
              <span className="material-symbols-outlined text-lg">light_mode</span>
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setIsDark(true); }}
              className={`p-1.5 rounded-md transition-all ${isDark ? "bg-primary text-white" : "text-slate-400 hover:text-slate-600"}`}
              title="Dark mode"
            >
              <span className="material-symbols-outlined text-lg">dark_mode</span>
            </button>
          </div>

          <div className="h-6 w-px bg-slate-200 dark:bg-border-dark" />

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowNotifications(!showNotifications); setShowUserMenu(false); }}
              className="relative p-2 text-slate-500 dark:text-slate-400 hover:text-primary transition-colors"
              title="Notifications"
            >
              <span className="material-symbols-outlined">notifications</span>
              {hasUnread && <span className="absolute top-2 right-2 flex h-2 w-2 rounded-full bg-red-500" />}
            </button>

            {showNotifications && (
              <div
                className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl shadow-xl z-50 overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-border-dark">
                  <span className="text-sm font-bold">Notifications</span>
                  {notifications.length > 0 && (
                    <button
                      onClick={() => setNotifications([])}
                      className="text-[10px] font-bold text-primary hover:underline uppercase tracking-wider"
                    >
                      Clear all
                    </button>
                  )}
                </div>

                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <span className="material-symbols-outlined text-slate-400 text-3xl mb-2">notifications_off</span>
                    <p className="text-xs text-slate-400">All caught up!</p>
                  </div>
                ) : (
                  <div className="max-h-72 overflow-y-auto code-scrollbar">
                    {notifications.map((n) => (
                      <div key={n.id} className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/5 border-b border-slate-50 dark:border-border-dark/50 last:border-0">
                        <span className={`material-symbols-outlined text-xl flex-shrink-0 mt-0.5 ${n.color}`}>{n.icon}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{n.title}</p>
                          <p className="text-xs text-slate-400 truncate mt-0.5">{n.sub}</p>
                          <p className="text-[10px] text-slate-400 mt-1">{n.time}</p>
                        </div>
                        <button
                          onClick={() => dismissNotification(n.id)}
                          className="text-slate-300 hover:text-slate-500 dark:text-slate-600 dark:hover:text-slate-400 flex-shrink-0"
                        >
                          <span className="material-symbols-outlined text-sm">close</span>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* User menu */}
          <div className="relative flex items-center gap-3 pl-1">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-bold leading-none">{user?.username ?? "User"}</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">Pro Plan</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setShowUserMenu(!showUserMenu); setShowNotifications(false); }}
              className="size-9 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center text-primary font-bold text-sm hover:bg-primary/30 transition-colors"
              title="Account menu"
            >
              {user?.username?.[0]?.toUpperCase() ?? "U"}
            </button>

            {showUserMenu && (
              <div
                className="absolute right-0 top-full mt-2 w-48 bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded-xl shadow-xl py-1 z-50"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="px-4 py-2.5 border-b border-slate-100 dark:border-border-dark">
                  <p className="text-sm font-semibold truncate">{user?.username}</p>
                  <p className="text-xs text-slate-400 truncate">{user?.email}</p>
                </div>
                <button
                  onClick={() => setActiveView("workspace")}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">grid_view</span>
                  Workspace
                </button>
                <button
                  onClick={() => setActiveView("docs")}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">menu_book</span>
                  Documentation
                </button>
                <div className="border-t border-slate-100 dark:border-border-dark mt-1" />
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-500 hover:bg-red-500/5 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">logout</span>
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ════════════════ MAIN ════════════════ */}
      <main className="flex flex-1 overflow-hidden relative">

        {/* Mobile sidebar overlay */}
        {showMobileSidebar && (
          <div className="fixed inset-0 z-30 lg:hidden" onClick={() => setShowMobileSidebar(false)}>
            <div className="absolute inset-0 bg-black/50" />
            <div className="absolute left-0 top-0 bottom-0 w-72 z-40" onClick={(e) => e.stopPropagation()}>
              <Sidebar
                history={history}
                selectedId={selectedHistoryId}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onSelect={handleSelectHistory}
                onNew={handleNew}
                loading={historyLoading}
              />
            </div>
          </div>
        )}

        {/* Desktop sidebar — always visible */}
        <Sidebar
          history={history}
          selectedId={selectedHistoryId}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onSelect={handleSelectHistory}
          onNew={handleNew}
          loading={historyLoading}
        />

        {/* ── Workspace view ── */}
        {activeView === "workspace" && (
          <WorkspaceView
            history={history}
            onOpenReview={(item) => handleSelectHistory(item)}
            onNewSession={handleNew}
            username={user?.username ?? ""}
          />
        )}

        {/* ── Docs view ── */}
        {activeView === "docs" && (
          <DocsView onNavToReviewer={() => setActiveView("reviewer")} />
        )}

        {/* ── Reviewer view ── */}
        {activeView === "reviewer" && (
          <>
            <section className="flex-1 flex flex-col bg-slate-50 dark:bg-background-dark relative overflow-hidden">
              {/* Tab bar */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 dark:border-border-dark bg-white dark:bg-surface-dark/40 shrink-0">
                <div className="flex items-center gap-1 overflow-x-auto">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTabId(tab.id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-sm font-medium whitespace-nowrap transition-all ${
                        tab.id === activeTabId
                          ? "bg-slate-100 dark:bg-background-dark text-primary border-t-2 border-primary"
                          : "hover:bg-slate-100 dark:hover:bg-surface-dark/60 text-slate-500 border-t-2 border-transparent"
                      }`}
                    >
                      <span className="material-symbols-outlined text-sm">
                        {getTabIcon(tab.language)}
                      </span>
                      <span className="max-w-[120px] truncate">{tab.filename}</span>
                      <span
                        className="material-symbols-outlined text-xs hover:text-red-500 cursor-pointer ml-0.5"
                        onClick={(e) => closeTab(tab.id, e)}
                      >
                        close
                      </span>
                    </button>
                  ))}
                  <button
                    onClick={addTab}
                    className="p-1.5 text-slate-400 hover:text-primary transition-colors"
                    title="New tab (Ctrl+T)"
                  >
                    <span className="material-symbols-outlined text-sm">add</span>
                  </button>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {error && (
                    <span className="text-xs text-red-500 flex items-center gap-1">
                      <span className="material-symbols-outlined text-xs">error</span>
                      {error}
                      <button onClick={() => setError("")} className="ml-1 hover:text-red-300">
                        <span className="material-symbols-outlined text-xs">close</span>
                      </button>
                    </span>
                  )}
                  <label className="flex items-center gap-2 px-2 py-1 rounded-md border border-slate-200 dark:border-border-dark bg-slate-50 dark:bg-background-dark/60 text-xs font-bold text-slate-500 dark:text-slate-300">
                    <span className="material-symbols-outlined text-sm">translate</span>
                    <select
                      value={activeTab.reviewLanguage}
                      onChange={(e) => handleReviewLanguageChange(e.target.value as ReviewLanguage)}
                      className="bg-transparent outline-none"
                    >
                      {(Object.entries(REVIEW_LANGUAGE_META) as Array<[ReviewLanguage, (typeof REVIEW_LANGUAGE_META)[ReviewLanguage]]>).map(([value, meta]) => (
                        <option key={value} value={value} className="text-slate-900">
                          {meta.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    onClick={handleReview}
                    disabled={reviewing || !activeTab.code.trim()}
                    className="flex items-center gap-2 px-4 py-1.5 bg-green-500/10 text-green-500 hover:bg-green-500 hover:text-white rounded-md text-xs font-bold transition-all border border-green-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
                    title="Review code (Ctrl+Enter)"
                  >
                    <span className={`material-symbols-outlined text-sm ${reviewing ? "animate-spin" : ""}`}>
                      {reviewing ? "autorenew" : "play_arrow"}
                    </span>
                    {reviewing ? "Reviewing..." : "Review Code"}
                  </button>
                </div>
              </div>

              {/* Editor + dropzone */}
              <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-[#0d1117]">
                {showDropzone && (
                  <div className="p-6 border-b border-slate-200 dark:border-white/5 bg-white dark:bg-white/[0.02] shrink-0">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".py,.ts,.tsx,.js,.jsx,.java,.sql,.cpp,.cs"
                      className="hidden"
                      onChange={handleFileUpload}
                    />
                    <div
                      className="border-2 border-dashed border-slate-300 dark:border-white/10 rounded-xl p-8 flex flex-col items-center justify-center text-center group hover:border-primary/50 transition-colors cursor-pointer"
                      onClick={() => fileInputRef.current?.click()}
                      onDrop={handleDrop}
                      onDragOver={(e) => e.preventDefault()}
                    >
                      <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-primary text-3xl">upload_file</span>
                      </div>
                      <p className="text-slate-600 dark:text-slate-300 font-medium">
                        Drop code files here or{" "}
                        <span className="text-primary">browse files</span>
                      </p>
                      <p className="text-slate-400 dark:text-slate-500 text-xs mt-1">Calibrated model active for Python, C++, and Java</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); setShowDropzone(false); }}
                        className="mt-4 text-xs text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-400 transition-colors flex items-center gap-1"
                      >
                        <span className="material-symbols-outlined text-xs">keyboard_arrow_up</span>
                        Collapse
                      </button>
                    </div>
                  </div>
                )}

                <div className="flex-1 overflow-hidden">
                  <CodeEditor
                    value={activeTab.code}
                    language={activeTab.language}
                    onChange={updateActiveTabCode}
                    onMount={(editor) => { editorRef.current = editor; }}
                    onCursorChange={(line, col) => setCursorPos({ line, col })}
                    isDark={isDark}
                  />
                </div>
              </div>

              {/* Status bar */}
              <div className="h-10 border-t border-slate-200 dark:border-border-dark flex items-center px-4 justify-between bg-white dark:bg-surface-dark/40 text-[10px] uppercase font-bold tracking-widest text-slate-400 shrink-0">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-xs">info</span>
                    UTF-8
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-xs">code</span>
                    {langLabel}
                  </span>
                  {!showDropzone && (
                    <button
                      onClick={() => setShowDropzone(true)}
                      className="flex items-center gap-1 hover:text-primary transition-colors"
                      title="Show upload zone (Ctrl+U)"
                    >
                      <span className="material-symbols-outlined text-xs">upload_file</span>
                      Upload
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <span>Line {cursorPos.line}, Col {cursorPos.col}</span>
                  <span className="text-green-500">Master Branch</span>
                </div>
              </div>
            </section>

            {/* Review insights panel */}
            <ReviewPanel result={result} onScrollToLine={scrollToLine} />
          </>
        )}
      </main>

      {/* ════════════════ MOBILE FABs ════════════════ */}
      <div className="absolute bottom-6 right-6 flex flex-col gap-3 lg:hidden z-20">
        <button
          onClick={handleReview}
          disabled={reviewing}
          className="size-12 rounded-full bg-primary text-white shadow-xl flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-50"
          title="Review code"
        >
          <span className={`material-symbols-outlined ${reviewing ? "animate-spin" : ""}`}>
            {reviewing ? "autorenew" : "analytics"}
          </span>
        </button>
        <button
          onClick={() => setShowMobileSidebar(true)}
          className="size-12 rounded-full bg-surface-dark text-white shadow-xl flex items-center justify-center border border-border-dark hover:bg-border-dark transition-colors"
          title="Open session history"
        >
          <span className="material-symbols-outlined">menu</span>
        </button>
      </div>
    </div>
  );
}
