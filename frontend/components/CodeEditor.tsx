"use client";
import dynamic from "next/dynamic";
import type * as Monaco from "monaco-editor";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 bg-slate-100 dark:bg-[#0d1117] flex items-center justify-center">
      <span className="material-symbols-outlined text-slate-400 dark:text-slate-600 text-4xl animate-spin">autorenew</span>
    </div>
  ),
});

interface CodeEditorProps {
  value: string;
  language: string;
  onChange: (val: string) => void;
  onMount?: (editor: Monaco.editor.IStandaloneCodeEditor) => void;
  onCursorChange?: (line: number, col: number) => void;
  isDark?: boolean;
}

export default function CodeEditor({
  value,
  language,
  onChange,
  onMount,
  onCursorChange,
  isDark = true,
}: CodeEditorProps) {
  return (
    <MonacoEditor
      height="100%"
      language={language}
      value={value}
      onChange={(v) => onChange(v || "")}
      theme={isDark ? "vs-dark" : "vs"}
      onMount={(editor) => {
        onMount?.(editor);
        editor.onDidChangeCursorPosition((e) => {
          onCursorChange?.(e.position.lineNumber, e.position.column);
        });
      }}
      options={{
        fontSize: 14,
        fontFamily: "'Fira Code', monospace",
        fontLigatures: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        lineNumbers: "on",
        renderLineHighlight: "gutter",
        padding: { top: 12, bottom: 12 },
        smoothScrolling: true,
        cursorSmoothCaretAnimation: "on",
        bracketPairColorization: { enabled: true },
        wordWrap: "on",
        tabSize: 4,
        automaticLayout: true,
        scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
      }}
    />
  );
}
