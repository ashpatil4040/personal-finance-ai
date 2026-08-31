import { AlertTriangle, ShieldAlert, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Anomalies } from "@/lib/api";
import { currency, formatDate } from "@/lib/format";

const KIND_LABEL: Record<string, string> = {
  duplicate: "Duplicate",
  amount_outlier: "Outlier",
  new_merchant: "New merchant",
};

export function AnomaliesCard({ data }: { data: Anomalies }) {
  const empty = data.count === 0;
  return (
    <Card className={empty ? "" : "border-amber-300/60 bg-gradient-to-br from-amber-50 to-transparent dark:from-amber-950/30"}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {empty ? (
            <ShieldCheck className="size-4 text-emerald-600" />
          ) : (
            <ShieldAlert className="size-4 text-amber-600" />
          )}
          Unusual activity
          <Badge variant={empty ? "secondary" : "destructive"}>{data.count}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{data.summary}</p>
        {!empty && (
          <ul className="space-y-2.5">
            {data.anomalies.map((a, i) => (
              <li
                key={`${a.kind}-${a.date}-${a.description}-${i}`}
                className="flex gap-3 rounded-lg border bg-background/80 px-3 py-2.5"
              >
                <AlertTriangle
                  className={`mt-0.5 size-4 shrink-0 ${
                    a.severity === "high" ? "text-rose-500" : "text-amber-500"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium">{a.description}</span>
                    <Badge variant="outline">{KIND_LABEL[a.kind] ?? a.kind}</Badge>
                    <span className="text-xs text-muted-foreground">{formatDate(a.date)}</span>
                  </div>
                  <p className="mt-0.5 text-sm tabular-nums text-rose-600">{currency(a.amount)}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{a.reason}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
