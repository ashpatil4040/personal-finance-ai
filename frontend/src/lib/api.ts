export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Account {
  id: number;
  name: string;
  type: string;
  institution: string;
  created_at: string;
}

export interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  category: string;
  account_id: number | null;
  statement_id: number | null;
}

export interface Insights {
  summary: {
    total_income: number;
    total_spending: number;
    net: number;
    savings_rate: number;
    transaction_count: number;
  };
  spending_by_category: { category: string; amount: number }[];
  monthly_spending: { month: string; amount: number }[];
  insights: string[];
}

export interface UploadResult {
  statement_id: number;
  filename: string;
  imported: number;
  account_id: number | null;
  method: string;
}

export interface AskResponse {
  answer: string;
  tools_used: string[];
  grounded: boolean;
}

export interface Digest {
  has_data: boolean;
  narrative: string;
  recommendations: string[];
  facts: {
    month?: string;
    previous_month?: string | null;
    total_spending?: number;
    spend_change_pct?: number | null;
    savings_rate?: number | null;
    top_category?: { category: string; amount: number } | null;
    category_movers?: { category: string; delta: number }[];
    largest_transactions?: { description: string; amount: number; category: string }[];
  };
}

const TOKEN_KEY = "pfai_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = tokenStore.get();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...options, headers });
  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? (detail[0]?.msg ?? "Request failed")
          : `Request failed (${res.status})`;
    throw new ApiError(res.status, message);
  }
  return data as T;
}

export const api = {
  register: (body: { email: string; password: string; full_name?: string }) =>
    request<AuthResponse>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request<User>("/api/auth/me"),

  listAccounts: () => request<Account[]>("/api/accounts"),

  listTransactions: (params?: { category?: string; account_id?: number }) => {
    const q = new URLSearchParams();
    if (params?.category) q.set("category", params.category);
    if (params?.account_id != null) q.set("account_id", String(params.account_id));
    const qs = q.toString();
    return request<Transaction[]>(`/api/transactions${qs ? `?${qs}` : ""}`);
  },
  createTransaction: (body: {
    date: string;
    description: string;
    amount: number;
    account_id?: number | null;
  }) => request<Transaction>("/api/transactions", { method: "POST", body: JSON.stringify(body) }),
  deleteTransaction: (id: number) =>
    request<void>(`/api/transactions/${id}`, { method: "DELETE" }),

  insights: () => request<Insights>("/api/insights"),

  ask: (question: string) =>
    request<AskResponse>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  digest: () => request<Digest>("/api/digest"),

  upload: (file: File, accountId?: number | null) => {
    const form = new FormData();
    form.append("file", file);
    if (accountId != null) form.append("account_id", String(accountId));
    return request<UploadResult>("/api/uploads", { method: "POST", body: form });
  },
};

export { ApiError };
