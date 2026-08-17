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
import type { Insights } from "@/lib/api";
import { currency, currencyShort } from "@/lib/format";

const COLORS = [
  "#6366f1",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#a855f7",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
  "#94a3b8",
];

const tooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--popover-foreground)",
  fontSize: 12,
};

export function CategoryChart({ data }: { data: Insights["spending_by_category"] }) {
  if (!data.length) {
    return <p className="text-sm text-muted-foreground py-12 text-center">No spending recorded yet.</p>;
  }
  return (
    <div className="flex flex-col sm:flex-row items-center gap-4">
      <ResponsiveContainer width="100%" height={220} className="max-w-[260px]">
        <PieChart>
          <Pie data={data} dataKey="amount" nameKey="category" innerRadius={58} outerRadius={95} paddingAngle={2}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="var(--card)" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number, n: string) => [currency(v), n]} contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="flex-1 w-full space-y-1.5">
        {data.slice(0, 6).map((d, i) => (
          <li key={d.category} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <span className="size-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
              {d.category}
            </span>
            <span className="font-medium tabular-nums">{currency(d.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function MonthlyChart({ data }: { data: Insights["monthly_spending"] }) {
  if (!data.length) {
    return <p className="text-sm text-muted-foreground py-12 text-center">No monthly data yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <XAxis dataKey="month" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
        <YAxis stroke="var(--muted-foreground)" fontSize={12} tickFormatter={currencyShort} tickLine={false} axisLine={false} width={48} />
        <Tooltip
          formatter={(v: number) => [currency(v), "Spending"]}
          contentStyle={tooltipStyle}
          cursor={{ fill: "var(--accent)" }}
        />
        <Bar dataKey="amount" fill="#6366f1" radius={[6, 6, 0, 0]} maxBarSize={56} />
      </BarChart>
    </ResponsiveContainer>
  );
}
