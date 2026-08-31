import { ArrowDownRight, ArrowUpRight, Lightbulb, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Digest } from "@/lib/api";
import { currency } from "@/lib/format";

export function MonthlyDigest({ digest }: { digest: Digest }) {
  const movers = digest.facts.category_movers ?? [];
  return (
    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="size-4 text-primary" />
          Monthly digest
          {digest.facts.month && (
            <span className="ml-1 text-xs font-normal text-muted-foreground">
              {digest.facts.month}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-relaxed">{digest.narrative}</p>

        {movers.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {movers.map((m) => {
              const up = m.delta > 0;
              return (
                <span
                  key={m.category}
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                    up
                      ? "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
                      : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                  }`}
                >
                  {up ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}
                  {m.category} {up ? "+" : "-"}
                  {currency(Math.abs(m.delta))}
                </span>
              );
            })}
          </div>
        )}

        {digest.recommendations.length > 0 && (
          <ul className="space-y-1.5">
            {digest.recommendations.map((r, i) => (
              <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                <Lightbulb className="mt-0.5 size-3.5 shrink-0 text-amber-500" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
