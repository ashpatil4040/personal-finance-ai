import { Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Transaction } from "@/lib/api";
import { currency, formatDate } from "@/lib/format";

const CATEGORY_TONE: Record<string, string> = {
  Income: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  Groceries: "bg-lime-100 text-lime-700 dark:bg-lime-950 dark:text-lime-300",
  Dining: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  Transport: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  Housing: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  Utilities: "bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300",
  Entertainment: "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950 dark:text-fuchsia-300",
  Shopping: "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
  Health: "bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300",
};

export function TransactionsTable({
  transactions,
  onDelete,
  compact = false,
}: {
  transactions: Transaction[];
  onDelete?: (id: number) => void;
  compact?: boolean;
}) {
  if (!transactions.length) {
    return (
      <p className="text-sm text-muted-foreground py-10 text-center">
        No transactions yet. Upload a statement to get started.
      </p>
    );
  }
  return (
    <Table className="w-full table-fixed">
      <TableHeader>
        <TableRow>
          {!compact && <TableHead className="w-28">Date</TableHead>}
          <TableHead>Description</TableHead>
          {!compact && <TableHead className="w-32">Category</TableHead>}
          <TableHead className="w-28 text-right">Amount</TableHead>
          {onDelete && <TableHead className="w-10" />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {transactions.map((t) => (
          <TableRow key={t.id}>
            {!compact && (
              <TableCell className="whitespace-nowrap text-muted-foreground">{formatDate(t.date)}</TableCell>
            )}
            <TableCell className="max-w-0 truncate font-medium" title={t.description}>
              {t.description}
              {compact && (
                <span className="ml-2 text-xs font-normal text-muted-foreground">{t.category}</span>
              )}
            </TableCell>
            {!compact && (
              <TableCell>
                <Badge variant="secondary" className={CATEGORY_TONE[t.category] ?? ""}>
                  {t.category}
                </Badge>
              </TableCell>
            )}
            <TableCell
              className={`whitespace-nowrap text-right tabular-nums font-medium ${t.amount < 0 ? "text-rose-600" : "text-emerald-600"}`}
            >
              {currency(t.amount)}
            </TableCell>
            {onDelete && (
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-muted-foreground hover:text-rose-600"
                  onClick={() => onDelete(t.id)}
                  aria-label="Delete transaction"
                >
                  <Trash2 className="size-4" />
                </Button>
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
