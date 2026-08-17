import { useEffect, useState } from "react";
import { api, type Insights, type Transaction } from "./api";
import { CategoryChart, MonthlyChart } from "./components/Charts";
import { StatCards } from "./components/StatCards";

const today = () => new Date().toISOString().slice(0, 10);

const fmtAmount = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function App() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [date, setDate] = useState(today());
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");

  async function refresh() {
    try {
      const [txns, ins] = await Promise.all([
        api.listTransactions(),
        api.insights(),
      ]);
      setTransactions(txns);
      setInsights(ins);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    const value = parseFloat(amount);
    if (!description.trim() || Number.isNaN(value)) {
      setError("Enter a description and a numeric amount.");
      return;
    }
    try {
      await api.createTransaction({ date, description: description.trim(), amount: value });
      setDescription("");
      setAmount("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function onDelete(id: number) {
    try {
      await api.deleteTransaction(id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="app">
      <div className="header">
        <span className="logo">💸</span>
        <div>
          <h1>Personal Finance AI</h1>
          <p>Track spending and get AI-powered insights on your money.</p>
        </div>
      </div>

      {error && <p className="error">⚠ {error}</p>}

      {insights && <StatCards summary={insights.summary} />}

      <div className="grid cols" style={{ marginTop: 16 }}>
        <div className="card">
          <h2>Add a transaction</h2>
          <form className="add" onSubmit={onAdd}>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              aria-label="date"
            />
            <input
              placeholder="Description (e.g. Starbucks Coffee)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              aria-label="description"
            />
            <input
              placeholder="Amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              aria-label="amount"
            />
            <button className="primary" type="submit">
              Add
            </button>
          </form>
          <p className="hint">
            Tip: negative amounts are expenses, positive are income. The category
            is predicted automatically.
          </p>

          <h2 style={{ marginTop: 8 }}>Transactions</h2>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description}</td>
                  <td>
                    <span className="pill">{t.category}</span>
                  </td>
                  <td className="amount" style={{ color: t.amount < 0 ? "var(--red)" : "var(--green)" }}>
                    {fmtAmount(t.amount)}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="del" title="Delete" onClick={() => onDelete(t.id)}>
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid" style={{ gap: 16 }}>
          <div className="card insights">
            <span className="badge">AI INSIGHTS</span>
            <ul style={{ paddingLeft: 18, margin: 0 }}>
              {insights?.insights.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h2>Spending by category</h2>
            {insights && <CategoryChart data={insights.spending_by_category} />}
          </div>
          <div className="card">
            <h2>Monthly spending</h2>
            {insights && <MonthlyChart data={insights.monthly_spending} />}
          </div>
        </div>
      </div>
    </div>
  );
}
