import { Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function InsightsPanel({ insights }: { insights: string[] }) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="size-4 text-indigo-500" />
          AI Insights
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {insights.map((line, i) => (
            <li key={i} className="flex gap-2.5 text-sm leading-relaxed">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-indigo-500" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
