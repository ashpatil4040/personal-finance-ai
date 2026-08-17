import type { Insights } from "../api";

const fmt = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export function StatCards({ summary }: { summary: Insights["summary"] }) {
  return (
    <div className="grid stats">
      <div className="card stat">
        <div className="label">Income</div>
        <div className="value pos">{fmt(summary.total_income)}</div>
      </div>
      <div className="card stat">
        <div className="label">Spending</div>
        <div className="value neg">{fmt(summary.total_spending)}</div>
      </div>
      <div className="card stat">
        <div className="label">Net</div>
        <div className={`value ${summary.net >= 0 ? "pos" : "neg"}`}>
          {fmt(summary.net)}
        </div>
      </div>
      <div className="card stat">
        <div className="label">Savings Rate</div>
        <div className="value">{summary.savings_rate.toFixed(0)}%</div>
      </div>
    </div>
  );
}
