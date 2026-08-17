import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Insights } from "../api";

const COLORS = [
  "#5b8def",
  "#3ecf8e",
  "#f2b45b",
  "#f2617a",
  "#a97bf0",
  "#4dd0e1",
  "#e0e0e0",
  "#ff8a65",
  "#9ccc65",
];

const currency = (n: number) => `$${n.toFixed(0)}`;

export function CategoryChart({
  data,
}: {
  data: Insights["spending_by_category"];
}) {
  if (!data.length) return <p className="hint">No spending recorded yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey="amount"
          nameKey="category"
          innerRadius={55}
          outerRadius={95}
          paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v: number, n: string) => [currency(v), n]}
          contentStyle={{ background: "#1f2937", border: "1px solid #2a3547" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function MonthlyChart({
  data,
}: {
  data: Insights["monthly_spending"];
}) {
  if (!data.length) return <p className="hint">No monthly data yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <XAxis dataKey="month" stroke="#93a1b5" fontSize={12} />
        <YAxis stroke="#93a1b5" fontSize={12} tickFormatter={currency} />
        <Tooltip
          formatter={(v: number) => [currency(v), "Spending"]}
          contentStyle={{ background: "#1f2937", border: "1px solid #2a3547" }}
          cursor={{ fill: "rgba(91,141,239,0.1)" }}
        />
        <Bar dataKey="amount" fill="#5b8def" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
