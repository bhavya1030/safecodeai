const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: { id: number; email: string; username: string };
}

export interface ReviewResult {
  confidence: number;
  syntax_error: boolean;
  error_line: number | null;
  error_msg: string;
  issues: [string, number, string][];
  complexity: number;
}

export interface ReviewResponse {
  id: number;
  result: ReviewResult;
  created_at: string;
}

export interface HistoryItem {
  id: number;
  filename: string;
  result: ReviewResult;
  created_at: string;
  code: string;
}

export const api = {
  signup: (email: string, username: string, password: string) =>
    request<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  review: (code: string, filename: string, language?: string) =>
    request<ReviewResponse>("/api/review", {
      method: "POST",
      body: JSON.stringify({ code, filename, language }),
    }),

  getHistory: () => request<HistoryItem[]>("/api/reviews"),
};
