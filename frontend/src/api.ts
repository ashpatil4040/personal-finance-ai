export interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  category: string;
}

export interface NewTransaction {
  date: string;
  description: string;
  amount: number;
  category?: string | null;
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

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listTransactions: () =>
    fetch("/api/transactions").then((r) => json<Transaction[]>(r)),
  createTransaction: (t: NewTransaction) =>
    fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(t),
    }).then((r) => json<Transaction>(r)),
  deleteTransaction: (id: number) =>
    fetch(`/api/transactions/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new Error(`Delete failed: ${r.status}`);
    }),
  insights: () => fetch("/api/insights").then((r) => json<Insights>(r)),
};
