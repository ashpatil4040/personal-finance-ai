import { PiggyBank, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { Insights } from "@/lib/api";
import { currency } from "@/lib/format";

function Stat({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  tone?: "up" | "down" | "neutral";
}) {
  const toneClass =
    tone === "up" ? "text-emerald-600" : tone === "down" ? "text-rose-600" : "text-foreground";
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex size-11 items-center justify-center rounded-xl bg-muted text-muted-foreground">
          {icon}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className={`text-2xl font-semibold tabular-nums ${toneClass}`}>{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function StatCards({ summary }: { summary: Insights["summary"] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Income" value={currency(summary.total_income)} icon={<TrendingUp className="size-5" />} tone="up" />
      <Stat label="Spending" value={currency(summary.total_spending)} icon={<TrendingDown className="size-5" />} tone="down" />
      <Stat
        label="Net"
        value={currency(summary.net)}
        icon={<Wallet className="size-5" />}
        tone={summary.net >= 0 ? "up" : "down"}
      />
      <Stat label="Savings Rate" value={`${summary.savings_rate.toFixed(0)}%`} icon={<PiggyBank className="size-5" />} />
    </div>
  );
}
