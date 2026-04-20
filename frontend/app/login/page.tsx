"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login(email, password);
      localStorage.setItem("token", res.access_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background-dark font-display flex flex-col">
      {/* Header */}
      <header className="flex items-center px-6 py-4 border-b border-border-dark">
        <div className="flex items-center gap-2 text-primary">
          <span className="material-symbols-outlined text-3xl">terminal</span>
          <h2 className="text-xl font-bold tracking-tight">SafeCodeAI</h2>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Card */}
          <div className="bg-surface-dark border border-border-dark rounded-xl p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="size-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-xl">lock</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-100">Welcome back</h1>
                <p className="text-xs text-slate-400">Sign in to continue reviewing code</p>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-3 mb-5 text-sm">
                <span className="material-symbols-outlined text-sm">error</span>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  className="w-full bg-background-dark border border-border-dark rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                  placeholder="you@example.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPass ? "text" : "password"}
                    className="w-full bg-background-dark border border-border-dark rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
                    placeholder="••••••••"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm">
                      {showPass ? "visibility_off" : "visibility"}
                    </span>
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 flex items-center justify-center gap-2 bg-primary text-white rounded-lg font-bold text-sm hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined text-sm animate-spin">autorenew</span>
                    Signing in...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-sm">login</span>
                    Sign in
                  </>
                )}
              </button>
            </form>

            <p className="text-center text-xs text-slate-400 mt-6">
              Don&apos;t have an account?{" "}
              <Link href="/signup" className="text-primary font-semibold hover:text-primary/80 transition-colors">
                Sign up for free
              </Link>
            </p>
          </div>

          {/* Features */}
          <div className="grid grid-cols-3 gap-3 mt-6">
            {[
              { icon: "security", label: "Security Analysis" },
              { icon: "speed", label: "Instant Feedback" },
              { icon: "history", label: "Full History" },
            ].map((f) => (
              <div
                key={f.label}
                className="bg-surface-dark border border-border-dark rounded-xl p-3 flex flex-col items-center gap-2 text-center"
              >
                <span className="material-symbols-outlined text-primary text-xl">{f.icon}</span>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{f.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
